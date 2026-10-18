"""Robust price parsing for strings as displayed on the site.

Handles currency symbols/codes, thousands separators, US and EU decimal formats
and ranges such as "$20.00 to $30.00". Amounts that carry a currency marker are
preferred over bare numbers, so quantities and percentages ("2 for $19.99",
"save 20% $90.00") are not mistaken for the price.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_NUMBER = r"\d[\d.,\s]*\d|\d"
_NUMBER_RE = re.compile(r"\d[\d.,]*")

# longest markers first, so "US $" wins over "$"
_CURRENCY_MARKERS = {
    "US $": "USD", "C $": "CAD", "AU $": "AUD", "USD": "USD", "CAD": "CAD", "AUD": "AUD",
    "ILS": "ILS", "₪": "ILS", "EUR": "EUR", "€": "EUR", "GBP": "GBP", "£": "GBP", "$": "USD",
}
_MARKER = "|".join(re.escape(m) for m in sorted(_CURRENCY_MARKERS, key=len, reverse=True))
_MONEY_RE = re.compile(
    rf"(?P<pre>{_MARKER})\s?(?P<num1>{_NUMBER})|(?P<num2>{_NUMBER})\s?(?P<post>{_MARKER})"
)
_RANGE_SEPARATOR_RE = re.compile(r"^\s*(to|-|–)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str | None  # ISO code, or None when the text had no currency marker


def _normalize_number(raw: str) -> Decimal:
    """Normalize localized thousands and decimal separators into a Decimal."""
    s = re.sub(r"\s", "", raw).rstrip(".,")
    has_comma, has_dot = "," in s, "." in s
    if has_comma and has_dot:
        # the right-most separator is the decimal one
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        head, _, tail = s.rpartition(",")
        if s.count(",") == 1 and len(tail) in (1, 2):
            s = f"{head}.{tail}"
        else:
            s = s.replace(",", "")
    elif has_dot and s.count(".") > 1:
        s = s.replace(".", "")
    return Decimal(s)


def _money(match: re.Match) -> Money:
    """Convert a currency-marked regex match into Money."""
    marker = match.group("pre") or match.group("post")
    number = match.group("num1") or match.group("num2")
    return Money(_normalize_number(number), _CURRENCY_MARKERS[marker])


def parse_money_range(text: str | None) -> tuple[Money, Money] | None:
    """Return (low, high) for a price or "X to Y" range, or None if there is no number.

    The first currency-marked amount is the price; a second one counts only when it is
    joined to the first by a range separator (so "$59.99 + $10 shipping" is 59.99).
    Text without any currency marker falls back to the lowest bare number.
    """
    if not text:
        return None
    marked = list(_MONEY_RE.finditer(text))
    if marked:
        low = _money(marked[0])
        if len(marked) > 1 and _RANGE_SEPARATOR_RE.match(text[marked[0].end():marked[1].start()]):
            return low, _money(marked[1])
        return low, low
    values = [_normalize_number(m) for m in _NUMBER_RE.findall(text)]
    if not values:
        return None
    return Money(min(values), None), Money(max(values), None)


def parse_money(text: str | None) -> Money | None:
    """Return the price (lowest end of a range) with its currency, or None."""
    money_range = parse_money_range(text)
    return money_range[0] if money_range else None


def parse_price_range(text: str | None) -> tuple[float, float] | None:
    """Return (lowest, highest) price found in text as floats, or None."""
    money_range = parse_money_range(text)
    if not money_range:
        return None
    return float(money_range[0].amount), float(money_range[1].amount)


def parse_price(text: str | None) -> float | None:
    """Return the lowest price in text (for ranges) as a float, or None if not parseable."""
    money = parse_money(text)
    return float(money.amount) if money else None
