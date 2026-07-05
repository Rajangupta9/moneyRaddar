# RupeeRadar — Architecture

> Companion to [context.md](context.md). This document proposes a concrete,
> buildable architecture for the RupeeRadar prototype and resolves the open
> decisions listed there. Choices favor a **working end-to-end prototype** and
> **privacy-conscious, local-first** processing, per the challenge constraints.

---

## 1. Design Principles

1. **Local-first / privacy by default** — Raw statements are processed on the
   user's machine (or a self-hosted backend). No financial data is persisted to
   third-party services. Only *anonymized, minimal* text snippets are sent to an
   LLM, and only when the deterministic layer can't classify confidently.
2. **Deterministic core, AI on the edges** — A fast rules engine handles the
   bulk of cleaning, categorization, and recurring detection. AI is used for
   (a) fallback categorization of unknown merchants and (b) natural-language
   insight generation — never as the sole source of truth for numbers.
3. **Pipeline, not monolith** — Each stage (ingest → clean → categorize →
   detect → metrics → insights → present) is an independent, testable module
   with a clear input/output contract.
4. **Prototype over completeness** — Support a few common statement formats well
   rather than every bank. Everything degrades gracefully to CSV.

---

## 2. Technology Stack

| Layer            | Choice                                   | Why |
|------------------|------------------------------------------|-----|
| Frontend         | **React + Vite + TypeScript**            | Fast dev, component ecosystem, easy static deploy |
| Charts           | **Recharts**                             | Simple declarative charts for the dashboard |
| Backend / API    | **Python 3.11 + FastAPI**                | Best data-processing ecosystem; async, typed, auto OpenAPI docs |
| Data processing  | **pandas**                               | Cleaning, grouping, aggregation |
| File parsing     | **pdfplumber** (PDF), **openpyxl** (XLSX), stdlib `csv` | Cover the common bank exports |
| Categorization   | **Rules engine + Groq (LLM) fallback**   | Deterministic first, AI for the long tail |
| Insights         | **Groq API (OpenAI-compatible)**         | Human-readable, grounded in computed numbers |
| Storage          | **SQLite** (local file) or in-memory     | Zero-config, local, private |
| Packaging        | **Docker Compose** (optional)            | One-command local run |

> **LLM note:** the project uses **Groq** (OpenAI-compatible API, `groq`
> Python SDK). Default model **`llama-3.3-70b-versatile`** for both
> categorization and insight generation; optionally switch high-volume
> categorization to the faster **`llama-3.1-8b-instant`**. The API key lives
> only in the backend `.env` (`GROQ_API_KEY`). Groq serves open models, so no
> financial data trains a provider model; still send only de-identified text.

---

## 3. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend (React)                        │
│  Upload ▸ Dashboard ▸ Transactions table ▸ Insights ▸ Report   │
└───────────────┬───────────────────────────────▲──────────────┘
                │ POST /upload (multipart)        │ JSON (summary,
                │                                 │ transactions, insights)
                ▼                                 │
┌──────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                      │
│                                                                │
│   ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌────────────┐   │
│   │ 1 Ingest │▸ │ 2 Clean/ │▸ │ 3 Categor- │▸ │ 4 Recurring│   │
│   │  Parser  │  │ Normalize│  │   izer     │  │  Detector  │   │
│   └──────────┘  └──────────┘  └─────┬──────┘  └─────┬──────┘   │
│                                     │               │          │
│                              ┌──────▼───────────────▼──────┐   │
│                              │  5 Metrics / Aggregation     │   │
│                              └──────────────┬───────────────┘  │
│                                             ▼                  │
│                              ┌──────────────────────────────┐  │
│                              │  6 Insight Generator (LLM)    │  │
│                              └──────────────┬───────────────┘  │
│                                             ▼                  │
│                              ┌──────────────────────────────┐  │
│                              │  7 Report Builder / Response  │  │
│                              └──────────────────────────────┘  │
│                                                                │
│   Sidecars:  Rules DB (YAML/JSON)   SQLite   Groq API client   │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Pipeline Stages (module contracts)

### Stage 1 — Ingest / Parse
- **Input:** uploaded file (`.csv`, `.xlsx`, `.pdf`) or pasted text.
- **Job:** detect format, extract a raw tabular structure, map bank-specific
  columns to a canonical schema via a small set of **column-mapping profiles**
  (e.g. "Date"/"Txn Date"/"Value Date" → `date`).
- **Output:** list of `RawTransaction` dicts (unnormalized).
- **Notes:** PDF is the hardest; use `pdfplumber` table extraction with a
  text-line fallback + regex. Unknown formats fall back to a generic CSV mapper
  and surface a "map your columns" step in the UI.

