from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime
from pathlib import Path

import httpx

from ..config import CityConfig
from ..provenance import persist_snapshot
from .salvador_portal import BASE_URL, PUBLIC_PORTAL, SOURCE_SYSTEM, parse_brl

ENDPOINT = "/aquisicao/gridDetalhada"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Origin": PUBLIC_PORTAL.rstrip("/"),
        "Referer": PUBLIC_PORTAL,
        "User-Agent": "municipal-transparency-research/0.2 (+public-data-audit)",
    }


def _iso_br_date(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return text


def stable_source_key(row: dict) -> str:
    """Internal deduplication key; not an official identifier."""
    parts = [
        str(row.get("nuProcesso") or ""),
        str(row.get("nuModalidadeSigef") or ""),
        str(row.get("nuAquisicao") or ""),
        str(row.get("cdUnidadeGestora") or ""),
        str(row.get("dtPublicacao") or ""),
        str(row.get("vlAquisicao") or ""),
        str(row.get("dsObjeto") or ""),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalize(row: dict, city: CityConfig, *, observed_at: str, snapshot_sha256: str) -> dict:
    publication = _iso_br_date(row.get("dtPublicacao"))
    acquisition_date = _iso_br_date(row.get("dtAquisicao"))
    modality_id = row.get("cdModalidadeLicitacao")
    try:
        modality_id = int(modality_id) if modality_id not in (None, "") else None
    except (TypeError, ValueError):
        modality_id = None
    year = None
    if publication and len(publication) >= 4 and publication[:4].isdigit():
        year = int(publication[:4])
    return {
        "city_slug": city.slug,
        "source_system": SOURCE_SYSTEM,
        "source_record_key": stable_source_key(row),
        "source_record_id_observed": row.get("id"),
        "process_number": row.get("nuProcesso"),
        "notice_number": row.get("nuModalidadeSigef"),
        "acquisition_number": row.get("nuAquisicao"),
        "year": year,
        "modality_id": modality_id,
        "modality_name": row.get("dsModalidadeLicitacao"),
        "acquisition_type": row.get("dsTipoAquisica"),
        "direct_purchase_basis": row.get("dsFundamentacaoCompraDireta"),
        "object": row.get("dsObjeto"),
        "agency_code": row.get("cdOrgao"),
        "agency_name": row.get("dsOrgao"),
        "agency_abbreviation": row.get("sgOrgao"),
        "unit_code": row.get("cdUnidadeGestora"),
        "unit_name": row.get("dsUnidadeGestora"),
        "dom_number": row.get("nuDom"),
        "published_at": publication,
        "acquisition_at": acquisition_date,
        "acquisition_value": parse_brl(row.get("vlAquisicao")),
        "municipality_ibge": city.ibge_code,
        "municipality_name": city.name,
        "uf": city.uf,
        "source_url": PUBLIC_PORTAL,
        "api_endpoint": BASE_URL + ENDPOINT,
        "observed_at": observed_at,
        "snapshot_sha256": snapshot_sha256,
    }


def _fetch_page(
    client: httpx.Client,
    *,
    url: str,
    payload: dict,
    page: int,
    max_attempts: int = 7,
) -> tuple[httpx.Response, int]:
    last_response: httpx.Response | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.post(url, json=payload)
            last_response = response
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == max_attempts:
                raise
            time.sleep(min(0.75 * (2 ** (attempt - 1)), 12.0))
            continue
        if response.status_code not in RETRYABLE_STATUS:
            response.raise_for_status()
            return response, attempt
        if attempt == max_attempts:
            response.raise_for_status()
        retry_after = response.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after else min(0.75 * (2 ** (attempt - 1)), 12.0)
        except ValueError:
            delay = min(0.75 * (2 ** (attempt - 1)), 12.0)
        time.sleep(delay)
    assert last_response is not None
    last_response.raise_for_status()
    return last_response, max_attempts


def collect(city: CityConfig, start: date, end: date, out_dir: Path, *, sleep_seconds: float = 0.08) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    payload = {
        "dataInicio": start.isoformat(),
        "dataFim": end.isoformat(),
        "agrupamentos": [],
        "filtros": [],
    }
    rows: list[dict] = []
    page_meta: list[dict] = []
    expected_total = None
    expected_pages = None
    official_total_value = None

    with httpx.Client(headers=_headers(), follow_redirects=True, timeout=60.0) as client:
        page = 1
        while True:
            url = f"{BASE_URL}{ENDPOINT}?pagina={page}"
            response, attempts = _fetch_page(client, url=url, payload=payload, page=page)
            meta = persist_snapshot(
                out_dir=raw_dir,
                source_id=f"salvador_aquisicoes_p{page:04d}",
                requested_url=url,
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=response.headers.get("content-type", "application/json"),
                body=response.content,
            )
            data = response.json()
            pagination = data.get("paginacao") or {}
            if page == 1:
                expected_total = int(pagination.get("total") or 0)
                expected_pages = int(pagination.get("paginas") or 0)
                official_total_value = (data.get("totalizadores") or {}).get("Valor")
            else:
                current_total = int(pagination.get("total") or 0)
                current_pages = int(pagination.get("paginas") or 0)
                if current_total != expected_total or current_pages != expected_pages:
                    raise RuntimeError(
                        f"pagination changed during collection on page {page}: "
                        f"expected total/pages {expected_total}/{expected_pages}, got {current_total}/{current_pages}"
                    )
            page_rows = data.get("dados") or []
            rows.extend(normalize(row, city, observed_at=meta.collected_at, snapshot_sha256=meta.sha256) for row in page_rows)
            page_meta.append({
                "page": page,
                "rows": len(page_rows),
                "sha256": meta.sha256,
                "status_code": meta.status_code,
                "final_url": meta.final_url,
                "attempts": attempts,
            })
            if expected_pages is None or page >= expected_pages:
                break
            page += 1
            if sleep_seconds:
                time.sleep(sleep_seconds)

    unique: dict[str, dict] = {}
    duplicate_keys: list[str] = []
    for row in rows:
        key = row["source_record_key"]
        if key in unique:
            duplicate_keys.append(key)
        unique[key] = row
    normalized = list(unique.values())

    jsonl = out_dir / "acquisitions.jsonl"
    with jsonl.open("w", encoding="utf-8") as handle:
        for row in normalized:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    completeness = {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_system": SOURCE_SYSTEM,
        "source_url": PUBLIC_PORTAL,
        "api_endpoint": BASE_URL + ENDPOINT,
        "api_reported_total_records": expected_total,
        "api_reported_pages": expected_pages,
        "api_reported_total_value_brl_text": official_total_value,
        "records_received": len(rows),
        "unique_stable_records": len(normalized),
        "duplicate_stable_keys": len(duplicate_keys),
        "pages_collected": len(page_meta),
        "complete_for_filter": bool(expected_total == len(rows) and expected_pages == len(page_meta)),
        "scope_note": "Complete for the unfiltered official Salvador acquisition API and requested date interval; this does not prove completeness across PNCP or independent sectoral systems.",
        "id_note": "The API response field 'id' varied across equivalent requests during discovery. source_record_key is an internal deterministic deduplication key, not an official identifier.",
        "pages": page_meta,
    }
    summary = out_dir / "summary.json"
    summary.write_text(json.dumps(completeness, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"jsonl": jsonl, "summary": summary, "completeness": completeness}
