"""Target 1 of 3: cart pricing.

Money is Decimal end to end. Intermediate values keep full precision and the
total is quantized exactly once, which is what lets CHK-003 (a rounding-mode
swap) hide until an amount lands on an exact half-cent tie.

Every `active` branch in this file is a seeded defect from app/defects.py. They
are deliberately small and plausible - the kind of edit that survives review -
and none of them raise where the clean path would not.

Pricing order:
    line gross -> per-line quantity tier discount -> goods
    goods -> promo percentage -> discounted
    shipping from goods (free at or above the threshold)
    VAT on (discounted + shipping)
    total = discounted + shipping + VAT, quantized once
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Any, Iterable

CENT = Decimal("0.01")
VAT_RATE = Decimal("0.20")
FREE_SHIPPING_THRESHOLD = Decimal("50.00")
SHIPPING_FEE = Decimal("4.99")

# (minimum qty, discount rate), highest tier first
TIERS: tuple[tuple[int, Decimal], ...] = (
    (12, Decimal("0.15")),
    (6, Decimal("0.10")),
    (3, Decimal("0.05")),
)

PROMOS: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE25": Decimal("0.25"),
    "HALF": Decimal("0.50"),
}


def tier_rate(qty: int, active: set[str]) -> Decimal:
    """Quantity discount rate for a line of `qty` units."""
    for minimum, rate in TIERS:
        if "CHK-002" in active:
            # Off-by-one: the tier no longer includes its own boundary, so a
            # cart of exactly 3 / 6 / 12 units is charged the tier below.
            if qty > minimum:
                return rate
        elif qty >= minimum:
            return rate
    return Decimal("0")


def promo_rate(code: str | None) -> Decimal:
    if not code:
        return Decimal("0")
    return PROMOS.get(code.strip().upper(), Decimal("0"))


def price_cart(
    cart: Iterable[dict[str, Any]],
    active: Iterable[str] | None = None,
    promo: str | None = None,
) -> dict[str, Any]:
    """Price a cart. Returns every intermediate amount, not just the total."""
    active = set(active or ())

    lines: list[dict[str, Any]] = []
    goods = Decimal("0")
    for item in cart:
        qty = int(item["qty"])
        if qty <= 0 and "CHK-006" not in active:
            # CHK-006 removes this guard, so a negative quantity becomes a
            # silent credit on the order instead of a rejected request.
            raise ValueError(f"quantity must be positive, got {qty} for {item.get('sku')}")
        unit = Decimal(str(item["unit_price"]))
        if unit < 0:
            raise ValueError(f"unit_price must not be negative for {item.get('sku')}")

        gross = unit * qty
        rate = tier_rate(qty, active)
        discount = gross * rate
        net = gross - discount
        goods += net
        lines.append(
            {
                "sku": item.get("sku", "?"),
                "qty": qty,
                "unit_price": unit,
                "gross": _q(gross),
                "tier_rate": rate,
                "tier_discount": _q(discount),
                "net": _q(net),
            }
        )

    shipping = _shipping_for(goods, active)

    rate = promo_rate(promo)
    if "CHK-001" in active:
        # Promo percentage is applied to goods *plus* shipping, so a discount
        # code silently discounts delivery too.
        promo_discount = (goods + shipping) * rate
    else:
        promo_discount = goods * rate
    discounted = goods - promo_discount

    if "CHK-005" in active:
        # VAT is computed on the pre-discount subtotal: every discounted order
        # is overcharged tax.
        taxable = goods + shipping
    else:
        taxable = discounted + shipping
    vat = taxable * VAT_RATE

    raw_total = discounted + shipping + vat
    if "CHK-003" in active:
        # Banker's rounding instead of half-up. Identical on almost every cart;
        # differs by one cent only on an exact half-cent tie.
        total = raw_total.quantize(CENT, rounding=ROUND_HALF_EVEN)
    else:
        total = raw_total.quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "lines": lines,
        "goods": _q(goods),
        "promo": (promo or "").strip().upper() or None,
        "promo_rate": rate,
        "promo_discount": _q(promo_discount),
        "discounted": _q(discounted),
        "shipping": _q(shipping),
        "taxable": _q(taxable),
        "vat": _q(vat),
        "total": total,
    }


def _shipping_for(goods: Decimal, active: set[str]) -> Decimal:
    if "CHK-004" in active:
        # Strict `>`: an order of exactly the threshold amount is charged
        # shipping even though the page promised it free.
        free = goods > FREE_SHIPPING_THRESHOLD
    else:
        free = goods >= FREE_SHIPPING_THRESHOLD
    return Decimal("0.00") if free else SHIPPING_FEE


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)
