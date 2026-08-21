#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from transparencia.collectors.comex import (  # noqa: E402
    COMEX_API_BASE,
    ComexStatClient,
    aggregate_countries,
    aggregate_monthly,
    aggregate_products,
    attach_yoy_and_screening,
    summarize_flows,
    unwrap_list,
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_raw(raw_dir: Path, *, name: str, endpoint: str, body: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    envelope = {"endpoint": endpoint, "request_body": body, "response": payload}
    encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    target = raw_dir / f"{name}.json"
    target.write_bytes(encoded + b"\n")
    return {"file": str(target.name), "sha256": digest, "bytes": target.stat().st_size}


def period(year: int, month: int) -> tuple[str, str]:
    return f"{year}-01", f"{year}-{month:02d}"


def compact_products(products: list[dict[str, Any]], *, limit: int = 400) -> list[dict[str, Any]]:
    ordered = sorted(products, key=lambda row: float(row.get("exports_fob") or 0) + float(row.get("imports_fob") or 0), reverse=True)
    return ordered[:limit]


def collect_scope(
    *, client: ComexStatClient, out_root: Path, scope_name: str,
    query: Callable[..., tuple[dict[str, Any], Any]], filters: list[dict[str, Any]],
    methodology: str, update_scope: str,
) -> dict[str, Any]:
    coverage: dict[str, Any] = {
        "status": "unavailable", "scope": scope_name, "methodology": methodology,
        "source": "MDIC / Comex Stat", "api": COMEX_API_BASE,
    }
    manifest: list[dict[str, Any]] = []
    try:
        last = client.get_last_update(update_scope)
        current_from, current_to = period(last.year, last.month)
        previous_from, previous_to = period(last.year - 1, last.month)
        coverage.update({
            "source_updated_at": last.updated,
            "source_year": last.year,
            "source_month": last.month,
            "period_current": {"from": current_from, "to": current_to},
            "period_previous": {"from": previous_from, "to": previous_to},
        })
        batches: dict[str, list[dict[str, Any]]] = {}
        for period_name, start, end in (("current", current_from, current_to), ("previous", previous_from, previous_to)):
            for flow in ("export", "import"):
                body = client.query_body(flow=flow, start=start, end=end, filters=filters, details=["country", "heading"], month_detail=True)
                payload, _response = query(flow=flow, start=start, end=end, filters=filters, details=["country", "heading"], month_detail=True)
                manifest.append(persist_raw(
                    out_root / "raw", name=f"{scope_name}_{period_name}_{flow}",
                    endpoint=f"/{update_scope}?language=pt", body=body, payload=payload,
                ))
                batches[f"{period_name}_{flow}"] = unwrap_list(payload)

        current_exports = batches["current_export"]
        current_imports = batches["current_import"]
        previous_exports = batches["previous_export"]
        previous_imports = batches["previous_import"]
        summary = summarize_flows(current_exports, current_imports)
        previous_summary = summarize_flows(previous_exports, previous_imports)
        current_products = aggregate_products(current_exports, current_imports)
        previous_products = aggregate_products(previous_exports, previous_imports)
        screened = attach_yoy_and_screening(current_products, previous_products)
        countries = aggregate_countries(current_exports, current_imports)
        monthly = aggregate_monthly(current_exports, current_imports)

        def yoy(current: float, previous: float) -> float | None:
            return None if previous == 0 else (current - previous) / previous

        write_json(out_root / scope_name / "summary.json", {
            **summary,
            "previous_period": previous_summary,
            "exports_yoy": yoy(summary["exports_fob"], previous_summary["exports_fob"]),
            "imports_yoy": yoy(summary["imports_fob"], previous_summary["imports_fob"]),
            "balance_change_fob": summary["balance_fob"] - previous_summary["balance_fob"],
            "period": {"from": current_from, "to": current_to},
            "comparison_period": {"from": previous_from, "to": previous_to},
            "source_updated_at": last.updated,
            "source": "MDIC / Comex Stat",
            "methodology": methodology,
        })
        write_json(out_root / scope_name / "products.json", compact_products(screened))
        write_json(out_root / scope_name / "countries.json", countries[:250])
        write_json(out_root / scope_name / "monthly.json", monthly)
        write_json(out_root / scope_name / "opportunities.json", screened[:250])
        coverage.update({
            "status": "complete_for_api_query",
            "current_export_rows": len(current_exports),
            "current_import_rows": len(current_imports),
            "previous_export_rows": len(previous_exports),
            "previous_import_rows": len(previous_imports),
            "products": len(current_products),
            "countries": len(countries),
            "note": "Completo apenas para as consultas descritas no manifesto; não significa completude de toda a economia regional.",
        })
    except Exception as exc:  # noqa: BLE001
        coverage.update({
            "status": "unavailable", "error_type": type(exc).__name__, "error": str(exc),
            "note": "A falha da fonte não é convertida em zero de exportações/importações.",
        })
    return {"coverage": coverage, "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta inteligência econômica Bahia/Salvador no Comex Stat")
    parser.add_argument("--out", type=Path, default=None, help="Diretório do snapshot. Padrão: regions/bahia/data/snapshots/AAAA-MM-DD")
    args = parser.parse_args()
    out_root = args.out or ROOT / "regions" / "bahia" / "data" / "snapshots" / date.today().isoformat()
    out_root.mkdir(parents=True, exist_ok=True)

    state_method = "Bahia / dados gerais: exportação por UF corresponde à UF produtora; importação por UF corresponde ao domicílio fiscal do importador."
    city_method = "Salvador / dados municipais: exportação e importação correspondem ao domicílio fiscal da empresa declarante; não provam produção ou consumo físico no município."

    with ComexStatClient() as client:
        bahia = collect_scope(
            client=client, out_root=out_root, scope_name="bahia", query=client.query_general,
            filters=[{"filter": "state", "values": [29]}], methodology=state_method, update_scope="general",
        )
        salvador = collect_scope(
            client=client, out_root=out_root, scope_name="salvador", query=client.query_cities,
            filters=[{"filter": "state", "values": [29]}, {"filter": "city", "values": [2927408]}],
            methodology=city_method, update_scope="cities",
        )

    coverage = {
        "generated_at": date.today().isoformat(),
        "bahia": bahia["coverage"],
        "salvador": salvador["coverage"],
        "interstate_dependency": {
            "status": "historical_baseline_normalized",
            "source": "SEI - cadeia regional de valor (matriz interestadual 2017) + MIP Bahia 2012",
            "note": "A dependência interestadual possui linha de base estrutural histórica normalizada separadamente. Não é inferida do Comex Stat nem apresentada como percentual corrente de 2026.",
        },
    }
    manifest = {"generated_at": date.today().isoformat(), "raw_files": bahia["manifest"] + salvador["manifest"], "hash_algorithm": "SHA-256"}
    write_json(out_root / "coverage.json", coverage)
    write_json(out_root / "manifest.json", manifest)
    write_json(ROOT / "regions" / "bahia" / "data" / "latest.json", {
        "snapshot": out_root.name,
        "path": str(out_root.relative_to(ROOT)),
        "bahia_status": coverage["bahia"]["status"],
        "salvador_status": coverage["salvador"]["status"],
    })
    print(json.dumps({
        "snapshot": str(out_root), "bahia": coverage["bahia"]["status"],
        "salvador": coverage["salvador"]["status"], "raw_files": len(manifest["raw_files"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
