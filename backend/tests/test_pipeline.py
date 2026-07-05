"""Phase 1 acceptance: unit tests for each stage + an end-to-end /api/analyze.

Covers date/amount parsing, merchant extraction, rule hits, dedupe, and metric
math that reconciles (income - spend == net_savings), per the plan's Phase 1
acceptance criteria.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Category, Direction
from app.pipeline import run_pipeline
from app.pipeline.categorize import categorize
from app.pipeline.clean import clean, extract_merchant, parse_amount, parse_date
from app.pipeline.ingest import parse_csv
from app.pipeline.metrics import compute_summary

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
client = TestClient(app)


def read_sample(name: str) -> str:
    return (SAMPLE_DIR / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Stage 2 — date parsing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-06-14", "2026-06-14"),
        ("14/06/2026", "2026-06-14"),  # day-first (Indian convention)
        ("14-06-2026", "2026-06-14"),
        ("01/06/2026", "2026-06-01"),
        ("14 Jun 2026", "2026-06-14"),
        ("garbage", None),
        (None, None),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


# --------------------------------------------------------------------------- #
# Stage 2 — amount parsing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,10,000.00", 110000.0),  # Indian grouping
        ("₹450", 450.0),
        ("-380.50", -380.50),
        ("2,340.00", 2340.0),
        ("(123.45)", -123.45),  # accounting negative
        ("", None),
        (None, None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


# --------------------------------------------------------------------------- #
# Stage 2 — merchant extraction
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "desc,expected",
    [
        ("UPI/SWIGGY/1234567890/PAYMENT/HDFC", "SWIGGY"),
        ("IMPS-SWIGGY INSTAMART-987654", "SWIGGY INSTAMART"),
        ("UPI-OLA CABS-556677", "OLA CABS"),
        ("SAL/JUN/GLOBEX SOFTWARE LLP", "GLOBEX SOFTWARE LLP"),
        ("NETFLIX SUBSCRIPTION", "NETFLIX SUBSCRIPTION"),
    ],
)
def test_extract_merchant(desc, expected):
    assert extract_merchant(desc) == expected


# --------------------------------------------------------------------------- #
# Stage 1+2 — ingest resolves debit/credit and Dr/Cr into signed amounts
# --------------------------------------------------------------------------- #
def test_hdfc_debit_credit_columns():
    raw, profile = parse_csv(read_sample("sample_hdfc.csv"))
    assert profile == "hdfc"
    txns = clean(raw)
    salary = next(t for t in txns if "SALARY" in t.description_raw)
    swiggy = next(t for t in txns if "SWIGGY" in t.description_raw)
    assert salary.amount == 120000.0 and salary.direction == Direction.CREDIT
    assert swiggy.amount == -450.0 and swiggy.direction == Direction.DEBIT


def test_icici_dr_cr_indicator():
    raw, profile = parse_csv(read_sample("sample_icici.csv"))
    assert profile == "icici"
    txns = clean(raw)
    sal = next(t for t in txns if "GLOBEX" in t.description_raw)
    emi = next(t for t in txns if "BAJAJ" in t.description_raw)
    assert sal.amount == 110000.0 and sal.direction == Direction.CREDIT
    assert emi.amount == -5600.0 and emi.direction == Direction.DEBIT


# --------------------------------------------------------------------------- #
# Stage 2 — dedupe
# --------------------------------------------------------------------------- #
def test_dedupe_exact_duplicates():
    raw, _ = parse_csv(read_sample("sample_generic.csv"))
    txns = clean(raw)
    coffee = [t for t in txns if "Coffee" in t.description_raw]
    # The generic sample has the same coffee row twice; only one survives.
    assert len(coffee) == 1


# --------------------------------------------------------------------------- #
# Stage 3 — rule hits
# --------------------------------------------------------------------------- #
def test_rule_categorization():
    raw, _ = parse_csv(read_sample("sample_hdfc.csv"))
    txns = categorize(clean(raw))
    by_desc = {t.description_raw: t.category for t in txns}
    assert by_desc["UPI/SWIGGY/1234567890/Payment/HDFC"] == Category.FOOD
    assert by_desc["NETFLIX SUBSCRIPTION"] == Category.SUBSCRIPTIONS
    assert by_desc["ACH DR/HDFC HOME LOAN EMI"] == Category.EMI
    assert by_desc["NEFT/RENT PAYMENT/LANDLORD"] == Category.RENT
    assert by_desc["SIP/AXIS MUTUAL FUND"] == Category.INVESTMENTS
    assert by_desc["SALARY CREDIT ACME TECHNOLOGIES PVT LTD"] == Category.SALARY
    assert by_desc["UPI/UBER/1122334455/Ride"] == Category.TRAVEL
    # Every rule-categorized txn is stamped as such.
    assert all(t.category_source.value == "rule" for t in txns)


# --------------------------------------------------------------------------- #
# Stage 5 — metric math reconciles
# --------------------------------------------------------------------------- #
def test_metrics_reconcile():
    txns, summary, _ = run_pipeline(read_sample("sample_hdfc.csv"))
    # income - spend == net_savings (deterministic reconciliation)
    assert round(summary.total_income - summary.total_spend, 2) == summary.net_savings
    # HDFC sample: one salary + one cashback credit.
    assert summary.total_income == 120000.0 + 150.0
    # Category percentages of spend sum to ~1.
    assert abs(sum(c.pct for c in summary.by_category) - 1.0) < 0.001
    # Biggest expense is the home-loan EMI (₹32,000).
    assert summary.biggest_transaction.amount == -32000.0
    assert summary.savings_rate == round(summary.net_savings / summary.total_income, 4)


def test_metrics_empty_input():
    summary = compute_summary([])
    assert summary.total_income == 0.0 and summary.net_savings == 0.0


# --------------------------------------------------------------------------- #
# End-to-end — POST /api/analyze
# --------------------------------------------------------------------------- #
def test_analyze_endpoint_end_to_end():
    csv_bytes = read_sample("sample_icici.csv").encode("utf-8")
    resp = client.post(
        "/api/analyze",
        files={"file": ("sample_icici.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert len(body["transactions"]) > 0
    summary = body["summary"]
    assert round(summary["total_income"] - summary["total_spend"], 2) == summary["net_savings"]
    # Phase 1 leaves these for later phases.
    assert body["recurring"] == [] and body["insights"] == []


def test_analyze_rejects_non_csv():
    resp = client.post(
        "/api/analyze",
        files={"file": ("statement.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 415
