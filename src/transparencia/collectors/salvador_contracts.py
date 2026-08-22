from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx

from ..config import CityConfig
from ..provenance import persist_snapshot

API_BASE = "https://apitmptransparencia.salvador.ba.gov.br/api"
PUBLIC_PORTAL = "https://transparencia.salvador.ba.gov.br/"
ENDPOINT = "/contratos/gridDetalhada"
SOURCE_SYSTEM = "SALVADOR_TRANSPARENCIA_API_CONTRATOS"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Window:
    start: date
    end: date


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "municipal-transparency-research/0.5 (+public-data-audit)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://transparencia.salvador.ba.gov.br",
        "Referer": PUBLIC_PORTAL,
        "Accept-Language": "pt-BR,pt;q=0.9",
    }


def _request_body(window: Window) -> dict:
    # This shape is required by the current official frontend/API. Omitting the
    # empty grouping/filter arrays caused the endpoint to stall in prior probes.
    return {
        "dataInicio": window.start.isoformat(),
        "dataFim": window.end.isoformat(),
        "agrupamentos": [],
        "filtros": [],
    }


def _records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("dados", "data", "content", "items", "registros"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _pages(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    pagination = payload.get("paginacao")
    if isinstance(pagination, dict):
        for key in ("paginas", "totalPaginas", "totalPages"):
            value = pagination.get(key)
            if isinstance(value, int):
                return value
    for key in ("paginas", "totalPaginas", "totalPages"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def _total(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    pagination = payload.get("paginacao")
    if isinstance(pagination, dict):
        for key in ("total", "quantidadeRegistros", "totalRegistros"):
            value = pagination.get(key)
            if isinstance(value, int):
                return value
    for key in ("total", "quantidadeRegistros", "totalRegistros"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def _stable_record_key(row: dict) -> str:
    """Internal deduplication key that ignores the API's technical UUID field.

    All substantive source fields are retained in the hash. The key is not exposed as
    an official contract identifier and is only used to avoid duplicate rows when an
    adaptive date window overlaps the same contract.
    """
    stable_row = {key: value for key, value in row.items() if key != "id"}
    canonical = json.dumps(stable_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _split(window: Window) -> tuple[Window, Window] | None:
    if window.start >= window.end:
        return None
    days = (window.end - window.start).days
    mid = window.start + timedelta(days=days // 2)
    return Window(window.start, mid), Window(mid + timedelta(days=1), window.end)


def _partition(start: date, end: date, max_days: int) -> list[Window]:
    if max_days < 1:
        raise ValueError("max_days deve ser >= 1")
    if end < start:
        raise ValueError("end anterior a start")
    windows: list[Window] = []
    current = start
    while current <= end:
        current_end = min(current + timedelta(days=max_days - 1), end)
        windows.append(Window(current, current_end))
        current = current_end + timedelta(days=1)
    return windows


def _window_complete(
    *,
    error: str | None,
    pages_collected: int,
    records_received: int,
    reported_pages: int | None,
    reported_total: int | None,
) -> bool:
    if error is not None or reported_pages is None or reported_total is None:
        return False
    pages_ok = reported_pages == 0 or pages_collected >= reported_pages
    return pages_collected > 0 and pages_ok and records_received == reported_total


def _fetch_page(
    client: httpx.Client,
    *,
    url: str,
    payload: dict,
    max_attempts: int,
) -> tuple[httpx.Response, int]:
    last_response: httpx.Response | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.post(url, json=payload)
            last_response = response
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == max_attempts:
                raise
            time.sleep(min(0.5 * (2 ** (attempt - 1)), 3.0))
            continue
        if response.status_code not in RETRYABLE_STATUS:
            response.raise_for_status()
            return response, attempt
        if attempt == max_attempts:
            response.raise_for_status()
        retry_after = response.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after else min(0.5 * (2 ** (attempt - 1)), 3.0)
        except ValueError:
            delay = min(0.5 * (2 ** (attempt - 1)), 3.0)
        time.sleep(delay)
    assert last_response is not None
    last_response.raise_for_status()
    return last_response, max_attempts


def _unattempted_window(window: Window, error: str) -> dict:
    return {
        "start": window.start.isoformat(),
        "end": window.end.isoformat(),
        "completed": False,
        "status": None,
        "pages_collected": 0,
        "records_received": 0,
        "reported_pages": None,
        "reported_total": None,
        "pagination_metadata_complete": False,
        "http_attempts": 0,
        "error": error,
    }


def collect(
    city: CityConfig,
    start: date,
    end: date,
    out_dir: Path,
    *,
    timeout_seconds: float = 35.0,
    initial_window_days: int = 366,
    max_windows: int = 16,
    max_pages_per_window: int = 2000,
    max_attempts: int = 2,
    page_workers: int = 8,
    max_runtime_seconds: float = 600.0,
) -> Path:
    """Collect the official municipal detailed contract grid with strict coverage checks.

    The collector first queries the broadest bounded interval (normally the entire current year).
    Once page/count metadata is known, remaining pages are fetched with moderate concurrency.
    Only if a window fails is it bisected. Completeness requires exact reconciliation with the
    source-reported page and record totals. Timeouts, missing metadata, pagination drift and
    execution-budget exhaustion remain explicit partial coverage and never become zero records.
    """
    if end < start:
        raise ValueError("end anterior a start")
    if max_windows < 1 or page_workers < 1 or max_attempts < 1:
        raise ValueError("max_windows, page_workers e max_attempts devem ser >= 1")
    if max_runtime_seconds <= 0:
        raise ValueError("max_runtime_seconds deve ser > 0")

    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"municipal_contract_grid_{start.isoformat()}_{end.isoformat()}.jsonl"
    queue = _partition(start, end, initial_window_days)
    if len(queue) > max_windows:
        raise ValueError("particionamento inicial excede max_windows")

    terminal_windows: list[dict] = []
    seen: dict[str, dict] = {}
    logical_request_count = 0
    http_attempt_count = 0
    started_at = time.monotonic()
    budget_exhausted = False

    def elapsed() -> float:
        return time.monotonic() - started_at

    def accept_response(
        *,
        response: httpx.Response,
        page: int,
        window: Window,
        url: str,
        expected_pages: int | None,
        expected_total: int | None,
    ) -> tuple[list[dict], int | None, int | None, str | None]:
        meta = persist_snapshot(
            out_dir=out_dir / "raw",
            source_id=f"salvador_contratos_{window.start}_{window.end}_p{page:04d}",
            requested_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", "application/json"),
            body=response.content,
        )
        try:
            payload = response.json() if response.content.strip() else {}
        except Exception as exc:
            return [], expected_pages, expected_total, f"InvalidJSON: {exc}"
        rows = _records(payload)
        current_pages = _pages(payload)
        current_total = _total(payload)
        if page == 1:
            expected_pages = current_pages
            expected_total = current_total
        elif current_pages != expected_pages or current_total != expected_total:
            return (
                [],
                expected_pages,
                expected_total,
                "PaginationChanged: "
                f"expected pages/total {expected_pages}/{expected_total}, "
                f"got {current_pages}/{current_total} on page {page}",
            )
        for raw in rows:
            key = _stable_record_key(raw)
            seen.setdefault(key, {
                "city_slug": city.slug,
                "source_system": SOURCE_SYSTEM,
                "source_record_key": key,
                "source_record_key_note": "Internal SHA-256 excluding the API technical id field; not an official contract identifier.",
                "filter_start": window.start.isoformat(),
                "filter_end": window.end.isoformat(),
                "source_record": raw,
                "source_url": PUBLIC_PORTAL,
                "api_endpoint": url,
                "observed_at": meta.collected_at,
                "snapshot_sha256": meta.sha256,
            })
        return rows, expected_pages, expected_total, None

    with httpx.Client(headers=_headers(), follow_redirects=True, timeout=timeout_seconds) as client:
        while queue:
            window = queue.pop(0)
            if elapsed() >= max_runtime_seconds:
                terminal_windows.append(_unattempted_window(window, "CollectorBudgetExceededBeforeRequest"))
                terminal_windows.extend(_unattempted_window(p, "CollectorBudgetExceededBeforeRequest") for p in queue)
                queue.clear()
                budget_exhausted = True
                break

            body = _request_body(window)
            window_rows = 0
            window_pages = 0
            window_attempts = 0
            reported_pages: int | None = None
            reported_total: int | None = None
            error: str | None = None
            status: int | None = None

            first_url = f"{API_BASE}{ENDPOINT}?pagina=1"
            logical_request_count += 1
            try:
                response, attempts = _fetch_page(client, url=first_url, payload=body, max_attempts=max_attempts)
                window_attempts += attempts
                http_attempt_count += attempts
                status = response.status_code
                rows, reported_pages, reported_total, error = accept_response(
                    response=response,
                    page=1,
                    window=window,
                    url=first_url,
                    expected_pages=None,
                    expected_total=None,
                )
                if error is None:
                    window_pages = 1
                    window_rows = len(rows)
            except Exception as exc:
                window_attempts += max_attempts
                http_attempt_count += max_attempts
                error = f"{type(exc).__name__}: {exc}"

            if error is None and reported_pages is not None and reported_pages > max_pages_per_window:
                error = f"PageLimitExceeded: reported_pages={reported_pages} limit={max_pages_per_window}"

            if error is None and reported_pages is not None and reported_pages > 1:
                remaining_pages = list(range(2, reported_pages + 1))
                batch_size = max(page_workers, page_workers * 4)
                for offset in range(0, len(remaining_pages), batch_size):
                    if elapsed() >= max_runtime_seconds:
                        error = "CollectorBudgetExceeded"
                        budget_exhausted = True
                        break
                    batch = remaining_pages[offset: offset + batch_size]
                    with ThreadPoolExecutor(max_workers=page_workers) as executor:
                        futures = {}
                        for page in batch:
                            url = f"{API_BASE}{ENDPOINT}?pagina={page}"
                            logical_request_count += 1
                            future = executor.submit(
                                _fetch_page,
                                client,
                                url=url,
                                payload=body,
                                max_attempts=max_attempts,
                            )
                            futures[future] = (page, url)
                        for future in as_completed(futures):
                            page, url = futures[future]
                            try:
                                response, attempts = future.result()
                                window_attempts += attempts
                                http_attempt_count += attempts
                                rows, _, _, page_error = accept_response(
                                    response=response,
                                    page=page,
                                    window=window,
                                    url=url,
                                    expected_pages=reported_pages,
                                    expected_total=reported_total,
                                )
                                if page_error:
                                    error = page_error if error is None else f"{error}; {page_error}"
                                else:
                                    window_pages += 1
                                    window_rows += len(rows)
                            except Exception as exc:
                                window_attempts += max_attempts
                                http_attempt_count += max_attempts
                                page_error = f"page {page}: {type(exc).__name__}: {exc}"
                                error = page_error if error is None else f"{error}; {page_error}"
                    if error is not None:
                        break

            completed = _window_complete(
                error=error,
                pages_collected=window_pages,
                records_received=window_rows,
                reported_pages=reported_pages,
                reported_total=reported_total,
            )

            if not completed and not budget_exhausted and len(terminal_windows) + len(queue) + 2 <= max_windows:
                parts = _split(window)
                if parts:
                    queue[0:0] = list(parts)
                    continue

            terminal_windows.append({
                "start": window.start.isoformat(),
                "end": window.end.isoformat(),
                "completed": completed,
                "status": status,
                "pages_collected": window_pages,
                "records_received": window_rows,
                "reported_pages": reported_pages,
                "reported_total": reported_total,
                "pagination_metadata_complete": reported_pages is not None and reported_total is not None,
                "http_attempts": window_attempts,
                "error": error,
            })

            if budget_exhausted:
                terminal_windows.extend(_unattempted_window(p, "CollectorBudgetExceededBeforeRequest") for p in queue)
                queue.clear()

    runtime_seconds = round(elapsed(), 3)
    with output.open("w", encoding="utf-8") as handle:
        for row in seen.values():
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    complete = bool(terminal_windows) and all(item["completed"] for item in terminal_windows)
    coverage = {
        "source_system": SOURCE_SYSTEM,
        "source_url": PUBLIC_PORTAL,
        "api_endpoint": f"{API_BASE}{ENDPOINT}",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "records_unique": len(seen),
        "logical_page_requests": logical_request_count,
        "http_attempts": http_attempt_count,
        "runtime_seconds": runtime_seconds,
        "max_runtime_seconds": max_runtime_seconds,
        "budget_exhausted": budget_exhausted,
        "initial_window_days": initial_window_days,
        "page_workers": page_workers,
        "max_windows": max_windows,
        "request_body_shape": ["dataInicio", "dataFim", "agrupamentos", "filtros"],
        "windows": terminal_windows,
        "complete_for_filter": complete,
        "coverage_note": (
            "Complete only for the official municipal contract grid and the requested date filter: every adaptive interval reconciled explicit source-reported page and record totals."
            if complete else
            "Partial: at least one adaptive interval did not reconcile explicit source pagination/count metadata. Successful source responses are preserved; timeout, missing metadata, execution-budget exhaustion and failed intervals are never converted to zero."
        ),
        "semantics_note": "The date interval is passed exactly as ISO dates accepted by the source. Source rows are preserved without renaming unknown fields. The internal deduplication key is not an official identifier.",
    }
    (out_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
