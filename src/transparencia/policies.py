from __future__ import annotations

import re
from dataclasses import dataclass

ACCOUNTING_STAGES = ("committed", "liquidated", "paid")


def digits(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def is_business_cnpj(value: object) -> bool:
    """Public supplier identity policy: Brazilian business CNPJ only."""
    return len(digits(value)) == 14


def require_exact_evidence(method: str | None) -> None:
    if not method or not method.startswith("exact_"):
        raise ValueError("public relation requires an exact_ evidence method")


def validate_accounting_stage(stage: str) -> str:
    if stage not in ACCOUNTING_STAGES:
        raise ValueError(f"invalid accounting stage: {stage}")
    return stage


@dataclass(frozen=True)
class AccountingAmounts:
    committed: float | None = None
    liquidated: float | None = None
    paid: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        """Keep official accounting stages separate by construction."""
        return {
            "committed": self.committed,
            "liquidated": self.liquidated,
            "paid": self.paid,
        }
