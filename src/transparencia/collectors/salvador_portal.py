from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import httpx

from ..config import CityConfig
from ..provenance import persist_snapshot

BASE_URL = "https://apitmptransparencia.salvador.ba.gov.br/api"
PUBLIC_PORTAL = "https://transparencia.salvador.ba.gov.br/"
SOURCE_SYSTEM = "SALVADOR_TRANSPARENCIA_API"


def parse_brl(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Origin": PUBLIC_PORTAL.rstrip("/"),
        "Referer": PUBLIC_PORTAL,
        "User-Agent": "municipal-transparency-research/0.2 (+public-data-audit)",
    }


def _payload(start: date, end: date, *, agrupamentos: list[dict] | None = None) -> dict:
    return {
        "dataInicio": start.isoformat(),
        "dataFim": end.isoformat(),
        "agrupamentos": agrupamentos or [],
        "filtros": [],
    }


def _post(client: httpx.Client, path: str, payload: dict, out_dir: Path, source_id: str) -> tuple[object, object]:
    url = BASE_URL + path
    response = client.post(url, json=payload)
    response.raise_for_status()
    meta = persist_snapshot(
        out_dir=out_dir / "raw",
        source_id=source_id,
        requested_url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=response.headers.get("content-type", "application/json"),
        body=response.content,
    )
    return response.json(), meta


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _split_description(value: object) -> tuple[str | None, str]:
    text = " ".join(str(value or "").split())
    if " - " not in text:
        return None, text
    left, right = text.split(" - ", 1)
    return left.strip() or None, right.strip()


def normalize_revenue_detail(payload: object, city: CityConfig, *, start: date, end: date, source_url: str,
                             observed_at: str, snapshot_sha256: str) -> list[dict]:
    data = payload.get("dados", []) if isinstance(payload, dict) else []
    rows: list[dict] = []
    for item in data if isinstance(data, list) else []:
        code = str(item.get("id") or "").strip() or None
        _, name = _split_description(item.get("descricao"))
        identity = f"{city.slug}|revenue|{code}|{start.isoformat()}|{end.isoformat()}"
        rows.append({
            "city_slug": city.slug,
            "source_system": SOURCE_SYSTEM,
            "event_key": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            "event_date": None,
            "agency_code": None,
            "agency_name": None,
            "nature_code": code,
            "nature_name": name,
            "funding_source_code": None,
            "funding_source_name": None,
            "forecast_value": parse_brl(item.get("previstoAno")),
            "updated_forecast_value": None,
            "collected_value": parse_brl(item.get("arrecadadoPeriodo")),
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "accumulated_value": parse_brl(item.get("acumulado")),
            "performance_percent": parse_brl(item.get("desempenho")),
            "raw_description": item.get("descricao"),
        })
    return rows


