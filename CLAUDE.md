# CLAUDE.md — НутриМайнд

## What is this project?

НутриМайнд — Telegram Mini App (TWA) for AI-driven weight management using CBT (Cognitive Behavioral Therapy) pattern detection. Russian-language only. Targets 50M+ Russians with excess weight. Freemium model: 499 RUB/month.

## Documentation

Read SPARC docs in this order for full context:

1. `docs/sparc/Final_Summary.md` — Architecture overview, key decisions
2. `docs/sparc/PRD.md` — Features F1-F10, constraints, metrics
3. `docs/sparc/Architecture.md` — System diagram, components, data model, ADRs
4. `docs/sparc/Specification.md` — User stories (7 epics, 13 stories) with Gherkin AC
5. `docs/sparc/Pseudocode.md` — 4 algorithms, 10 API endpoints, data structures
6. `docs/sparc/Refinement.md` — 25 edge cases, test strategy, performance targets
7. `docs/sparc/Completion.md` — Deployment, CI/CD, monitoring, launch checklist
8. `docs/sparc/Validation_Report.md` — INVEST/SMART scoring for all user stories
9. `docs/sparc/BDD_Scenarios.feature` — 45+ BDD scenarios for all epics

## Tech Stack

- **Frontend:** React 18 + TypeScript + `@telegram-apps/sdk-react` + Vite + TailwindCSS + Zustand
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Alembic
- **Bot:** python-telegram-bot v20+ (webhook mode)
- **Database:** PostgreSQL 16 + Redis 7
- **AI:** OpenAI API (GPT-4o-mini) + custom pattern detection algorithms
- **Worker:** RQ (Redis Queue) for async AI jobs
- **Infra:** Docker Compose + Nginx + Let's Encrypt on VPS (Moscow DC)

## Project Structure

```
nutrimind/
├── frontend/              # React TWA (Vite)
│   └── src/
│       ├── app/           # App shell, router, providers
│       ├── features/      # Feature modules (onboarding, food-log, dashboard, etc.)
│       ├── entities/      # Domain models (user, food-entry, pattern, insight)
│       └── shared/        # API client, hooks, UI components, utils
├── backend/               # FastAPI
│   └── app/
│       ├── routers/       # API endpoints
│       ├── models/        # SQLAlchemy ORM
│       ├── schemas/       # Pydantic request/response
│       ├── services/      # Business logic
│       ├── ai/            # Pattern detector, food parser, insight generator, risk predictor
│       └── workers/       # RQ background jobs
├── bot/                   # Telegram Bot (python-telegram-bot)
├── nginx/                 # Reverse proxy config
├── migrations/            # Alembic
├── docker-compose.yml     # Production
├── docker-compose.dev.yml # Development
└── docs/sparc/            # SPARC documentation
```

## Mandatory Rules

### Authentication
- **Telegram initData HMAC-SHA256 validation on EVERY API request.** Never trust client-side data.
- JWT tokens: 15 min access + 7 day refresh. Always validate on backend.

### Security
- No PII in logs. Hash telegram_id, never log food text or user names.
- No hardcoded secrets. All via environment variables / Docker secrets.
- No client-side subscription checks. Always verify on backend.
- No direct OpenAI calls from frontend. Always proxy through backend API.
- Input validation: Pydantic schemas on all endpoints. Max 500 chars for food text.
- 152-ФЗ compliance: all data on Russian servers, support data export + deletion.

### Code Quality
- Russian language for all user-facing text. English for code, variables, comments.
- Full TypeScript (frontend) — no `any` types. Pydantic v2 (backend) — no untyped dicts.
- Async everywhere: SQLAlchemy async sessions, httpx async for external APIs.
- Service layer pattern: routers → services → models. No direct DB access in routers.
- No `SELECT *`. Always specify columns.
- No floating point for money. Use integer kopecks.

### Frontend
- Feature Sliced Design: `app/ → features/ → entities/ → shared/`
- Hash-based routing (TWA requirement): `createHashRouter()`
- Zustand for state. No Redux.
- Bundle budget: < 150KB gzipped.

### Backend
- All AI/LLM calls through RQ worker (async), never in request handler path.
- Exception: food parser has 3s timeout in request path, fallback to async on timeout.
- API conventions: `/api/v1/`, JSON camelCase, ISO 8601 UTC timestamps.
- Error format: `{ "error": { "code": "ERROR_CODE", "message": "..." } }`

### Database
- Table names: snake_case, plural. Column names: snake_case.
- Primary keys: `UUID DEFAULT gen_random_uuid()`
- All timestamps: `TIMESTAMPTZ` (with timezone, UTC)
- Hard delete with CASCADE (not soft delete) for 152-ФЗ compliance.
- One Alembic migration per feature.

### Testing
- Backend: pytest + pytest-asyncio + testcontainers. Target: 80%+ coverage.
- Frontend: vitest + React Testing Library. Target: 70%+ coverage.
- E2E: Playwright, 5 critical paths only.
- AI quality: labeled test sets (200 food descriptions, 50 synthetic user profiles).

## Implementation Priority

Build features in this order:

1. **Infrastructure** — Docker Compose, PostgreSQL, Redis, Nginx, project scaffold
2. **Auth (F10)** — Telegram initData → JWT
3. **Food Logging (F2)** — Text input → Russian food parser → save
4. **Onboarding (F1)** — AI interview (2 questions) → cluster assignment
5. **Pattern Detector (F3)** — Time-series analysis → pattern discovery
6. **Insights (F4)** — Daily AI insight generation
7. **Risk Predictor (F5)** — Daily risk score → push notification
8. **CBT Lessons (F6)** — 20 lessons, progress tracking
9. **Paywall (F7)** — Telegram Stars + ЮKassa
10. **Invite (F8)** — Referral links, premium reward
11. **Notifications (F9)** — Bot push for risk alerts
12. **Data Privacy (F10)** — Export + deletion for 152-ФЗ

## Key Commands

- `/init` — Bootstrap entire project from SPARC docs
- `/feature <name>` — Start structured feature development lifecycle
- `/test` — Generate and run tests for current changes
- `/deploy` — Build, test, and deploy to VPS
- `/myinsights` — View captured development insights

## Performance Targets

| Endpoint | Target |
|----------|--------|
| Auth (initData) | < 100ms |
| Food log | < 300ms (DB), < 3s (AI) |
| Insights (cached) | < 100ms |
| Patterns | < 200ms |
| Lessons | < 50ms |
| AI generation | < 5s (worker) |
