import json
import sqlite3
from pathlib import Path

from transparencia.ingest import ingest_events


def test_ingest_normalized_financial_events(tmp_path: Path):
    revenue = tmp_path / "revenue.jsonl"
    expense = tmp_path / "expense.jsonl"
    revenue.write_text(json.dumps({
        "city_slug": "teste", "source_system": "OFFICIAL", "event_key": "r1",
        "nature_code": "1", "nature_name": "Receita", "forecast_value": 100.0,
        "collected_value": 80.0, "source_url": "https://example.org/r",
        "observed_at": "2026-08-17", "snapshot_sha256": "abc",
    }) + "\n", encoding="utf-8")
    expense.write_text(json.dumps({
        "city_slug": "teste", "source_system": "OFFICIAL", "event_key": "e1", "stage": "pago",
        "supplier_document": "123", "supplier_name": "Fornecedor", "gross_value": 50.0,
        "source_url": "https://example.org/e", "observed_at": "2026-08-17", "snapshot_sha256": "def",
    }) + "\n", encoding="utf-8")

    db = tmp_path / "events.db"
    result = ingest_events(db, revenue_jsonl=[revenue], expense_jsonl=[expense])
    assert result == {"revenue_events": 1, "expense_events": 1}

    conn = sqlite3.connect(db)
    try:
        assert conn.execute("select nature_code, collected_value from revenue_events").fetchone() == ("1", 80.0)
        assert conn.execute("select stage, supplier_document, gross_value from expense_events").fetchone() == ("pago", "123", 50.0)
    finally:
        conn.close()
