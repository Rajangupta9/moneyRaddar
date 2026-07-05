# RupeeRadar — Edge Cases & Corner Cases

> Derived from [architecture.md](architecture.md) and
> [implementation-plan.md](implementation-plan.md). A checklist of the
> real-world corner cases each pipeline stage must survive, so "handle messy
> real-world transaction descriptions" (an explicit evaluation criterion) is
> designed for, not discovered in the demo.

**Severity:** 🔴 must handle (breaks correctness/crashes) ·
🟠 should handle (wrong-but-recoverable) · 🟡 nice-to-have (polish).
Each row lists the **expected behavior** — the contract the code must meet.

---

## 1. Ingest / Parse (Stage 1 · Phase 1 & 5)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| I1 | Empty file / 0 rows | 🔴 | Reject with a clear "no transactions found" error, not a 500. |
| I2 | Header-only file (no data rows) | 🔴 | Same as I1; empty summary, not a crash. |
| I3 | Missing/renamed columns (`Txn Date` vs `Date` vs `Value Date`) | 🔴 | Column-mapping profiles resolve aliases; unknown → manual-mapping fallback. |
| I4 | Extra/unknown columns | 🟠 | Ignore gracefully; don't break mapping. |
| I5 | Reordered columns | 🟠 | Map by header name, never by position. |
| I6 | Preamble/footer junk rows (bank name, "Opening balance", disclaimers) | 🔴 | Detect the real header row; skip non-data lines. |
| I7 | Delimiter variance (`,` vs `;` vs tab); quoted fields containing commas | 🟠 | Sniff delimiter; use a real CSV parser, not `split(",")`. |
| I8 | Encoding: UTF-8 BOM, Latin-1, Windows-1252, `₹` mojibake | 🟠 | Detect/normalize encoding; never crash on decode. |
| I9 | Excessively large file (100k+ rows) | 🟠 | Stream/limit; guard memory; enforce a size cap with a friendly message. |
| I10 | Wrong file type or corrupt bytes (image renamed `.csv`, truncated PDF) | 🔴 | Validate; reject with actionable error. |
| I11 | Multi-account / multi-sheet XLSX | 🟠 | Pick/ask which sheet; don't silently merge accounts. |
| I12 | PDF with no extractable text (scanned image) | 🔴 | Detect zero text; message "OCR not supported — export CSV". No silent empty result. |
| I13 | PDF tables spanning multiple pages / repeated headers | 🟠 | Stitch pages; drop repeated header rows. |
| I14 | Merged multi-line description cells (PDF wrap) | 🟠 | Re-join continuation lines into one transaction. |
| I15 | Two amount columns (separate Debit & Credit) vs one signed column | 🔴 | Detect layout; reconcile into signed `amount`. |

---

## 2. Clean / Normalize (Stage 2 · Phase 1)

### Dates
| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| D1 | Mixed formats: `14/06/2026`, `2026-06-14`, `14-Jun-26`, `06/14/2026` | 🔴 | Parse each; infer day/month order per column (consistency check). |
| D2 | Ambiguous `01/02/2026` (DD/MM vs MM/DD) | 🟠 | Infer from column-wide evidence (values >12); default to DD/MM (Indian bank), flag if uncertain. |
| D3 | Two-digit years (`26`) | 🟠 | Pivot to 2000s sanely; reject implausible future/past. |
| D4 | Missing/blank date | 🟠 | Quarantine row or carry statement period; never emit `NaT` into metrics. |
| D5 | Value date ≠ transaction date | 🟡 | Pick one consistently (txn date); document choice. |

### Amounts
| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| A1 | Thousands separators, Indian lakh grouping `1,20,000.00` | 🔴 | Strip grouping correctly (not just US `,`). |
| A2 | Currency symbols/codes `₹`, `Rs.`, `INR`, trailing `/-` | 🔴 | Strip before parsing. |
| A3 | Negatives as `(1,200.00)`, trailing `-`, or `Dr`/`Cr` suffix | 🔴 | Map all to correct sign + `direction`. |
| A4 | Debit/Credit indicated by a separate column or `CR`/`DR` text | 🔴 | Resolve sign from indicator, not guesswork. |
| A5 | Blank amount in a debit or credit column (the "other" side) | 🔴 | Treat blank as 0/none; don't parse to `NaN` and pollute sums. |
| A6 | Zero-amount / reversal / adjustment entries | 🟠 | Keep but flag; exclude 0 from "biggest" logic. |
| A7 | Balance column present/absent/inconsistent | 🟡 | Optional; never required for correctness. |
| A8 | Amount with comma as decimal (`1.200,50` EU style) | 🟡 | Detect locale; low priority for Indian data. |
| A9 | Rounding / float precision in sums | 🟠 | Use fixed 2-dp rounding (or integer paise) to avoid `74499.999`. |

