from __future__ import annotations

import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from transparencia.collectors import pncp, pncp_contracts
from transparencia.config import load_city

ROOT = Path('.')
CITY_SLUG = 'salvador'
SNAPSHOTS_ROOT = Path('cities/salvador/data/snapshots')
VALIDATION_ROOT = Path('cities/salvador/data/validation')


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def line_count(path: Path | None) -> int:
    if not path or not path.exists():
        return 0
    with path.open('r', encoding='utf-8') as handle:
        return sum(1 for line in handle if line.strip())


def normalize_cnpj(value: object) -> str | None:
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    return digits if len(digits) == 14 else None


def normalize_cnpjs(values) -> set[str]:
    result: set[str] = set()
    for value in values or []:
        cnpj = normalize_cnpj(value)
        if cnpj:
            result.add(cnpj)
    return result


def first_jsonl(directory: Path, prefix: str) -> Path | None:
    matches = sorted(directory.glob(f'{prefix}*.jsonl')) if directory.exists() else []
    return matches[0] if matches else None


def contract_records_from_coverage(coverage: dict) -> int:
    return int(coverage.get('records_after_salvador_scope_filter') or coverage.get('records') or 0)


def successful_query_cnpjs(coverage: dict) -> tuple[set[str], list[str]]:
    found: set[str] = set()
    failures: list[str] = []
    for query in coverage.get('queries') or []:
        cnpj = normalize_cnpj(query.get('cnpj_orgao'))
        if cnpj:
            found.add(cnpj)
        if query.get('complete') is not True or query.get('error'):
            failures.append(cnpj or '<sem-cnpj>')
    return found, failures


def build_summary(*, today: date, start: date, municipal_cnpj: str | None,
                  discovered_cnpjs: set[str], supplied_cnpjs: set[str],
                  procurement_path: Path | None, procurement_cov: dict,
                  contract_path: Path | None, contract_cov: dict,
                  retained_cnpjs: set[str], errors: list[dict],
                  collection_mode: str) -> dict:
    procurement_records = line_count(procurement_path)
    contract_records = line_count(contract_path)
    discovery_complete = bool(procurement_cov.get('complete'))
    contracts_complete = bool(contract_cov.get('complete_for_supplied_agencies_and_filter'))
    contract_scope = normalize_cnpjs(contract_cov.get('agency_cnpjs'))
    discovery_scope = set(discovered_cnpjs)
    if municipal_cnpj:
        discovery_scope.add(municipal_cnpj)
    complete_for_discovered = (
        discovery_complete
        and contracts_complete
        and discovery_scope.issubset(contract_scope)
    )
    return {
        'observed_at_date': today.isoformat(),
        'period_start': start.isoformat(),
        'period_end': today.isoformat(),
        'role': 'complementary_only',
        'collection_mode': collection_mode,
        'agency_cnpjs_supplied': sorted(supplied_cnpjs),
        'agency_cnpjs_discovered_from_procurements': sorted(
            cnpj for cnpj in discovered_cnpjs if cnpj != municipal_cnpj
        ),
        'agency_cnpjs_retained_from_history': sorted(retained_cnpjs),
        'agency_cnpj_discovery_complete': discovery_complete,
        'procurements': {
            'ran': procurement_path is not None,
            'complete_for_municipal_filter': discovery_complete,
            'records': procurement_records,
            'stopped_status': procurement_cov.get('stopped_status'),
            'adaptive_splits': len(procurement_cov.get('adaptive_splits') or []),
            'terminal_failures': len(procurement_cov.get('terminal_failures') or []),
        },
        'contracts': {
            'ran': contract_path is not None,
            'complete_for_supplied_agencies_and_filter': contracts_complete,
            'complete_for_discovered_municipal_agencies_and_filter': complete_for_discovered,
            'records': contract_records,
            'query_errors': len(contract_cov.get('errors') or []),
        },
        'errors': errors,
        'coverage_rule': (
            'PNCP is complementary only. Agency CNPJs are discovered from PNCP municipal procurements for Salvador; '
            'previously validated agency CNPJs may be retained across retries, and the configured municipality CNPJ is added when valid. '
            'Municipal-agency discovery is complete only when every modality/date segment reaches a normal source end, including adaptively split recovery segments. '
            'Contract coverage is complete only for the explicitly supplied CNPJ set when every CNPJ/date contract query reaches a normal source end. '
            'No timeout, HTTP error or missing query is interpreted as zero records.'
        ),
    }


