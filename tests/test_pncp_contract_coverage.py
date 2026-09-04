from datetime import date

from transparencia.collectors.pncp_contracts import build_coverage_payload, in_scope
from transparencia.config import CityConfig

CITY = CityConfig(
    slug="salvador",
    name="Salvador",
    uf="BA",
    ibge_code="2927408",
    municipality_cnpj="13927801000149",
)


def _query(*, completed: bool, error: str | None = None) -> dict:
    return {
        "agency_cnpj": "13927801000149",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "completed": completed,
        "pages_collected": 2,
        "source_rows_received": 3,
        "scope_rows_received": 2,
        "reported_pages": 2,
        "reported_total": 3,
        "pagination_metadata_complete": True,
        "explicit_empty": False,
        "error": error,
    }


def test_contract_coverage_emits_canonical_manifest_and_legacy_fields():
    payload = build_coverage_payload(
        CITY,
        date(2026, 1, 1),
        date(2026, 1, 31),
        scope="executivo",
        cnpjs=("13927801000149",),
        queries=[_query(completed=True)],
        records_unique_in_scope=2,
    )

    assert payload["manifest_version"] == 1
    assert payload["complete"] is True
    assert payload["records"] == 2
    assert payload["complete_for_supplied_agencies_and_filter"] is True
    assert payload["counts_by_status"]["complete_for_filter"] == 1
    entry = payload["entries"][0]
    assert entry["dataset"] == "contracts"
    assert entry["status"] == "complete_for_filter"
    assert "cnpjOrgao=13927801000149" in entry["filter_description"]


def test_contract_coverage_marks_inconclusive_queries_partial():
    query = _query(completed=False, error="HTTP 503 after retries")
    payload = build_coverage_payload(
        CITY,
        date(2026, 1, 1),
        date(2026, 1, 31),
        scope="executivo",
        cnpjs=("13927801000149",),
        queries=[query],
        records_unique_in_scope=0,
    )

    assert payload["complete"] is False
    assert payload["counts_by_status"]["partial"] == 1
    assert payload["entries"][0]["status"] == "partial"


def test_contract_scope_prefers_official_ibge_when_present():
    record = {
        "orgaoEntidade": {"esferaId": "M", "poderId": "E"},
        "unidadeOrgao": {
            "municipioNome": "Salvador",
            "codigoIbge": "9999999",
        },
    }
    assert not in_scope(record, CITY, "executivo")