### Stage 2 — Clean / Normalize
- Parse and standardize **dates** (multiple formats → ISO).
- Parse **amounts**: strip currency symbols/commas; resolve debit vs. credit
  (single signed column, or separate debit/credit columns) into a signed
  `amount` (+income / −expense) plus an explicit `direction`.
- Clean the **description**: uppercase-normalize, collapse whitespace, strip
  UPI/IMPS/NEFT ref numbers, extract a probable **merchant** token
  (e.g. `UPI/SWIGGY/...` → `SWIGGY`).
- Deduplicate identical rows.
- **Output:** `Transaction` records matching the canonical schema (§5).

### Stage 3 — Categorize
Hybrid, in priority order:
1. **Rules engine** — keyword/regex → category map (e.g. `SWIGGY|ZOMATO` →
   `Food`; `NETFLIX|SPOTIFY|PRIME` → `Subscriptions`; `RENT` → `Rent`). Stored
   in a human-editable `rules.yaml`. Fast, free, deterministic.
2. **Merchant memory** — previously categorized merchants cached in SQLite so a
   merchant is classified once and reused.
3. **LLM fallback (Groq — Llama 3.3 70B)** — only for descriptions the rules
   can't resolve. Batched, sent **without** account numbers/PII, asked to return
   a category strictly from the canonical enum. Results are written back to
   merchant memory to shrink future LLM usage.
- **Output:** each transaction gets `category` + `category_source`
  (`rule`/`memory`/`llm`) + optional `confidence`.

### Stage 4 — Recurring Detection
- Group by normalized merchant / cleaned description.
- Flag a group as recurring when it shows **≥ 3 occurrences** with a
  **regular cadence** (monthly/weekly/quarterly) and **stable amount**
  (within a tolerance band, e.g. ±5%).
- Classify recurring type: `Subscription`, `EMI`, `Rent`, `SIP`, `Insurance`.
- **Output:** `RecurringSeries[]` (merchant, cadence, avg amount, next expected
  date, member transaction ids).

### Stage 5 — Metrics / Aggregation (pandas)
Compute deterministically (never via LLM):
- `total_income`, `total_spend`, `net_savings`, `savings_rate`
- Spend by category, top N categories
- Biggest single transaction (and biggest per category)
- Monthly trend (spend/income per month)
- Recurring spend total & count
- **Output:** `Summary` object consumed by both the dashboard and the insight
  generator.

### Stage 6 — Insight Generator (Groq LLM)
- **Input:** the computed `Summary` + recurring series (numbers only, no PII).
- **Job:** produce **≥ 3** concrete, human-readable insights that cite **actual
  amounts** — e.g. *"You spent ₹18,400 on Food this month, 32% of your
  spending and up 12% vs last month."*
- **Guardrails:** the LLM is told to use only the provided figures and not
  invent numbers; output is a structured JSON list (`title`, `detail`,
  `severity`) so the UI can render it and a validator can sanity-check amounts.

### Stage 7 — Report Builder / Response
- Assemble the API response: cleaned transactions + summary + recurring +
  insights.
- Generate a **shareable report**: server-rendered HTML → optional PDF export
  (client-side print-to-PDF for the prototype), plus a downloadable cleaned CSV.

---

## 5. Canonical Data Model

```jsonc
// Transaction
{
  "id": "txn_0001",
  "date": "2026-06-14",              // ISO 8601
  "description_raw": "UPI/SWIGGY/1234567890/Payment",
  "merchant": "SWIGGY",              // extracted
  "amount": -450.00,                 // signed: - = expense, + = income
  "direction": "debit",             // debit | credit
  "balance": 25340.00,               // if available
  "category": "Food",               // canonical enum
  "category_source": "rule",         // rule | memory | llm
  "is_recurring": false,
  "recurring_id": null
}
```

```jsonc
// Canonical categories (enum)
["Food","Travel","Shopping","Bills","EMI",
 "Subscriptions","Salary","Rent","Investments","Other"]
```

```jsonc
// Summary (computed, deterministic)
{
  "period": { "start": "2026-06-01", "end": "2026-06-30" },
  "total_income": 120000.0,
  "total_spend": 74500.0,
  "net_savings": 45500.0,
  "savings_rate": 0.379,
  "by_category": [ { "category": "Food", "amount": 18400.0, "pct": 0.247 } ],
  "top_categories": ["Food","Rent","Shopping"],
  "biggest_transaction": { "id": "txn_0091", "amount": -32000.0, "merchant": "..." },
  "recurring_total": 21500.0,
  "monthly_trend": [ { "month": "2026-06", "spend": 74500.0, "income": 120000.0 } ]
}
```

