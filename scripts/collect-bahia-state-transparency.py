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

from transparencia.collectors.bahia_open_data import (  # noqa: E402
    ckan_package_resilient,
    normalize_ckan_package,
    official_tce_url_candidates,
    persist_json_snapshot,
    stream_first_available,
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
    out_root = args.out or Path("regions") / "bahia" / "data" / "state_transparency" / "snapshots" / date.today().isoformat()
    if not out_root.is_absolute():
        out_root = ROOT / out_root
    out_root = out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    coverage: dict[str, Any] = {
        "generated_at": date.today().isoformat(),
        "ckan": {},
        "tce": {},
        "status": "partial",
    }
    manifest: list[dict[str, Any]] = []
    catalog_rows = []

    headers = {
        "Accept": "application/json,text/csv,*/*",
        "Accept-Encoding": "identity",
        "User-Agent": "Mozilla/5.0 transparencia-municipal/0.5",
    }

    for source in reference["sources"]:
        if not source.get("dataset"):
            continue
        dataset = source["dataset"]
        try:
            payload, transport = ckan_package_resilient(dataset, headers=headers, timeout=60.0)
            snapshot_meta = persist_json_snapshot(out_root / "raw", f"ckan_{dataset}", payload)
            manifest.append({"source_id": source["id"], "transport": transport, **snapshot_meta})
            normalized = normalize_ckan_package(payload)
            catalog_rows.append({**source, "status": "metadata_collected", "transport": transport, "ckan": normalized})
            coverage["ckan"][dataset] = {
                "status": "metadata_collected",
                "resources": len(normalized["resources"]),
                "metadata_modified": normalized.get("metadata_modified"),
                **transport,
            }
        except Exception as exc:  # noqa: BLE001
            catalog_rows.append({**source, "status": "unavailable", "error": str(exc)})
            coverage["ckan"][dataset] = {
                "status": "unavailable",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

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
            candidates = official_tce_url_candidates(job["url"])
            try:
                temp, evidence, attempts = stream_first_available(candidates, headers=headers)
                summary = job["summarize"](temp)
                write_json(out_root / job["target"], {
                    "source": "TCE/BA",
                    "canonical_source_url": job["url"],
                    "retrieved_from": evidence.url,
                    "attempts": attempts,
                    "reference_year": args.year if job["id"] == "expenses" else None,
                    "evidence": evidence.__dict__,
                    "summary": summary,
                })
                coverage["tce"][job["id"]] = {
                    "status": "processed",
                    "canonical_source_url": job["url"],
                    "retrieved_from": evidence.url,
                    "attempts": attempts,
                    "sha256": evidence.sha256,
                    "bytes": evidence.bytes,
                    "rows": summary.get("totals", {}).get("rows", summary.get("rows")),
                }
                manifest.append({
                    "source_id": f"tce_{job['id']}",
                    "canonical_source_url": job["url"],
                    "url": evidence.url,
                    "sha256": evidence.sha256,
                    "bytes": evidence.bytes,
                    "content_type": evidence.content_type,
                })
            except Exception as exc:  # noqa: BLE001
                coverage["tce"][job["id"]] = {
                    "status": "unavailable",
                    "canonical_source_url": job["url"],
                    "attempted_urls": candidates,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            finally:
                if temp and temp.exists():
                    temp.unlink(missing_ok=True)
    else:
        coverage["tce"] = {"status": "not_run", "note": "Execução solicitada com --skip-tce-large"}

    write_json(out_root / "catalog.json", {"observed_at": date.today().isoformat(), "rows": catalog_rows})
    processed = sum(1 for item in coverage["ckan"].values() if item.get("status") == "metadata_collected")
    tce_processed = sum(1 for item in coverage["tce"].values() if isinstance(item, dict) and item.get("status") == "processed")

    if processed >= 5 and (args.skip_tce_large or tce_processed == 3):
        coverage["status"] = "complete_for_defined_collection"
    elif processed >= 5 or tce_processed > 0:
        coverage["status"] = "partial_with_verified_sources"
    else:
        coverage["status"] = "partial"

    coverage["summary"] = {
        "ckan_datasets_collected": processed,
        "ckan_datasets_expected": 6,
        "tce_datasets_processed": tce_processed,
        "tce_datasets_expected": 0 if args.skip_tce_large else 3,
    }
    coverage["note"] = (
        "Completo para a rotina definida significa metadados CKAN consultados e, quando habilitado, "
        "os três arquivos automatizados do TCE processados. Fallback TLS do CKAN, quando necessário, "
        "é registrado explicitamente. Não significa completude de toda a transparência estadual."
    )
    write_json(out_root / "coverage.json", coverage)
    write_json(out_root / "manifest.json", {"hash_algorithm": "SHA-256", "entries": manifest})
    write_json(region_root / "data" / "state_transparency" / "latest.json", {
        "snapshot": out_root.name,
        "path": str(out_root.relative_to(ROOT.resolve())),
        "status": coverage["status"],
        "summary": coverage["summary"],
    })
    print(json.dumps({
        "snapshot": str(out_root),
        "status": coverage["status"],
        "ckan_collected": processed,
        "tce_processed": tce_processed,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
