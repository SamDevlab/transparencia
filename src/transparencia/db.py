from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from .config import CityWorkspace

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
"""


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build(db_path: Path, workspace: CityWorkspace, pncp_jsonl: list[Path] | None = None) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    city = workspace.config
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR REPLACE INTO cities VALUES (?,?,?,?,?)",
                     (city.slug, city.name, city.uf, city.ibge_code, city.municipality_cnpj))
        for source in workspace.sources:
            conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?)",
                         (city.slug, source.get("id"), source.get("publisher"), source.get("scope"),
                          source.get("authority"), source.get("url"), source.get("notes")))
        for row in _csv_rows(workspace.seed_dir / "officials.csv"):
            conn.execute("INSERT OR REPLACE INTO officials VALUES (?,?,?,?,?,?,?)",
                         (city.slug, row["name"], row["office"], row.get("party"), row.get("legislature"),
                          row["source_url"], row["observed_at"]))
        for row in _csv_rows(workspace.seed_dir / "fiscal_observations.csv"):
            conn.execute("INSERT OR REPLACE INTO fiscal_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (city.slug, row["entity"], row["period"], row["metric"], float(row["value_brl"]) if row.get("value_brl") else None,
                          row.get("reported_value_text"), row["precision"], row.get("budget_stage"), row["source_url"],
                          row.get("source_location"), row["observed_at"], row.get("notes")))
        for row in _csv_rows(workspace.seed_dir / "legislative_observations.csv"):
            conn.execute("INSERT OR REPLACE INTO legislative_observations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (city.slug, row["entity"], row["period"], row["metric"], float(row["value_numeric"]) if row.get("value_numeric") else None,
                          row.get("reported_value_text"), row["precision"], row["source_url"], row.get("source_location"), row["observed_at"], row.get("notes")))
        for path in pncp_jsonl or []:
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                keys = ["city_slug","source_system","pncp_control_number","process_number","notice_number","year","modality_id","modality_name","object","agency_cnpj","agency_name","sphere","power","unit_code","unit_name","municipality_ibge","municipality_name","uf","published_at","proposal_opening_at","proposal_closing_at","estimated_value","homologated_value","status_name","source_url","observed_at","snapshot_sha256"]
                conn.execute(f"INSERT OR IGNORE INTO procurements ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", [row.get(k) for k in keys])
        conn.commit()
    finally:
        conn.close()
