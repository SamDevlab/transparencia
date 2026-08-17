from __future__ import annotations

import sqlite3
from pathlib import Path


def supplier_concentration(db_path: Path, city_slug: str) -> list[dict]:
    """Aggregate known contract global values by supplier.

    This is a descriptive concentration measure only. It must not be interpreted as
    evidence of irregularity without procurement context and additional evidence.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COALESCE(SUM(global_value),0) FROM contracts WHERE city_slug=? AND global_value IS NOT NULL",
            (city_slug,),
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT supplier_document, supplier_name, COUNT(*) AS contract_count,
                   SUM(global_value) AS known_global_value
            FROM contracts
            WHERE city_slug=? AND supplier_document IS NOT NULL AND global_value IS NOT NULL
            GROUP BY supplier_document, supplier_name
            ORDER BY known_global_value DESC, supplier_name
            """,
            (city_slug,),
        ).fetchall()
        return [
            {
                "supplier_document": row["supplier_document"],
                "supplier_name": row["supplier_name"],
                "contract_count": row["contract_count"],
                "known_global_value": row["known_global_value"],
                "share_of_known_value": (row["known_global_value"] / total) if total else None,
                "interpretation": "descriptive_concentration_not_irregularity",
            }
            for row in rows
        ]
    finally:
        conn.close()