### Description / Merchant
| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| M1 | UPI ref noise `UPI/SWIGGY/1234567890/Payment/HDFC` | 🔴 | Extract `SWIGGY`; strip ref numbers/bank/handle. |
| M2 | IMPS/NEFT/RTGS formats with different delimiters | 🔴 | Handle `/`, `-`, `*`, space separators. |
| M3 | Blank / non-informative description (`ATM WDL`, `TRANSFER`) | 🟠 | Keep raw; merchant may be empty → `Other`. |
| M4 | Same merchant, many spellings (`AMAZON`, `AMZN`, `Amazon Pay`, `AMAZON.IN`) | 🟠 | Normalize/canonicalize so recurring + memory group them. |
| M5 | Merchant embedded mid-string with extra tokens | 🟠 | Token extraction, not first-word assumption. |
| M6 | Non-ASCII / regional-script merchant names | 🟡 | Preserve; don't crash normalization. |
| M7 | Personal names in P2P transfers (PII) | 🔴 | Never send to LLM un-redacted; treat as `Other`/transfer. |

### Dedupe
| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| C1 | Truly identical rows (double-export) | 🟠 | Dedupe on (date, amount, description, balance). |
| C2 | Legit same-day, same-amount, same-merchant txns (two ₹200 coffees) | 🔴 | Do **not** over-dedupe; require a distinguishing key or keep both. |

---

## 3. Categorize (Stage 3 · Phase 1 rules, Phase 4 LLM)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| G1 | No rule matches | 🔴 | Default to `Other` (Phase 1); LLM fallback (Phase 4). |
| G2 | Multiple rules match (`AMAZON` → Shopping vs Amazon Prime → Subscriptions) | 🟠 | Deterministic precedence (specific > generic); document order. |
| G3 | Ambiguous merchant (`PAYTM`, `PHONEPE` = wallet, any category) | 🟠 | Low-confidence; lean `Other` or infer from counterparty if present. |
| G4 | Income mis-tagged as expense (salary, refund, cashback) | 🔴 | Use `direction`: credits → Salary/Investments/Other-income, not spend. |
| G5 | Refund/reversal of a prior expense | 🟠 | Credit that offsets category; don't inflate income. |
| G6 | Self-transfers between own accounts | 🟠 | Recognize/flag; exclude from spend to avoid double counting. |
| G7 | Category enum drift | 🔴 | Validate every category ∈ canonical enum; reject others. |
| G8 (LLM) | LLM returns a value outside the enum or free text | 🔴 | Constrain + validate; on violation fall back to `Other`. |
| G9 (LLM) | LLM returns different categories for the same merchant across batches | 🟠 | Merchant-memory cache pins first decision for consistency. |
| G10 (LLM) | LLM call fails / rate-limited / no API key | 🔴 | Degrade to `Other`; app still completes (Phase 4 guardrail). |
| G11 (LLM) | Prompt-injection text inside a description | 🟠 | Treat description as data, not instructions; strict output schema. |

---

## 4. Recurring Detection (Stage 4 · Phase 3)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| R1 | Fewer than 3 occurrences | 🔴 | Not recurring (threshold), even if amounts match. |
| R2 | Irregular gaps (annual, 28–31 day months, Feb) | 🟠 | Tolerance window on cadence; month-length aware. |
| R3 | Amount drift (variable EMI, rent hike, usage bills) | 🟠 | ±5% band; allow a "variable recurring" class rather than dropping it. |
| R4 | Merchant spelling variance across occurrences | 🔴 | Group on normalized merchant (see M4), not raw string. |
| R5 | Two different subscriptions, same amount, same merchant name | 🟡 | Don't over-merge; consider day-of-month signature. |
| R6 | Statement too short to see a full cycle | 🟠 | Report "insufficient history"; don't false-positive. |
| R7 | Cancelled subscription (stops mid-history) | 🟡 | Detect as past-recurring; next-date logic shouldn't project forever. |
| R8 | One-off large purchase EMI-converted later | 🟡 | Classify emerging EMI once ≥3 installments appear. |
| R9 | Next-expected date crossing month/year boundary | 🟠 | Correct date math (leap years, Dec→Jan). |
| R10 | Weekly vs monthly ambiguity (4–5 occurrences/month) | 🟠 | Pick cadence by dominant gap; don't flip-flop. |

---

