import json
from pathlib import Path

from transparencia.config import CityConfig, load_city


def test_city_config_is_data_driven(tmp_path: Path):
    root = tmp_path / "cities" / "teste"
    root.mkdir(parents=True)
    (root / "city.json").write_text(json.dumps({"slug":"teste","name":"Cidade Teste","uf":"ba","ibge_code":"1234567"}), encoding="utf-8")
    (root / "sources.csv").write_text("id,publisher,scope,authority,url,notes\na,P,executivo,primary,https://example.org,x\n", encoding="utf-8")
    ws = load_city(tmp_path, "teste")
    assert ws.config == CityConfig("teste", "Cidade Teste", "BA", "1234567", None)
    assert ws.sources[0]["id"] == "a"
