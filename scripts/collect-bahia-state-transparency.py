#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from transparencia.collectors.bahia_open_data import (  # noqa: E402
    BahiaOpenDataError,
    ckan_package,
    normalize_ckan_package,
    persist_json_snapshot,
    stream_to_temp,
    summarize_hash_csv,
    summarize_tce_expenses,
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta transparência estadual da Bahia (SEFAZ/CKAN + TCE/BA)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--skip-tce-large", action="store_true", help="Coleta apenas metadados CKAN e catálogo quando a rede estiver limitada")
    args = parser.parse_args()

    region_root = ROOT / "regions" / "bahia"
    reference = json.loads((region_root / "data" / "reference" / "state_transparency_catalog.json").read_text(encoding="utf-8"))
    out_root = args.out or region_root / "data" / "state_transparency" / "snapshots" / date.today().isoformat()
    out_root.mkdir(parents=True, exist_ok=True)

    coverage: dict[str, Any] = {
        "generated_at": date.today().isoformat(),
        "ckan": {},
        "tce": {},
        "status": "partial",
    }
    manifest: list[dict[str, Any]] = []
    catalog_rows = []

    headers = {"Accept": "application/json,text/csv,*/*", "User-Agent": "transparencia-municipal/0.4"}
    with httpx.Client(headers=headers, timeout=120.0, follow_redirects=True) as client:
        for source in reference["sources"]:
            if not source.get("dataset"):
                continue
            dataset = source["dataset"]
            try:
                payload = ckan_package(client, dataset)
                manifest.append({"source_id": source["id"], **persist_json_snapshot(out_root / "raw", f"ckan_{dataset}", payload)})
                normalized = normalize_ckan_package(payload)
                catalog_rows.append({**source, "status": "metadata_collected", "ckan": normalized})
                coverage["ckan"][dataset] = {"status": "metadata_collected", "resources": len(normalized["resources"]), "metadata_modified": normalized.get("metadata_modified")}
            except Exception as exc:  # noqa: BLE001
                catalog_rows.append({**source, "status": "unavailable", "error": str(exc)})
                coverage["ckan"][dataset] = {"status": "unavailable", "error_type": type(exc).__name__, "error": str(exc)}

        if not args.skip_tce_large:
            tce_jobs = [
                {
                    "id": "expenses",
                    "url": f"https://www.tce.ba.gov.br/images/transparencia/despesa-detalhada/despesa-detalhada/Despesa_detalhada_Exercicio_{args.year}.csv",
                    "summarize": summarize_tce_expenses,
                    "target": "tce_expenses.json",
                },
                {
                    "id": "contracts",
                    "url": "https://www.tce.ba.gov.br/contratos/dados-abertos",
                    "summarize": lambda path: summarize_hash_csv(path, value_headers=("VALOR ATUAL",)),
                    "target": "tce_contracts.json",
                },
                {
                    "id": "procurements",
                    "url": "https://www.tce.ba.gov.br/institucional/transparencia/licitacoes/dados-abertos",
                    "summarize": lambda path: summarize_hash_csv(path, value_headers=("VALOR DA PROPOSTA VENCEDORA",)),
                    "target": "tce_procurements.json",
                },
            ]
            for job in tce_jobs:
                temp = None
                try:
                    temp, evidence = stream_to_temp(client, job["url"])
                    summary = job["summarize"](temp)
                    write_json(out_root / job["target"], {
                        "source": "TCE/BA",
                        "source_url": job["url"],
                        "reference_year": args.year if job["id"] == "expenses" else None,
                        "evidence": evidence.__dict__,
                        "summary": summary,
                    })
                    coverage["tce"][job["id"]] = {"status": "processed", "sha256": evidence.sha256, "bytes": evidence.bytes, "rows": summary.get("totals", {}).get("rows", summary.get("rows"))}
                    manifest.append({"source_id": f"tce_{job['id']}", "url": evidence.url, "sha256": evidence.sha256, "bytes": evidence.bytes, "content_type": evidence.content_type})
                except Exception as exc:  # noqa: BLE001
                    coverage["tce"][job["id"]] = {"status": "unavailable", "error_type": type(exc).__name__, "error": str(exc)}
                finally:
                    if temp and temp.exists():
                        temp.unlink(missing_ok=True)
        else:
            coverage["tce"] = {"status": "not_run", "note": "Execução solicitada com --skip-tce-large"}

    write_json(out_root / "catalog.json", {"observed_at": date.today().isoformat(), "rows": catalog_rows})
    processed = sum(1 for item in coverage["ckan"].values() if item.get("status") == "metadata_collected")
    tce_processed = sum(1 for item in coverage["tce"].values() if isinstance(item, dict) and item.get("status") == "processed")
    coverage["status"] = "complete_for_defined_collection" if processed >= 5 and (args.skip_tce_large or tce_processed == 3) else "partial"
    coverage["note"] = "Completo para a rotina definida significa metadados CKAN consultados e, quando habilitado, os três arquivos automatizados do TCE processados. Não significa completude de toda a transparência estadual."
    write_json(out_root / "coverage.json", coverage)
    write_json(out_root / "manifest.json", {"hash_algorithm": "SHA-256", "entries": manifest})
    write_json(region_root / "data" / "state_transparency" / "latest.json", {
        "snapshot": out_root.name,
        "path": str(out_root.relative_to(ROOT)),
        "status": coverage["status"],
    })
    print(json.dumps({"snapshot": str(out_root), "status": coverage["status"], "ckan_collected": processed, "tce_processed": tce_processed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
