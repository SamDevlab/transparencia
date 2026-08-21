#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
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


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").casefold().strip()


def _filter_options(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("id") not in (None, "") and any(value.get(key) for key in ("text", "name", "noMunMin")):
                rows.append(value)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload.get("data") if isinstance(payload, dict) else payload)
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[f"{row.get('id')}|{row.get('text') or row.get('name') or row.get('noMunMin')}"] = row
    return list(unique.values())


def resolve_filter_value(
    client: ComexStatClient,
    *,
    scope: str,
    filter_name: str,
    target: str,
    raw_dir: Path,
    manifest: list[dict[str, Any]],
) -> Any:
    response = client._request("GET", f"/{scope}/filters/{filter_name}", params={"language": "pt"})  # noqa: SLF001
    payload = response.json()
    manifest.append(persist_raw(
        raw_dir,
        name=f"filter_{scope}_{filter_name}",
        endpoint=f"/{scope}/filters/{filter_name}?language=pt",
        body={},
        payload=payload,
    ))
    options = _filter_options(payload)
    wanted = _normalized(target)
    matches = []
    for row in options:
        label = row.get("text") or row.get("name") or row.get("noMunMin") or ""
        normalized = _normalized(label)
        if wanted == normalized or wanted in normalized:
            matches.append(row)
    if not matches:
        raise RuntimeError(f"Comex Stat não retornou valor de filtro para {scope}/{filter_name}: {target}")
    # Salvador pode aparecer com sufixo de UF; prioriza rótulos mais curtos/exatos.
    matches.sort(key=lambda row: (0 if _normalized(row.get("text") or row.get("name") or row.get("noMunMin")) == wanted else 1, len(str(row.get("text") or ""))))
    value = matches[0].get("id")
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def period(year: int, month: int) -> tuple[str, str]:
    return f"{year}-01", f"{year}-{month:02d}"


def compact_products(products: list[dict[str, Any]], *, limit: int = 400) -> list[dict[str, Any]]:
    ordered = sorted(products, key=lambda row: float(row.get("exports_fob") or 0) + float(row.get("imports_fob") or 0), reverse=True)
    return ordered[:limit]


def collect_scope(
    *,
    client: ComexStatClient,
    out_root: Path,
    scope_name: str,
    query: Callable[..., tuple[dict[str, Any], Any]],
    filters: list[dict[str, Any]],
    details: list[str],
    methodology: str,
    update_scope: str,
) -> dict[str, Any]:
    coverage: dict[str, Any] = {
        "status": "unavailable",
        "scope": scope_name,
        "methodology": methodology,
        "source": "MDIC / Comex Stat",
        "api": COMEX_API_BASE,
        "filters": filters,
        "details": details,
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
                body = client.query_body(flow=flow, start=start, end=end, filters=filters, details=details, month_detail=True)
                payload, _response = query(flow=flow, start=start, end=end, filters=filters, details=details, month_detail=True)
                manifest.append(persist_raw(
                    out_root / "raw",
                    name=f"{scope_name}_{period_name}_{flow}",
                    endpoint=f"/{update_scope}?language=pt",
                    body=body,
                    payload=payload,
                ))
                batches[f"{period_name}_{flow}"] = unwrap_list(payload)

        current_exports = batches["current_export"]
        current_imports = batches["current_import"]
        previous_exports = batches["previous_export"]
        previous_imports = batches["previous_import"]
        if not current_exports and not current_imports:
            raise RuntimeError(f"Consulta {scope_name} retornou zero linhas de exportação e importação; cobertura não pode ser marcada como completa")

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
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "note": "A falha da fonte ou consulta vazia inesperada não é convertida em zero de exportações/importações.",
        })
    return {"coverage": coverage, "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta inteligência econômica Bahia/Salvador no Comex Stat")
    parser.add_argument("--out", type=Path, default=None, help="Diretório do snapshot. Padrão: regions/bahia/data/snapshots/AAAA-MM-DD")
    args = parser.parse_args()
    out_root = args.out or Path("regions") / "bahia" / "data" / "snapshots" / date.today().isoformat()
    if not out_root.is_absolute():
        out_root = ROOT / out_root
    out_root = out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    state_method = "Bahia / dados gerais: exportação por UF corresponde à UF produtora; importação por UF corresponde ao domicílio fiscal do importador."
    city_method = "Salvador / dados municipais: exportação e importação correspondem ao domicílio fiscal da empresa declarante; não provam produção ou consumo físico no município."
    filter_manifest: list[dict[str, Any]] = []

    with ComexStatClient() as client:
        general_bahia = resolve_filter_value(client, scope="general", filter_name="state", target="Bahia", raw_dir=out_root / "raw", manifest=filter_manifest)
        city_bahia = resolve_filter_value(client, scope="cities", filter_name="state", target="Bahia", raw_dir=out_root / "raw", manifest=filter_manifest)
        salvador_id = resolve_filter_value(client, scope="cities", filter_name="city", target="Salvador", raw_dir=out_root / "raw", manifest=filter_manifest)

        bahia = collect_scope(
            client=client,
            out_root=out_root,
            scope_name="bahia",
            query=client.query_general,
            filters=[{"filter": "state", "values": [general_bahia]}],
            details=["country", "state", "heading"],
            methodology=state_method,
            update_scope="general",
        )
        salvador = collect_scope(
            client=client,
            out_root=out_root,
            scope_name="salvador",
            query=client.query_cities,
            filters=[{"filter": "state", "values": [city_bahia]}, {"filter": "city", "values": [salvador_id]}],
            details=["country", "state", "city", "heading"],
            methodology=city_method,
            update_scope="cities",
        )

    coverage = {
        "generated_at": date.today().isoformat(),
        "bahia": bahia["coverage"],
        "salvador": salvador["coverage"],
        "resolved_filters": {"general_bahia": general_bahia, "cities_bahia": city_bahia, "salvador": salvador_id},
        "interstate_dependency": {
            "status": "historical_baseline_normalized",
            "source": "SEI - cadeia regional de valor (matriz interestadual 2017) + MIP Bahia 2012",
            "note": "A dependência interestadual possui linha de base estrutural histórica normalizada separadamente. Não é inferida do Comex Stat nem apresentada como percentual corrente de 2026.",
        },
    }
    manifest = {
        "generated_at": date.today().isoformat(),
        "raw_files": filter_manifest + bahia["manifest"] + salvador["manifest"],
        "hash_algorithm": "SHA-256",
    }
    write_json(out_root / "coverage.json", coverage)
    write_json(out_root / "manifest.json", manifest)
    write_json(ROOT / "regions" / "bahia" / "data" / "latest.json", {
        "snapshot": out_root.name,
        "path": str(out_root.relative_to(ROOT.resolve())),
        "bahia_status": coverage["bahia"]["status"],
        "salvador_status": coverage["salvador"]["status"],
    })
    print(json.dumps({
        "snapshot": str(out_root),
        "bahia": coverage["bahia"]["status"],
        "salvador": coverage["salvador"]["status"],
        "filters": coverage["resolved_filters"],
        "raw_files": len(manifest["raw_files"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