def validate_bundle(*, procurement_path: Path | None, procurement_cov: dict,
                    contract_path: Path | None, contract_cov: dict,
                    supplied_cnpjs: set[str], discovered_cnpjs: set[str],
                    municipal_cnpj: str | None) -> list[str]:
    issues: list[str] = []
    actual_procurements = line_count(procurement_path)
    declared_procurements = int(procurement_cov.get('records') or 0)
    if procurement_path is None:
        issues.append('procurement_jsonl_missing')
    elif actual_procurements != declared_procurements:
        issues.append(f'procurement_count_mismatch:{actual_procurements}!={declared_procurements}')

    actual_contracts = line_count(contract_path)
    declared_contracts = contract_records_from_coverage(contract_cov)
    if contract_path is None:
        issues.append('contract_jsonl_missing')
    elif actual_contracts != declared_contracts:
        issues.append(f'contract_count_mismatch:{actual_contracts}!={declared_contracts}')

    coverage_cnpjs = normalize_cnpjs(contract_cov.get('agency_cnpjs'))
    if coverage_cnpjs != supplied_cnpjs:
        issues.append(
            'contract_coverage_cnpjs_mismatch:'
            f'{sorted(coverage_cnpjs)}!={sorted(supplied_cnpjs)}'
        )

    if contract_cov.get('complete_for_supplied_agencies_and_filter') is True:
        query_cnpjs, failed_queries = successful_query_cnpjs(contract_cov)
        if failed_queries:
            issues.append(f'complete_contract_coverage_has_failed_queries:{sorted(failed_queries)}')
        if query_cnpjs != supplied_cnpjs:
            issues.append(
                'complete_contract_coverage_query_scope_mismatch:'
                f'{sorted(query_cnpjs)}!={sorted(supplied_cnpjs)}'
            )
        if contract_cov.get('errors'):
            issues.append('complete_contract_coverage_has_errors')

    if procurement_cov.get('complete') is True:
        discovery_scope = set(discovered_cnpjs)
        if municipal_cnpj:
            discovery_scope.add(municipal_cnpj)
        if not discovery_scope.issubset(coverage_cnpjs):
            issues.append(
                'complete_discovery_not_covered_by_contract_scope:'
                f'{sorted(discovery_scope - coverage_cnpjs)}'
            )

    return issues


def quality(summary: dict) -> tuple[int, int, int, int, int]:
    procurement = summary.get('procurements') or {}
    contracts = summary.get('contracts') or {}
    return (
        1 if summary.get('agency_cnpj_discovery_complete') else 0,
        1 if contracts.get('complete_for_supplied_agencies_and_filter') else 0,
        len(summary.get('agency_cnpjs_supplied') or []),
        int(procurement.get('records') or 0),
        int(contracts.get('records') or 0),
    )


def canonical_reconciliation(*, canonical_root: Path, today: date, start: date,
                             municipal_cnpj: str | None) -> dict:
    procurement_dir = canonical_root / 'procurements'
    contract_dir = canonical_root / 'contracts'
    procurement_path = first_jsonl(procurement_dir, 'contratacoes_')
    contract_path = first_jsonl(contract_dir, 'contratos_')
    procurement_cov = read_json(procurement_dir / 'coverage.json', {})
    contract_cov = read_json(contract_dir / 'coverage.json', {})
    discovered = set()
    if procurement_path:
        discovered.update(pncp_contracts.agency_cnpjs_from_procurements([procurement_path]))
    contract_scope = normalize_cnpjs(contract_cov.get('agency_cnpjs'))
    supplied = set(contract_scope)
    discovery_scope = set(discovered)
    if municipal_cnpj:
        discovery_scope.add(municipal_cnpj)

    issues = validate_bundle(
        procurement_path=procurement_path,
        procurement_cov=procurement_cov,
        contract_path=contract_path,
        contract_cov=contract_cov,
        supplied_cnpjs=supplied,
        discovered_cnpjs=discovered,
        municipal_cnpj=municipal_cnpj,
    )
    exact_scope_match = bool(discovery_scope) and discovery_scope == contract_scope
    can_close = (
        not issues
        and procurement_cov.get('complete') is True
        and contract_cov.get('complete_for_supplied_agencies_and_filter') is True
        and exact_scope_match
    )

    report = {
        'checked_at': datetime.now(ZoneInfo('America/Bahia')).isoformat(),
        'canonical_consistent': not issues,
        'issues': issues,
        'procurement_records_actual': line_count(procurement_path),
        'procurement_records_declared': int(procurement_cov.get('records') or 0),
        'contract_records_actual': line_count(contract_path),
        'contract_records_declared': contract_records_from_coverage(contract_cov),
        'discovered_cnpjs': sorted(discovered),
        'discovery_scope_with_configured_municipality': sorted(discovery_scope),
        'contract_coverage_cnpjs': sorted(contract_scope),
        'exact_cnpj_scope_match': exact_scope_match,
        'can_close_discovery_and_contract_scope': can_close,
    }

    if can_close:
        summary = build_summary(
            today=today,
            start=start,
            municipal_cnpj=municipal_cnpj,
            discovered_cnpjs=discovered,
            supplied_cnpjs=contract_scope,
            procurement_path=procurement_path,
            procurement_cov=procurement_cov,
            contract_path=contract_path,
            contract_cov=contract_cov,
            retained_cnpjs=set(),
            errors=[],
            collection_mode='pncp_reconciled_complete_discovery_and_exact_contract_scope',
        )
        summary['reconciliation'] = {
            'method': 'exact_cnpj_set_and_normalized_row_count_consistency',
            'procurement_and_contract_scope_match': True,
            'no_fuzzy_identity_matching': True,
        }
        write_json(canonical_root / 'summary.json', summary)
        report['canonical_summary_updated'] = True
    else:
        report['canonical_summary_updated'] = False

    write_json(VALIDATION_ROOT / 'pncp_complementary_reconciliation.json', report)
    return report


