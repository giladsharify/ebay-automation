"""Robust price parsing for strings as displayed on the site.

Handles currency symbols/codes, thousands separators, US and EU decimal formats
and ranges such as "$20.00 to $30.00".
"""
from __future__ import annotations

import re

_NUMBER_RE = re.compile(r"\d[\d.,]*")


def _normalize_number(raw: str) -> float:
    """Normalize localized thousands and decimal separators into a float string."""
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
    return float(s)


def parse_price_range(text: str | None) -> tuple[float, float] | None:
    """Return (lowest, highest) price found in text, or None if there is no number."""
    if not text:
        return None
    values = [_normalize_number(m) for m in _NUMBER_RE.findall(text)]
    if not values:
        return None
    return min(values), max(values)


def parse_price(text: str | None) -> float | None:
    """Return the lowest price in text (for ranges), or None if not parseable."""
    price_range = parse_price_range(text)
    return price_range[0] if price_range else None
