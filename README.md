# BenefitPulse Engine

**BenefitPulse** watches card transactions, flags unused protections (purchase protection, return protection, travel delay, extended warranty), scores eligibility, pre-fills claims, and answers policy questions through a RAG-backed chat assistant.

This prototype runs **only** with **Supabase** (Postgres + Auth) and a **Google Gemini API key**. There is no offline / local-JSON demo mode.

```
Transaction → Transaction Intelligence → Benefit Knowledge (ChromaDB RAG)
           → Rules Engine → Confidence → Claim Prefill → UI + Assistant
```

---

## Stack

| Layer | Technology |
|--------|------------|
| Frontend | React 19, Vite, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Agents | LangGraph multi-agent pipeline + Google Gemini |
| RAG | ChromaDB + Gemini embeddings over 6 policy markdown files |
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth |

**Happy path:** Sign in → Overview → Benefits / Transactions / Simulate → Claim review → Submit → Ask the assistant.

---

## Prerequisites

1. **Python** 3.11+ and **Node.js** 20+
2. **Google Gemini API key** — [Google AI Studio](https://aistudio.google.com/apikey)
3. **Supabase project** — [supabase.com](https://supabase.com)

Without `GOOGLE_API_KEY` and all `SUPABASE_*` variables, the backend **refuses to start**.

---

## Setup

### 1. Supabase schema

1. Create a free Supabase project.
2. SQL Editor → run the full file `supabase/schema.sql`.
3. Authentication → Providers → Email enabled.
4. Authentication → Settings → turn **off** “Confirm email” for local development (or confirm emails manually).
5. Project Settings → API → copy URL, anon key, service role key, and JWT secret.

### 2. Backend env

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # Unix: cp .env.example .env
```

Edit `backend/.env` (required fields):

```env
GOOGLE_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001

SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 3. Seed sample data (optional but recommended)

```bash
cd backend
python scripts/seed_supabase.py
```

Creates a sample member with The Platinum Card® and a few transactions:

| Field | Value |
|--------|--------|
| Email | `demo@amex.com` |
| Password | `demo1234` |

You can also sign up a new account in the UI (gets a Platinum card automatically).

### 4. Build / refresh ChromaDB index

```bash
cd backend
python scripts/reindex_chroma.py
```

Uses Gemini embeddings. First run may take a minute.

### 5. Start API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  
- Stack status: http://localhost:8000/api/system/status  

### 6. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173  

Copy `frontend/.env.example` → `frontend/.env` only if the API is not on `localhost:8000` (Vite proxies by default).

---

## Project layout

```
card-benefit-activation-engine/
├── frontend/                 # React + Vite UI
│   └── src/                  # pages, components, API client
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph pipeline + chat assistant
│   │   ├── rag/              # ChromaDB vector store
│   │   ├── routers/          # FastAPI routes
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Supabase store, auth, clients
│   │   └── main.py
│   ├── knowledge_base/       # policy markdown for RAG
│   ├── scripts/              # reindex, seed, probes
│   ├── .env.example
│   └── requirements.txt
├── supabase/
│   └── schema.sql
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
| Transaction Intelligence | Normalize merchant, category, product type (Gemini) |
| Benefit Knowledge | Pull policy chunks from ChromaDB + candidate benefits |
| Rules Evaluation | Deterministic eligible / not eligible |
| Confidence | Weighted score + breakdown |
| Claim Prefill | Near-complete claim + short explanation |
| Assistant | Conversational Q&A with claim + policy context |

Live detect: `POST /api/benefits/detect/{transaction_id}`

---

## API snapshot

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login (Supabase Auth) |
| POST | `/api/auth/signup` | Signup (Supabase Auth) |
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

Indexed into ChromaDB at startup with Gemini embeddings.

---

## Environment variables

See `backend/.env.example` and `frontend/.env.example`. **Never commit real keys** — `.env` files are gitignored.

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_API_KEY` | Yes | Gemini agents + embeddings |
| `SUPABASE_URL` | Yes | Project URL |
| `SUPABASE_ANON_KEY` | Yes | Client auth |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Server writes (bypass RLS) |
| `SUPABASE_JWT_SECRET` | Yes | Token validation |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash` |
| `EMBEDDING_MODEL` | No | Default `models/gemini-embedding-001` |

More detail: [SETUP_CLOUD.md](./SETUP_CLOUD.md).

---

## License

Prototype for educational use. Not an official product of any card network.
