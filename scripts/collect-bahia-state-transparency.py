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


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta transparência estadual da Bahia (SEFAZ/CKAN + TCE/BA)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--skip-tce-large", action="store_true", help="Coleta somente os metadados oficiais do CKAN")
    args = parser.parse_args()

    region_root = ROOT / "regions" / "bahia"
    reference = json.loads((region_root / "data" / "reference" / "state_transparency_catalog.json").read_text(encoding="utf-8"))
    out_root = args.out or Path("regions") / "bahia" / "data" / "state_transparency" / "snapshots" / date.today().isoformat()
    if not out_root.is_absolute():
        out_root = ROOT / out_root
    out_root = out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    existing_coverage = read_json(out_root / "coverage.json", {}) or {}
    existing_manifest = read_json(out_root / "manifest.json", {"entries": []}) or {"entries": []}
    existing_latest = read_json(region_root / "data" / "state_transparency" / "latest.json", {}) or {}

    coverage: dict[str, Any] = {
        "generated_at": date.today().isoformat(),
        "ckan": {},
        "tce": {},
        "status": "partial",
        "collection_mode": "metadata_only" if args.skip_tce_large else "full",
    }
    for key in ("sefaz_data", "sefaz_data_summary"):
        if key in existing_coverage:
            coverage[key] = existing_coverage[key]

    manifest: list[dict[str, Any]] = []
    catalog_rows = []

    headers = {
        "Accept": "application/json,text/csv,*/*",
        "Accept-Encoding": "identity",
        "User-Agent": "Mozilla/5.0 transparencia-municipal/0.6",
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
        coverage["tce"] = {"status": "not_run", "note": "Fase rápida: arquivos grandes do TCE serão tentados na fase de enriquecimento."}

    write_json(out_root / "catalog.json", {"observed_at": date.today().isoformat(), "rows": catalog_rows})
    processed = sum(1 for item in coverage["ckan"].values() if item.get("status") == "metadata_collected")
    tce_processed = sum(1 for item in coverage["tce"].values() if isinstance(item, dict) and item.get("status") == "processed")

    if args.skip_tce_large and processed >= 5:
        coverage["status"] = "complete_for_metadata_collection"
    elif not args.skip_tce_large and processed >= 5 and tce_processed == 3:
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
        "A fase de metadados pode ficar completa mesmo sem baixar os arquivos grandes do TCE. "
        "A cobertura plena da rotina exige os metadados CKAN e os três conjuntos automatizados do TCE. "
        "Dados SEFAZ já processados são preservados entre reexecuções. Fallback TLS do CKAN, quando necessário, "
        "fica registrado e nunca é silencioso."
    )
    write_json(out_root / "coverage.json", coverage)

    new_ids = {entry.get("source_id") for entry in manifest}
    preserved_entries = [
        entry for entry in (existing_manifest.get("entries") or [])
        if entry.get("source_id") not in new_ids
    ]
    write_json(out_root / "manifest.json", {"hash_algorithm": "SHA-256", "entries": preserved_entries + manifest})

    latest_payload = {
        "snapshot": out_root.name,
        "path": str(out_root.relative_to(ROOT.resolve())),
        "status": coverage["status"],
        "collection_mode": coverage["collection_mode"],
        "summary": coverage["summary"],
    }
    if coverage.get("sefaz_data_summary"):
        latest_payload["sefaz_data"] = coverage["sefaz_data_summary"]
    elif existing_latest.get("sefaz_data"):
        latest_payload["sefaz_data"] = existing_latest["sefaz_data"]
    write_json(region_root / "data" / "state_transparency" / "latest.json", latest_payload)

    print(json.dumps({
        "snapshot": str(out_root),
        "status": coverage["status"],
        "mode": coverage["collection_mode"],
        "ckan_collected": processed,
        "tce_processed": tce_processed,
        "sefaz_data_processed": (coverage.get("sefaz_data_summary") or {}).get("processed", 0),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
