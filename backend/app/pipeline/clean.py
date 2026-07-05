"""Stage 2 — Clean / Normalize.

Turn `RawTransaction` strings into canonical `Transaction`s:

* parse dates from several formats into ISO 8601 (day-first, per Indian banks);
* parse amounts (strip ₹/commas), resolving debit/credit into a signed `amount`
  plus an explicit `direction`;
* normalize the description and extract a probable **merchant** token, stripping
  UPI/IMPS/NEFT rails and reference numbers;
* drop exact-duplicate rows.

See docs/architecture.md §4 Stage 2.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..models import Direction, RawTransaction, Transaction

# Tried in order; day-first variants precede month-first to match Indian banks.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d %B %Y",
    "%m/%d/%Y",
)

# Everything that is not a digit, dot or minus is noise in an amount string.
_AMOUNT_NOISE = re.compile(r"[^\d.\-]")

# Payment rails, indicators and month tokens that are never a merchant name.
_RAIL_TOKENS = {
    "UPI", "IMPS", "NEFT", "RTGS", "ACH", "NACH", "POS", "ATM", "SIP", "SAL",
    "DR", "CR", "TXN", "REF", "IN", "OUT", "P2M", "P2A", "PMT",
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
}

_DELIMITERS = re.compile(r"[\/\-|:*#]+")
_WHITESPACE = re.compile(r"\s+")
_ONLY_DIGITS = re.compile(r"^[\d\s]+$")
_LETTERS = re.compile(r"[A-Z]")


def parse_date(value: str | None) -> str | None:
    """Parse a date string into ISO `YYYY-MM-DD`, or None if unrecognized."""
    if not value:
        return None
    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_amount(value: str | None) -> float | None:
    """Parse an amount, stripping ₹, commas and spaces. Handles (123.45) as −."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = _AMOUNT_NOISE.sub("", text)
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    if negative:
        amount = -abs(amount)
    return amount


def _resolve_amount(raw: RawTransaction) -> tuple[float | None, Direction | None]:
    """Collapse debit/credit columns or a signed amount into (amount, direction)."""
    debit = parse_amount(raw.debit)
    if debit:
        return -abs(debit), Direction.DEBIT

    credit = parse_amount(raw.credit)
    if credit:
        return abs(credit), Direction.CREDIT

    amount = parse_amount(raw.amount)
    if amount is None or amount == 0:
        return None, None
    if amount < 0:
        return amount, Direction.DEBIT
    # A positive single-column amount is treated as income (a credit).
    return amount, Direction.CREDIT


def normalize_description(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().upper())


def extract_merchant(description_norm: str) -> str | None:
    """Pull the first meaningful token out of a normalized description.

    `UPI/SWIGGY/1234567890/Payment` -> `SWIGGY`;
    `IMPS-SWIGGY INSTAMART-987654`  -> `SWIGGY INSTAMART`.
    """
    if not description_norm:
        return None
    parts = [p.strip() for p in _DELIMITERS.split(description_norm) if p.strip()]
    for part in parts:
        # Strip leading rail/indicator/month words within the segment too, so
        # "ACH DR/HDFC HOME LOAN EMI" yields "HDFC HOME LOAN EMI", not "ACH DR".
        words = part.split()
        while words and words[0] in _RAIL_TOKENS:
            words.pop(0)
        candidate = " ".join(words)
        if not candidate or _ONLY_DIGITS.match(candidate):
            continue
        if len(_LETTERS.findall(candidate)) >= 2:
            return candidate
    return description_norm


def clean(raw_transactions: list[RawTransaction]) -> list[Transaction]:
    """Normalize raw rows into canonical transactions, dropping duplicates."""
    seen: set[tuple[str, str, float]] = set()
    transactions: list[Transaction] = []
    counter = 1

    for raw in raw_transactions:
        date = parse_date(raw.date)
        amount, direction = _resolve_amount(raw)
        # Skip rows we can't place on a timeline or a ledger.
        if date is None or amount is None or direction is None:
            continue

        description_raw = (raw.description or "").strip()
        description_norm = normalize_description(description_raw)
        merchant = extract_merchant(description_norm)

        key = (date, description_raw, round(amount, 2))
        if key in seen:
            continue
        seen.add(key)

        transactions.append(
            Transaction(
                id=f"txn_{counter:04d}",
                date=date,
                description_raw=description_raw,
                merchant=merchant,
                amount=round(amount, 2),
                direction=direction,
                balance=parse_amount(raw.balance),
            )
        )
        counter += 1

    return transactions
