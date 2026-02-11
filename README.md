# НутриМайнд — AI-powered Weight Management Telegram Mini App

AI-powered weight management platform built as a Telegram Mini App, combining cognitive behavioral therapy (CBT) with intelligent food tracking and personalized insights.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS |
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| Database | PostgreSQL 16 + Redis 7 |
| Bot | python-telegram-bot 21 |
| AI | OpenAI GPT-4o-mini via RQ workers |
| Infra | Docker Compose, Nginx |

## Project Structure

```
├── backend/          # FastAPI API + Alembic migrations + RQ workers
├── frontend/         # React Telegram Mini App (Feature Sliced Design)
├── bot/              # Telegram bot (webhook + polling modes)
├── nginx/            # Reverse proxy config
├── docs/sparc/       # SPARC PRD documentation
└── docker-compose*.yml
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your real values:
#   TELEGRAM_BOT_TOKEN=<your-token>
#   OPENAI_API_KEY=<your-key>
#   SECRET_KEY=<random-64-chars>
#   DB_PASSWORD=<random-32-chars>
```

### 2. Start dev environment

```bash
docker compose -f docker-compose.dev.yml up -d
```

This starts:
- **API** at http://localhost:8000 (with hot reload)
- **PostgreSQL** at localhost:5432
- **Redis** at localhost:6379
- **RQ Worker** listening on `ai_heavy`, `ai_light` queues
- **Bot** in polling mode

### 3. Run database migration

```bash
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
```

### 4. Verify

```bash
curl http://localhost:8000/api/health
# {"status":"ok","version":"0.1.0"}
```

### 5. Frontend development

```bash
cd frontend && npm install && npm run dev
```

### 6. Run tests

```bash
# Backend
docker compose -f docker-compose.dev.yml exec api pytest -v

# Frontend
cd frontend && npm test
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/telegram` | Authenticate via Telegram initData |
| POST | `/api/onboarding/interview` | Submit onboarding answers |
| POST | `/api/food/log` | Log a food entry |
| GET | `/api/food/history` | Get food history |
| GET | `/api/insights/today` | Get today's insights |
| GET | `/api/patterns` | Get detected patterns |
| GET | `/api/lessons/{id}` | Get CBT lesson |
| POST | `/api/lessons/{id}/complete` | Mark lesson complete |
| POST | `/api/payments/subscribe` | Create subscription |
| DELETE | `/api/payments/subscription` | Cancel subscription |
| POST | `/api/invite/generate` | Generate invite code |
| POST | `/api/invite/redeem` | Redeem invite code |
| GET | `/api/health` | Health check |
| GET | `/api/health/ready` | Readiness check (DB + Redis) |

## Documentation

Full SPARC PRD documentation is in `docs/sparc/`:

- **Specification.md** — User stories, epics, acceptance criteria
- **Pseudocode.md** — Algorithms, data flows, state machines
- **Architecture.md** — System design, ADRs, data model
- **Refinement.md** — Edge cases, testing, performance
- **Completion.md** — Deployment, CI/CD, monitoring
