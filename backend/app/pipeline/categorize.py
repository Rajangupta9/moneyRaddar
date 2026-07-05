"""Stage 3 — Categorize (rules only).

Deterministic, keyword/regex categorization from a human-editable `rules.yaml`.
The first matching pattern (top-to-bottom) wins; anything unmatched defaults to
`Other`. Every transaction is stamped with `category_source="rule"`.

The LLM fallback (merchant memory + Groq) arrives in Phase 4; this stage stays
the fast, free, deterministic first pass. See docs/architecture.md §4 Stage 3.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..models import Category, CategorySource, Transaction

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.yaml"

# Cache of compiled rules keyed by resolved file path.
_RULES_CACHE: dict[str, list[tuple[Category, re.Pattern[str]]]] = {}


def load_rules(path: str | Path | None = None) -> list[tuple[Category, re.Pattern[str]]]:
    """Load and compile categorization rules, preserving file order = priority."""
    resolved = Path(path) if path else RULES_PATH
    key = str(resolved)
    if key in _RULES_CACHE:
        return _RULES_CACHE[key]

    data = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    compiled: list[tuple[Category, re.Pattern[str]]] = []
    for category, patterns in (data.get("categories") or {}).items():
        cat = Category(category)
        for pattern in patterns or []:
            compiled.append((cat, re.compile(pattern, re.IGNORECASE)))

    _RULES_CACHE[key] = compiled
    return compiled


def categorize(
    transactions: list[Transaction],
    rules: list[tuple[Category, re.Pattern[str]]] | None = None,
) -> list[Transaction]:
    """Assign a category to each transaction in place; returns the same list."""
    active_rules = rules if rules is not None else load_rules()

    for txn in transactions:
        text = txn.description_raw
        if txn.merchant:
            text = f"{text} {txn.merchant}"

        category = Category.OTHER
        for candidate, pattern in active_rules:
            if pattern.search(text):
                category = candidate
                break

        txn.category = category
        txn.category_source = CategorySource.RULE

    return transactions
