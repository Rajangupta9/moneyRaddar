# RupeeRadar

AI-powered personal finance assistant that turns messy bank-statement data into
clear spending insights. See [docs/](docs/) for the full context, architecture,
phase-wise plan, and edge-case catalogue.

- [docs/context.md](docs/context.md) — problem & requirements
- [docs/architecture.md](docs/architecture.md) — system design
- [docs/implementation-plan.md](docs/implementation-plan.md) — phased build plan
- [docs/edge-cases.md](docs/edge-cases.md) — corner cases

> **LLM:** RupeeRadar uses **Groq** (default model
> `llama-3.3-70b-versatile`, OpenAI-compatible API) for fallback
> categorization and insight generation.

## Status
**Phase 0 — Scaffolding complete.** Runnable empty app: FastAPI health endpoint,
canonical models, and a React shell with the six views. Pipeline logic lands
from Phase 1 onward.

## Layout
```
RupeeRadar/
├── backend/     FastAPI + pipeline (Python 3.11)
├── frontend/    React + Vite + TypeScript
├── sample_data/ Anonymized example statements
└── docs/        Project documentation
```

## Backend — run
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your GROQ_API_KEY
uvicorn app.main:app --reload # http://localhost:8000/api/health
```

Run tests:
```bash
cd backend
pytest
```

## Frontend — run
```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```
The dev server proxies `/api` to the backend on port 8000 (see
`frontend/vite.config.ts`).

## Privacy
Financial data is processed locally. Only de-identified merchant strings and
aggregate numbers are ever sent to the Groq LLM, and only when rules can't
classify a transaction. The API key stays server-side. See
[docs/architecture.md §8](docs/architecture.md).
