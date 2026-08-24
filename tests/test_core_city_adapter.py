import json

import pytest

from transparencia.coverage import CoverageEntry, CoverageManifest
from transparencia.history import ComparableSnapshot, diff_snapshots
from transparencia.policies import AccountingAmounts, is_business_cnpj, require_exact_evidence
from transparencia.reconcile import normalize_identifier, reconcile_exact


def test_complete_coverage_requires_scope_and_source_reconciliation(tmp_path):
    with pytest.raises(ValueError):
        CoverageEntry(dataset="contracts", source_system="CITY_API", status="complete_for_filter")

    with pytest.raises(ValueError):
        CoverageEntry(
            dataset="contracts",
            source_system="CITY_API",
            status="complete_for_filter",
            records=9,
            reported_total=10,
            note="complete for date filter",
        )

    manifest = CoverageManifest(city_slug="example", period_start="2026-01-01", period_end="2026-08-23")
    manifest.add(
        CoverageEntry(
            dataset="contracts",
            source_system="CITY_API",
            status="complete_for_filter",
            period_start="2026-01-01",
            period_end="2026-08-22",
            records=10,
            pages=2,
            reported_total=10,
            reported_pages=2,
            note="Complete only for the official API and stated date filter.",
        )
    )
    path = manifest.write(tmp_path / "coverage.json")
    data = json.loads(path.read_text())
    assert data["counts_by_status"]["complete_for_filter"] == 1
    assert data["latest_source_as_of"] == "2026-08-22"


def test_exact_reconciliation_ignores_names_and_objects():
    assert normalize_identifier(" 123/2026-ABC ") == "1232026ABC"
    local = [
        {
            "source_system": "CITY_API",
            "source_record_key": "local-1",
            "process_number": "12/2026",
            "notice_number": "PE-1",
            "year": 2026,
            "object": "same object words",
        }
    ]
    reference = [
        {
            "source_record_key": "ref-1",
            "process_number": "12-2026",
            "notice_number": "PE/1",
            "year": 2026,
            "object": "different text",
        },
        {
            "source_record_key": "ref-2",
            "process_number": "99/2026",
            "notice_number": "PE-99",
            "year": 2026,
            "object": "same object words",
        },
    ]
    result = reconcile_exact(local, reference)[0]
    assert result["status"] == "exact_match"
    assert result["reference_record_keys"] == ["ref-1"]


def test_exact_reconciliation_preserves_ambiguity():
    local = [{"source_record_key": "local", "process_number": "7/2026"}]
    reference = [
        {"source_record_key": "a", "process_number": "7-2026"},
        {"source_record_key": "b", "process_number": "7/2026"},
    ]
    assert reconcile_exact(local, reference)[0]["status"] == "multiple_candidates"


def test_pncp_procurement_control_is_a_direct_exact_identity():
    procurement = [{
        "source_system": "PNCP",
        "source_record_key": "purchase",
        "pncp_procurement_control_number": "40.637.159/0001-36-1-000124/2026",
        "process_number": "purchase-process",
        "object": "coffee",
    }]
    contracts = [{
        "source_record_key": "contract",
        "pncp_procurement_control_number": "40637159000136-1-000124/2026",
        "process_number": "different-process",
        "object": "completely different text",
    }]
    result = reconcile_exact(procurement, contracts)[0]
    assert result["status"] == "exact_match"
    assert result["reference_record_keys"] == ["contract"]
    assert {row["name"] for row in result["matched_keys"]} == {"pncp_procurement_control"}


def test_history_requires_complete_same_source_and_exact_identity():
    previous = ComparableSnapshot.from_rows(
        source_system="CITY_CONTRACTS",
        as_of="2026-08-20",
        complete_for_filter=True,
        rows=[
            {"management_unit": "100", "contract_number": "CT-1", "status": "active", "value": 10},
            {"management_unit": "100", "contract_number": "CT-2", "status": "active", "value": 20},
        ],
    )
    current = ComparableSnapshot.from_rows(
        source_system="CITY_CONTRACTS",
        as_of="2026-08-23",
        complete_for_filter=True,
        rows=[
            {"management_unit": "100", "contract_number": "CT/1", "status": "closed", "value": 10},
            {"management_unit": "100", "contract_number": "CT-3", "status": "active", "value": 30},
        ],
    )
    events = diff_snapshots(
        previous,
        current,
        identity_fields=("management_unit", "contract_number"),
        tracked_fields=("status", "value"),
    )
    assert [event["type"] for event in events] == ["changed", "removed", "added"]
    assert events[0]["changes"]["status"] == {"before": "active", "after": "closed"}

    incomplete = ComparableSnapshot.from_rows(
        source_system="CITY_CONTRACTS",
        as_of="2026-08-24",
        complete_for_filter=False,
        rows=[],
    )
    with pytest.raises(ValueError):
        diff_snapshots(current, incomplete, identity_fields=("contract_number",), tracked_fields=("status",))


def test_privacy_and_accounting_invariants_are_explicit():
    assert is_business_cnpj("12.345.678/0001-90")
    assert not is_business_cnpj("123.456.789-00")
    require_exact_evidence("exact_process_number")
    with pytest.raises(ValueError):
        require_exact_evidence("supplier_name_similarity")
    assert AccountingAmounts(committed=100, liquidated=80, paid=70).to_dict() == {
        "committed": 100,
        "liquidated": 80,
        "paid": 70,
    }
