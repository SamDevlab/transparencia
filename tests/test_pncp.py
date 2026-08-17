from datetime import date

from transparencia.collectors.pncp import date_windows, in_scope, normalize_record, parse_active_modality_ids
from transparencia.config import CityConfig

CITY = CityConfig("teste", "Cidade Teste", "BA", "1234567")


def sample(power="E", sphere="M", city="Cidade Teste"):
    return {"numeroControlePNCP":"x/2026","orgaoEntidade":{"esferaId":sphere,"poderId":power,"razaosocial":"MUNICIPIO"},"unidadeOrgao":{"municipioNome":city,"ufSigla":"BA"}}


def test_windows_cover_range_without_overlap():
    windows = list(date_windows(date(2026,1,1), date(2026,2,15), max_days=30))
    assert windows[0].end == date(2026,1,30)
    assert windows[1].start == date(2026,1,31)
    assert windows[-1].end == date(2026,2,15)


def test_scope_uses_configured_city_not_hardcoded_name():
    assert in_scope(sample(), CITY, "executivo")
    assert not in_scope(sample(city="Outra Cidade"), CITY, "executivo")
    assert in_scope(sample(power="L"), CITY, "legislativo")


def test_normalization_keeps_city_and_provenance():
    row = normalize_record(sample(), CITY, "2026-08-17T00:00:00+00:00", "abc")
    assert row["city_slug"] == "teste"
    assert row["snapshot_sha256"] == "abc"


def test_modalities_discovered_from_payload():
    assert parse_active_modality_ids([{"id":6,"statusAtivo":True},{"id":"8","statusAtivo":True},{"id":99,"statusAtivo":False}]) == (6,8)
