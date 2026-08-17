from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

import httpx

from ..config import CityConfig
from ..provenance import persist_snapshot

PNCP_ENDPOINT = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
PNCP_MODALITIES_ENDPOINT = "https://pncp.gov.br/api/pncp/v1/modalidades"


def parse_active_modality_ids(payload: object) -> tuple[int, ...]:
    if isinstance(payload, dict):
        rows = payload.get("data") or payload.get("content") or payload.get("items") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    ids: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("statusAtivo") is False:
            continue
        value = row.get("id")
        if isinstance(value, int):
            ids.add(value)
        elif isinstance(value, str) and value.isdigit():
            ids.add(int(value))
    if not ids:
        raise ValueError("PNCP não devolveu modalidades ativas; coleta interrompida para não presumir domínio")
    return tuple(sorted(ids))


def discover_modality_ids(client: httpx.Client, out_dir: Path) -> tuple[int, ...]:
    response = client.get(PNCP_MODALITIES_ENDPOINT, params={"statusAtivo": "true"})
    response.raise_for_status()
    persist_snapshot(out_dir=out_dir / "snapshots", source_id="pncp_modalidades",
                     requested_url=str(response.request.url), final_url=str(response.url),
                     status_code=response.status_code,
                     content_type=response.headers.get("content-type", "application/json"),
                     body=response.content)
    return parse_active_modality_ids(response.json())


@dataclass(frozen=True)
class Window:
    start: date
    end: date


def date_windows(start: date, end: date, max_days: int = 30) -> Iterable[Window]:
    if end < start:
        raise ValueError("end anterior a start")
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=max_days - 1), end)
        yield Window(cursor, stop)
        cursor = stop + timedelta(days=1)


def _party(record: dict) -> tuple[str | None, str | None]:
    org = record.get("orgaoEntidade") or {}
    return org.get("esferaId"), org.get("poderId")


def _city(record: dict) -> str | None:
    return (record.get("unidadeOrgao") or {}).get("municipioNome")


def in_scope(record: dict, city: CityConfig, scope: str) -> bool:
    sphere, power = _party(record)
    record_city = (_city(record) or "").strip().casefold()
    if sphere != "M" or record_city != city.name.strip().casefold():
        return False
    if scope == "municipal":
        return True
    if scope == "executivo":
        return power == "E"
    if scope == "legislativo":
        return power == "L"
    raise ValueError(f"scope inválido: {scope}")


def normalize_record(r: dict, city: CityConfig, observed_at: str, snapshot_sha256: str) -> dict:
    org = r.get("orgaoEntidade") or {}
    unit = r.get("unidadeOrgao") or {}
    return {
        "city_slug": city.slug,
        "source_system": "PNCP",
        "pncp_control_number": r.get("numeroControlePNCP") or r.get("numeroControlePncp"),
        "process_number": r.get("processo"),
        "notice_number": r.get("numeroCompra"),
        "year": r.get("anoCompra"),
        "modality_id": r.get("modalidadeId"),
        "modality_name": r.get("modalidadeNome"),
        "object": r.get("objetoCompra"),
        "agency_cnpj": org.get("cnpj"),
        "agency_name": org.get("razaosocial"),
        "sphere": org.get("esferaId"),
        "power": org.get("poderId"),
        "unit_code": unit.get("codigoUnidade"),
        "unit_name": unit.get("nomeUnidade"),
        "municipality_ibge": unit.get("codigoIbge") or unit.get("municipioId") or city.ibge_code,
        "municipality_name": unit.get("municipioNome"),
        "uf": unit.get("ufSigla") or city.uf,
        "published_at": r.get("dataPublicacaoPncp"),
        "proposal_opening_at": r.get("dataAberturaProposta"),
        "proposal_closing_at": r.get("dataEncerramentoProposta"),
        "estimated_value": r.get("valorTotalEstimado"),
        "homologated_value": r.get("valorTotalHomologado"),
        "status_name": r.get("situacaoCompraNome"),
        "source_url": r.get("linkSistemaOrigem") or r.get("linkProcessoEletronico"),
        "observed_at": observed_at,
        "snapshot_sha256": snapshot_sha256,
    }


def collect(city: CityConfig, start: date, end: date, out_dir: Path, *, scope: str = "executivo",
            page_size: int = 50, sleep_seconds: float = 0.25) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"contratacoes_{scope}_{start.isoformat()}_{end.isoformat()}.jsonl"
    seen: set[str] = set()
    headers = {"User-Agent": "transparencia-municipal/0.1", "Accept": "application/json"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        modality_ids = discover_modality_ids(client, out_dir)
        for window in date_windows(start, end):
            for modality_id in modality_ids:
                page = 1
                while True:
                    params = {
                        "dataInicial": window.start.strftime("%Y%m%d"),
                        "dataFinal": window.end.strftime("%Y%m%d"),
                        "codigoModalidadeContratacao": modality_id,
                        "uf": city.uf,
                        "codigoMunicipioIbge": city.ibge_code,
                        "pagina": page,
                        "tamanhoPagina": page_size,
                    }
                    url = PNCP_ENDPOINT + "?" + urlencode(params)
                    response = client.get(PNCP_ENDPOINT, params=params)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        time.sleep(min(2 ** min(page, 5), 30))
                        response = client.get(PNCP_ENDPOINT, params=params)
                    response.raise_for_status()
                    meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id="pncp_consulta",
                                            requested_url=url, final_url=str(response.url),
                                            status_code=response.status_code,
                                            content_type=response.headers.get("content-type", "application/json"),
                                            body=response.content)
                    payload = response.json()
                    records = payload.get("data") or payload.get("content") or []
                    for raw in records:
                        if not in_scope(raw, city, scope):
                            continue
                        row = normalize_record(raw, city, meta.collected_at, meta.sha256)
                        key = row.get("pncp_control_number") or json.dumps(row, sort_keys=True, ensure_ascii=False)
                        if key not in seen:
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
