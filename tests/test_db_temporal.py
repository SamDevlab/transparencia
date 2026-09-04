import json
import sqlite3
from pathlib import Path

from transparencia.config import load_city
from transparencia.db import build


def _workspace(tmp_path: Path):
    city = tmp_path / "cities" / "teste"
    (city / "data" / "seed").mkdir(parents=True)
    (city / "city.json").write_text(
        json.dumps({"slug": "teste", "name": "Cidade Teste", "uf": "BA", "ibge_code": "1234567"}),
        encoding="utf-8",
    )
    (city / "sources.csv").write_text(
        "id,publisher,scope,authority,url,notes\na,Prefeitura,executivo,primary,https://example.org,Fonte\n",
        encoding="utf-8",
    )
    return load_city(tmp_path, "teste")


def test_latest_procurement_observation_wins_even_if_files_arrive_out_of_order(tmp_path: Path):
    older = tmp_path / "older.jsonl"
    newer = tmp_path / "newer.jsonl"
    base = {
        "city_slug": "teste",
        "source_system": "PNCP",
        "pncp_control_number": "PNCP-1",
        "process_number": "1/2026",
        "notice_number": "1/2026",
        "year": 2026,
        "object": "Objeto",
        "source_url": "https://example.org/pncp-1",
    }
    older.write_text(
        json.dumps({**base, "status_name": "Recebendo proposta", "observed_at": "2026-09-01T10:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    newer.write_text(
        json.dumps({**base, "status_name": "Homologada", "observed_at": "2026-09-03T10:00:00Z"}) + "\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "out.db"
    # Intentionally pass newest first and oldest last: consolidated state must not regress.
    build(db_path, _workspace(tmp_path), pncp_jsonl=[newer, older])

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "select status_name, observed_at from procurements where pncp_control_number = 'PNCP-1'"
        ).fetchone()
        assert row == ("Homologada", "2026-09-03T10:00:00Z")
    finally:
        conn.close()
