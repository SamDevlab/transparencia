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


def agency_cnpjs_from_procurements(paths: Iterable[Path]) -> tuple[str, ...]:
    values: set[str] = set()
    for path in paths:
        if not path or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            cnpj = "".join(ch for ch in str(row.get("agency_cnpj") or "") if ch.isdigit())
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
    detail_url = None
    if cnpj and year and sequence:
        detail_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/contratos/{year}/{sequence}"
    return {
        "city_slug": city.slug,
        "source_system": "PNCP",
        "pncp_control_number": r.get("numeroControlePNCP") or r.get("numeroControlePncp"),
        "procurement_control_number": r.get("numeroControlePNCPCompra") or r.get("numeroControlePncpCompra"),
        "contract_number": r.get("numeroContratoEmpenho"),
        "year": year,
        "sequence": sequence,
        "contract_type_id": r.get("tipoContratoId"),
        "contract_type_name": r.get("tipoContratoNome"),
        "process_number": r.get("processo"),
        "object": r.get("objetoContrato"),
        "agency_cnpj": cnpj,
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
    max_attempts: int = 3,
) -> Path:
    """Collect PNCP contracts for explicitly supplied agency CNPJs with auditable coverage."""
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"contratos_{scope}_{start.isoformat()}_{end.isoformat()}.jsonl"
    cnpjs = tuple(sorted({"".join(ch for ch in c if ch.isdigit()) for c in agency_cnpjs if c}))
    cnpjs = tuple(cnpj for cnpj in cnpjs if len(cnpj) == 14)
    if not cnpjs:
        raise ValueError("nenhum CNPJ de órgão fornecido para coleta de contratos")

    headers = {"User-Agent": "transparencia-municipal/0.3 (+public-data-audit)", "Accept": "application/json"}
    seen: set[str] = set()
    queries: list[dict] = []
    errors: list[dict] = []

    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        for cnpj in cnpjs:
            for window in date_windows(start, end):
                page = 1
                pages_collected = 0
                records_received = 0
                query_complete = False
                query_error: str | None = None
                while True:
                    params = {
                        "dataInicial": window.start.strftime("%Y%m%d"),
                        "dataFinal": window.end.strftime("%Y%m%d"),
                        "cnpjOrgao": cnpj,
                        "pagina": page,
                        "tamanhoPagina": page_size,
                    }
                    request_url = PNCP_CONTRACTS_ENDPOINT + "?" + urlencode(params)
                    response = None
                    for attempt in range(1, max_attempts + 1):
                        try:
                            response = client.get(PNCP_CONTRACTS_ENDPOINT, params=params)
                            if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
                                time.sleep(min(2 ** attempt, 12))
                                continue
                            response.raise_for_status()
                            break
                        except Exception as exc:
                            if attempt >= max_attempts:
                                query_error = f"{type(exc).__name__}: {exc}"
                            else:
                                time.sleep(min(2 ** attempt, 12))
                    if query_error or response is None:
                        break

                    meta = persist_snapshot(
                        out_dir=out_dir / "snapshots",
                        source_id="pncp_contratos",
                        requested_url=request_url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type", "application/json"),
                        body=response.content,
                    )
                    payload = {} if response.status_code == 204 or not response.content.strip() else response.json()
                    records = payload.get("data") or payload.get("content") or []
                    pages_collected += 1
                    records_received += len(records)
                    for raw in records:
                        if not in_scope(raw, city, scope):
                            continue
                        row = normalize_record(raw, city, meta.collected_at, meta.sha256)
                        key = row.get("pncp_control_number") or json.dumps(row, sort_keys=True, ensure_ascii=False)
                        if key in seen:
                            continue
                        seen.add(key)
                        sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

                    total_pages = payload.get("totalPaginas") or payload.get("totalPages")
                    normal_end = (
                        not records
                        or (isinstance(total_pages, int) and page >= total_pages)
                        or payload.get("paginasRestantes") == 0
                        or len(records) < page_size
                    )
                    if normal_end:
                        query_complete = True
                        break
                    page += 1
                    time.sleep(sleep_seconds)

                item = {
                    "cnpj_orgao": cnpj,
                    "window_start": window.start.isoformat(),
                    "window_end": window.end.isoformat(),
                    "pages_collected": pages_collected,
                    "records_received_before_scope_filter": records_received,
                    "complete": query_complete,
                    "error": query_error,
                }
                queries.append(item)
                if query_error:
                    errors.append(item)

    complete = bool(queries) and all(item["complete"] for item in queries)
    coverage = {
        "source_system": "PNCP",
        "source_url": PNCP_CONTRACTS_ENDPOINT,
        "scope": scope,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "agency_cnpjs": list(cnpjs),
        "records_after_salvador_scope_filter": len(seen),
        "complete_for_supplied_agencies_and_filter": complete,
        "queries": queries,
        "errors": errors,
        "coverage_note": (
            "Complete only for the explicitly supplied agency CNPJs, PNCP contract endpoint, requested date interval and municipal scope filter. The supplied CNPJ set itself may be incomplete if upstream procurement discovery was partial."
            if complete else
            "Partial: at least one PNCP CNPJ/date query did not reach a normal source end. Persisted contract rows remain valid; missing queries are not interpreted as zero."
        ),
    }
    (out_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
