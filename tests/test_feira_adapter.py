from pathlib import Path

from transparencia.config import load_city


def test_feira_de_santana_uses_generic_city_workspace():
    repo_root = Path(__file__).resolve().parents[1]
    workspace = load_city(repo_root, "feira-de-santana")

    assert workspace.config.slug == "feira-de-santana"
    assert workspace.config.name == "Feira de Santana"
    assert workspace.config.uf == "BA"
    assert workspace.config.ibge_code == "2910800"
    assert workspace.config.municipality_cnpj == "14043574000151"

    source_ids = {source["id"] for source in workspace.sources}
    assert "portal_transparencia_executivo" in source_ids
    assert "diario_oficial" in source_ids
    assert "camara_transparencia" in source_ids
    assert "pncp" in source_ids
