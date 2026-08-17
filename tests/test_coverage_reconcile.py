import json

import pytest

from transparencia.coverage import CoverageEntry, CoverageManifest
from transparencia.reconcile import normalize_identifier, reconcile_exact


def test_coverage_manifest_requires_scope_note_for_complete(tmp_path):
    with pytest.raises(ValueError):
        CoverageEntry(dataset="x", source_system="s", status="complete_for_filter")

    manifest = CoverageManifest(city_slug="salvador", period_start="2026-01-01", period_end="2026-08-17")
    manifest.add(CoverageEntry(
        dataset="acquisitions",
        source_system="SALVADOR_TRANSPARENCIA_API",
        status="complete_for_filter",
        period_start="2026-01-01",
        period_end="2026-08-17",
        records=2306,
        pages=231,
        note="Complete only for the official API and stated unfiltered date interval.",
    ))
    manifest.add(CoverageEntry(dataset="cms_commitments", source_system="CMS_EMPENHOS", status="partial", note="pagination not proven"))
    path = manifest.write(tmp_path / "coverage.json")
    data = json.loads(path.read_text())
    assert data["counts_by_status"]["complete_for_filter"] == 1
    assert data["counts_by_status"]["partial"] == 1


def test_identifier_normalization_is_exact_and_punctuation_insensitive():
    assert normalize_identifier(" 123/2026-ABC ") == "1232026ABC"
    assert normalize_identifier(None) is None


def test_reconcile_exact_does_not_fuzzy_match_objects():
    local = [{"source_system": "LOCAL", "source_record_key": "a", "process_number": "12/2026", "notice_number": "PE-1", "year": 2026}]
    reference = [
        {"pncp_control_number": "pncp-1", "process_number": "12-2026", "notice_number": "PE/1", "year": 2026},
        {"pncp_control_number": "pncp-2", "process_number": "99/2026", "notice_number": "PE-99", "year": 2026, "object": "same words"},
    ]
    rows = reconcile_exact(local, reference)
    assert rows[0]["status"] == "exact_match"
    assert rows[0]["reference_control_numbers"] == ["pncp-1"]


def test_reconcile_exact_preserves_ambiguity():
    local = [{"source_record_key": "a", "process_number": "7/2026"}]
    reference = [
        {"pncp_control_number": "p1", "process_number": "7-2026"},
        {"pncp_control_number": "p2", "process_number": "7/2026"},
    ]
    assert reconcile_exact(local, reference)[0]["status"] == "multiple_candidates"
