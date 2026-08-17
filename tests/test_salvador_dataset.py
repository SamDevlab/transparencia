import csv
import hashlib
import sqlite3
from pathlib import Path

from transparencia.config import load_city
from transparencia.db import build

ROOT = Path(__file__).resolve().parents[1]


def test_salvador_snapshot_counts_and_identity(tmp_path: Path):
    ws = load_city(ROOT, "salvador")
    assert ws.config.ibge_code == "2927408"
    assert ws.config.uf == "BA"
    assert len(ws.sources) == 15
    db = tmp_path / "salvador.db"
    build(db, ws)
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("select count(*) from officials").fetchone()[0] == 43
        assert conn.execute("select count(*) from fiscal_observations").fetchone()[0] == 9
        assert conn.execute("select count(*) from legislative_observations").fetchone()[0] == 2
        assert conn.execute("select count(*) from procurements").fetchone()[0] == 4
    finally:
        conn.close()


def test_salvador_evidence_manifest_matches_files():
    manifest = ROOT / "cities" / "salvador" / "data" / "evidence" / "manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    for row in rows:
        path = ROOT / row["file"]
        assert path.exists()
        assert path.stat().st_size == int(row["bytes"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
