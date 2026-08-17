from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .db import SCHEMA

REVENUE_KEYS = (
    "city_slug", "source_system", "event_key", "event_date", "agency_code", "agency_name",
    "nature_code", "nature_name", "funding_source_code", "funding_source_name",
    "forecast_value", "updated_forecast_value", "collected_value", "source_url",
    "observed_at", "snapshot_sha256",
)

EXPENSE_KEYS = (
    "city_slug", "source_system", "event_key", "stage", "event_date", "agency_code", "agency_name",
    "supplier_document", "supplier_name", "process_number", "contract_number",
    "function_code", "function_name", "subfunction_code", "subfunction_name",
    "program_code", "program_name", "action_code", "action_name",
    "expense_nature_code", "expense_nature_name", "funding_source_code", "funding_source_name",
    "gross_value", "net_value", "source_url", "observed_at", "snapshot_sha256",
)


def _rows(paths: Iterable[Path]) -> Iterable[dict]:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)


def _insert(conn: sqlite3.Connection, table: str, keys: tuple[str, ...], rows: Iterable[dict]) -> int:
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
    count = 0
    for row in rows:
        conn.execute(sql, [row.get(key) for key in keys])
        count += 1
    return count


def ingest_events(
    db_path: Path,
    *,
    revenue_jsonl: Iterable[Path] = (),
    expense_jsonl: Iterable[Path] = (),
) -> dict[str, int]:
    """Load normalized, source-linked financial events into the reusable SQLite model.

    The function never infers missing values. City adapters must normalize source records and
    carry source_url/observed_at/snapshot_sha256 before ingestion.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        revenue = _insert(conn, "revenue_events", REVENUE_KEYS, _rows(revenue_jsonl))
        expense = _insert(conn, "expense_events", EXPENSE_KEYS, _rows(expense_jsonl))
        conn.commit()
        return {"revenue_events": revenue, "expense_events": expense}
    finally:
        conn.close()
