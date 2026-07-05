# RupeeRadar — Phase-wise Implementation Plan

> Derived from [architecture.md](architecture.md) and [context.md](context.md).
> Expands the M1–M6 build order into concrete, sequenced tasks with deliverables
> and acceptance criteria. Each phase is **independently demoable**, honoring the
> "working end-to-end prototype over completeness" constraint.

**Legend:** 🎯 Goal · 📦 Deliverables · ✅ Acceptance criteria · 🔗 Depends on ·
🧩 Architecture ref

---

## Phase 0 — Project Scaffolding & Foundations
🎯 Stand up the repo skeleton, tooling, and shared contracts so every later
phase drops into place.

🔗 Depends on: nothing (start here).
🧩 Ref: §2 Tech Stack, §5 Data Model, §9 Repo Layout.

### Tasks
- [ ] Create the repo layout from §9 (`backend/`, `frontend/`, `sample_data/`).
- [ ] **Backend:** init Python 3.11 project, `requirements.txt`
      (`fastapi`, `uvicorn`, `pandas`, `pydantic`, `python-multipart`,
      `pdfplumber`, `openpyxl`, `pyyaml`, `groq`, `pytest`).
- [ ] Scaffold FastAPI app (`app/main.py`) with `/api/health`.
- [ ] Define **canonical pydantic models** (`app/models.py`): `RawTransaction`,
      `Transaction`, `Category` enum, `RecurringSeries`, `Summary`, `Insight`.
- [ ] **Frontend:** init React + Vite + TypeScript, add Recharts, set up
      `src/api.ts` client and routing shell for the 6 views.
- [ ] Add `.env.example` (backend) with `GROQ_API_KEY` placeholder.
- [ ] Add 2–3 **anonymized sample CSV statements** to `sample_data/`.
- [ ] Wire dev scripts (`uvicorn` reload, `vite dev`) and CORS.

📦 Runnable empty app: frontend loads, hits `/api/health`, models importable.
✅ `pytest` runs (even if 0 tests); `GET /api/health` returns 200; frontend dev
server renders an empty shell talking to the backend.

---

## Phase 1 (M1) — Core Pipeline, CSV only
🎯 Prove the full end-to-end path: **ingest → clean → rules-categorize →
metrics**, returned as JSON from a single endpoint.

🔗 Depends on: Phase 0.
🧩 Ref: §4 Stages 1–3 & 5, §6 API.

### Tasks
- [ ] **Stage 1 — `ingest.py` (CSV):** detect header, apply 2–3
      **column-mapping profiles** → `RawTransaction[]`; generic fallback mapper.
- [ ] **Stage 2 — `clean.py`:** ISO date parsing (multi-format); amount parsing
      (strip ₹/commas, resolve debit/credit → signed `amount` + `direction`);
      description normalize + **merchant extraction** (regex on UPI/IMPS/NEFT);
      dedupe.
- [ ] **Stage 3 — `categorize.py` (rules only):** author `rules.yaml`
      (keyword/regex → category for the canonical enum); apply rules, default to
      `Other`; set `category_source="rule"`.
- [ ] **Stage 5 — `metrics.py`:** pandas aggregation → `Summary`
      (income, spend, savings, savings rate, by-category, top categories,
      biggest transaction, monthly trend).
- [ ] **API:** `POST /api/analyze` (collapsed upload+analyze) returns
      `{ transactions, summary }`.
- [ ] **Tests:** unit tests for date/amount parsing, merchant extraction, rule
      hits, and metric math against a known sample CSV.

📦 One API call turns a messy CSV into cleaned+categorized transactions + a
computed summary.
✅ Given a sample CSV, `/api/analyze` returns correctly signed amounts, sane
categories, and metrics that reconcile (`income − spend == net_savings`);
core unit tests pass.

---

## Phase 2 (M2) — Dashboard
🎯 Make the M1 output visible: an actual spend summary dashboard.

🔗 Depends on: Phase 1.
🧩 Ref: §7 Views 1–2; follow the `dataviz` skill for charts.

