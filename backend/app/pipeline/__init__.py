"""RupeeRadar processing pipeline.

Each stage is an independent, testable module with a clear input/output
contract (docs/architecture.md §4). Phase 1 wires stages 1, 2, 3 and 5:

    ingest (CSV) -> clean/normalize -> rules-categorize -> metrics
"""

from __future__ import annotations

from ..models import Summary, Transaction
from .categorize import categorize
from .clean import clean
from .ingest import parse_csv
from .metrics import compute_summary

__all__ = ["parse_csv", "clean", "categorize", "compute_summary", "run_pipeline"]


def run_pipeline(csv_text: str) -> tuple[list[Transaction], Summary, str]:
    """Run the full Phase 1 pipeline over raw CSV text.

    Returns the cleaned+categorized transactions, the computed summary, and the
    name of the column-mapping profile that matched (useful for diagnostics).
    """
    raw, profile = parse_csv(csv_text)
    transactions = clean(raw)
    categorize(transactions)
    summary = compute_summary(transactions)
    return transactions, summary, profile
