from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

import httpx

from ..config import CityConfig
from ..provenance import persist_snapshot
from .pncp import date_windows

PNCP_CONTRACTS_ENDPOINT = "https://pncp.gov.br/api/consulta/v1/contratos"
RETRYABLE = {429, 500, 502, 503, 504}


def agency_cnpjs_from_procurements(paths: Iterable[Path]) -> tuple[str, ...]:
    values: set[str] = set()
    for path in paths:
        if not path or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            cnpj = "".join(ch for ch in str(row.get("agency_cnpj") or row.get("agency_document") or "") if ch.isdigit())
            if len(cnpj) == 14:
                values.add(cnpj)
    return tuple(sorted(values))


def _org(record: dict) -> dict:
    return record.get("orgaoEntidade") or record.get("orgao") or {}


def _unit(record: dict) -> dict:
    return record.get("unidadeOrgao") or record.get("unidadeExecutora") or {}


def in_scope(record: dict, city: CityConfig, scope: str) -> bool:
    org = _org(record)
    unit = _unit(record)
    sphere = org.get("esferaId") or org.get("esfera")
    power = org.get("poderId") or org.get("poder")
    municipality_name = str(unit.get("municipioNome") or unit.get("nomeMunicipio") or "").strip().casefold()
    municipality_ibge = str(unit.get("codigoIbge") or unit.get("codigoIbgeMunicipio") or unit.get("municipioId") or "")
    city_match = municipality_ibge == city.ibge_code or municipality_name == city.name.strip().casefold()
    if sphere != "M" or not city_match:
        return False
    if scope == "municipal":
        return True
    if scope == "executivo":
        return power == "E"
    if scope == "legislativo":
        return power == "L"
    raise ValueError(f"scope inválido: {scope}")


def normalize_record(r: dict, city: CityConfig, observed_at: str, snapshot_sha256: str) -> dict:
    org = _org(r)
    unit = _unit(r)
    cnpj = org.get("cnpj")
    year = r.get("anoContrato")
    sequence = r.get("sequencialContrato") or r.get("sequencial")
    contract_control = r.get("numeroControlePNCP") or r.get("numeroControlePncp")
    procurement_control = r.get("numeroControlePNCPCompra") or r.get("numeroControlePncpCompra")
    detail_url = None
    if cnpj and year and sequence:
        detail_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/contratos/{year}/{sequence}"
    return {
        "city_slug": city.slug,
        "source_system": "PNCP",
        # Backward-compatible fields kept for existing consumers.
        "pncp_control_number": contract_control,
        "procurement_control_number": procurement_control,
        # Canonical identities used by the generic reconciler.
        "pncp_contract_control_number": contract_control,
        "pncp_procurement_control_number": procurement_control,
        "contract_number": r.get("numeroContratoEmpenho"),
        "year": year,
        "sequence": sequence,
        "contract_type_id": r.get("tipoContratoId"),
        "contract_type_name": r.get("tipoContratoNome"),
        "process_number": r.get("processo"),
        "object": r.get("objetoContrato"),
        "agency_cnpj": cnpj,
        "agency_document": cnpj,
        "agency_name": org.get("razaoSocial") or org.get("razaosocial") or org.get("nome"),
        "sphere": org.get("esferaId") or org.get("esfera"),
        "power": org.get("poderId") or org.get("poder"),
        "unit_code": unit.get("codigoUnidade") or unit.get("codigo"),
        "unit_name": unit.get("nomeUnidade"),
        "municipality_ibge": unit.get("codigoIbge") or unit.get("codigoIbgeMunicipio") or unit.get("municipioId") or city.ibge_code,
        "municipality_name": unit.get("municipioNome") or unit.get("nomeMunicipio") or city.name,
        "uf": unit.get("ufSigla") or unit.get("uf") or city.uf,
        "supplier_type": r.get("tipoPessoa"),
        "supplier_document": r.get("niFornecedor"),
        "supplier_name": r.get("nomeRazaoSocialFornecedor"),
        "initial_value": r.get("valorInicial"),
        "global_value": r.get("valorGlobal"),
        "accumulated_value": r.get("valorAcumulado"),
        "installments": r.get("numeroParcelas"),
        "installment_value": r.get("valorParcela"),
        "signed_at": r.get("dataAssinatura"),
        "valid_from": r.get("dataVigenciaInicio"),
        "valid_to": r.get("dataVigenciaFim"),
        "published_at": r.get("dataPublicacaoPncp"),
        "updated_at": r.get("dataAtualizacao"),
        "source_url": detail_url or str(r.get("linkSistemaOrigem") or ""),
        "observed_at": observed_at,
        "snapshot_sha256": snapshot_sha256,
    }


