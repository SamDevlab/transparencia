from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from .config import load_city
from .coverage import CoverageEntry, CoverageManifest
from .db import build as build_db
from .ingest import ingest_events
from .reconcile import write_reconciliation
from .collectors import (
    cms,
    cms_commitments,
    pncp,
    pncp_contracts,
    salvador_acquisitions,
    salvador_contracts,
    salvador_portal,
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def run_salvador_project(
    repo_root: Path,
    *,
    start: date,
    end: date,
    out_dir: Path,
    include_pncp: bool = True,
    include_cms_auxiliary: bool = True,
) -> dict:
    """Run the Salvador production collection pipeline with explicit source-scoped coverage.

    `pipeline_complete` means every configured production step was attempted and represented in the
    final manifest. It never means every public record that may exist in Salvador was retrieved.
    """
    if end < start:
        raise ValueError("end anterior a start")

    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    workspace = load_city(repo_root, "salvador")
    city = workspace.config
    manifest = CoverageManifest(city_slug=city.slug, period_start=start.isoformat(), period_end=end.isoformat())
    errors: list[dict] = []
    outputs: dict[str, str] = {}
    pncp_paths: list[Path] = []
    pncp_paths_by_scope: dict[str, Path] = {}
    pncp_procurement_complete: dict[str, bool] = {}
    contract_paths: list[Path] = []
    cms_expense_path: Path | None = None

    def attempt(name: str, fn: Callable[[], object]) -> object | None:
        try:
            return fn()
        except Exception as exc:
            errors.append({"step": name, "error_type": type(exc).__name__, "error": str(exc)})
            return None

    # Executivo: receita e execução agregada da despesa.
    finance_dir = out_dir / "prefeitura_finance"
    finance_result = attempt("prefeitura_finance", lambda: salvador_portal.collect(city, start, end, finance_dir))
    if finance_result:
        summary_path = finance_dir / "summary.json"
        summary = _read_json(summary_path)
        counts = summary.get("record_counts") or {}
        outputs["prefeitura_finance_summary"] = _relative(summary_path, repo_root)
        manifest.add(CoverageEntry(
            dataset="prefeitura_finance",
            source_system=salvador_portal.SOURCE_SYSTEM,
            status="complete_for_filter",
            period_start=start.isoformat(), period_end=end.isoformat(),
            records=sum(int(v or 0) for v in counts.values()),
            source_url=salvador_portal.PUBLIC_PORTAL,
            evidence_path=_relative(summary_path, repo_root),
            note="Complete for the unfiltered finance endpoints requested by this adapter and date interval; creditor rows are aggregates, not individual payments.",
        ))
    else:
        manifest.add(CoverageEntry(
            dataset="prefeitura_finance", source_system=salvador_portal.SOURCE_SYSTEM, status="unavailable",
            period_start=start.isoformat(), period_end=end.isoformat(), source_url=salvador_portal.PUBLIC_PORTAL,
            note="Collector was attempted but the public source did not complete successfully in this run.",
        ))

    # Executivo: catálogo municipal de aquisições.
    acquisitions_dir = out_dir / "prefeitura_acquisitions"
    acquisitions_result = attempt("prefeitura_acquisitions", lambda: salvador_acquisitions.collect(city, start, end, acquisitions_dir))
    acquisition_jsonl: Path | None = None
    if acquisitions_result:
        acquisition_jsonl = acquisitions_dir / "acquisitions.jsonl"
        acq_summary = _read_json(acquisitions_dir / "summary.json")
        complete = bool(acq_summary.get("complete_for_filter"))
        manifest.add(CoverageEntry(
            dataset="prefeitura_acquisitions",
            source_system=salvador_portal.SOURCE_SYSTEM,
            status="complete_for_filter" if complete else "partial",
            period_start=start.isoformat(), period_end=end.isoformat(),
            records=int(acq_summary.get("unique_stable_records") or 0),
            pages=int(acq_summary.get("pages_collected") or 0),
            source_url=salvador_portal.PUBLIC_PORTAL,
            evidence_path=_relative(acquisitions_dir / "summary.json", repo_root),
            note=(
                "Complete only for the unfiltered official Salvador acquisition API and requested interval; this does not prove completeness across PNCP or sectoral systems."
                if complete else
                "The official Salvador acquisition API collection did not satisfy its own reported count/page completeness checks."
            ),
        ))
        outputs["prefeitura_acquisitions"] = _relative(acquisition_jsonl, repo_root)
    else:
        manifest.add(CoverageEntry(
            dataset="prefeitura_acquisitions", source_system=salvador_portal.SOURCE_SYSTEM, status="unavailable",
            period_start=start.isoformat(), period_end=end.isoformat(), source_url=salvador_portal.PUBLIC_PORTAL,
            note="Collector was attempted but the public source did not complete successfully in this run.",
        ))

    # Executivo: grade detalhada municipal de contratos. A própria cobertura registra timeouts/lacunas.
    municipal_contract_dir = out_dir / "prefeitura_contracts"
    municipal_contract_path = attempt(
        "prefeitura_contracts",
        lambda: salvador_contracts.collect(city, start, end, municipal_contract_dir),
    )
    if municipal_contract_path:
        contract_cov = _read_json(municipal_contract_dir / "coverage.json")
        complete = bool(contract_cov.get("complete_for_filter"))
        outputs["prefeitura_contract_grid"] = _relative(municipal_contract_path, repo_root)
        manifest.add(CoverageEntry(
            dataset="prefeitura_contract_grid",
            source_system=salvador_contracts.SOURCE_SYSTEM,
            status="complete_for_filter" if complete else "partial",
            period_start=start.isoformat(), period_end=end.isoformat(),
            records=int(contract_cov.get("records_unique") or _count_jsonl(municipal_contract_path)),
            source_url=salvador_contracts.PUBLIC_PORTAL,
            evidence_path=_relative(municipal_contract_dir / "coverage.json", repo_root),
            note=str(contract_cov.get("coverage_note") or "Official municipal detailed contract grid coverage."),
        ))
    else:
        manifest.add(CoverageEntry(
            dataset="prefeitura_contract_grid", source_system=salvador_contracts.SOURCE_SYSTEM, status="unavailable",
            period_start=start.isoformat(), period_end=end.isoformat(), source_url=salvador_contracts.PUBLIC_PORTAL,
            note="The official detailed municipal contract route was attempted but the collector itself could not finish or write coverage.",
        ))

    # Legislativo: empenhos da visão pública padrão do ScriptCase.
    commitments_dir = out_dir / "cms_commitments"
    commitment_result = attempt("cms_commitments", lambda: cms_commitments.collect(repo_root, commitments_dir))
    if commitment_result:
        coverage = commitment_result["coverage"]
        output = commitment_result["output"]
        cms_expense_path = commitment_result.get("expense_output")
        outputs["cms_commitments"] = _relative(output, repo_root)
        if cms_expense_path:
            outputs["cms_expense_events"] = _relative(cms_expense_path, repo_root)
        manifest.add(CoverageEntry(
            dataset="cms_commitments",
            source_system=cms_commitments.SOURCE_SYSTEM,
            status="complete_for_filter" if coverage.get("complete") else "partial",
            records=int(coverage.get("records_parsed") or coverage.get("records_visible_and_parsed") or 0),
            pages=int(coverage.get("pages_with_records") or 0),
            source_url=cms_commitments.URL,
            evidence_path=_relative(commitments_dir / "coverage.json", repo_root),
            note=str(coverage.get("coverage_note") or "Public Câmara commitment ledger coverage as reported by collector."),
        ))
    else:
        manifest.add(CoverageEntry(
            dataset="cms_commitments", source_system=cms_commitments.SOURCE_SYSTEM, status="unavailable",
            source_url=cms_commitments.URL, note="Câmara commitment collector failed in this run; no completeness claim is made.",
        ))

    if include_cms_auxiliary:
        auxiliary_dir = out_dir / "cms_auxiliary"
        travel = attempt("cms_travel", lambda: cms.collect_travel(auxiliary_dir))
        if travel:
            travel_cov = _read_json(auxiliary_dir / "cms_travel_expenses.coverage.json")
            outputs["cms_travel"] = _relative(travel, repo_root)
            manifest.add(CoverageEntry(
                dataset="cms_travel_expenses", source_system="CMS", status="complete_for_filter" if travel_cov.get("complete") else "partial",
                records=int(travel_cov.get("records") or 0), pages=int(travel_cov.get("pages_collected") or 0), source_url=cms.TRAVEL_URL,
                evidence_path=_relative(auxiliary_dir / "cms_travel_expenses.coverage.json", repo_root),
                note="Complete means the CMS travel page pagination reached source exhaustion without a blocking status; it is not a statement about unrelated expense systems." if travel_cov.get("complete") else "The CMS travel source stopped pagination; collected rows remain valid but coverage is partial.",
            ))
        else:
            manifest.add(CoverageEntry(dataset="cms_travel_expenses", source_system="CMS", status="unavailable", source_url=cms.TRAVEL_URL, note="Collector failed in this run."))

        documents = attempt("cms_documents", lambda: cms.collect_document_catalog(auxiliary_dir))
        if documents:
            doc_cov = _read_json(auxiliary_dir / "cms_documents.coverage.json")
            sections = doc_cov.get("sections") or {}
            complete = bool(sections) and all(bool(v.get("complete")) for v in sections.values())
            outputs["cms_documents"] = _relative(documents, repo_root)
            manifest.add(CoverageEntry(
                dataset="cms_document_catalog", source_system="CMS", status="complete_for_filter" if complete else "partial",
                records=int(doc_cov.get("records") or 0), source_url="https://www.cms.ba.gov.br/transparencia",
                evidence_path=_relative(auxiliary_dir / "cms_documents.coverage.json", repo_root),
                note="Complete only for the configured CMS transparency document sections and their pagination." if complete else "At least one configured CMS document section did not reach source exhaustion.",
            ))
        else:
            manifest.add(CoverageEntry(dataset="cms_document_catalog", source_system="CMS", status="unavailable", source_url="https://www.cms.ba.gov.br/transparencia", note="Collector failed in this run."))

        certames = attempt("cms_certames_visible", lambda: cms.collect_certames_visible(auxiliary_dir))
        if certames:
            outputs["cms_certames_visible"] = _relative(certames, repo_root)
            manifest.add(CoverageEntry(
                dataset="cms_certames_visible", source_system="CMS_CERTAMES", status="partial",
                records=_count_jsonl(certames), source_url=cms.CERTAMES_URL,
                evidence_path=_relative(certames, repo_root),
                note="The ScriptCase server-visible page is collected, but complete catalogue pagination has not yet been proven by this collector.",
            ))
        else:
            manifest.add(CoverageEntry(dataset="cms_certames_visible", source_system="CMS_CERTAMES", status="unavailable", source_url=cms.CERTAMES_URL, note="Collector failed in this run."))

    # PNCP: aquisições por poder, como fonte complementar/reconciliação.
    if include_pncp:
        for scope in ("executivo", "legislativo"):
            pncp_dir = out_dir / f"pncp_{scope}"
            path = attempt(f"pncp_{scope}", lambda scope=scope, pncp_dir=pncp_dir: pncp.collect(city, start, end, pncp_dir, scope=scope))
            if path:
                pncp_paths.append(path)
                pncp_paths_by_scope[scope] = path
                cov = _read_json(pncp_dir / "coverage.json")
                complete = bool(cov.get("complete"))
                pncp_procurement_complete[scope] = complete
                outputs[f"pncp_{scope}"] = _relative(path, repo_root)
                manifest.add(CoverageEntry(
                    dataset=f"pncp_procurements_{scope}", source_system="PNCP",
                    status="complete_for_filter" if complete else "partial",
                    period_start=start.isoformat(), period_end=end.isoformat(), records=int(cov.get("records") or _count_jsonl(path)),
                    source_url=pncp.PNCP_ENDPOINT,
                    evidence_path=_relative(pncp_dir / "coverage.json", repo_root),
                    note=("Complete for the PNCP query dimensions used by the collector and requested interval." if complete else "PNCP stopped the collection (for example by rate limiting); persisted records remain valid but coverage is partial."),
                ))
            else:
                pncp_procurement_complete[scope] = False
                manifest.add(CoverageEntry(
                    dataset=f"pncp_procurements_{scope}", source_system="PNCP", status="unavailable",
                    period_start=start.isoformat(), period_end=end.isoformat(), source_url=pncp.PNCP_ENDPOINT,
                    note="PNCP collector failed in this run; municipal sources remain independently valid.",
                ))

        # PNCP contracts: only CNPJs discovered in each scope plus the configured municipality CNPJ.
        for scope in ("executivo", "legislativo"):
            procurement_path = pncp_paths_by_scope.get(scope)
            if not procurement_path:
                manifest.add(CoverageEntry(
                    dataset=f"pncp_contracts_{scope}", source_system="PNCP", status="not_run",
                    period_start=start.isoformat(), period_end=end.isoformat(), source_url=pncp_contracts.PNCP_CONTRACTS_ENDPOINT,
                    note="Contract queries were not run because no PNCP procurement output for this scope was available to discover agency CNPJs.",
                ))
                continue
            cnpjs = set(pncp_contracts.agency_cnpjs_from_procurements([procurement_path]))
            if city.municipality_cnpj:
                cnpjs.add(city.municipality_cnpj)
            contract_dir = out_dir / f"pncp_contracts_{scope}"
            path = attempt(
                f"pncp_contracts_{scope}",
                lambda scope=scope, contract_dir=contract_dir, cnpjs=cnpjs: pncp_contracts.collect(
                    city, start, end, contract_dir, agency_cnpjs=cnpjs, scope=scope
                ),
            )
            if path:
                cov = _read_json(contract_dir / "coverage.json")
                queries_complete = bool(cov.get("complete_for_supplied_agencies_and_filter"))
                upstream_complete = bool(pncp_procurement_complete.get(scope))
                complete = queries_complete and upstream_complete
                contract_paths.append(path)
                outputs[f"pncp_contracts_{scope}"] = _relative(path, repo_root)
                manifest.add(CoverageEntry(
                    dataset=f"pncp_contracts_{scope}", source_system="PNCP",
                    status="complete_for_filter" if complete else "partial",
                    period_start=start.isoformat(), period_end=end.isoformat(),
                    records=int(cov.get("records_after_salvador_scope_filter") or _count_jsonl(path)),
                    source_url=pncp_contracts.PNCP_CONTRACTS_ENDPOINT,
                    evidence_path=_relative(contract_dir / "coverage.json", repo_root),
                    note=(
                        "Complete for PNCP contract queries over the agency CNPJs discovered from a complete PNCP procurement run for the same scope and interval."
                        if complete else
                        "Partial overall: either at least one PNCP contract query was incomplete or the upstream procurement run did not prove that the supplied agency-CNPJ set was complete."
                    ),
                ))
            else:
                manifest.add(CoverageEntry(
                    dataset=f"pncp_contracts_{scope}", source_system="PNCP", status="unavailable",
                    period_start=start.isoformat(), period_end=end.isoformat(), source_url=pncp_contracts.PNCP_CONTRACTS_ENDPOINT,
                    note="PNCP contract collection was attempted for discovered agency CNPJs but failed before a coverage file could be used.",
                ))
    else:
        for scope in ("executivo", "legislativo"):
            manifest.add(CoverageEntry(
                dataset=f"pncp_procurements_{scope}", source_system="PNCP", status="not_run",
                period_start=start.isoformat(), period_end=end.isoformat(), source_url=pncp.PNCP_ENDPOINT,
                note="PNCP collection was explicitly skipped for this run.",
            ))
            manifest.add(CoverageEntry(
                dataset=f"pncp_contracts_{scope}", source_system="PNCP", status="not_run",
                period_start=start.isoformat(), period_end=end.isoformat(), source_url=pncp_contracts.PNCP_CONTRACTS_ENDPOINT,
                note="PNCP collection was explicitly skipped for this run.",
            ))

    # Exact-only procurement reconciliation. No fuzzy matching is promoted to fact.
    reference_procurement = pncp_paths_by_scope.get("executivo")
    if acquisition_jsonl and reference_procurement:
        reconciliation_path = out_dir / "reconciliation" / "prefeitura_vs_pncp_executivo.jsonl"
        attempt("reconcile_prefeitura_pncp", lambda: write_reconciliation(acquisition_jsonl, reference_procurement, reconciliation_path))
        if reconciliation_path.exists():
            outputs["reconciliation_prefeitura_pncp"] = _relative(reconciliation_path, repo_root)

    # Rebuildable query database.
    db_path = out_dir / "salvador.db"
    attempt("build_db", lambda: build_db(db_path, workspace, pncp_jsonl=pncp_paths, contract_jsonl=contract_paths))
    if db_path.exists():
        revenue_path = finance_dir / "revenue_events.jsonl"
        revenue_paths = [revenue_path] if revenue_path.exists() else []
        expense_paths = [cms_expense_path] if cms_expense_path and cms_expense_path.exists() else []
        attempt("ingest_events", lambda: ingest_events(db_path, revenue_jsonl=revenue_paths, expense_jsonl=expense_paths))
        outputs["sqlite"] = _relative(db_path, repo_root)

    coverage_path = manifest.write(out_dir / "project_coverage.json")
    outputs["coverage"] = _relative(coverage_path, repo_root)
    report = {
        "city": asdict(city),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_status": "pipeline_complete",
        "status_meaning": "All configured production steps were attempted. Dataset completeness remains source-scoped and is reported in project_coverage.json.",
        "coverage_counts": manifest.counts_by_status,
        "errors": errors,
        "outputs": outputs,
        "methodology": [
            "No source, no fact.",
            "Raw source snapshots carry SHA-256 provenance where the collector supports snapshots.",
            "Commitment, liquidation and payment are never conflated.",
            "Aggregate institutional spending is never attributed to an individual.",
            "Identity links require exact official evidence or a documented alias; name similarity alone is not a match.",
            "High value, concentration, dispensa or inexigibilidade are descriptive audit signals, not proof of irregularity.",
            "Reconciliation uses exact normalized identifiers only; ambiguity remains ambiguity.",
            "A failed source query is represented as partial/unavailable, never as zero records.",
        ],
    }
    report_path = out_dir / "project_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["report"] = _relative(report_path, repo_root)
    return report
