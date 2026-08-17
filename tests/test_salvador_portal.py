from datetime import date

from transparencia.collectors.salvador_portal import (
    normalize_expense_dimension,
    normalize_revenue_detail,
    parse_brl,
)
from transparencia.config import CityConfig

CITY = CityConfig(slug="salvador", name="Salvador", uf="BA", ibge_code="2927408")


def test_parse_brl_pt_br_and_numeric():
    assert parse_brl("8.976.901.581,28") == 8976901581.28
    assert parse_brl("-1.009.013,04") == -1009013.04
    assert parse_brl(12.5) == 12.5
    assert parse_brl(None) is None


def test_normalize_revenue_detail_preserves_source_and_period():
    payload = {"dados": [{
        "id": "1113034101",
        "descricao": "1113034101 - Imposto de Renda Retido",
        "previstoAno": "170.321.000,00",
        "arrecadadoPeriodo": "94.682.243,82",
        "acumulado": "94.682.243,82",
        "desempenho": "55,59",
    }]}
    rows = normalize_revenue_detail(
        payload, CITY, start=date(2026, 1, 1), end=date(2026, 8, 17),
        source_url="https://example.org/api/receita/gridDetalhada",
        observed_at="2026-08-17T00:00:00Z", snapshot_sha256="abc",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["nature_code"] == "1113034101"
    assert row["forecast_value"] == 170321000.0
    assert row["collected_value"] == 94682243.82
    assert row["period_start"] == "2026-01-01"
    assert row["period_end"] == "2026-08-17"
    assert row["snapshot_sha256"] == "abc"


def test_normalize_expense_creditor_is_explicit_aggregate():
    payload = {"dados": [{
        "id": "1", "descricao": "1 - ORACLE DO BRASIL SISTEMAS LTDA",
        "empenhado": 954977.13, "liquidado": 972583.67, "pago": 916147.49, "bruto": 972583.67,
    }]}
    rows = normalize_expense_dimension(
        payload, CITY, dimension="creditor", start=date(2026, 1, 1), end=date(2026, 8, 17),
        source_url="https://example.org/api/despesa/gridDetalhada",
        observed_at="2026-08-17T00:00:00Z", snapshot_sha256="def",
    )
    assert rows == [{
        "city_slug": "salvador",
        "source_system": "SALVADOR_TRANSPARENCIA_API",
        "dimension": "creditor",
        "dimension_code": "1",
        "dimension_name": "ORACLE DO BRASIL SISTEMAS LTDA",
        "period_start": "2026-01-01",
        "period_end": "2026-08-17",
        "committed_value": 954977.13,
        "liquidated_value": 972583.67,
        "paid_value": 916147.49,
        "gross_value": 972583.67,
        "source_url": "https://example.org/api/despesa/gridDetalhada",
        "observed_at": "2026-08-17T00:00:00Z",
        "snapshot_sha256": "def",
    }]
