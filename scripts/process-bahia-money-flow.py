#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from transparencia.collectors.bahia_sefaz_download import download_ckan_resource_resilient  # noqa: E402
from transparencia.collectors.bahia_sefaz_money_flow import build_exact_money_flow  # noqa: E402


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def choose_zip(catalog: dict[str, Any], dataset: str, preferred_name: str) -> dict[str, Any]:
    for row in catalog.get("rows") or []:
        if row.get("dataset") != dataset:
            continue
        resources = (row.get("ckan") or {}).get("resources") or []
        for resource in resources:
            if str(resource.get("name") or "").casefold() == preferred_name.casefold() and resource.get("url"):
                return resource
        for resource in resources:
            if str(resource.get("format") or "").upper() == "ZIP" and resource.get("url"):
                return resource
    raise RuntimeError(f"ZIP oficial não encontrado no catálogo para {dataset}")


def expected_size(resource: dict[str, Any]) -> int | None:
    try:
        return int(resource.get("size")) if resource.get("size") not in (None, "") else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera o fio exato licitação → contrato → pagamento da Bahia")
    parser.add_argument("--year", type=int, default=date.today().year)
    args = parser.parse_args()

    state_root = ROOT / "regions" / "bahia" / "data" / "state_transparency"
    latest_path = state_root / "latest.json"
    latest = read_json(latest_path)
    if not latest?.get("path") if False else False:
        pass
    if not latest or not latest.get("path"):
        raise RuntimeError("Snapshot estadual mais recente não encontrado")
    snapshot = (ROOT / latest["path"]).resolve()
    catalog = read_json(snapshot / "catalog.json", {"rows": []})
    contracts = read_json(snapshot / "sefaz_contratos.json")
    if not contracts:
        raise RuntimeError("Resumo estadual de contratos ainda não está disponível")
    primary_contracts = (contracts.get("summary") or {}).get("primary_table") or {}
    contract_keys = primary_contracts.get("instrument_keys") or []
    if not contract_keys:
        raise RuntimeError("Resumo de contratos sem chaves oficiais de instrumento")

    procurement_resource = choose_zip(catalog, "licitacoes", "Licitacoes.zip")
    payments_resource = choose_zip(catalog, "pagamentos", "Pagamentos.zip")
    headers = {
        "Accept": "application/zip,application/octet-stream,*/*",
        "Accept-Encoding": "identity",
        "User-Agent": "Mozilla/5.0 transparencia-municipal/0.9",
    }

    procurement_path: Path | None = None
    payments_path: Path | None = None
    try:
        procurement_path, procurement_evidence, procurement_transport = download_ckan_resource_resilient(
            procurement_resource["url"],
            expected_size=expected_size(procurement_resource),
            headers=headers,
        )
        payments_path, payments_evidence, payments_transport = download_ckan_resource_resilient(
            payments_resource["url"],
            expected_size=expected_size(payments_resource),
            headers=headers,
        )
        flow = build_exact_money_flow(
            procurement_path,
            payments_path,
            contract_keys,
            target_year=args.year,
        )
        payload = {
            "source": "SEFAZ/AGE Bahia - SIMPAS/FIPLAN",
            "selected_year": args.year,
            "resources": {
                "licitacoes": {
                    "id": procurement_resource.get("id"),
                    "name": procurement_resource.get("name"),
                    "last_modified": procurement_resource.get("last_modified"),
                    "url": procurement_resource.get("url"),
                    "sha256": procurement_evidence.sha256,
                    "bytes": procurement_evidence.bytes,
                    "download_mode": procurement_transport.get("download_mode"),
                    "tls_verified": procurement_transport.get("tls_verified"),
                },
                "pagamentos": {
                    "id": payments_resource.get("id"),
                    "name": payments_resource.get("name"),
                    "last_modified": payments_resource.get("last_modified"),
                    "url": payments_resource.get("url"),
                    "sha256": payments_evidence.sha256,
                    "bytes": payments_evidence.bytes,
                    "download_mode": payments_transport.get("download_mode"),
                    "tls_verified": payments_transport.get("tls_verified"),
                },
                "contratos": {
                    "sha256": contracts.get("evidence", {}).get("sha256"),
                    "resource_name": contracts.get("resource", {}).get("name"),
                    "instrument_keys_used": len(contract_keys),
                },
            },
            "summary": flow["summary"],
            "top_end_to_end": flow["top_end_to_end"],
            "coverage": flow["coverage"],
            "identity_rule": flow["identity_rule"],
            "interpretation": flow["interpretation"],
            "privacy_rule": flow["privacy_rule"],
        }
        output = snapshot / "sefaz_money_flow.json"
        write_json(output, payload)

        coverage = read_json(snapshot / "coverage.json", {})
        coverage["money_flow"] = {
            "status": "processed",
            "output": output.name,
            "selected_year": args.year,
            "identity": "exact_official_identifiers_only",
            **flow["summary"],
        }
        write_json(snapshot / "coverage.json", coverage)
        latest["money_flow"] = {
            "status": "processed",
            "selected_year": args.year,
            "instruments_end_to_end": flow["summary"]["instruments_end_to_end"],
        }
        write_json(latest_path, latest)
        print(json.dumps({"status": "processed", **flow["summary"]}, ensure_ascii=False))
        return 0
    finally:
        if procurement_path and procurement_path.exists():
            procurement_path.unlink(missing_ok=True)
        if payments_path and payments_path.exists():
            payments_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
