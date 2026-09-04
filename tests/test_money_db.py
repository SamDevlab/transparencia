import json
import sqlite3
from pathlib import Path

from transparencia.config import load_city
from transparencia.db import build


def _workspace(tmp_path: Path) -> Path:
    city = tmp_path / "cities" / "teste"
    seed = city / "data" / "seed"
    seed.mkdir(parents=True)
    (city / "city.json").write_text(
        json.dumps({"slug": "teste", "name": "Cidade Teste", "uf": "BA", "ibge_code": "1234567"}),
        encoding="utf-8",
    )
    (city / "sources.csv").write_text(
        "id,publisher,scope,authority,url,notes\na,Prefeitura,executivo,primary,https://example.org,Fonte\n",
        encoding="utf-8",
    )
    (seed / "fiscal_observations.csv").write_text(
        "entity,period,metric,value_brl,reported_value_text,precision,budget_stage,source_url,source_location,observed_at,notes\n"
        "Prefeitura,2026,receita,0.10,R$ 0,10,exact,arrecadada,https://example.org/fiscal,p.1,2026-09-01T00:00:00Z,\n",
        encoding="utf-8",
    )
    return city


def test_build_persists_integer_centavos_for_public_money(tmp_path: Path):
    _workspace(tmp_path)
    procurement = tmp_path / "procurements.jsonl"
    procurement.write_text(
        json.dumps({
            "city_slug": "teste",
            "source_system": "PNCP",
            "pncp_control_number": "proc-1",
            "estimated_value": 1234.56,
            "homologated_value": 1200.01,
            "observed_at": "2026-09-02T00:00:00Z",
        }) + "\n",
        encoding="utf-8",
    )
    contract = tmp_path / "contracts.jsonl"
    contract.write_text(
        json.dumps({
            "city_slug": "teste",
            "source_system": "PNCP",
            "pncp_control_number": "contract-1",
            "contract_number": "1/2026",
            "global_value": 99.99,
            "installment_value": 33.33,
            "observed_at": "2026-09-03T00:00:00Z",
        }) + "\n",
        encoding="utf-8",
    )

    db = tmp_path / "out.db"
    build(db, load_city(tmp_path, "teste"), pncp_jsonl=[procurement], contract_jsonl=[contract])

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "select entity_type, entity_key, field_name, value_cents from money_exact order by entity_type, field_name"
        ).fetchall()
        assert ("procurement", "proc-1", "estimated_value", 123456) in rows
        assert ("procurement", "proc-1", "homologated_value", 120001) in rows
        assert ("contract", "contract-1", "global_value", 9999) in rows
        assert ("contract", "contract-1", "installment_value", 3333) in rows
        assert any(row[0] == "fiscal_observation" and row[2] == "value_brl" and row[3] == 10 for row in rows)
    finally:
        conn.close()


def test_exact_money_does_not_regress_when_older_snapshot_arrives_last(tmp_path: Path):
    _workspace(tmp_path)
    newer = tmp_path / "newer.jsonl"
    older = tmp_path / "older.jsonl"
    newer.write_text(json.dumps({
        "city_slug": "teste", "source_system": "PNCP", "pncp_control_number": "proc-1",
        "estimated_value": 200.02, "observed_at": "2026-09-03T00:00:00Z",
    }) + "\n", encoding="utf-8")
    older.write_text(json.dumps({
        "city_slug": "teste", "source_system": "PNCP", "pncp_control_number": "proc-1",
        "estimated_value": 100.01, "observed_at": "2026-09-01T00:00:00Z",
    }) + "\n", encoding="utf-8")

    db = tmp_path / "out.db"
    build(db, load_city(tmp_path, "teste"), pncp_jsonl=[newer, older])

    conn = sqlite3.connect(db)
    try:
        assert conn.execute(
            "select value_cents from money_exact where entity_type='procurement' and entity_key='proc-1' and field_name='estimated_value'"
        ).fetchone()[0] == 20002
    finally:
        conn.close()