### Tasks
- [ ] **Upload view:** drag-and-drop CSV → calls `/api/analyze`, handles
      loading/error states.
- [ ] **Dashboard view:** KPI tiles (income, spend, savings, savings rate);
      category breakdown (pie/bar); monthly trend line; biggest-transaction
      callout.
- [ ] **Transactions view:** searchable/filterable table of cleaned rows.
- [ ] Shared components: `KpiTile`, `CategoryChart`, `TrendChart`,
      `TransactionsTable`.
- [ ] Invoke the **`dataviz` skill** before building charts (palette, chart
      types, KPI tile design, light/dark).

📦 Upload a CSV in the browser → see KPIs, category chart, trend, and a
transactions table.
✅ Numbers on the dashboard match the API `Summary`; charts render in light and
dark; empty/error states handled.

---

## Phase 3 (M3) — Recurring Detection
🎯 Detect subscriptions/EMIs/rent/SIPs/insurance and surface them.

🔗 Depends on: Phase 1 (data) + Phase 2 (UI).
🧩 Ref: §4 Stage 4, §7 View 4.

### Tasks
- [ ] **Stage 4 — `recurring.py`:** group by normalized merchant; flag series
      with **≥3 occurrences**, regular cadence (weekly/monthly/quarterly), and
      **stable amount (±5%)**; classify type
      (`Subscription`/`EMI`/`Rent`/`SIP`/`Insurance`); compute avg amount +
      next-expected date → `RecurringSeries[]`.
- [ ] Back-annotate transactions with `is_recurring` + `recurring_id`.
- [ ] Extend `Summary` with `recurring_total` / count; include series in
      `/api/analyze` response.
- [ ] **Recurring view:** list detected series with cadence, amount, next date;
      link members back to the transactions table.
- [ ] **Tests:** synthetic series (monthly Netflix, EMI, rent) detected;
      one-off transactions not flagged.

📦 A "Recurring" screen listing detected subscriptions/EMIs with cadence and
next-due date.
✅ Seeded recurring patterns are detected with correct cadence/type; false
positives on random one-offs are avoided in tests.

---

## Phase 4 (M4) — LLM Layer (Groq)
🎯 Add AI where it earns its place: **fallback categorization** for unknown
merchants and **grounded insight generation**.

🔗 Depends on: Phases 1 & 3.
🧩 Ref: §4 Stages 3 & 6, §2 LLM note. Uses the `groq` SDK (OpenAI-compatible).

### Tasks
- [ ] **`llm.py`:** Groq client, model config (`llama-3.3-70b-versatile` by
      default; optional `llama-3.1-8b-instant` for high-volume categorization),
      key from `.env` (`GROQ_API_KEY`), retry/timeout.
- [ ] **Merchant memory — `store.py`:** SQLite cache of merchant→category;
      read before LLM, write after (shrinks future calls).
- [ ] **Stage 3 fallback:** for rule-misses, batch de-identified
      merchant/description strings → Groq → category **constrained to the
      enum**; set `category_source="llm"` + confidence; persist to memory.
- [ ] **Stage 6 — `insights.py`:** send **computed numbers only** (Summary +
      recurring) → Groq → **≥3** insights as structured JSON
      (`title`,`detail`,`severity`) citing real amounts.
- [ ] **Guardrails:** redaction before any call; **number validator** rejecting
      insights whose figures aren't in the Summary; graceful degrade if no API
      key (skip insights, keep rules-only categorization).
- [ ] **Insights view:** render insight cards.
- [ ] **Tests:** enum-constraint enforcement; validator rejects hallucinated
      numbers; memory cache hit path; no-API-key fallback.

📦 Unknown merchants get sensibly categorized; the app shows ≥3 personalized,
number-grounded insights.
✅ LLM categories always fall within the enum; every displayed insight's numbers
trace to the Summary; app still runs (degraded) without an API key.

---

## Phase 5 (M5) — Formats & Report
🎯 Broaden ingestion beyond CSV and produce a shareable deliverable.

