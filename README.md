# BenefitPulse Engine

**BenefitPulse** watches card transactions, flags unused protections (purchase protection, return protection, travel delay, extended warranty), scores eligibility, pre-fills claims, and answers policy questions through a RAG-backed chat assistant.

This repo is a working **prototype** — local demo mode out of the box, optional free-tier cloud (Gemini + Supabase) when you want live agents and Postgres.

```
Transaction → Transaction Intelligence → Benefit Knowledge (RAG)
           → Rules Engine → Confidence → Claim Prefill → UI + Assistant
```

---

## What’s in the box

| Layer | Stack |
|--------|--------|
| Frontend | React 19, Vite, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Agents | LangGraph multi-agent pipeline |
| RAG | ChromaDB + 6 policy markdown docs |
| LLM | Google Gemini (free tier) with rule fallback |
| Data | Local JSON demo store **or** Supabase Postgres |
| Auth | Demo tokens **or** Supabase Auth |

**Happy path:** Sign in → Dashboard (detections) → Claim review (pre-filled) → Submit → Ask the assistant.

---

## Quick start (demo mode — no cloud keys)

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # Unix: cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### 3. Demo login

| Field | Value |
|--------|--------|
| Email | `demo@amex.com` |
| Password | `demo1234` |

Seed data: one Platinum card, sample transactions, detected benefits, and draft claims.

---

## Optional: live Gemini + Supabase

### Gemini (live agents + better RAG)

1. Create a key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Put it in `backend/.env`:

```env
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001
```

3. Rebuild the vector index (once, or after policy edits):

```bash
cd backend
python scripts/reindex_chroma.py
```

Without a key the pipeline still runs using **rule-based fallbacks**.

### Supabase (cloud Postgres + Auth)

1. Create a free project at [supabase.com](https://supabase.com).
2. SQL Editor → run `supabase/schema.sql`.
3. Auth → Email enabled; for local demos, turn off “Confirm email”.
4. Project Settings → API → fill `backend/.env`:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
DEMO_MODE=false
DATA_BACKEND=supabase
```

5. Seed the demo user and data:

```bash
cd backend
python scripts/seed_supabase.py
```

6. Restart the backend. Check status: http://localhost:8000/api/system/status

> `DEMO_MODE=true` keeps data on local JSON but can still use Gemini + ChromaDB.

Copy `frontend/.env.example` → `frontend/.env` only if the API is not on `localhost:8000` (Vite proxies by default).

---

## Project layout

```
BenefitPulse-Engine/
├── frontend/                 # React + Vite UI
│   ├── public/               # favicon, robots.txt
│   └── src/                  # pages, components, API client
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph pipeline + chat assistant
│   │   ├── rag/              # ChromaDB vector store
│   │   ├── routers/          # FastAPI routes
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # demo store, auth, Supabase
│   │   └── main.py
│   ├── knowledge_base/       # policy markdown for RAG
│   ├── scripts/              # reindex, seed, probes
│   └── requirements.txt
├── supabase/
│   └── schema.sql
├── .gitignore
└── README.md
```

---

## Agent pipeline

```
Transaction Intelligence → Benefit Knowledge (RAG) → Rules Engine
→ Confidence (≥ 0.60) → Claim Prefill → END
```

| Agent | Job |
|--------|-----|
| Transaction Intelligence | Normalize merchant, category, product type |
| Benefit Knowledge | Pull policy chunks + candidate benefits |
| Rules Evaluation | Deterministic eligible / not eligible |
| Confidence | Weighted score + breakdown |
| Claim Prefill | Near-complete claim + short explanation |
| Assistant | Conversational Q&A with claim + policy context |

Live detect: `POST /api/benefits/detect/{transaction_id}`

---

## API snapshot

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/signup` | Signup |
| GET | `/api/dashboard` | Aggregate dashboard |
| GET | `/api/benefits` | Detected benefits |
| GET | `/api/benefits/{id}` | Benefit + claim detail |
| POST | `/api/claims/{id}/submit` | Submit claim |
| POST | `/api/claims/{id}/documents` | Upload receipt |
| POST | `/api/assistant/chat` | Chatbot |
| GET | `/api/system/status` | Stack status |

---

## Knowledge base (RAG)

Under `backend/knowledge_base/`:

1. `purchase_protection_guide.md`
2. `return_protection_policy.md`
3. `travel_delay_insurance.md`
4. `extended_warranty.md`
5. `general_exclusions.md`
6. `faq_benefits.md`

Indexed into ChromaDB at startup (keyword fallback if embeddings are unavailable).

---

## Environment variables

See `backend/.env.example` and `frontend/.env.example`. **Never commit real keys** — `.env` files are gitignored.

---

## Requirements

- **Python** 3.11+
- **Node.js** 20+ (or recent LTS)
- Optional: Google AI Studio key, Supabase free project

---

## License

Prototype for educational / demo use. Not an official product of any card network.
