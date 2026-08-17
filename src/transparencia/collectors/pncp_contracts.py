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


def _json_payload_or_empty(response: httpx.Response) -> dict:
    if response.status_code == 204 or not response.content.strip():
        return {}
    return response.json()


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
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"contratos_{scope}_{start.isoformat()}_{end.isoformat()}.jsonl"
    cnpjs = tuple(sorted({"".join(ch for ch in c if ch.isdigit()) for c in agency_cnpjs if c}))
    if not cnpjs:
        raise ValueError("nenhum CNPJ de órgão fornecido para coleta de contratos")
    headers = {"User-Agent": "transparencia-municipal/0.2", "Accept": "application/json"}
    seen: set[str] = set()
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        for cnpj in cnpjs:
            if len(cnpj) != 14:
                continue
            for window in date_windows(start, end):
                page = 1
                while True:
                    params = {
                        "dataInicial": window.start.strftime("%Y%m%d"),
                        "dataFinal": window.end.strftime("%Y%m%d"),
                        "cnpjOrgao": cnpj,
                        "pagina": page,
                        "tamanhoPagina": page_size,
                    }
                    request_url = PNCP_CONTRACTS_ENDPOINT + "?" + urlencode(params)
                    response = client.get(PNCP_CONTRACTS_ENDPOINT, params=params)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        time.sleep(min(2 ** min(page, 5), 30))
                        response = client.get(PNCP_CONTRACTS_ENDPOINT, params=params)
                    response.raise_for_status()
                    meta = persist_snapshot(
                        out_dir=out_dir / "snapshots",
                        source_id="pncp_contratos",
                        requested_url=request_url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type", "application/json"),
                        body=response.content,
                    )
                    payload = _json_payload_or_empty(response)
                    records = payload.get("data") or payload.get("content") or []
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
                    if not records or (isinstance(total_pages, int) and page >= total_pages):
                        break
                    if payload.get("paginasRestantes") == 0 or len(records) < page_size:
                        break
                    page += 1
                    time.sleep(sleep_seconds)
    return output