🔗 Depends on: Phases 1–4.
🧩 Ref: §4 Stages 1 & 7, §6 API, §7 View 6.

### Tasks
- [ ] **Stage 1 — XLSX ingest** via `openpyxl` (reuse mapping profiles).
- [ ] **Stage 1 — PDF ingest** via `pdfplumber` table extraction + **regex
      text-line fallback**; recommend CSV when confidence is low.
- [ ] **Column-mapping fallback UI:** when auto-mapping fails, let the user map
      columns manually (satisfies §11 messy-format risk).
- [ ] **Stage 7 — `report.py`:** server-rendered HTML report (summary +
      categories + recurring + insights); `GET /api/report/{id}`.
- [ ] **Exports:** `GET /api/export/{id}` cleaned CSV; client-side
      print-to-PDF for the report.
- [ ] Split endpoints if needed (`/api/upload` preview + `/api/analyze`).
- [ ] **Tests:** XLSX + PDF sample parsing; report/CSV export shape.

📦 Upload CSV/XLSX/PDF; download a shareable report and a cleaned CSV.
✅ All three formats reach the same canonical schema; report renders and PDF/CSV
export download correctly.

---

## Phase 6 (M6) — Privacy Polish, Docs & Deploy
🎯 Deliver the privacy-conscious, runnable final per the evaluation criteria.

🔗 Depends on: Phases 1–5.
🧩 Ref: §8 Privacy & Security, §1 Principles.

### Tasks
- [ ] **Redaction pass** hardened: strip ref/card/account digits + phone numbers
      before any external call; unit-test the scrubber.
- [ ] **Delete-my-data** action: wipe session (SQLite rows / in-memory store).
- [ ] Confirm **no raw statement** ever leaves the backend; audit LLM payloads.
- [ ] **`docker-compose.yml`** for one-command local run; README with setup,
      env, and privacy notes.
- [ ] End-to-end smoke test via the `verify` skill on the full flow.
- [ ] Optional: deploy (static frontend + backend) with API key server-side.

📦 A deployed or locally runnable app that takes a raw statement and produces a
clear, shareable finance summary — privacy-conscious by construction.
✅ Redaction verified on payloads; delete-data wipes state; `docker compose up`
runs the whole app; README lets a fresh user run it end-to-end.

---

## Cross-Cutting Concerns (every phase)
- **Testing:** grow `backend/tests/` with each stage; keep sample data
  anonymized.
- **Contracts stay stable:** the canonical models (§5) are the interface between
  phases — change them deliberately.
- **Privacy is not a final step:** never log raw descriptions; redact before any
  external call from Phase 4 onward.
- **Numbers are code, not AI:** all metrics computed deterministically; the LLM
  only narrates validated figures.

## Dependency Flow
```
Phase 0 ─▶ Phase 1 ─┬─▶ Phase 2 ─┐
                    └─▶ Phase 3 ──┼─▶ Phase 4 ─▶ Phase 5 ─▶ Phase 6
                                  ┘
```

## Requirements Traceability (context.md → phases)
| Requirement (context.md)            | Delivered in |
|-------------------------------------|--------------|
| Accept bank statement data          | P1 (CSV), P5 (XLSX/PDF) |
| Extract/clean into structured form  | P1 (Stage 2) |
| Categorize into canonical groups    | P1 (rules), P4 (LLM fallback) |
| Detect recurring payments           | P3 |
| Key financial metrics               | P1 (Stage 5) |
| Human-readable insights (≥3)        | P4 |
| Simple UI / dashboard / report      | P2 (dashboard), P5 (report) |
| Privacy-conscious handling          | P4 (redaction), P6 (polish) |
| Deployed/locally runnable           | P6 |

## Suggested MVP Cut
If time-boxed, **Phases 0–2 + Phase 3** already satisfy most core requirements
(ingest, clean, categorize, recurring, metrics, dashboard). **Phase 4** adds the
required ≥3 insights. Treat **Phase 5 PDF** and **Phase 6 deploy** as the
stretch items.
