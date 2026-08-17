from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from transparencia.collectors.cms import collect_certames_visible, collect_document_catalog, collect_travel
from transparencia.collectors.pncp import collect as collect_pncp
from transparencia.collectors.pncp_contracts import agency_cnpjs_from_procurements, collect as collect_contracts
from transparencia.collectors.webapp_discovery import discover
from transparencia.config import load_city

ROOT = Path("cities/salvador/data/snapshots/2026-08-17")
ROOT.mkdir(parents=True, exist_ok=True)
ws = load_city(Path.cwd(), "salvador")
start = date(2025, 1, 1)
end = date(2026, 8, 17)
summary: dict = {
    "snapshot_date": end.isoformat(),
    "period_start": start.isoformat(),
    "period_end": end.isoformat(),
    "city": {"name": ws.config.name, "uf": ws.config.uf, "ibge_code": ws.config.ibge_code},
    "coverage_notes": [],
    "errors": {},
}


def rows(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def asset_contexts(root: Path) -> list[dict]:
    needles = (
        "apitmptransparencia", "RealizacaoDespesa", "RealizacaoReceita", "ReceitaDadosAbertos",
        "DespesaDadosAbertos", "ContratosVigentes", "FornecedoresPrestadoresDeServico",
        "LicitacoesDispensasInexigibilidade", "DetalhamentoResultadosDasLicitacoes",
    )
    found: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".js", ".json", ".html"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in needles:
            for match in re.finditer(re.escape(needle), text, re.I):
                left = max(0, match.start() - 350)
                right = min(len(text), match.end() + 500)
                snippet = " ".join(text[left:right].split())
                found.append({"file": str(path), "needle": needle, "snippet": snippet})
                if len(found) >= 250:
                    return found
    return found


procurement_path: Path | None = None
try:
    procurement_path = collect_pncp(ws.config, start, end, ROOT / "pncp", scope="municipal", sleep_seconds=0.08)
    procurement_rows = rows(procurement_path)
    summary["pncp_procurements"] = {
        "records": len(procurement_rows),
        "by_power": dict(Counter(r.get("power") or "unknown" for r in procurement_rows)),
        "unique_agency_cnpjs": len({r.get("agency_cnpj") for r in procurement_rows if r.get("agency_cnpj")}),
        "known_estimated_value_brl": sum(float(r["estimated_value"]) for r in procurement_rows if r.get("estimated_value") is not None),
        "known_homologated_value_brl": sum(float(r["homologated_value"]) for r in procurement_rows if r.get("homologated_value") is not None),
    }
except Exception as exc:
    summary["errors"]["pncp_procurements"] = f"{type(exc).__name__}: {exc}"
    procurement_rows = []

try:
    cnpjs = set(agency_cnpjs_from_procurements([procurement_path] if procurement_path else []))
    if ws.config.municipality_cnpj:
        cnpjs.add(ws.config.municipality_cnpj)
    (ROOT / "agency_cnpjs.json").write_text(json.dumps(sorted(cnpjs), indent=2) + "\n", encoding="utf-8")
    contract_path = collect_contracts(ws.config, start, end, ROOT / "pncp_contracts", agency_cnpjs=cnpjs, scope="municipal", sleep_seconds=0.08)
    contract_rows = rows(contract_path)
    supplier_values: defaultdict[str, float] = defaultdict(float)
    supplier_counts: Counter[str] = Counter()
    supplier_names: dict[str, str | None] = {}
    for r in contract_rows:
        doc = r.get("supplier_document")
        if doc:
            supplier_counts[doc] += 1
            supplier_names[doc] = r.get("supplier_name")
            if r.get("global_value") is not None:
                supplier_values[doc] += float(r["global_value"])
    known_total = sum(supplier_values.values())
    top = sorted(supplier_values, key=supplier_values.get, reverse=True)[:25]
    summary["pncp_contracts"] = {
        "records": len(contract_rows),
        "by_power": dict(Counter(r.get("power") or "unknown" for r in contract_rows)),
        "unique_suppliers": len(supplier_counts),
        "known_global_value_brl": known_total,
        "supplier_concentration": [
            {
                "supplier_document": doc,
                "supplier_name": supplier_names.get(doc),
                "contract_count": supplier_counts[doc],
                "known_global_value_brl": supplier_values[doc],
                "share_of_known_global_value": supplier_values[doc] / known_total if known_total else None,
                "interpretation": "descriptive_concentration_not_irregularity",
            }
            for doc in top
        ],
    }
except Exception as exc:
    summary["errors"]["pncp_contracts"] = f"{type(exc).__name__}: {exc}"

try:
    travel_path = collect_travel(ROOT / "cms")
    travel_rows = rows(travel_path)
    coverage = read_json(ROOT / "cms" / "cms_travel_expenses.coverage.json")
    with Path("cities/salvador/data/seed/officials.csv").open(encoding="utf-8", newline="") as handle:
        official_names = {r["name"].strip().casefold(): r["name"] for r in csv.DictReader(handle)}
    exact_matches: list[dict] = []
    totals: defaultdict[str, float] = defaultdict(float)
    for r in travel_rows:
        name = r.get("user_name") or ""
        totals[name] += float(r.get("value_brl") or 0)
        if name.strip().casefold() in official_names:
            exact_matches.append({
                "travel_user": name,
                "official_name": official_names[name.strip().casefold()],
                "date": r.get("date"),
                "value_brl": r.get("value_brl"),
                "match_method": "exact_normalized_name",
                "source_url": r.get("source_url"),
            })
    summary["cms_travel"] = {
        "records": len(travel_rows),
        "total_value_brl": sum(totals.values()),
        "unique_users": len(totals),
        "coverage": coverage,
        "exact_name_matches_to_official_registry": exact_matches,
        "note": "Exact-name match is a linkage candidate, not proof of identity when names are ambiguous.",
    }
except Exception as exc:
    summary["errors"]["cms_travel"] = f"{type(exc).__name__}: {exc}"

try:
    docs_path = collect_document_catalog(ROOT / "cms")
    doc_rows = rows(docs_path)
    summary["cms_documents"] = {
        "records": len(doc_rows),
        "by_section": dict(Counter(r.get("section") or "unknown" for r in doc_rows)),
        "coverage": read_json(ROOT / "cms" / "cms_documents.coverage.json"),
    }
except Exception as exc:
    summary["errors"]["cms_documents"] = f"{type(exc).__name__}: {exc}"

try:
    certames_path = collect_certames_visible(ROOT / "cms")
    certame_rows = rows(certames_path)
    summary["cms_certames_visible"] = {
        "records": len(certame_rows),
        "coverage": "server_visible_page_only",
        "note": "The CMS application reports a larger client-side catalogue; this file is not labelled complete.",
    }
except Exception as exc:
    summary["errors"]["cms_certames_visible"] = f"{type(exc).__name__}: {exc}"

for key, url in {
    "prefeitura_portal": "https://transparencia.salvador.ba.gov.br/",
    "cms_financeiro": "https://cmsalvador.sys.inf.br/consulta.html",
    "cms_certames_app": "https://cmsalvador.sys.inf.br/ca/licitacao/",
}.items():
    try:
        path = discover(url, ROOT / "discovery" / key)
        payload = read_json(path)
        summary.setdefault("discoveries", {})[key] = {
            "candidate_count": len(payload.get("candidates", [])),
            "candidates": payload.get("candidates", []),
            "errors": payload.get("errors", []),
        }
    except Exception as exc:
        summary["errors"][f"discovery_{key}"] = f"{type(exc).__name__}: {exc}"

contexts = asset_contexts(ROOT / "discovery" / "prefeitura_portal")
(ROOT / "discovery" / "prefeitura_portal" / "api_contexts.json").write_text(
    json.dumps(contexts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
summary["prefeitura_api_contexts"] = {"records": len(contexts), "file": "discovery/prefeitura_portal/api_contexts.json"}
summary["coverage_notes"].extend([
    "PNCP coverage is reconciliatory: absence in PNCP is not treated as proof that a local procurement does not exist.",
    "CMS pagination may be partial when the official source returns 403/429; partial coverage is explicitly recorded.",
    "CMS certame visible-page output is explicitly partial until its export/API pagination is discovered.",
    "No concentration metric is labelled fraud, corruption or irregularity without separate evidence.",
])
(ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