def copy_candidate_to_canonical(*, candidate_root: Path, canonical_root: Path,
                                procurement_path: Path, contract_path: Path,
                                summary: dict) -> None:
    pairs = [
        (procurement_path, canonical_root / 'procurements' / procurement_path.name),
        (candidate_root / 'procurements' / 'coverage.json', canonical_root / 'procurements' / 'coverage.json'),
        (contract_path, canonical_root / 'contracts' / contract_path.name),
        (candidate_root / 'contracts' / 'coverage.json', canonical_root / 'contracts' / 'coverage.json'),
    ]
    for source, destination in pairs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    write_json(canonical_root / 'summary.json', summary)


def main() -> None:
    now = datetime.now(ZoneInfo('America/Bahia'))
    today = now.date()
    start = date(today.year, 1, 1)
    canonical_root = SNAPSHOTS_ROOT / today.isoformat() / 'pncp_complementary'
    canonical_root.mkdir(parents=True, exist_ok=True)
    VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)

    city = load_city(ROOT, CITY_SLUG).config
    municipal_cnpj = normalize_cnpj(city.municipality_cnpj)

    reconciliation = canonical_reconciliation(
        canonical_root=canonical_root,
        today=today,
        start=start,
        municipal_cnpj=municipal_cnpj,
    )

    baseline_summary = read_json(canonical_root / 'summary.json', {})
    known_cnpjs = normalize_cnpjs(baseline_summary.get('agency_cnpjs_supplied'))
    prior_summaries = sorted(
        path for path in SNAPSHOTS_ROOT.glob('*/pncp_complementary/summary.json')
        if path.parent.parent.name < today.isoformat()
    )
    if prior_summaries:
        known_cnpjs.update(normalize_cnpjs(read_json(prior_summaries[-1], {}).get('agency_cnpjs_supplied')))

    run_id = os.environ.get('GITHUB_RUN_ID') or now.strftime('%Y%m%dT%H%M%S')
    run_attempt = os.environ.get('GITHUB_RUN_ATTEMPT') or '1'
    attempt_id = f'{run_id}-{run_attempt}'
    attempt_root = canonical_root / 'attempts' / attempt_id
    if attempt_root.exists():
        attempt_root = canonical_root / 'attempts' / f'{attempt_id}-{now.strftime("%H%M%S%f")}'
    candidate_root = attempt_root / 'candidate'
    procurement_dir = candidate_root / 'procurements'
    contract_dir = candidate_root / 'contracts'
    candidate_root.mkdir(parents=True, exist_ok=True)

    errors: list[dict] = []
    procurement_path: Path | None = None
    procurement_cov: dict = {}
    contract_path: Path | None = None
    contract_cov: dict = {}
    discovered_cnpjs: set[str] = set()

    try:
        procurement_path = pncp.collect(
            city,
            start,
            today,
            procurement_dir,
            scope='municipal',
            page_size=50,
            sleep_seconds=0.5,
        )
        procurement_cov = read_json(procurement_dir / 'coverage.json', {})
        if procurement_path and procurement_path.exists():
            discovered_cnpjs.update(pncp_contracts.agency_cnpjs_from_procurements([procurement_path]))
    except Exception as exc:
        errors.append({'step': 'agency_discovery', 'type': type(exc).__name__, 'error': str(exc)})
        procurement_cov = read_json(procurement_dir / 'coverage.json', {})
        procurement_path = first_jsonl(procurement_dir, 'contratacoes_')
        if procurement_path:
            discovered_cnpjs.update(pncp_contracts.agency_cnpjs_from_procurements([procurement_path]))

    supplied_cnpjs = set(known_cnpjs) | set(discovered_cnpjs)
    if municipal_cnpj:
        supplied_cnpjs.add(municipal_cnpj)
    else:
        errors.append({
            'step': 'configuration',
            'type': 'MissingMunicipalityCNPJ',
            'error': 'city.municipality_cnpj is not a 14-digit CNPJ',
        })

    if supplied_cnpjs:
        try:
            contract_path = pncp_contracts.collect(
                city,
                start,
                today,
                contract_dir,
                agency_cnpjs=sorted(supplied_cnpjs),
                scope='municipal',
                page_size=500,
                window_days=366,
                sleep_seconds=2.0,
                max_attempts=5,
            )
            contract_cov = read_json(contract_dir / 'coverage.json', {})
        except Exception as exc:
            errors.append({'step': 'contracts', 'type': type(exc).__name__, 'error': str(exc)})
            contract_cov = read_json(contract_dir / 'coverage.json', {})
            contract_path = first_jsonl(contract_dir, 'contratos_')
    else:
        errors.append({
            'step': 'contracts',
            'type': 'MissingAgencyCNPJ',
            'error': 'no valid municipal agency CNPJ was available for PNCP contract collection',
        })

    retained_cnpjs = known_cnpjs - discovered_cnpjs
    if municipal_cnpj:
        retained_cnpjs.discard(municipal_cnpj)
    summary = build_summary(
        today=today,
        start=start,
        municipal_cnpj=municipal_cnpj,
        discovered_cnpjs=discovered_cnpjs,
        supplied_cnpjs=supplied_cnpjs,
        procurement_path=procurement_path,
        procurement_cov=procurement_cov,
        contract_path=contract_path,
        contract_cov=contract_cov,
        retained_cnpjs=retained_cnpjs,
        errors=errors,
        collection_mode='pncp_staged_municipal_discovery_plus_retained_and_configured_cnpj',
    )
    write_json(candidate_root / 'summary.json', summary)

    consistency_issues = validate_bundle(
        procurement_path=procurement_path,
        procurement_cov=procurement_cov,
        contract_path=contract_path,
        contract_cov=contract_cov,
        supplied_cnpjs=supplied_cnpjs,
        discovered_cnpjs=discovered_cnpjs,
        municipal_cnpj=municipal_cnpj,
    )

    baseline_score = quality(baseline_summary) if baseline_summary else None
    candidate_score = quality(summary)
    promoted = False
    reason = 'candidate_inconsistent'

    if not consistency_issues and procurement_path and contract_path:
        suspicious_drop = False
        if baseline_summary:
            baseline_scope = normalize_cnpjs(baseline_summary.get('agency_cnpjs_supplied'))
            baseline_contracts = int((baseline_summary.get('contracts') or {}).get('records') or 0)
            candidate_contracts = int((summary.get('contracts') or {}).get('records') or 0)
            if baseline_scope.issubset(supplied_cnpjs) and candidate_contracts < baseline_contracts:
                suspicious_drop = True
        if suspicious_drop:
            reason = 'candidate_complete_scope_would_drop_contract_rows'
        elif baseline_score is not None and candidate_score < baseline_score:
            reason = 'candidate_regressed_against_canonical_baseline'
        else:
            copy_candidate_to_canonical(
                candidate_root=candidate_root,
                canonical_root=canonical_root,
                procurement_path=procurement_path,
                contract_path=contract_path,
                summary=summary,
            )
            promoted = True
            reason = 'candidate_consistent_and_not_regressive'

    attempt_report = {
        'observed_at': now.isoformat(),
        'attempt_id': attempt_root.name,
        'candidate_score': list(candidate_score),
        'baseline_score': list(baseline_score) if baseline_score is not None else None,
        'candidate_consistent': not consistency_issues,
        'consistency_issues': consistency_issues,
        'promoted_to_canonical': promoted,
        'reason': reason,
        'candidate_summary': summary,
        'canonical_reconciliation_before_attempt': reconciliation,
    }
    write_json(attempt_root / 'attempt_report.json', attempt_report)
    write_json(VALIDATION_ROOT / 'pncp_complementary_last_attempt.json', attempt_report)

    final_reconciliation = canonical_reconciliation(
        canonical_root=canonical_root,
        today=today,
        start=start,
        municipal_cnpj=municipal_cnpj,
    )
    print(json.dumps({
        'attempt': attempt_report,
        'canonical_after_attempt': final_reconciliation,
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
