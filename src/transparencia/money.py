from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
HUNDRED = Decimal(100)


def money_to_cents(value: object) -> int | None:
    """Convert a BRL-like source value to integer centavos without binary-float math.

    Existing collectors may still expose compatibility floats. This helper converts
    from their textual representation through Decimal and stores the canonical minor
    unit as an integer. Values with more than two decimal places are rounded using
    ROUND_HALF_UP, matching ordinary currency rounding.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid monetary value: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"non-finite monetary value: {value!r}")
    quantized = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    return int(quantized * HUNDRED)


def cents_to_brl_text(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(int(cents))
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"
