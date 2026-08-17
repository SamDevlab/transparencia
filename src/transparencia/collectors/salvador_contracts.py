from __future__ import annotations

import hashlib
import json
import time
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


@dataclass(frozen=True)
class Window:
    start: date
    end: date


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "municipal-transparency-research/0.3 (+public-data-audit)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://transparencia.salvador.ba.gov.br",
        "Referer": PUBLIC_PORTAL,
        "Accept-Language": "pt-BR,pt;q=0.9",
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
    # Internal deduplication only. It is not represented as an official contract identifier.
    canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _split(window: Window) -> tuple[Window, Window] | None:
    if window.start >= window.end:
        return None
    days = (window.end - window.start).days
    mid = window.start + timedelta(days=days // 2)
    return Window(window.start, mid), Window(mid + timedelta(days=1), window.end)


def collect(
    city: CityConfig,
    start: date,
    end: date,
    out_dir: Path,
    *,
    timeout_seconds: float = 30.0,
    max_windows: int = 32,
    max_pages_per_window: int = 2000,
) -> Path:
    """Attempt the official municipal detailed contract grid without inventing completeness.

    The frontend-observed request is POST /contratos/gridDetalhada?pagina=N with the filter object as
    JSON body. Large intervals can time out; failed intervals are bisected up to `max_windows`.
    Coverage is complete_for_filter only when every final window completed and each source-reported
    page/count check closed. Otherwise persisted successful rows remain valid and coverage is partial.
    """
    if end < start:
        raise ValueError("end anterior a start")
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"municipal_contract_grid_{start.isoformat()}_{end.isoformat()}.jsonl"
    queue: list[Window] = [Window(start, end)]
    terminal_windows: list[dict] = []
    seen: dict[str, dict] = {}
    request_count = 0

    with httpx.Client(headers=_headers(), follow_redirects=True, timeout=timeout_seconds) as client:
        while queue:
            window = queue.pop(0)
            body = {"dataInicio": window.start.isoformat(), "dataFim": window.end.isoformat()}
            page = 1
            window_rows = 0
            window_pages = 0
            reported_pages: int | None = None
            reported_total: int | None = None
            error: str | None = None
            status: int | None = None

            while page <= max_pages_per_window:
                request_count += 1
                url = f"{API_BASE}{ENDPOINT}?pagina={page}"
                try:
                    response = client.post(url, json=body)
                    status = response.status_code
                    if status in {429, 500, 502, 503, 504}:
                        time.sleep(min(2 ** min(page, 4), 10))
                        response = client.post(url, json=body)
                        status = response.status_code
                    response.raise_for_status()
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    break

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
                    error = f"InvalidJSON: {exc}"
                    break

                rows = _records(payload)
                if reported_pages is None:
                    reported_pages = _pages(payload)
                if reported_total is None:
                    reported_total = _total(payload)
                window_pages += 1
                window_rows += len(rows)
                for raw in rows:
                    key = _stable_record_key(raw)
                    seen.setdefault(key, {
                        "city_slug": city.slug,
                        "source_system": SOURCE_SYSTEM,
                        "source_record_key": key,
                        "source_record_key_note": "Internal SHA-256 of the complete source row for deduplication; not an official contract identifier.",
                        "filter_start": window.start.isoformat(),
                        "filter_end": window.end.isoformat(),
                        "source_record": raw,
                        "source_url": PUBLIC_PORTAL,
                        "api_endpoint": url,
                        "observed_at": meta.collected_at,
                        "snapshot_sha256": meta.sha256,
                    })

                if not rows:
                    break
                if reported_pages is not None and page >= reported_pages:
                    break
                page += 1

            completed = error is None and (
                window_pages > 0
                and (
                    reported_pages is None
                    or window_pages >= reported_pages
                )
                and (
                    reported_total is None
                    or window_rows >= reported_total
                )
            )

            if not completed and error and len(terminal_windows) + len(queue) + 2 <= max_windows:
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
                "error": error,
            })

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
        "request_count": request_count,
        "windows": terminal_windows,
        "complete_for_filter": complete,
        "coverage_note": (
            "Complete only for the official municipal contract grid and the requested date filter: every adaptive interval and source-reported pagination/count check completed."
            if complete else
            "Partial: at least one adaptive interval of the official municipal detailed contract grid did not complete. Successful source responses are preserved; zero is never inferred for failed intervals."
        ),
        "semantics_note": "source_record is preserved without renaming unknown municipal fields. The internal source_record_key is not an official identifier.",
    }
    (out_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
