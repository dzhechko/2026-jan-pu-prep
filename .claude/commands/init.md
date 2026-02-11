# /init — Bootstrap НутриМайнд Project

Generate the complete project structure from SPARC documentation. This command creates all directories, configuration files, Docker setup, and initial code scaffolding.

## Prerequisites
- Docker and Docker Compose installed
- Node.js 20+ and Python 3.12+ available
- SPARC docs at `docs/sparc/` (Architecture.md, Pseudocode.md, Completion.md)

## Execution

### Phase 1: Foundation (Sequential)

1. Create root configuration files:
   - `.gitignore` (Python + Node.js + Docker + .env)
   - `.env.example` (from Completion.md environment variables)
   - `docker-compose.yml` (from Architecture.md infrastructure section)
   - `docker-compose.dev.yml` (from Completion.md dev environment)

2. Git commit: `chore(infra): initial project structure`

### Phase 2: Services (Parallel — use Task tool)

**Task 1: Backend scaffolding**
- Create `backend/` directory structure per Architecture.md
- `backend/requirements.txt` (FastAPI, SQLAlchemy, Pydantic, redis, rq, httpx, openai, python-telegram-bot, alembic, pytest, ruff)
- `backend/Dockerfile`
- `backend/app/main.py` (FastAPI app with lifespan, CORS, error handler)
- `backend/app/config.py` (pydantic-settings from env vars)
- `backend/app/dependencies.py` (DB session, get_current_user)
- `backend/app/middleware/telegram_auth.py` (initData HMAC validation)
- `backend/alembic.ini` + `backend/migrations/env.py`
- All SQLAlchemy models from Architecture.md data model
- Empty router/service/schema files for each feature

**Task 2: Frontend scaffolding**
- `npx create-vite frontend --template react-ts`
- Install: `@telegram-apps/sdk-react`, `zustand`, `react-router-dom`, `axios`, `tailwindcss`
- Create `frontend/src/` directory structure per Architecture.md
- `frontend/src/app/App.tsx` (TWA init + theme + router)
- `frontend/src/app/router.tsx` (hash router with all routes)
- `frontend/src/shared/api/client.ts` (axios with JWT interceptor)
- `frontend/src/shared/hooks/useTelegram.ts` (TWA SDK hook)
- Empty feature directories for each feature module

**Task 3: Bot scaffolding**
- Create `bot/` directory structure
- `bot/requirements.txt` (python-telegram-bot)
- `bot/Dockerfile`
- `bot/bot.py` (webhook handler + /start command with Mini App button)
- `bot/handlers/start.py`
- `bot/handlers/notifications.py`

**Task 4: Nginx scaffolding**
- `nginx/nginx.conf` from Architecture.md

### Phase 3: Integration (Sequential)

1. Build all Docker images: `docker compose build`
2. Start services: `docker compose -f docker-compose.dev.yml up -d`
3. Run initial migration: `docker compose exec api alembic upgrade head`
4. Verify health: `curl http://localhost:8000/api/health`
5. Run backend tests: `docker compose exec api pytest`
6. Run frontend build: `docker compose exec frontend npm run build`

### Phase 4: Finalize

1. Generate `README.md` with setup instructions
2. Git commit: `feat(infra): complete project scaffolding`
3. Git tag: `v0.0.1-scaffold`
4. Print summary of created files and next steps

## Expected Output

```
nutrimind/
├── frontend/          (12 files)
├── backend/           (25 files)
├── bot/               (5 files)
├── nginx/             (1 file)
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
~50 files total
```

## Flags
- `--skip-tests` — Skip Phase 3 test execution
- `--skip-docker` — Skip Docker build (just create files)
- `--dry-run` — Print plan without creating files

## Error Recovery
- If Docker build fails: check Dockerfiles, verify base images
- If migration fails: check DATABASE_URL, verify PostgreSQL is running
- If frontend build fails: check package.json, run `npm install`
- On any failure: fix the issue and re-run Phase 3 only
