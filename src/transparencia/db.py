from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import CityWorkspace
from .money import money_to_cents

SCHEMA = r"""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS cities (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    uf TEXT NOT NULL,
    ibge_code TEXT NOT NULL,
    municipality_cnpj TEXT
);
CREATE TABLE IF NOT EXISTS sources (
    city_slug TEXT NOT NULL,
    id TEXT NOT NULL,
    publisher TEXT NOT NULL,
    scope TEXT NOT NULL,
    authority TEXT NOT NULL,
    url TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (city_slug, id)
);
CREATE TABLE IF NOT EXISTS officials (
    city_slug TEXT NOT NULL,
    name TEXT NOT NULL,
    office TEXT NOT NULL,
    party TEXT,
    legislature TEXT,
    source_url TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY (city_slug, name, office, observed_at)
);
CREATE TABLE IF NOT EXISTS fiscal_observations (
    city_slug TEXT NOT NULL,
    entity TEXT NOT NULL,
    period TEXT NOT NULL,
    metric TEXT NOT NULL,
    value_brl REAL,
    reported_value_text TEXT,
    precision TEXT NOT NULL,
    budget_stage TEXT,
    source_url TEXT NOT NULL,
    source_location TEXT,
    observed_at TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (city_slug, entity, period, metric, source_url, source_location)
);
CREATE TABLE IF NOT EXISTS legislative_observations (
    city_slug TEXT NOT NULL,
    entity TEXT NOT NULL,
    period TEXT NOT NULL,
    metric TEXT NOT NULL,
    value_numeric REAL,
    reported_value_text TEXT,
    precision TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_location TEXT,
    observed_at TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (city_slug, entity, period, metric, source_url, source_location)
);
CREATE TABLE IF NOT EXISTS procurements (
    city_slug TEXT NOT NULL,
    source_system TEXT NOT NULL,
    pncp_control_number TEXT,
    process_number TEXT,
    notice_number TEXT,
    year INTEGER,
    modality_id INTEGER,
    modality_name TEXT,
    object TEXT,
    agency_cnpj TEXT,
    agency_name TEXT,
    sphere TEXT,
    power TEXT,
    unit_code TEXT,
    unit_name TEXT,
    municipality_ibge TEXT,
    municipality_name TEXT,
    uf TEXT,
    published_at TEXT,
    proposal_opening_at TEXT,
    proposal_closing_at TEXT,
    estimated_value REAL,
    homologated_value REAL,
    status_name TEXT,
    source_url TEXT,
    observed_at TEXT NOT NULL,
    snapshot_sha256 TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_procurement_pncp ON procurements(city_slug, pncp_control_number)
WHERE pncp_control_number IS NOT NULL;
CREATE TABLE IF NOT EXISTS contracts (
    city_slug TEXT NOT NULL,
    source_system TEXT NOT NULL,
    pncp_control_number TEXT,
    procurement_control_number TEXT,
    contract_number TEXT,
    year INTEGER,
    sequence INTEGER,
    contract_type_id INTEGER,
    contract_type_name TEXT,
    process_number TEXT,
    object TEXT,
    agency_cnpj TEXT,
    agency_name TEXT,
    sphere TEXT,
    power TEXT,
    unit_code TEXT,
    unit_name TEXT,
    municipality_ibge TEXT,
    municipality_name TEXT,
    uf TEXT,
    supplier_type TEXT,
    supplier_document TEXT,
    supplier_name TEXT,
    initial_value REAL,
    global_value REAL,
    accumulated_value REAL,
    installments INTEGER,
    installment_value REAL,
    signed_at TEXT,
    valid_from TEXT,
    valid_to TEXT,
    published_at TEXT,
    updated_at TEXT,
    source_url TEXT,
    observed_at TEXT NOT NULL,
    snapshot_sha256 TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_pncp ON contracts(city_slug, pncp_control_number)
WHERE pncp_control_number IS NOT NULL;
CREATE TABLE IF NOT EXISTS suppliers (
    city_slug TEXT NOT NULL,
    document TEXT NOT NULL,
    person_type TEXT,
    name TEXT,
    source_system TEXT NOT NULL,
    first_observed_at TEXT NOT NULL,
    PRIMARY KEY (city_slug, document, source_system)
);
CREATE TABLE IF NOT EXISTS expense_events (
    city_slug TEXT NOT NULL,
    source_system TEXT NOT NULL,
    event_key TEXT NOT NULL,
    stage TEXT NOT NULL,
    event_date TEXT,
    agency_code TEXT,
    agency_name TEXT,
    supplier_document TEXT,
    supplier_name TEXT,
    process_number TEXT,
    contract_number TEXT,
    function_code TEXT,
    function_name TEXT,
    subfunction_code TEXT,
    subfunction_name TEXT,
    program_code TEXT,
    program_name TEXT,
    action_code TEXT,
    action_name TEXT,
    expense_nature_code TEXT,
    expense_nature_name TEXT,
    funding_source_code TEXT,
    funding_source_name TEXT,
    gross_value REAL,
    net_value REAL,
    source_url TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    snapshot_sha256 TEXT,
    PRIMARY KEY (city_slug, source_system, event_key, stage)
);
CREATE TABLE IF NOT EXISTS revenue_events (
    city_slug TEXT NOT NULL,
    source_system TEXT NOT NULL,
    event_key TEXT NOT NULL,
    event_date TEXT,
    agency_code TEXT,
    agency_name TEXT,
    nature_code TEXT,
    nature_name TEXT,
    funding_source_code TEXT,
    funding_source_name TEXT,
    forecast_value REAL,
    updated_forecast_value REAL,
    collected_value REAL,
    source_url TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    snapshot_sha256 TEXT,
    PRIMARY KEY (city_slug, source_system, event_key)
);
CREATE TABLE IF NOT EXISTS money_exact (
    city_slug TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    field_name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'BRL',
    value_cents INTEGER NOT NULL,
    source_value_text TEXT NOT NULL,
    observed_at TEXT,
    PRIMARY KEY (city_slug, entity_type, entity_key, field_name, currency)
);
"""

