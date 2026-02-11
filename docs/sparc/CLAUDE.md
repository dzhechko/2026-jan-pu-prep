# CLAUDE.md — НутриМайнд

## Project Overview

НутриМайнд — Telegram Mini App (TWA) for AI-driven weight management using CBT pattern detection. Russian language only.

## Documentation Reading Order

1. `docs/sparc/Final_Summary.md` — Project overview and architecture summary
2. `docs/sparc/PRD.md` — Product requirements, features F1-F10, constraints
3. `docs/sparc/Architecture.md` — System diagram, components, data model, ADRs
4. `docs/sparc/Specification.md` — User stories with acceptance criteria (6 epics)
5. `docs/sparc/Pseudocode.md` — Algorithms, API contracts, data structures
6. `docs/sparc/Refinement.md` — Edge cases, test strategy, performance targets
7. `docs/sparc/Completion.md` — Deployment, CI/CD, monitoring, checklists

## Tech Stack

- **Frontend:** React 18 + TypeScript + `@telegram-apps/sdk-react` + Vite + TailwindCSS + Zustand
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Alembic
- **Bot:** python-telegram-bot v20+ (webhook mode)
- **Database:** PostgreSQL 16 + Redis 7
- **AI:** OpenAI API (GPT-4o-mini) + custom pattern detection
- **Worker:** RQ (Redis Queue) for async AI jobs
- **Infra:** Docker Compose + Nginx + Let's Encrypt

## Project Structure

```
nutrimind/
├── frontend/          # React TWA app (Vite)
├── backend/           # FastAPI API service
│   ├── app/
│   │   ├── routers/   # API endpoints
│   │   ├── models/    # SQLAlchemy ORM
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   ├── ai/        # AI pipeline (pattern detector, food parser, etc.)
│   │   └── workers/   # RQ background jobs
│   ├── migrations/    # Alembic
│   └── tests/
├── bot/               # Telegram Bot service
├── nginx/             # Reverse proxy config
├── docker-compose.yml
└── CLAUDE.md
```

## Implementation Rules

### Must Follow
- **Auth:** Telegram initData HMAC validation on EVERY API request. Never trust client-side data.
- **No PII in logs:** Hash telegram_id, never log food text or names.
- **Russian language:** All user-facing text in Russian. Variable names and code in English.
- **Type safety:** Full TypeScript (frontend), Pydantic schemas (backend) — no `Any` types.
- **Async:** All DB operations via SQLAlchemy async. All HTTP calls via httpx async.

### Should Follow
- **Feature Sliced Design:** Frontend organized by `app/ → features/ → entities/ → shared/`.
- **Service layer pattern:** Routers call services, services call models. No direct DB access in routers.
- **AI calls are async:** All OpenAI API calls go through RQ worker, never in request path (except food parser with < 3s timeout).

### Must Avoid
- **No hardcoded secrets.** All via environment variables.
- **No `SELECT *`.** Always specify columns.
- **No floating point for money.** Use integer kopecks (cents) for all currency.
- **No client-side subscription checks.** Always verify on backend.
- **No direct OpenAI calls from frontend.** Always proxy through backend.

## API Conventions

```
Base URL: /api/v1/
Auth header: Authorization: Bearer <JWT>
Request body: JSON (camelCase)
Response body: JSON (camelCase)
Errors: { "error": { "code": "ERROR_CODE", "message": "Human readable" } }
Pagination: ?limit=20&offset=0
Timestamps: ISO 8601 (UTC)
```

## Database Conventions

- Table names: `snake_case`, plural (`users`, `food_entries`)
- Column names: `snake_case`
- Primary keys: `id UUID DEFAULT gen_random_uuid()`
- Timestamps: `TIMESTAMPTZ` (always with timezone)
- Soft delete: NOT used (hard delete with CASCADE for 152-ФЗ compliance)
- Migrations: One migration per feature, descriptive name

## Testing Approach

- **Backend:** pytest + pytest-asyncio + testcontainers (PostgreSQL, Redis)
- **Frontend:** vitest + React Testing Library
- **E2E:** Playwright (5 critical paths only)
- **AI quality:** Labeled test sets (200 food descriptions, 50 synthetic profiles)
- **Coverage target:** 80%+ backend, 70%+ frontend

```bash
# Run backend tests
cd backend && pytest --cov=app

# Run frontend tests
cd frontend && npm run test

# Run E2E
cd frontend && npx playwright test
```

## Common Tasks

### Add new API endpoint
1. Create Pydantic schema in `backend/app/schemas/`
2. Create service method in `backend/app/services/`
3. Create router in `backend/app/routers/`
4. Register router in `backend/app/main.py`
5. Add tests in `backend/tests/`

### Add new frontend feature
1. Create feature directory in `frontend/src/features/<name>/`
2. Add route in `frontend/src/app/router.tsx`
3. Create API client method in `frontend/src/shared/api/`
4. Add tests

### Run database migration
```bash
# Create migration
docker compose exec api alembic revision --autogenerate -m "description"
# Apply
docker compose exec api alembic upgrade head
# Rollback
docker compose exec api alembic downgrade -1
```

### Deploy
```bash
git push origin main  # triggers GitHub Actions CI/CD
# Or manual:
ssh deploy@<vps> "cd /opt/nutrimind && git pull && docker compose up -d --build"
```

## Priority Order (MVP)

Implement features in this order:

1. **Infrastructure:** Docker Compose, PostgreSQL, Redis, Nginx, project scaffolding
2. **Auth (F10):** Telegram initData → JWT flow
3. **Food Logging (F2):** Text input → Russian food parser → save
4. **Onboarding (F1):** AI interview (2 questions) → cluster assignment
5. **Pattern Detector (F3):** Time-series analysis → pattern discovery
6. **Insights (F4):** Daily AI insight generation → dashboard card
7. **Risk Predictor (F5):** Daily risk score → push notification
8. **CBT Lessons (F6):** 20 lessons, progress tracking
9. **Paywall (F7):** After 3 insights → Telegram Stars + ЮKassa
10. **Invite (F8):** Referral links, premium reward
11. **Notifications (F9):** Bot push for risk alerts + reminders
