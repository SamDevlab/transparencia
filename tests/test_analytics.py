import sqlite3
from pathlib import Path

from transparencia.analytics import supplier_concentration
from transparencia.db import SCHEMA


def test_supplier_concentration_is_descriptive(tmp_path: Path):
    db = tmp_path / "x.db"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    for doc, name, value in [("1", "A", 75.0), ("2", "B", 25.0)]:
        conn.execute(
            "INSERT INTO contracts (city_slug,source_system,supplier_document,supplier_name,global_value,observed_at) VALUES (?,?,?,?,?,?)",
            ("cidade", "PNCP", doc, name, value, "now"),
        )
    conn.commit()
    conn.close()
    rows = supplier_concentration(db, "cidade")
    assert rows[0]["supplier_name"] == "A"
    assert rows[0]["share_of_known_value"] == 0.75
    assert rows[0]["interpretation"] == "descriptive_concentration_not_irregularity"
