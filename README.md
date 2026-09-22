# INSPECTRA — AI-Powered Legal Metrology Inspection System

> **SIH26034** — Software System to Check Compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011.

---

## Architecture

```
INSPECTRA/
├── docker-compose.yml       # PostgreSQL + pgAdmin
├── backend/                 # FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── main.py
│   │   ├── core/           # config, database, security
│   │   ├── models/         # SQLAlchemy models (8 entities)
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/            # REST API routers
│   │   ├── services/       # Business logic + storage abstraction
│   │   ├── agents/         # AI agent stubs (Phase 2)
│   │   └── rules/          # Rule engine stubs (Phase 2)
└── frontend/                # React + TypeScript + Tailwind + shadcn/ui
    └── src/
        ├── pages/          # Dashboard, Inspections, Products
        ├── components/     # Layout + UI components
        ├── lib/            # api.ts (axios), auth.ts
        └── types/          # TypeScript interfaces
```

---

## Prerequisites

| Tool | Version | Required for |
|------|---------|--------------|
| Docker Desktop | Latest | PostgreSQL (no local install needed) |
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |

---

## Quick Start

### 1. Start PostgreSQL (Docker)

```bash
# From the project root
docker-compose up -d
```

- PostgreSQL runs on `localhost:5432`
- pgAdmin UI available at `http://localhost:5050`
  - Email: `admin@inspectra.gov.in` / Password: `admin`
  - Add server: host=`postgres`, port=`5432`, db=`inspectra`, user=`inspectra`, pass=`inspectra_secret`

Data is persisted in the `postgres_data` Docker volume — survives container restarts.

---

### 2. Backend Setup

```bash
cd backend

# Copy environment file
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# Create a virtual environment
python -m venv .venv

# Activate
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Database tables are **created automatically** on first startup.

---

### 3. Frontend Setup

```bash
cd frontend

# Copy environment file
copy .env.example .env   # Windows

# Install dependencies (skip if already done)
npm install

# Start dev server
npm run dev
```

- Frontend: `http://localhost:5173`

---

## First Use

1. Open `http://localhost:5173`
2. Click **Register** → create an account (choose `ADMIN` or `SUPERVISOR` for full access)
3. Sign in
4. Navigate to **Products** → add a product
5. Go to **Inspections** → **New Inspection**
6. Select product → enter notes → upload package images
7. View the inspection detail — status, images, timeline
8. **Dashboard** shows live counts from the database

---

## Roles

| Role | Permissions |
|------|-------------|
| `INSPECTOR` | Create/view own inspections and products |
| `SUPERVISOR` | View all inspections and users |
| `ADMIN` | Full access |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | — | JWT signing secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token lifetime |
| `STORAGE_BACKEND` | `local` | `local` (disk) or `s3` (future) |
| `LOCAL_UPLOAD_DIR` | `uploads` | Directory for uploaded images |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (OAuth2 form) |
| GET | `/api/users/me` | Current user profile |
| GET/POST | `/api/products/` | List / create products |
| GET/POST | `/api/inspections/` | List / create inspections |
| GET | `/api/inspections/{id}` | Inspection detail |
| PATCH | `/api/inspections/{id}/status` | Update status |
| POST | `/api/inspections/{id}/images` | Upload image |
| GET | `/api/dashboard/stats` | Aggregated stats |
| GET | `/api/dashboard/recent-inspections` | Recent inspections |

Full interactive docs: `http://localhost:8000/docs`

---

## What's Implemented (Phase 1)

- [x] PostgreSQL via Docker with persistent volume
- [x] JWT authentication (register, login, protected routes)
- [x] Role-based access (INSPECTOR / SUPERVISOR / ADMIN)
- [x] Product CRUD
- [x] Inspection creation with unique number (`INS-2026-XXXXX`)
- [x] Multi-image upload with view type labels (FRONT/BACK/etc.)
- [x] Storage service abstraction (local → S3 swap via env var)
- [x] Dashboard with real DB statistics
- [x] Full frontend: Login, Dashboard, Inspections, Products

## What's NOT Implemented Yet (Phase 2+)

- [ ] AI Agents: Label Agent, Quantity Agent, Declaration Agent
- [ ] Rule Engines: Declaration Engine, Measurement Engine
- [ ] Compliance Checks (all stubs in DB schema, no data written)
- [ ] Human Review workflow
- [ ] PDF Report generation
- [ ] S3 storage backend

---

## Stopping

```bash
# Stop Docker services
docker-compose down

# Stop Docker and remove data volume (WARNING: deletes all data)
docker-compose down -v
```