PROCUREMENT_KEYS = [
    "city_slug", "source_system", "pncp_control_number", "process_number", "notice_number", "year",
    "modality_id", "modality_name", "object", "agency_cnpj", "agency_name", "sphere", "power",
    "unit_code", "unit_name", "municipality_ibge", "municipality_name", "uf", "published_at",
    "proposal_opening_at", "proposal_closing_at", "estimated_value", "homologated_value", "status_name",
    "source_url", "observed_at", "snapshot_sha256",
]

CONTRACT_KEYS = [
    "city_slug", "source_system", "pncp_control_number", "procurement_control_number", "contract_number",
    "year", "sequence", "contract_type_id", "contract_type_name", "process_number", "object", "agency_cnpj",
    "agency_name", "sphere", "power", "unit_code", "unit_name", "municipality_ibge", "municipality_name",
    "uf", "supplier_type", "supplier_document", "supplier_name", "initial_value", "global_value",
    "accumulated_value", "installments", "installment_value", "signed_at", "valid_from", "valid_to",
    "published_at", "updated_at", "source_url", "observed_at", "snapshot_sha256",
]


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_observed_at(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_newer_observation(candidate: object, current: object) -> bool:
    candidate_dt = _parse_observed_at(candidate)
    current_dt = _parse_observed_at(current)
    if candidate_dt is not None and current_dt is not None:
        return candidate_dt > current_dt
    candidate_text = str(candidate or "")
    current_text = str(current or "")
    return bool(candidate_text) and candidate_text > current_text


def _entity_key(*parts: object) -> str:
    return "|".join(str(part or "").strip() for part in parts)


def _upsert_exact_money(
    conn: sqlite3.Connection,
    *,
    city_slug: str,
    entity_type: str,
    entity_key: str,
    field_name: str,
    value: object,
    observed_at: object,
) -> None:
    cents = money_to_cents(value)
    if cents is None or not entity_key:
        return

    existing = conn.execute(
        "SELECT observed_at FROM money_exact "
        "WHERE city_slug=? AND entity_type=? AND entity_key=? AND field_name=? AND currency='BRL'",
        (city_slug, entity_type, entity_key, field_name),
    ).fetchone()
    if existing is not None and not _is_newer_observation(observed_at, existing[0]):
        return

    conn.execute(
        """
        INSERT INTO money_exact (
            city_slug, entity_type, entity_key, field_name, currency,
            value_cents, source_value_text, observed_at
        ) VALUES (?, ?, ?, ?, 'BRL', ?, ?, ?)
        ON CONFLICT(city_slug, entity_type, entity_key, field_name, currency)
        DO UPDATE SET
            value_cents=excluded.value_cents,
            source_value_text=excluded.source_value_text,
            observed_at=excluded.observed_at
        """,
        (
            city_slug,
            entity_type,
            entity_key,
            field_name,
            cents,
            str(value).strip(),
            str(observed_at or "") or None,
        ),
    )


def _record_procurement_money(conn: sqlite3.Connection, row: dict) -> None:
    key = str(row.get("pncp_control_number") or "").strip() or _entity_key(
        row.get("source_system"), row.get("notice_number"), row.get("process_number"), row.get("source_url")
    )
    for field_name in ("estimated_value", "homologated_value"):
        _upsert_exact_money(
            conn,
            city_slug=str(row.get("city_slug") or ""),
            entity_type="procurement",
            entity_key=key,
            field_name=field_name,
            value=row.get(field_name),
            observed_at=row.get("observed_at"),
        )


def _record_contract_money(conn: sqlite3.Connection, row: dict) -> None:
    key = str(row.get("pncp_control_number") or "").strip() or _entity_key(
        row.get("source_system"), row.get("contract_number"), row.get("year"), row.get("source_url")
    )
    for field_name in ("initial_value", "global_value", "accumulated_value", "installment_value"):
        _upsert_exact_money(
            conn,
            city_slug=str(row.get("city_slug") or ""),
            entity_type="contract",
            entity_key=key,
            field_name=field_name,
            value=row.get(field_name),
            observed_at=row.get("observed_at"),
        )


def _upsert_latest_by_pncp(
    conn: sqlite3.Connection,
    *,
    table: str,
    keys: list[str],
    row: dict,
) -> None:
    control = row.get("pncp_control_number")
    city_slug = row.get("city_slug")
    if not control or not city_slug:
        conn.execute(
            f"INSERT OR IGNORE INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
            [row.get(key) for key in keys],
        )
        return

    existing = conn.execute(
        f"SELECT observed_at FROM {table} WHERE city_slug = ? AND pncp_control_number = ?",
        (city_slug, control),
    ).fetchone()
    if existing is None:
        conn.execute(
            f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
            [row.get(key) for key in keys],
        )
        return
    if not _is_newer_observation(row.get("observed_at"), existing[0]):
        return

    mutable = [key for key in keys if key not in {"city_slug", "pncp_control_number"}]
    conn.execute(
        f"UPDATE {table} SET {','.join(f'{key}=?' for key in mutable)} "
        "WHERE city_slug = ? AND pncp_control_number = ?",
        [row.get(key) for key in mutable] + [city_slug, control],
    )


def build(
    db_path: Path,
    workspace: CityWorkspace,
    pncp_jsonl: list[Path] | None = None,
    contract_jsonl: list[Path] | None = None,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    city = workspace.config
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO cities VALUES (?,?,?,?,?)",
            (city.slug, city.name, city.uf, city.ibge_code, city.municipality_cnpj),
        )
        for source in workspace.sources:
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?)",
                (
                    city.slug,
                    source.get("id"),
                    source.get("publisher"),
                    source.get("scope"),
                    source.get("authority"),
                    source.get("url"),
                    source.get("notes"),
                ),
            )
        for row in _csv_rows(workspace.seed_dir / "officials.csv"):
            conn.execute(
                "INSERT OR REPLACE INTO officials VALUES (?,?,?,?,?,?,?)",
                (
                    city.slug,
                    row["name"],
                    row["office"],
                    row.get("party"),
                    row.get("legislature"),
                    row["source_url"],
                    row["observed_at"],
                ),
            )
        for row in _csv_rows(workspace.seed_dir / "fiscal_observations.csv"):
            conn.execute(
                "INSERT OR REPLACE INTO fiscal_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    city.slug,
                    row["entity"],
                    row["period"],
                    row["metric"],
                    float(row["value_brl"]) if row.get("value_brl") else None,
                    row.get("reported_value_text"),
                    row["precision"],
                    row.get("budget_stage"),
                    row["source_url"],
                    row.get("source_location"),
                    row["observed_at"],
                    row.get("notes"),
                ),
            )
            _upsert_exact_money(
                conn,
                city_slug=city.slug,
                entity_type="fiscal_observation",
                entity_key=_entity_key(
                    row.get("entity"), row.get("period"), row.get("metric"),
                    row.get("source_url"), row.get("source_location"),
                ),
                field_name="value_brl",
                value=row.get("value_brl"),
                observed_at=row.get("observed_at"),
            )
        for row in _csv_rows(workspace.seed_dir / "legislative_observations.csv"):
            conn.execute(
                "INSERT OR REPLACE INTO legislative_observations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    city.slug,
                    row["entity"],
                    row["period"],
                    row["metric"],
                    float(row["value_numeric"]) if row.get("value_numeric") else None,
                    row.get("reported_value_text"),
                    row["precision"],
                    row["source_url"],
                    row.get("source_location"),
                    row["observed_at"],
                    row.get("notes"),
                ),
            )
        for row in _csv_rows(workspace.seed_dir / "procurements.csv"):
            normalized = {key: row.get(key) or None for key in PROCUREMENT_KEYS}
            normalized["city_slug"] = city.slug
            if normalized["year"]:
                normalized["year"] = int(normalized["year"])
            if normalized["modality_id"]:
                normalized["modality_id"] = int(normalized["modality_id"])
            _record_procurement_money(conn, normalized)
            for money_key in ("estimated_value", "homologated_value"):
                if normalized[money_key]:
                    normalized[money_key] = float(normalized[money_key])
            _upsert_latest_by_pncp(conn, table="procurements", keys=PROCUREMENT_KEYS, row=normalized)
        for path in pncp_jsonl or []:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                _upsert_latest_by_pncp(conn, table="procurements", keys=PROCUREMENT_KEYS, row=row)
                _record_procurement_money(conn, row)
        for path in contract_jsonl or []:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                _upsert_latest_by_pncp(conn, table="contracts", keys=CONTRACT_KEYS, row=row)
                _record_contract_money(conn, row)
                if row.get("supplier_document"):
                    conn.execute(
                        "INSERT OR IGNORE INTO suppliers VALUES (?,?,?,?,?,?)",
                        (
                            city.slug,
                            row.get("supplier_document"),
                            row.get("supplier_type"),
                            row.get("supplier_name"),
                            row.get("source_system") or "PNCP",
                            row.get("observed_at"),
                        ),
                    )
        conn.commit()
    finally:
        conn.close()
