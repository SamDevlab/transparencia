from __future__ import annotations

import sqlite3
from pathlib import Path

from .money import cents_to_brl_text


_CONTRACT_ENTITY_KEY_SQL = """
CASE
    WHEN c.pncp_control_number IS NOT NULL AND TRIM(c.pncp_control_number) <> ''
        THEN TRIM(c.pncp_control_number)
    ELSE COALESCE(TRIM(c.source_system), '') || '|' ||
         COALESCE(TRIM(c.contract_number), '') || '|' ||
         COALESCE(CAST(c.year AS TEXT), '') || '|' ||
         COALESCE(TRIM(c.source_url), '')
END
"""


def supplier_concentration(db_path: Path, city_slug: str) -> list[dict]:
    """Aggregate known contract global values by supplier using integer centavos.

    money_exact is authoritative when available. A legacy contract row that predates
    exact-money persistence is converted to cents once, per row, only as a migration
    fallback; all aggregation after that point is integer arithmetic. The result
    exposes fallback counts so consumers cannot silently mistake migrated precision
    for source-exact precision.

    This is a descriptive concentration measure only. It must not be interpreted as
    evidence of irregularity without procurement context and additional evidence.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        values_cte = f"""
            WITH contract_values AS (
                SELECT
                    c.supplier_document,
                    c.supplier_name,
                    COALESCE(
                        m.value_cents,
                        CASE
                            WHEN c.global_value IS NOT NULL
                                THEN CAST(ROUND(c.global_value * 100.0) AS INTEGER)
                            ELSE NULL
                        END
                    ) AS global_value_cents,
                    CASE WHEN m.value_cents IS NOT NULL THEN 1 ELSE 0 END AS exact_value
                FROM contracts AS c
                LEFT JOIN money_exact AS m
                  ON m.city_slug = c.city_slug
                 AND m.entity_type = 'contract'
                 AND m.entity_key = {_CONTRACT_ENTITY_KEY_SQL}
                 AND m.field_name = 'global_value'
                 AND m.currency = 'BRL'
                WHERE c.city_slug = ?
                  AND c.supplier_document IS NOT NULL
            )
        """
        total = conn.execute(
            values_cte + "SELECT COALESCE(SUM(global_value_cents), 0) FROM contract_values WHERE global_value_cents IS NOT NULL",
            (city_slug,),
        ).fetchone()[0]
        rows = conn.execute(
            values_cte
            + """
            SELECT
                supplier_document,
                supplier_name,
                COUNT(*) AS contract_count,
                SUM(global_value_cents) AS known_global_value_cents,
                SUM(exact_value) AS exact_contract_count,
                COUNT(*) - SUM(exact_value) AS legacy_fallback_contract_count
            FROM contract_values
            WHERE global_value_cents IS NOT NULL
            GROUP BY supplier_document, supplier_name
            ORDER BY known_global_value_cents DESC, supplier_name
            """,
            (city_slug,),
        ).fetchall()
        return [
            {
                "supplier_document": row["supplier_document"],
                "supplier_name": row["supplier_name"],
                "contract_count": row["contract_count"],
                "known_global_value_cents": row["known_global_value_cents"],
                "known_global_value": row["known_global_value_cents"] / 100,
                "known_global_value_text": cents_to_brl_text(row["known_global_value_cents"]),
                "share_of_known_value": (row["known_global_value_cents"] / total) if total else None,
                "exact_contract_count": row["exact_contract_count"],
                "legacy_fallback_contract_count": row["legacy_fallback_contract_count"],
                "money_precision": (
                    "exact_cents"
                    if row["legacy_fallback_contract_count"] == 0
                    else "mixed_exact_and_legacy_row_rounding"
                ),
                "interpretation": "descriptive_concentration_not_irregularity",
            }
            for row in rows
        ]
    finally:
        conn.close()
