"""Stage 1 — Ingest / Parse (CSV).

Detect the header row, pick a bank-specific **column-mapping profile**, and emit
`RawTransaction` records (still unnormalized strings). Layouts we don't recognize
fall back to a generic heuristic mapper that guesses columns by name.

A `Dr/Cr` indicator column (e.g. ICICI) is folded into the debit/credit buckets
here so the cleaner (Stage 2) always sees a uniform shape.

See docs/architecture.md §4 Stage 1.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from ..models import RawTransaction

# Canonical fields a profile can map a source column onto.
_FIELDS = ("date", "description", "amount", "debit", "credit", "balance", "dr_cr")


@dataclass(frozen=True)
class ColumnProfile:
    """Maps canonical fields to a specific bank's column headers."""

    name: str
    date: str
    description: str
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    balance: str | None = None
    dr_cr: str | None = None

    @property
    def required_headers(self) -> list[str]:
        """Columns that must exist for this profile to be considered a match."""
        cols = [self.date, self.description]
        for c in (self.amount, self.debit, self.credit, self.dr_cr):
            if c:
                cols.append(c)
        return cols


# Known layouts, tried in order. `generic` matches plain `date,description,amount`.
PROFILES: list[ColumnProfile] = [
    ColumnProfile(
        name="hdfc",
        date="Date",
        description="Narration",
        debit="Withdrawal Amt",
        credit="Deposit Amt",
        balance="Closing Balance",
    ),
    ColumnProfile(
        name="icici",
        date="Txn Date",
        description="Transaction Remarks",
        amount="Amount (INR)",
        dr_cr="Dr/Cr",
    ),
    ColumnProfile(
        name="generic",
        date="date",
        description="description",
        amount="amount",
    ),
]

# Substrings that mark a row as a header rather than data.
_HEADER_HINTS = (
    "date",
    "narration",
    "description",
    "remarks",
    "particular",
    "detail",
    "amount",
    "withdraw",
    "deposit",
    "debit",
    "credit",
    "dr/cr",
    "balance",
)


def _norm(s: str) -> str:
    return s.strip().lower()


def _looks_like_header(cells: list[str]) -> bool:
    hits = sum(1 for c in cells if any(h in _norm(c) for h in _HEADER_HINTS))
    return hits >= 2


def _index_exact(header_lower: list[str], name: str) -> int | None:
    name = name.lower()
    for i, h in enumerate(header_lower):
        if h == name:
            return i
    return None


def _find(header_lower: list[str], *candidates: str) -> int | None:
    """Exact match first, then substring, over the given candidate names."""
    for cand in candidates:
        idx = _index_exact(header_lower, cand)
        if idx is not None:
            return idx
    for cand in candidates:
        for i, h in enumerate(header_lower):
            if cand in h:
                return i
    return None


def _match_profile(header: list[str]) -> ColumnProfile | None:
    header_lower = [_norm(h) for h in header]
    for profile in PROFILES:
        if all(_index_exact(header_lower, col) is not None for col in profile.required_headers):
            return profile
    return None


def _profile_mapping(profile: ColumnProfile, header: list[str]) -> dict[str, int]:
    header_lower = [_norm(h) for h in header]
    mapping: dict[str, int] = {}
    for field in _FIELDS:
        col = getattr(profile, field)
        if not col:
            continue
        idx = _index_exact(header_lower, col)
        if idx is not None:
            mapping[field] = idx
    return mapping


def _generic_mapping(header: list[str]) -> dict[str, int]:
    """Best-effort column guessing for unrecognized layouts (§11 risk)."""
    hl = [_norm(h) for h in header]
    mapping: dict[str, int] = {}

    date = _find(hl, "date")
    if date is not None:
        mapping["date"] = date

    desc = _find(hl, "description", "narration", "remarks", "particular", "detail")
    if desc is not None:
        mapping["description"] = desc

    debit = _find(hl, "withdrawal", "debit")
    credit = _find(hl, "deposit", "credit")
    if debit is not None:
        mapping["debit"] = debit
    if credit is not None:
        mapping["credit"] = credit

    # Only use a single signed amount column when there's no debit/credit split.
    if "debit" not in mapping and "credit" not in mapping:
        amount = _find(hl, "amount")
        if amount is not None:
            mapping["amount"] = amount

    drcr = _find(hl, "dr/cr", "cr/dr", "type")
    if drcr is not None:
        mapping["dr_cr"] = drcr

    balance = _find(hl, "balance")
    if balance is not None:
        mapping["balance"] = balance

    return mapping


def _cell(row: list[str], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    value = row[idx].strip()
    return value or None


def parse_csv(data: str) -> tuple[list[RawTransaction], str]:
    """Parse CSV text into `RawTransaction`s + the matched profile name."""
    reader = csv.reader(io.StringIO(data))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return [], "empty"

    header_idx = 0
    for i, row in enumerate(rows):
        if _looks_like_header(row):
            header_idx = i
            break

    header = [h.strip() for h in rows[header_idx]]
    data_rows = rows[header_idx + 1 :]

    profile = _match_profile(header)
    if profile is not None:
        mapping = _profile_mapping(profile, header)
        profile_name = profile.name
    else:
        mapping = _generic_mapping(header)
        profile_name = "generic-fallback"

    raw: list[RawTransaction] = []
    for row in data_rows:
        date = _cell(row, mapping.get("date"))
        description = _cell(row, mapping.get("description"))
        amount = _cell(row, mapping.get("amount"))
        debit = _cell(row, mapping.get("debit"))
        credit = _cell(row, mapping.get("credit"))
        balance = _cell(row, mapping.get("balance"))
        drcr = _cell(row, mapping.get("dr_cr"))

        # Fold a Dr/Cr indicator into debit/credit so Stage 2 sees one shape.
        if drcr and amount is not None:
            flag = drcr.strip().upper()
            if flag.startswith("D"):  # DR / Debit
                debit, amount = amount, None
            elif flag.startswith("C"):  # CR / Credit
                credit, amount = amount, None

        if not any((date, description, amount, debit, credit)):
            continue

        raw.append(
            RawTransaction(
                date=date,
                description=description,
                amount=amount,
                debit=debit,
                credit=credit,
                balance=balance,
            )
        )

    return raw, profile_name
