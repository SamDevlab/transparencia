import json
import sqlite3
from pathlib import Path

from transparencia.config import load_city
from transparencia.db import build


def test_build_db_contracts_and_suppliers(tmp_path: Path):
    city = tmp_path / "cities" / "teste"
    city.mkdir(parents=True)
    (city / "data" / "seed").mkdir(parents=True)
    (city / "city.json").write_text(json.dumps({"slug":"teste","name":"Cidade Teste","uf":"BA","ibge_code":"1234567"}), encoding="utf-8")
    (city / "sources.csv").write_text("id,publisher,scope,authority,url,notes\na,Prefeitura,executivo,primary,https://example.org,Fonte\n", encoding="utf-8")
    contracts = tmp_path / "contracts.jsonl"
    contracts.write_text(json.dumps({
        "city_slug":"teste","source_system":"PNCP","pncp_control_number":"x","contract_number":"1/2026","year":2026,
        "supplier_type":"PJ","supplier_document":"12345678000190","supplier_name":"Fornecedor","global_value":100.0,
        "source_url":"https://example.org/x","observed_at":"2026-08-17T00:00:00Z"
    }) + "\n", encoding="utf-8")
    db = tmp_path / "out.db"
    build(db, load_city(tmp_path, "teste"), contract_jsonl=[contracts])
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("select count(*) from contracts").fetchone()[0] == 1
        assert conn.execute("select document,name from suppliers").fetchone() == ("12345678000190", "Fornecedor")
    finally:
        conn.close()
