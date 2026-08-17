import json
import sqlite3
from pathlib import Path

from transparencia.config import load_city
from transparencia.db import build


def test_build_db_accepts_optional_seed_files(tmp_path: Path):
    city = tmp_path / "cities" / "teste"
    seed = city / "data" / "seed"
    seed.mkdir(parents=True)
    (city / "city.json").write_text(json.dumps({"slug":"teste","name":"Cidade Teste","uf":"BA","ibge_code":"1234567"}), encoding="utf-8")
    (city / "sources.csv").write_text("id,publisher,scope,authority,url,notes\na,Prefeitura,executivo,primary,https://example.org,Fonte\n", encoding="utf-8")
    (seed / "procurements.csv").write_text(
        "source_system,pncp_control_number,process_number,notice_number,year,modality_id,modality_name,object,agency_cnpj,agency_name,sphere,power,unit_code,unit_name,municipality_ibge,municipality_name,uf,published_at,proposal_opening_at,proposal_closing_at,estimated_value,homologated_value,status_name,source_url,observed_at,snapshot_sha256\n"
        "Portal Local,,,001/2026,2026,,Pregão,Objeto,,Prefeitura,M,E,,,1234567,Cidade Teste,BA,,,,1000,,Aberta,https://example.org/1,2026-08-17,\n",
        encoding="utf-8",
    )
    db = tmp_path / "out.db"
    build(db, load_city(tmp_path, "teste"))
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("select count(*) from cities").fetchone()[0] == 1
        assert conn.execute("select city_slug, notice_number, estimated_value from procurements").fetchone() == ("teste", "001/2026", 1000.0)
    finally:
        conn.close()
