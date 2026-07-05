"""Canonical data model — the stable contract between pipeline stages.

Mirrors docs/architecture.md §5. Changing these types is a deliberate,
cross-phase decision (see docs/implementation-plan.md cross-cutting concerns).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Canonical spending categories (closed enum)."""

    FOOD = "Food"
    TRAVEL = "Travel"
    SHOPPING = "Shopping"
    BILLS = "Bills"
    EMI = "EMI"
    SUBSCRIPTIONS = "Subscriptions"
    SALARY = "Salary"
    RENT = "Rent"
    INVESTMENTS = "Investments"
    OTHER = "Other"


class CategorySource(str, Enum):
    """How a transaction's category was decided."""

    RULE = "rule"
    MEMORY = "memory"
    LLM = "llm"


class Direction(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class RecurringType(str, Enum):
    SUBSCRIPTION = "Subscription"
    EMI = "EMI"
    RENT = "Rent"
    SIP = "SIP"
    INSURANCE = "Insurance"


class InsightSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    POSITIVE = "positive"


class RawTransaction(BaseModel):
    """Stage 1 output — unnormalized, straight from the parsed file."""

    date: str | None = None
    description: str | None = None
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    balance: str | None = None
    # Any columns we couldn't map, kept for the manual-mapping fallback.
    extra: dict[str, str] = Field(default_factory=dict)


class Transaction(BaseModel):
    """Stage 2+ canonical transaction."""

    id: str
    date: str  # ISO 8601 (YYYY-MM-DD)
    description_raw: str
    merchant: str | None = None
    amount: float  # signed: negative = expense, positive = income
    direction: Direction
    balance: float | None = None
    category: Category = Category.OTHER
    category_source: CategorySource = CategorySource.RULE
    confidence: float | None = None
    is_recurring: bool = False
    recurring_id: str | None = None


class RecurringSeries(BaseModel):
    """Stage 4 output — a detected recurring payment stream."""

    id: str
    merchant: str
    type: RecurringType
    cadence: str  # e.g. "monthly", "weekly", "quarterly"
    average_amount: float
    occurrences: int
    next_expected_date: str | None = None
    transaction_ids: list[str] = Field(default_factory=list)


class CategoryBreakdown(BaseModel):
    category: Category
    amount: float
    pct: float


class BiggestTransaction(BaseModel):
    id: str
    amount: float
    merchant: str | None = None
    description_raw: str | None = None
    date: str | None = None


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    spend: float
    income: float


class Period(BaseModel):
    start: str
    end: str


class Summary(BaseModel):
    """Stage 5 output — deterministic metrics (never LLM-computed)."""

    period: Period
    total_income: float
    total_spend: float
    net_savings: float
    savings_rate: float
    by_category: list[CategoryBreakdown] = Field(default_factory=list)
    top_categories: list[Category] = Field(default_factory=list)
    biggest_transaction: BiggestTransaction | None = None
    recurring_total: float = 0.0
    recurring_count: int = 0
    monthly_trend: list[MonthlyTrend] = Field(default_factory=list)


class Insight(BaseModel):
    """Stage 6 output — human-readable, number-grounded insight."""

    title: str
    detail: str
    severity: InsightSeverity = InsightSeverity.INFO


class AnalyzeResponse(BaseModel):
    """The full payload returned by POST /api/analyze."""

    session_id: str
    transactions: list[Transaction] = Field(default_factory=list)
    summary: Summary | None = None
    recurring: list[RecurringSeries] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_model: str
    llm_enabled: bool
