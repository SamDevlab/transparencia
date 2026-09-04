import json
from datetime import date

from transparencia.collectors.pncp import _write_coverage
from transparencia.config import CityConfig


def test_pncp_coverage_uses_canonical_manifest_and_keeps_legacy_summary(tmp_path):
    city = CityConfig("teste", "Cidade Teste", "BA", "1234567")
    _write_coverage(
        tmp_path,
        city=city,
        start=date(2026, 9, 1),
        end=date(2026, 9, 4),
        scope="executivo",
        complete=True,
        records=12,
    )

    payload = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    assert payload["complete"] is True
    assert payload["records"] == 12
    assert payload["counts_by_status"]["complete_for_filter"] == 1
    assert payload["entries"][0]["dataset"] == "procurements"
    assert payload["entries"][0]["filter_description"] == "municipality_ibge=1234567; uf=BA; scope=executivo"
