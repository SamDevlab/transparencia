#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from transparencia.collectors.bahia_sefaz_download import download_ckan_resource_resilient  # noqa: E402
from transparencia.collectors.bahia_sefaz_procurement_links import extract_procurement_instrument_links  # noqa: E402


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    state_root = ROOT / "regions" / "bahia" / "data" / "state_transparency"
    latest = read_json(state_root / "latest.json", {})
    if not latest.get("path"):
        raise RuntimeError("Snapshot estadual não encontrado")
    snapshot = ROOT / latest["path"]
    catalog = read_json(snapshot / "catalog.json", {"rows": []})
    licitacoes = next((row for row in catalog.get("rows") or [] if row.get("dataset") == "licitacoes"), None)
    if not licitacoes:
        raise RuntimeError("Catálogo de licitações estaduais não encontrado")
    resources = (licitacoes.get("ckan") or {}).get("resources") or []
    resource = next((row for row in resources if str(row.get("name") or "").casefold() in {"licitacoes.zip", "licitações.zip".casefold()}), None)
    if not resource:
        resource = next((row for row in resources if str(row.get("format") or "").upper() == "ZIP"), None)
    if not resource or not resource.get("url"):
        raise RuntimeError("ZIP oficial de licitações não encontrado")

    declared_size = int(resource.get("size")) if resource.get("size") not in (None, "") else None
    headers = {
        "Accept": "application/zip,application/octet-stream,*/*",
        "Accept-Encoding": "identity",
        "User-Agent": "Mozilla/5.0 transparencia-municipal/0.9",
    }
    temp = None
    try:
        temp, evidence, transport = download_ckan_resource_resilient(
            resource["url"], expected_size=declared_size, headers=headers
        )
        summary = extract_procurement_instrument_links(temp, target_year=2026)
        payload = {
            "source": "SEFAZ/AGE - Portal Dados Abertos da Bahia",
            "dataset": "licitacoes_contratos_links",
            "resource": {
                "id": resource.get("id"),
                "name": resource.get("name"),
                "last_modified": resource.get("last_modified"),
                "declared_size": resource.get("size"),
                "url": resource.get("url"),
            },
            "evidence": evidence.__dict__,
            "transport": transport,
            "summary": summary,
            "note": "Mapa derivado exclusivamente de campos oficiais das próprias tabelas SEFAZ/SIMPAS. Arquivo bruto não é republicado.",
        }
        write_json(snapshot / "sefaz_licitacoes_contratos_links.json", payload)

        coverage = read_json(snapshot / "coverage.json", {})
        coverage["procurement_contract_links"] = {
            "status": "processed",
            "selected_year": 2026,
            "exact_link_count": summary["exact_link_count"],
            "processes_with_instruments": summary["processes_with_instruments"],
            "unique_instruments": summary["unique_instruments"],
            "sha256": evidence.sha256,
        }
        write_json(snapshot / "coverage.json", coverage)
        print(json.dumps(coverage["procurement_contract_links"], ensure_ascii=False))
        return 0
    finally:
        if temp and temp.exists():
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
