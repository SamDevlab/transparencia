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

from transparencia.collectors.bahia_sefaz_files import (  # noqa: E402
    download_ckan_resource,
    summarize_sefaz_licitacoes_zip,
    summarize_sefaz_revenues,
)
from transparencia.collectors.bahia_sefaz_finance import (  # noqa: E402
    summarize_sefaz_expenses_zip,
    summarize_sefaz_payments_zip,
)

PRIORITY_DATASETS = ("receitas", "licitacoes", "despesas", "pagamentos")


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def choose_resource(
    catalog: dict[str, Any],
    dataset: str,
    formats: tuple[str, ...],
    *,
    preferred_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    resources: list[dict[str, Any]] = []
    for row in catalog.get("rows") or []:
        if row.get("dataset") == dataset:
            resources = (row.get("ckan") or {}).get("resources") or []
            break
    if not resources:
        raise RuntimeError(f"Nenhum recurso oficial encontrado no catálogo para {dataset}")

    preferred = {name.casefold() for name in preferred_names}
    if preferred:
        for resource in resources:
            if str(resource.get("name") or "").casefold() in preferred and resource.get("url"):
                return resource

    for fmt in formats:
        for resource in resources:
            if str(resource.get("format") or "").upper() == fmt and resource.get("url"):
                return resource
    raise RuntimeError(f"Recurso oficial {formats} não encontrado no catálogo para {dataset}")


def update_manifest(snapshot: Path, entry: dict[str, Any]) -> None:
    path = snapshot / "manifest.json"
    manifest = read_json(path, {"hash_algorithm": "SHA-256", "entries": []})
    entries = [item for item in manifest.get("entries") or [] if item.get("source_id") != entry.get("source_id")]
    entries.append(entry)
    manifest["hash_algorithm"] = "SHA-256"
    manifest["entries"] = entries
    write_json(path, manifest)


def summary_rows(dataset: str, summary: dict[str, Any]) -> int | None:
    if dataset == "receitas":
        return summary.get("rows")
    if dataset == "licitacoes":
        return summary.get("total_rows_across_related_tables")
    if dataset in {"despesas", "pagamentos"}:
        return (summary.get("primary_table") or {}).get("rows")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Processa recursos reais da SEFAZ/BA sem versionar arquivos brutos grandes")
    parser.add_argument("--snapshot", type=Path, default=None, help="Diretório do snapshot estadual; por padrão usa latest.json")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--datasets", nargs="+", choices=PRIORITY_DATASETS, default=PRIORITY_DATASETS)
    args = parser.parse_args()

    state_root = ROOT / "regions" / "bahia" / "data" / "state_transparency"
    latest_path = state_root / "latest.json"
    latest = read_json(latest_path)
    if args.snapshot:
        snapshot = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
    elif latest and latest.get("path"):
        snapshot = ROOT / latest["path"]
    else:
        raise RuntimeError("Nenhum snapshot estadual disponível para processamento SEFAZ")
    snapshot = snapshot.resolve()

    catalog = read_json(snapshot / "catalog.json", {"rows": []})
    coverage = read_json(snapshot / "coverage.json", {})
    coverage.setdefault("sefaz_data", {})
    headers = {
        "Accept": "text/csv,application/zip,application/octet-stream,*/*",
        "Accept-Encoding": "identity",
        "User-Agent": "Mozilla/5.0 transparencia-municipal/0.7",
    }

    processors = {
        "receitas": {
            "formats": ("CSV",),
            "preferred_names": ("Receitas.csv",),
            "output": "sefaz_receitas.json",
            "process": lambda path: summarize_sefaz_revenues(path, target_year=args.year),
        },
        "licitacoes": {
            "formats": ("ZIP",),
            "preferred_names": ("Licitacoes.zip", "Licitações.zip"),
            "output": "sefaz_licitacoes.json",
            "process": lambda path: summarize_sefaz_licitacoes_zip(path, target_year=args.year),
        },
        "despesas": {
            "formats": ("ZIP",),
            "preferred_names": ("Despesas.zip",),
            "output": "sefaz_despesas.json",
            "process": lambda path: summarize_sefaz_expenses_zip(path, target_year=args.year),
        },
        "pagamentos": {
            "formats": ("ZIP",),
            "preferred_names": ("Pagamentos.zip",),
            "output": "sefaz_pagamentos.json",
            "process": lambda path: summarize_sefaz_payments_zip(path, target_year=args.year),
        },
    }

    requested_processed = 0
    for dataset in args.datasets:
        config = processors[dataset]
        temp: Path | None = None
        try:
            resource = choose_resource(
                catalog,
                dataset,
                config["formats"],
                preferred_names=config.get("preferred_names", ()),
            )
            temp, evidence, transport = download_ckan_resource(resource["url"], headers=headers)
            summary = config["process"](temp)
            payload = {
                "source": "SEFAZ/AGE - Portal Dados Abertos da Bahia",
                "dataset": dataset,
                "resource": {
                    "id": resource.get("id"),
                    "name": resource.get("name"),
                    "format": resource.get("format"),
                    "last_modified": resource.get("last_modified"),
                    "metadata_modified": resource.get("metadata_modified"),
                    "declared_size": resource.get("size"),
                    "url": resource.get("url"),
                },
                "evidence": evidence.__dict__,
                "transport": transport,
                "summary": summary,
                "privacy": "O arquivo bruto foi processado temporariamente e não é republicado pelo projeto.",
            }
            write_json(snapshot / config["output"], payload)
            coverage["sefaz_data"][dataset] = {
                "status": "processed",
                "output": config["output"],
                "resource_id": resource.get("id"),
                "resource_name": resource.get("name"),
                "resource_last_modified": resource.get("last_modified"),
                "sha256": evidence.sha256,
                "bytes": evidence.bytes,
                "tls_verified": transport.get("tls_verified"),
                "rows": summary_rows(dataset, summary),
                "selected_year": args.year,
            }
            update_manifest(snapshot, {
                "source_id": f"sefaz_{dataset}_data",
                "url": evidence.url,
                "sha256": evidence.sha256,
                "bytes": evidence.bytes,
                "content_type": evidence.content_type,
                "resource_id": resource.get("id"),
                "resource_name": resource.get("name"),
                "resource_last_modified": resource.get("last_modified"),
                "tls_verified": transport.get("tls_verified"),
            })
            requested_processed += 1
        except Exception as exc:  # noqa: BLE001
            coverage["sefaz_data"][dataset] = {
                "status": "unavailable",
                "error_type": type(exc).__name__,
                "error": str(exc)[:2000],
                "selected_year": args.year,
                "note": "Falha de download/processamento não é convertida em zero registros ou zero reais.",
            }
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)

    total_processed = sum(
        1 for dataset in PRIORITY_DATASETS
        if (coverage["sefaz_data"].get(dataset) or {}).get("status") == "processed"
    )
    coverage["sefaz_data_summary"] = {
        "processed": total_processed,
        "expected": len(PRIORITY_DATASETS),
        "datasets": list(PRIORITY_DATASETS),
        "reference_year": args.year,
        "last_run_datasets": list(args.datasets),
        "last_run_processed": requested_processed,
    }
    write_json(snapshot / "coverage.json", coverage)

    if latest is None:
        latest = {}
    latest.update({
        "snapshot": snapshot.name,
        "path": str(snapshot.relative_to(ROOT.resolve())),
        "sefaz_data": coverage["sefaz_data_summary"],
    })
    write_json(latest_path, latest)

    print(json.dumps({
        "snapshot": str(snapshot),
        "requested_processed": requested_processed,
        "requested_expected": len(args.datasets),
        "total_processed": total_processed,
        "total_expected": len(PRIORITY_DATASETS),
        "datasets": {dataset: coverage["sefaz_data"].get(dataset) for dataset in args.datasets},
    }, ensure_ascii=False))
    return 0 if requested_processed == len(args.datasets) else 2


if __name__ == "__main__":
    raise SystemExit(main())