---

## 6. API Surface (FastAPI)

| Method | Endpoint            | Purpose |
|--------|---------------------|---------|
| `POST` | `/api/upload`       | Upload statement → returns a `session_id` + parsed preview |
| `POST` | `/api/analyze`      | Run full pipeline for a session → transactions + summary + recurring + insights |
| `GET`  | `/api/summary/{id}` | Fetch computed summary/metrics |
| `GET`  | `/api/report/{id}`  | Get shareable HTML/PDF report |
| `GET`  | `/api/export/{id}`  | Download cleaned transactions as CSV |

> For the simplest prototype, `/api/upload` and `/api/analyze` can be collapsed
> into a single synchronous call that returns the full result payload.

---

## 7. Frontend Views

1. **Upload** — drag-and-drop file, format hint, column-mapping fallback UI.
2. **Dashboard** — KPI tiles (income, spend, savings, savings rate); category
   pie/bar; monthly trend line; biggest-transaction callout.
3. **Transactions** — searchable/filterable table with editable category
   (edits feed merchant memory).
4. **Recurring** — list of detected subscriptions/EMIs with cadence & next date.
5. **Insights** — the ≥3 generated insight cards.
6. **Report** — printable/shareable summary + export buttons.

> Charting choices (color, chart type, KPI tiles) should follow the `dataviz`
> skill when the dashboard is built.

---

## 8. Privacy & Security

- **Local processing** — parsing, cleaning, categorization, and metrics run
  entirely on-device/backend; no raw statement leaves the environment.
- **Minimal LLM exposure** — only short, de-identified description/merchant
  strings and aggregate numbers are sent to the Groq LLM; account numbers,
  names, balances, and full statements are never transmitted.
- **No third-party persistence** — data stored only in a local SQLite file or
  in memory; a "delete my data" action wipes the session.
- **Secrets** — Groq API key in backend `.env`, never shipped to the client.
- **PII scrubbing** — a redaction pass strips ref numbers, card/account digits,
  and phone numbers before any external call.

---

## 9. Proposed Repository Layout

```
RupeeRadar/
├── docs/
│   ├── problemStatement.txt
│   ├── context.md
│   └── architecture.md          ← this file
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + routes
│   │   ├── pipeline/
│   │   │   ├── ingest.py        # Stage 1
│   │   │   ├── clean.py         # Stage 2
│   │   │   ├── categorize.py    # Stage 3 (rules + LLM)
│   │   │   ├── recurring.py     # Stage 4
│   │   │   ├── metrics.py       # Stage 5
│   │   │   ├── insights.py      # Stage 6 (Groq LLM)
│   │   │   └── report.py        # Stage 7
│   │   ├── rules.yaml           # merchant → category keyword rules
│   │   ├── models.py            # pydantic schemas (canonical model)
│   │   ├── llm.py               # Groq client + redaction
│   │   └── store.py             # SQLite / merchant memory
│   ├── tests/                   # sample statements + pipeline tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/ (Upload, Dashboard, Transactions, Recurring, Insights, Report)
│   │   ├── components/ (KpiTile, CategoryChart, TrendChart, ...)
│   │   └── api.ts
│   └── package.json
├── sample_data/                 # anonymized example statements
└── docker-compose.yml           # optional one-command run
```

---

## 10. Build Order (suggested milestones)

1. **M1 – Core pipeline (CSV only):** ingest → clean → rules categorize →
   metrics, returned as JSON. Proves the end-to-end path.
2. **M2 – Dashboard:** React KPIs + category/trend charts against M1 output.
3. **M3 – Recurring detection** + Recurring view.
4. **M4 – LLM layer:** Groq fallback categorization + insight generation with
   number-grounding guardrails.
5. **M5 – Formats & report:** PDF/XLSX ingest, shareable report + CSV export.
6. **M6 – Privacy polish:** redaction pass, delete-data action, docs/deploy.

> Each milestone is independently demoable, satisfying the "working end-to-end
> prototype over completeness" constraint.

---

## 11. Key Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Messy/varied statement formats | Column-mapping profiles + generic CSV fallback + manual mapping UI |
| PDF extraction unreliability | `pdfplumber` tables → regex text fallback; recommend CSV export path |
| LLM miscategorization / hallucinated numbers | Rules-first; LLM constrained to enum; metrics computed in code, not by LLM; number validator on insights |
| Privacy of financial data | Local processing, redaction, no third-party persistence |
| LLM cost/latency at volume | Rules + merchant memory cache minimize LLM calls; batch + fast Groq model (llama-3.1-8b-instant) |
