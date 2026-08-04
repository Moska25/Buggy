"""Clean-build behaviour of the checkout target.

These are the assertions that define "correct". Every expected value here is
the contract the seeded defects are measured against.
"""

from decimal import Decimal as D

import pytest

from app.targets.checkout import PROMOS, price_cart, tier_rate

CLEAN: set[str] = set()


def test_line_gross_is_unit_times_quantity():
    r = price_cart([{"sku": "A", "unit_price": "7.25", "qty": 4}], CLEAN)
    assert r["lines"][0]["gross"] == D("29.00")


def test_no_tier_discount_below_three_units():
    assert tier_rate(1, CLEAN) == D("0")
    assert tier_rate(2, CLEAN) == D("0")


@pytest.mark.parametrize("qty,rate", [(3, "0.05"), (5, "0.05"), (6, "0.10"), (11, "0.10"), (12, "0.15"), (50, "0.15")])
def test_tier_boundaries_are_inclusive(qty, rate):
    assert tier_rate(qty, CLEAN) == D(rate)


def test_plain_cart_totals_exactly():
    r = price_cart([{"sku": "A", "unit_price": "2.00", "qty": 5}], CLEAN)
    assert r["goods"] == D("9.50")
    assert r["shipping"] == D("4.99")
    assert r["vat"] == D("2.90")
    assert r["total"] == D("17.39")


def test_shipping_is_free_at_exactly_the_threshold():
    r = price_cart([{"sku": "B", "unit_price": "25.00", "qty": 2}], CLEAN)
    assert r["goods"] == D("50.00")
    assert r["shipping"] == D("0.00")
    assert r["total"] == D("60.00")


def test_shipping_is_charged_one_cent_below_the_threshold():
    r = price_cart([{"sku": "B", "unit_price": "24.995", "qty": 2}], CLEAN)
    assert r["goods"] == D("49.99")
    assert r["shipping"] == D("4.99")


def test_promo_discounts_goods_and_not_shipping():
    r = price_cart([{"sku": "C", "unit_price": "10.00", "qty": 2}], CLEAN, "SAVE10")
    assert r["promo_discount"] == D("2.00")   # 10% of 20.00 goods, not of 24.99
    assert r["shipping"] == D("4.99")
    assert r["total"] == D("27.59")


def test_vat_is_charged_on_the_discounted_base():
    cart = [{"sku": "D", "unit_price": "14.00", "qty": 10}]
    plain = price_cart(cart, CLEAN)
    promo = price_cart(cart, CLEAN, "SAVE25")
    assert plain["vat"] == D("25.20")
    assert promo["vat"] == D("18.90")
    assert promo["total"] == D("113.40")


def test_vat_is_twenty_percent_of_the_taxable_base():
    r = price_cart([{"sku": "E", "unit_price": "9.00", "qty": 2}], CLEAN)
    assert r["vat"] == (r["taxable"] * D("0.20")).quantize(D("0.01"))


@pytest.mark.parametrize("qty", [0, -1, -7])
def test_non_positive_quantity_is_rejected(qty):
    with pytest.raises(ValueError):
        price_cart([{"sku": "F", "unit_price": "5.00", "qty": qty}], CLEAN)


def test_negative_unit_price_is_rejected():
    with pytest.raises(ValueError):
        price_cart([{"sku": "G", "unit_price": "-1.00", "qty": 1}], CLEAN)


def test_unknown_promo_code_is_a_no_op():
    cart = [{"sku": "H", "unit_price": "9.00", "qty": 2}]
    assert price_cart(cart, CLEAN, "NONSENSE")["total"] == price_cart(cart, CLEAN)["total"]


@pytest.mark.parametrize("code", sorted(PROMOS))
def test_every_promo_code_reduces_the_total(code):
    cart = [{"sku": "I", "unit_price": "11.00", "qty": 4}]
    assert price_cart(cart, CLEAN, code)["total"] < price_cart(cart, CLEAN)["total"]


def test_total_is_rounded_half_up_on_an_exact_tie():
    # 5 x 1.41 lands on a pre-rounding total of 14.605 - an exact half-cent tie
    # with an even preceding digit. Half-up gives 14.03; half-even gives 14.02.
    r = price_cart([{"sku": "J", "unit_price": "1.41", "qty": 5}], CLEAN)
    assert r["total"] == D("14.03")


def test_multi_line_cart_goods_equals_sum_of_line_nets():
    cart = [
        {"sku": "K", "unit_price": "3.30", "qty": 4},
        {"sku": "L", "unit_price": "12.10", "qty": 7},
        {"sku": "M", "unit_price": "0.99", "qty": 13},
    ]
    r = price_cart(cart, CLEAN)
    assert abs(sum((line["net"] for line in r["lines"]), D("0")) - r["goods"]) <= D("0.02")
