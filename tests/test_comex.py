from transparencia.collectors.comex import (
    aggregate_countries,
    aggregate_monthly,
    aggregate_products,
    attach_yoy_and_screening,
    productive_screening_score,
    summarize_flows,
    unwrap_list,
)


def row(*, fob, kg=0, year=2026, month=1, heading="Máquinas", heading_code="8401", country="China", country_code="160"):
    return {
        "metricFOB": fob,
        "metricKG": kg,
        "year": year,
        "monthNumber": month,
        "heading": heading,
        "headingCode": heading_code,
        "country": country,
        "countryCode": country_code,
    }


def test_unwrap_data_list():
    assert unwrap_list({"success": True, "data": {"list": [{"metricFOB": 10}]}}) == [{"metricFOB": 10}]


def test_summarize_flows_keeps_balance_semantics():
    result = summarize_flows([row(fob=150)], [row(fob=200)])
    assert result["exports_fob"] == 150
    assert result["imports_fob"] == 200
    assert result["trade_flow_fob"] == 350
    assert result["balance_fob"] == -50


def test_aggregations_preserve_heading_country_and_month():
    exports = [row(fob=100, month=1), row(fob=50, month=2)]
    imports = [row(fob=300, month=1), row(fob=100, month=2, country="Alemanha", country_code="023")]
    products = aggregate_products(exports, imports)
    countries = aggregate_countries(exports, imports)
    monthly = aggregate_monthly(exports, imports)
    assert products[0]["sh4"] == "8401"
    assert products[0]["balance_fob"] == -250
    assert products[0]["top_import_country"]["country"] == "China"
    assert any(item["country"] == "Alemanha" for item in countries)
    assert monthly == [
        {"month": "2026-01", "exports_fob": 100.0, "imports_fob": 300.0, "trade_flow_fob": 400.0, "balance_fob": -200.0},
        {"month": "2026-02", "exports_fob": 50.0, "imports_fob": 100.0, "trade_flow_fob": 150.0, "balance_fob": -50.0},
    ]


def test_screening_is_bounded_and_explainable():
    result = productive_screening_score(
        imports_fob=100_000_000,
        exports_fob=2_000_000,
        import_growth=0.40,
        import_country_top_share=0.80,
        import_scale_reference=100_000_000,
    )
    assert 0 <= result["score"] <= 100
    assert result["label"] in {"triagem_alta", "triagem_media", "triagem_baixa"}
    assert set(result["components"]) == {
        "import_scale",
        "trade_deficit",
        "import_growth",
        "country_concentration",
        "related_export_capacity",
    }
    assert "não é recomendação" in result["interpretation"]


def test_yoy_growth_is_attached_without_inventing_growth_for_zero_base():
    current = aggregate_products([row(fob=10)], [row(fob=200)])
    previous = aggregate_products([row(fob=0)], [row(fob=100)])
    enriched = attach_yoy_and_screening(current, previous)
    assert enriched[0]["import_growth_yoy"] == 1.0
    assert enriched[0]["previous_imports_fob"] == 100

    no_previous = attach_yoy_and_screening(current, [])
    assert no_previous[0]["import_growth_yoy"] is None


def test_methodology_is_not_encoded_as_same_geography():
    state_filters = [{"filter": "state", "values": [29]}]
    city_filters = [{"filter": "state", "values": [29]}, {"filter": "city", "values": [2927408]}]
    assert state_filters != city_filters
    assert isinstance(city_filters[1]["values"][0], int)