def normalize_expense_dimension(payload: object, city: CityConfig, *, dimension: str, start: date, end: date,
                                source_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    data = payload.get("dados", []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
    rows: list[dict] = []
    for item in data if isinstance(data, list) else []:
        code = str(item.get("id") if item.get("id") is not None else item.get("codigo") or "").strip() or None
        parsed_code, name = _split_description(item.get("descricao"))
        code = code or parsed_code
        rows.append({
            "city_slug": city.slug,
            "source_system": SOURCE_SYSTEM,
            "dimension": dimension,
            "dimension_code": code,
            "dimension_name": name,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "committed_value": parse_brl(item.get("empenhado")),
            "liquidated_value": parse_brl(item.get("liquidado")),
            "paid_value": parse_brl(item.get("pago")),
            "gross_value": parse_brl(item.get("bruto")),
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def normalize_contract_units(payload: object, city: CityConfig, *, start: date, end: date, source_url: str,
                             observed_at: str, snapshot_sha256: str) -> list[dict]:
    data = payload if isinstance(payload, list) else []
    rows: list[dict] = []
    for item in data:
        code = str(item.get("codigo") or "").strip() or None
        _, name = _split_description(item.get("descricao"))
        rows.append({
            "city_slug": city.slug,
            "source_system": SOURCE_SYSTEM,
            "unit_code": code,
            "unit_name": name,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "contracted_value": parse_brl(item.get("contratado")),
            "committed_value": parse_brl(item.get("empenhado")),
            "liquidated_value": parse_brl(item.get("liquidado")),
            "paid_value": parse_brl(item.get("pago")),
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def collect(city: CityConfig, start: date, end: date, out_dir: Path) -> dict[str, Path]:
    """Collect official Prefeitura finance aggregates and detailed revenue.

    Expense creditor rows are official aggregates for the requested period, not individual payments.
    Raw HTTP responses are persisted with SHA-256 provenance before normalization.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    base = _payload(start, end)
    creditor_group = [{
        "atributo": "CDCREDOR", "descricao": "Credor", "nomeTabela": "CREDOR",
        "observacao": "É aquele que recebe recursos públicos.", "temAnoReferencia": False,
    }]

    outputs: dict[str, Path] = {}
    summary: dict[str, object] = {
        "city": asdict(city),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_system": SOURCE_SYSTEM,
        "public_portal": PUBLIC_PORTAL,
        "api_base": BASE_URL,
        "coverage": {
            "revenue_detail": "official API response for unfiltered period",
            "expense_function": "official API aggregate by function for unfiltered period",
            "expense_creditor": "official API aggregate by creditor for unfiltered period; not individual payment records",
            "contract_unit": "official API contract/execution aggregate by management unit for unfiltered period",
        },
    }

    with httpx.Client(headers=_headers(), follow_redirects=True, timeout=90.0) as client:
        revenue_total, rev_total_meta = _post(client, "/receita/totalizador", base, out_dir, "salvador_receita_totalizador")
        revenue_detail, rev_detail_meta = _post(client, "/receita/gridDetalhada", base, out_dir, "salvador_receita_detalhada")
        expense_total, exp_total_meta = _post(client, "/despesa/totalizador", base, out_dir, "salvador_despesa_totalizador")
        expense_functions, exp_fun_meta = _post(client, "/despesa/gridresumida", base, out_dir, "salvador_despesa_funcao")
        expense_creditors, exp_cred_meta = _post(client, "/despesa/gridDetalhada", {**base, "agrupamentos": creditor_group}, out_dir, "salvador_despesa_credor")
        contracts_total, contract_total_meta = _post(client, "/contratos/totalizador", base, out_dir, "salvador_contratos_totalizador")
        contract_units, contract_units_meta = _post(client, "/contratos/gridresumida", base, out_dir, "salvador_contratos_unidade")

    rev_rows = normalize_revenue_detail(
        revenue_detail, city, start=start, end=end, source_url=BASE_URL + "/receita/gridDetalhada",
        observed_at=rev_detail_meta.collected_at, snapshot_sha256=rev_detail_meta.sha256,
    )
    exp_fun_rows = normalize_expense_dimension(
        expense_functions, city, dimension="function", start=start, end=end,
        source_url=BASE_URL + "/despesa/gridresumida", observed_at=exp_fun_meta.collected_at,
        snapshot_sha256=exp_fun_meta.sha256,
    )
    exp_cred_rows = normalize_expense_dimension(
        expense_creditors, city, dimension="creditor", start=start, end=end,
        source_url=BASE_URL + "/despesa/gridDetalhada", observed_at=exp_cred_meta.collected_at,
        snapshot_sha256=exp_cred_meta.sha256,
    )
    contract_rows = normalize_contract_units(
        contract_units, city, start=start, end=end, source_url=BASE_URL + "/contratos/gridresumida",
        observed_at=contract_units_meta.collected_at, snapshot_sha256=contract_units_meta.sha256,
    )

    outputs["revenue_events"] = out_dir / "revenue_events.jsonl"
    outputs["expense_functions"] = out_dir / "expense_by_function.jsonl"
    outputs["expense_creditors"] = out_dir / "expense_by_creditor.jsonl"
    outputs["contract_units"] = out_dir / "contract_execution_by_unit.jsonl"
    _write_jsonl(outputs["revenue_events"], rev_rows)
    _write_jsonl(outputs["expense_functions"], exp_fun_rows)
    _write_jsonl(outputs["expense_creditors"], exp_cred_rows)
    _write_jsonl(outputs["contract_units"], contract_rows)

    summary.update({
        "revenue_totalizer": revenue_total,
        "expense_totalizer": expense_total,
        "contracts_totalizer": contracts_total,
        "record_counts": {
            "revenue_detail": len(rev_rows),
            "expense_functions": len(exp_fun_rows),
            "expense_creditors": len(exp_cred_rows),
            "contract_units": len(contract_rows),
        },
        "snapshot_sha256": {
            "revenue_totalizer": rev_total_meta.sha256,
            "revenue_detail": rev_detail_meta.sha256,
            "expense_totalizer": exp_total_meta.sha256,
            "expense_functions": exp_fun_meta.sha256,
            "expense_creditors": exp_cred_meta.sha256,
            "contracts_totalizer": contract_total_meta.sha256,
            "contract_units": contract_units_meta.sha256,
        },
    })
    outputs["summary"] = out_dir / "summary.json"
    outputs["summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return outputs
