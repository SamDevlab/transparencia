import pytest

from transparencia.money import cents_to_brl_text, money_to_cents


def test_money_to_cents_avoids_binary_float_arithmetic():
    assert money_to_cents("0.10") == 10
    assert money_to_cents("1234.56") == 123456
    assert money_to_cents(0.1 + 0.2) == 30


def test_money_to_cents_uses_currency_rounding():
    assert money_to_cents("1.005") == 101
    assert money_to_cents("1.004") == 100
    assert cents_to_brl_text(123456) == "1234.56"


def test_money_to_cents_rejects_non_finite_values():
    with pytest.raises(ValueError):
        money_to_cents("NaN")
