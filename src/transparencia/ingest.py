from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .db import SCHEMA, _upsert_exact_money

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


def _entity_key(*parts: object) -> str:
    return "|".join(str(part or "").strip() for part in parts)


def _record_event_money(
    conn: sqlite3.Connection,
    row: dict,
    *,
    entity_type: str,
    entity_key: str,
    fields: tuple[str, ...],
) -> None:
    for field_name in fields:
        _upsert_exact_money(
            conn,
            city_slug=str(row.get("city_slug") or ""),
            entity_type=entity_type,
            entity_key=entity_key,
            field_name=field_name,
            value=row.get(field_name),
            observed_at=row.get("observed_at"),
        )


def _insert(
    conn: sqlite3.Connection,
    table: str,
    keys: tuple[str, ...],
    rows: Iterable[dict],
    *,
    entity_type: str,
    money_fields: tuple[str, ...],
) -> int:
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
    count = 0
    for row in rows:
        conn.execute(sql, [row.get(key) for key in keys])
        if entity_type == "revenue_event":
            entity_key = _entity_key(row.get("source_system"), row.get("event_key"))
        else:
            entity_key = _entity_key(row.get("source_system"), row.get("event_key"), row.get("stage"))
        _record_event_money(
            conn,
            row,
            entity_type=entity_type,
            entity_key=entity_key,
            fields=money_fields,
        )
        count += 1
    return count


def ingest_events(
    db_path: Path,
    *,
    revenue_jsonl: Iterable[Path] = (),
    expense_jsonl: Iterable[Path] = (),
) -> dict[str, int]:
    """Load normalized, source-linked financial events into the reusable SQLite model.

    Compatibility REAL columns are still populated, but every BRL field is also
    persisted in money_exact as integer centavos. Downstream calculations should
    prefer the exact representation. The function never infers missing values.
    City adapters must normalize source records and carry source_url/observed_at/
    snapshot_sha256 before ingestion.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        revenue = _insert(
            conn,
            "revenue_events",
            REVENUE_KEYS,
            _rows(revenue_jsonl),
            entity_type="revenue_event",
            money_fields=("forecast_value", "updated_forecast_value", "collected_value"),
        )
        expense = _insert(
            conn,
            "expense_events",
            EXPENSE_KEYS,
            _rows(expense_jsonl),
            entity_type="expense_event",
            money_fields=("gross_value", "net_value"),
        )
        conn.commit()
        return {"revenue_events": revenue, "expense_events": expense}
    finally:
        conn.close()