## 5. Metrics / Aggregation (Stage 5 · Phase 1)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| T1 | Zero income (spend-only statement) | 🔴 | `savings_rate` guarded against ÷0 → 0 or N/A, not `Inf`/`NaN`. |
| T2 | Zero spend | 🟠 | Category charts handle empty gracefully. |
| T3 | Negative savings (spend > income) | 🟠 | Show negative honestly; don't clamp to 0. |
| T4 | Single transaction / single category | 🟠 | "Top categories" & percentages still valid. |
| T5 | All transactions in one month vs multi-month | 🟠 | Monthly trend adapts; "this month" defined by statement period. |
| T6 | Percentages must sum to ~100% | 🟠 | Rounding reconciliation so pie doesn't show 99.7%. |
| T7 | Biggest transaction ties / equal amounts | 🟡 | Deterministic tiebreak (date/id). |
| T8 | Self-transfers counted in spend | 🔴 | Exclude (see G6) to avoid inflated totals. |
| T9 | Currency mixing (foreign txn in USD) | 🟡 | Out of scope for prototype; flag/skip, don't sum across currencies. |
| T10 | Metric ≠ what LLM narrates | 🔴 | Metrics are code-of-record; insights validated against them. |

---

## 6. Insights (Stage 6 · Phase 4)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| N1 | LLM invents a number not in the Summary | 🔴 | Number validator rejects/regenerates; never display unverified figures. |
| N2 | Fewer than 3 insights returned | 🟠 | Retry or backfill deterministic insights to meet the ≥3 requirement. |
| N3 | Sparse data (1–2 transactions) | 🟠 | Generate honest, modest insights; no fabricated trends. |
| N4 | No prior month → "vs last month" impossible | 🟠 | Only make comparisons the data supports. |
| N5 | Malformed JSON from LLM | 🔴 | Robust parse/repair or retry; fail soft to deterministic insights. |
| N6 | Insight leaks PII (a person's name) | 🔴 | Only aggregate numbers sent in; validate output for stray PII. |
| N7 | Currency/locale formatting (₹, lakh grouping) | 🟡 | Format amounts consistently in output. |

---

## 7. Privacy & Security (§8 · Phase 4 & 6)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| P1 | Account/card numbers in descriptions | 🔴 | Redact before any LLM call; unit-tested scrubber. |
| P2 | Phone numbers / emails / UPI handles in text | 🔴 | Redact; never transmit. |
| P3 | Raw statement accidentally logged | 🔴 | Never log raw descriptions/amounts at info level. |
| P4 | LLM payload audit | 🔴 | Assert no PII fields present in outgoing request. |
| P5 | Delete-my-data leaves residue (SQLite, temp files, caches) | 🔴 | Wipe all session artifacts, including uploaded temp files. |
| P6 | API key exposure to client bundle | 🔴 | Key stays server-side only; never in frontend build. |
| P7 | Merchant-memory cache persists PII across sessions | 🟠 | Cache only normalized merchant→category, never PII/amounts. |

---

## 8. API / Upload / Frontend (§6, §7 · Phase 2 & 5)

| # | Edge case | Sev | Expected behavior |
|---|-----------|-----|-------------------|
| U1 | Upload wrong extension or > size cap | 🔴 | 4xx with clear message; no crash. |
| U2 | Concurrent uploads / session mixups | 🟠 | Isolate by `session_id`; no cross-contamination. |
| U3 | Analyze called before upload / invalid `session_id` | 🔴 | 404/409 with clear error. |
| U4 | Very long processing (large PDF) | 🟠 | Loading state; timeout handling; no frozen UI. |
| U5 | Backend down / network error | 🟠 | Frontend shows retryable error, not a blank screen. |
| U6 | User edits a category in the table | 🟠 | Persist edit; feed merchant memory; recompute metrics. |
| U7 | Empty result set reaches the dashboard | 🟠 | Empty states for KPIs/charts/tables, not broken charts. |
| U8 | Charts in light vs dark theme | 🟡 | Legible in both (per `dataviz`). |
| U9 | Report/CSV export with special chars or huge row count | 🟠 | Proper escaping/encoding; streamed download. |
| U10 | Manual column-mapping produces an invalid mapping | 🟠 | Validate mapping (required fields present) before analyze. |

---

## Priority Test Matrix (build fixtures for these first)
The highest-leverage 🔴 cases to encode as sample-data fixtures in
`backend/tests/` (per the plan's cross-cutting testing note):

1. **Messy CSV** covering I3, I6, I15, A1–A4, M1–M2 in one file.
2. **Debit/Credit two-column** bank export (A4, I15, G4).
3. **Indian number grouping + `₹`/`Dr`/`Cr`** amounts (A1–A3).
4. **UPI/IMPS description noise** with PII to test M1, M7, P1–P2.
5. **Recurring fixture** (monthly Netflix, variable EMI, rent hike) for R1–R4.
6. **Spend-only / zero-income** statement for T1, T3.
7. **Empty & header-only** files for I1–I2.
8. **LLM-off run** (no API key) proving G10 + N-degradation still completes.

> Rule of thumb: every 🔴 row should have a failing test before its fix, and a
> fixture that proves it stays fixed.
