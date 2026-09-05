import sqlite3
from pathlib import Path

from transparencia.analytics import supplier_concentration
from transparencia.db import SCHEMA


def test_supplier_concentration_is_descriptive_and_uses_exact_cents(tmp_path: Path):
    db = tmp_path / "x.db"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    for control, doc, name, value, cents in [
        ("c1", "1", "A", 75.0, 7500),
        ("c2", "2", "B", 25.0, 2500),
    ]:
        conn.execute(
            """
            INSERT INTO contracts (
                city_slug, source_system, pncp_control_number,
                supplier_document, supplier_name, global_value, observed_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            ("cidade", "PNCP", control, doc, name, value, "now"),
        )
        conn.execute(
            """
            INSERT INTO money_exact (
                city_slug, entity_type, entity_key, field_name, currency,
                value_cents, source_value_text, observed_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            ("cidade", "contract", control, "global_value", "BRL", cents, str(value), "now"),
        )
    conn.commit()
    conn.close()

    rows = supplier_concentration(db, "cidade")
    assert rows[0]["supplier_name"] == "A"
    assert rows[0]["known_global_value_cents"] == 7500
    assert rows[0]["known_global_value"] == 75
    assert rows[0]["share_of_known_value"] == 0.75
    assert rows[0]["exact_contract_count"] == 1
    assert rows[0]["legacy_fallback_contract_count"] == 0
    assert rows[0]["money_precision"] == "exact_cents"
    assert rows[0]["interpretation"] == "descriptive_concentration_not_irregularity"


def test_supplier_concentration_marks_legacy_real_fallback(tmp_path: Path):
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO contracts (
            city_slug, source_system, pncp_control_number,
            supplier_document, supplier_name, global_value, observed_at
        ) VALUES (?,?,?,?,?,?,?)
        """,
        ("cidade", "PNCP", "legacy-1", "1", "A", 0.1, "now"),
    )
    conn.commit()
    conn.close()

    row = supplier_concentration(db, "cidade")[0]
    assert row["known_global_value_cents"] == 10
    assert row["legacy_fallback_contract_count"] == 1
    assert row["money_precision"] == "mixed_exact_and_legacy_row_rounding"