def _records(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    for key in ("data", "content", "items", "registros"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def pagination_metadata(payload: object) -> tuple[int | None, int | None, int | None]:
    """Return (total_pages, total_records, remaining_pages) from common PNCP shapes."""
    if not isinstance(payload, dict):
        return None, None, None
    pagination = payload.get("paginacao") if isinstance(payload.get("paginacao"), dict) else {}

    def first_int(*values: object) -> int | None:
        for value in values:
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return None

    pages = first_int(
        payload.get("totalPaginas"),
        payload.get("totalPages"),
        payload.get("paginas"),
        pagination.get("totalPaginas"),
        pagination.get("totalPages"),
        pagination.get("paginas"),
    )
    total = first_int(
        payload.get("totalRegistros"),
        payload.get("totalRecords"),
        payload.get("total"),
        pagination.get("totalRegistros"),
        pagination.get("totalRecords"),
        pagination.get("total"),
    )
    remaining = first_int(payload.get("paginasRestantes"), pagination.get("paginasRestantes"))
    return pages, total, remaining


def query_complete(
    *,
    error: str | None,
    pages_collected: int,
    source_rows_received: int,
    reported_pages: int | None,
    reported_total: int | None,
    explicit_empty: bool = False,
) -> bool:
    """Require explicit pagination/count proof, except for an explicit empty response."""
    if error is not None:
        return False
    if explicit_empty:
        return source_rows_received == 0
    if reported_pages is None and reported_total is None:
        return False
    if reported_pages is not None and pages_collected < reported_pages:
        return False
    if reported_total is not None and source_rows_received != reported_total:
        return False
    return pages_collected > 0


def _get_with_backoff(
    client: httpx.Client,
    *,
    params: dict,
    max_retries: int = 3,
) -> httpx.Response:
    response: httpx.Response | None = None
    for attempt in range(max_retries + 1):
        response = client.get(PNCP_CONTRACTS_ENDPOINT, params=params)
        if response.status_code not in RETRYABLE:
            return response
        if attempt >= max_retries:
            return response
        retry_after = response.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 20)
        except ValueError:
            delay = min(2 ** (attempt + 1), 20)
        time.sleep(max(0.5, min(delay, 30)))
    assert response is not None
    return response


def collect(
    city: CityConfig,
    start: date,
    end: date,
    out_dir: Path,
    *,
    agency_cnpjs: Iterable[str],
    scope: str = "executivo",
    page_size: int = 100,
    sleep_seconds: float = 0.25,
) -> Path:
    """Collect PNCP contracts and persist source-scoped pagination proof.

    Completeness is only for the supplied CNPJs + date filter + requested power scope.
    The collector does not claim that the supplied CNPJ set is a complete registry of
    municipal entities.
    """
    if end < start:
        raise ValueError("end anterior a start")
    if page_size < 1:
        raise ValueError("page_size deve ser >= 1")

    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"contratos_{scope}_{start.isoformat()}_{end.isoformat()}.jsonl"
    cnpjs = tuple(sorted({"".join(ch for ch in c if ch.isdigit()) for c in agency_cnpjs if c}))
    cnpjs = tuple(cnpj for cnpj in cnpjs if len(cnpj) == 14)
    if not cnpjs:
        raise ValueError("nenhum CNPJ de órgão fornecido para coleta de contratos")

    headers = {"User-Agent": "transparencia-municipal/0.3", "Accept": "application/json"}
    seen: set[str] = set()
    queries: list[dict] = []

    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        for cnpj in cnpjs:
            for window in date_windows(start, end):
                page = 1
                pages_collected = 0
                source_rows_received = 0
                scope_rows = 0
                reported_pages: int | None = None
                reported_total: int | None = None
                error: str | None = None
                explicit_empty = False

                while True:
                    params = {
                        "dataInicial": window.start.strftime("%Y%m%d"),
                        "dataFinal": window.end.strftime("%Y%m%d"),
                        "cnpjOrgao": cnpj,
                        "pagina": page,
                        "tamanhoPagina": page_size,
                    }
                    request_url = PNCP_CONTRACTS_ENDPOINT + "?" + urlencode(params)
                    try:
                        response = _get_with_backoff(client, params=params)
                        meta = persist_snapshot(
                            out_dir=out_dir / "snapshots",
                            source_id="pncp_contratos",
                            requested_url=request_url,
                            final_url=str(response.url),
                            status_code=response.status_code,
                            content_type=response.headers.get("content-type", "application/json"),
                            body=response.content,
                        )
                        if response.status_code in RETRYABLE:
                            error = f"HTTP {response.status_code} after retries"
                            break
                        response.raise_for_status()
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        break

                    if response.status_code == 204 or not response.content.strip():
                        explicit_empty = True
                        pages_collected += 1
                        if reported_pages is None:
                            reported_pages = 0
                        if reported_total is None:
                            reported_total = 0
                        break

                    try:
                        payload = response.json()
                    except Exception as exc:
                        error = f"InvalidJSON: {exc}"
                        break

                    records = _records(payload)
                    current_pages, current_total, remaining_pages = pagination_metadata(payload)
                    if page == 1:
                        reported_pages = current_pages
                        reported_total = current_total
                    else:
                        if current_pages is not None and reported_pages is not None and current_pages != reported_pages:
                            error = f"PaginationChanged: pages {reported_pages} -> {current_pages}"
                            break
                        if current_total is not None and reported_total is not None and current_total != reported_total:
                            error = f"PaginationChanged: total {reported_total} -> {current_total}"
                            break
                        if reported_pages is None:
                            reported_pages = current_pages
                        if reported_total is None:
                            reported_total = current_total

                    pages_collected += 1
                    source_rows_received += len(records)
                    for raw in records:
                        if not in_scope(raw, city, scope):
                            continue
                        row = normalize_record(raw, city, meta.collected_at, meta.sha256)
                        scope_rows += 1
                        key = row.get("pncp_contract_control_number") or row.get("pncp_control_number") or json.dumps(row, sort_keys=True, ensure_ascii=False)
                        if key in seen:
                            continue
                        seen.add(key)
                        sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

                    if reported_pages is not None and page >= reported_pages:
                        break
                    if remaining_pages == 0:
                        break
                    if not records:
                        # Empty JSON page is only conclusive when pagination metadata says
                        # this is the end. Without metadata, keep coverage partial.
                        break
                    if reported_pages is None and remaining_pages is None and len(records) < page_size:
                        break

                    page += 1
                    time.sleep(sleep_seconds)

                completed = query_complete(
                    error=error,
                    pages_collected=pages_collected,
                    source_rows_received=source_rows_received,
                    reported_pages=reported_pages,
                    reported_total=reported_total,
                    explicit_empty=explicit_empty,
                )
                queries.append({
                    "agency_cnpj": cnpj,
                    "period_start": window.start.isoformat(),
                    "period_end": window.end.isoformat(),
                    "completed": completed,
                    "pages_collected": pages_collected,
                    "source_rows_received": source_rows_received,
                    "scope_rows_received": scope_rows,
                    "reported_pages": reported_pages,
                    "reported_total": reported_total,
                    "pagination_metadata_complete": reported_pages is not None or reported_total is not None or explicit_empty,
                    "explicit_empty": explicit_empty,
                    "error": error,
                })

    complete = bool(queries) and all(item["completed"] for item in queries)
    coverage = {
        "source_system": "PNCP",
        "api_endpoint": PNCP_CONTRACTS_ENDPOINT,
        "scope": scope,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "agency_cnpjs_supplied": list(cnpjs),
        "agency_discovery_complete": False,
        "agency_discovery_note": "The collector proves only the supplied CNPJ set; it does not discover every municipal legal entity.",
        "complete_for_supplied_agencies_and_filter": complete,
        "records_unique_in_scope": len(seen),
        "source_rows_received": sum(item["source_rows_received"] for item in queries),
        "queries": queries,
        "coverage_note": "Complete means every supplied-CNPJ/date-window query reconciled explicit PNCP pagination/count metadata (or an explicit empty response). It is not municipality-wide entity completeness.",
    }
    (out_dir / "coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
