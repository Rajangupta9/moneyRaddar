"""Stage 5 — Metrics / Aggregation (pandas).

Compute the `Summary` **deterministically** — never via the LLM. Income and
spend are derived from the signed `amount`; the category breakdown, monthly
trend and biggest transaction reflect expenses (debits) only.

Reconciliation guarantee: `total_income - total_spend == net_savings`.

`recurring_total` / `recurring_count` stay 0 until Phase 3 fills them in.
See docs/architecture.md §4 Stage 5 and §5 Summary.
"""

from __future__ import annotations

import pandas as pd

from ..models import (
    BiggestTransaction,
    Category,
    CategoryBreakdown,
    MonthlyTrend,
    Period,
    Summary,
    Transaction,
)


def _empty_summary() -> Summary:
    return Summary(
        period=Period(start="", end=""),
        total_income=0.0,
        total_spend=0.0,
        net_savings=0.0,
        savings_rate=0.0,
    )


def compute_summary(transactions: list[Transaction]) -> Summary:
    """Aggregate cleaned transactions into the deterministic `Summary`."""
    if not transactions:
        return _empty_summary()

    df = pd.DataFrame(
        {
            "id": t.id,
            "date": t.date,
            "merchant": t.merchant,
            "description_raw": t.description_raw,
            "amount": t.amount,
            "category": t.category.value,
        }
        for t in transactions
    )
    df["date"] = pd.to_datetime(df["date"])

    total_income = round(float(df.loc[df["amount"] > 0, "amount"].sum()), 2)
    total_spend = round(float(-df.loc[df["amount"] < 0, "amount"].sum()), 2)
    net_savings = round(total_income - total_spend, 2)
    savings_rate = round(net_savings / total_income, 4) if total_income > 0 else 0.0

    # Expenses only, with a positive magnitude column for aggregation.
    expenses = df[df["amount"] < 0].copy()
    expenses["magnitude"] = -expenses["amount"]

    by_category: list[CategoryBreakdown] = []
    if not expenses.empty and total_spend > 0:
        grouped = expenses.groupby("category")["magnitude"].sum().sort_values(ascending=False)
        for category, amount in grouped.items():
            amount = float(amount)
            by_category.append(
                CategoryBreakdown(
                    category=Category(category),
                    amount=round(amount, 2),
                    pct=round(amount / total_spend, 4),
                )
            )
    top_categories = [c.category for c in by_category[:3]]

    biggest_transaction: BiggestTransaction | None = None
    if not expenses.empty:
        row = expenses.loc[expenses["magnitude"].idxmax()]
        biggest_transaction = BiggestTransaction(
            id=str(row["id"]),
            amount=round(float(row["amount"]), 2),
            merchant=row["merchant"],
            description_raw=row["description_raw"],
            date=row["date"].date().isoformat(),
        )

    df["month"] = df["date"].dt.strftime("%Y-%m")
    monthly_trend: list[MonthlyTrend] = []
    for month, group in df.groupby("month"):
        spend = round(float(-group.loc[group["amount"] < 0, "amount"].sum()), 2)
        income = round(float(group.loc[group["amount"] > 0, "amount"].sum()), 2)
        monthly_trend.append(MonthlyTrend(month=str(month), spend=spend, income=income))
    monthly_trend.sort(key=lambda m: m.month)

    period = Period(
        start=df["date"].min().date().isoformat(),
        end=df["date"].max().date().isoformat(),
    )

    return Summary(
        period=period,
        total_income=total_income,
        total_spend=total_spend,
        net_savings=net_savings,
        savings_rate=savings_rate,
        by_category=by_category,
        top_categories=top_categories,
        biggest_transaction=biggest_transaction,
        recurring_total=0.0,
        recurring_count=0,
        monthly_trend=monthly_trend,
    )
