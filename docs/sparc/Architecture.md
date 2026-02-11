# Architecture: НутриМайнд (Telegram Mini App)

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CLOUD                           │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │ Telegram  │    │  Bot API     │    │  Telegram Stars API   │  │
│  │ Client    │◄──►│  (webhooks)  │    │  (payments)           │  │
│  └────┬─────┘    └──────┬───────┘    └───────────┬───────────┘  │
│       │                 │                         │              │
│       │  TWA iframe     │  updates/commands       │  invoices    │
└───────┼─────────────────┼─────────────────────────┼─────────────┘
        │                 │                         │
        ▼                 ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         VPS (Docker Compose)                     │
│                                                                  │
│  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐  │
│  │   Nginx          │   │   Bot Service    │   │  Worker       │  │
│  │   (reverse proxy)│   │   (webhooks +    │   │  (AI jobs)    │  │
│  │   TLS termination│   │    commands)      │   │              │  │
│  │   static files   │   │                  │   │              │  │
│  └────────┬─────────┘   └────────┬─────────┘   └──────┬───────┘  │
│           │                      │                     │          │
│           ▼                      ▼                     ▼          │
│  ┌─────────────────┐   ┌─────────────────────────────────────┐  │
│  │  Frontend (SPA)  │   │           API Service (FastAPI)      │  │
│  │  React + TWA SDK │   │                                     │  │
│  │  Vite build      │   │  /api/auth    — initData validation │  │
│  │  served by Nginx │   │  /api/food    — food logging        │  │
│  │                  │   │  /api/insights — AI insights        │  │
│  └──────────────────┘   │  /api/patterns — pattern detection  │  │
│                         │  /api/lessons  — CBT lessons        │  │
│                         │  /api/payments — Telegram Stars     │  │
│                         │  /api/invite   — referral system    │  │
│                         └────────────┬────────────────────────┘  │
│                                      │                           │
│                    ┌─────────────────┼──────────────────┐        │
│                    ▼                 ▼                  ▼        │
│           ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│           │  PostgreSQL   │  │    Redis      │  │  OpenAI API  │  │
│           │  (primary DB) │  │  (cache +     │  │  (LLM calls) │  │
│           │               │  │   job queue)  │  │              │  │
│           └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Frontend — Telegram Mini App (TWA)

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── app/
│   │   ├── App.tsx                  # Root component + TWA init
│   │   ├── router.tsx               # React Router (hash-based)
│   │   └── providers.tsx            # Context providers
│   ├── shared/
│   │   ├── api/                     # API client (axios + interceptors)
│   │   ├── hooks/                   # useTelegram, useAuth, useTheme
│   │   ├── ui/                      # Design system components
│   │   └── lib/                     # Utilities
│   ├── features/
│   │   ├── onboarding/              # AI Interview screens
│   │   ├── food-log/                # Food logging (text input + parser)
│   │   ├── dashboard/               # Main screen (insights, risk, lessons)
│   │   ├── insights/                # AI insight cards
│   │   ├── lessons/                 # CBT mini-lessons
│   │   ├── paywall/                 # Subscription screen
│   │   ├── invite/                  # Referral system
│   │   └── profile/                 # User settings
│   └── entities/
│       ├── user/                    # User model + store
│       ├── food-entry/              # FoodEntry model
│       ├── pattern/                 # Pattern model
│       └── insight/                 # Insight model
├── package.json
├── vite.config.ts
└── Dockerfile
```

**Tech Stack:**
- React 18 + TypeScript
- `@telegram-apps/sdk-react` — TWA SDK integration
- Vite — build tool
- Zustand — state management (lightweight, no boilerplate)
- React Router v6 — hash-based routing (TWA requirement)
- Axios — HTTP client
- TailwindCSS — styling

**TWA Integration Points:**
```typescript
// App initialization
import { init, postEvent } from '@telegram-apps/sdk';

async function initApp() {
  const components = await init();
  // Expand to full height
  postEvent('web_app_expand');
  // Enable closing confirmation
  postEvent('web_app_setup_closing_behavior', { need_confirmation: true });
  // Get theme from Telegram
  const theme = components.themeParams;
  // Get initData for auth
  const initData = components.initData;
  // Send initData to backend for validation
  const { token } = await api.post('/api/auth/telegram', {
    init_data: components.initDataRaw
  });
}
```

### 2. Backend — API Service (FastAPI)

```
backend/
├── app/
│   ├── main.py                      # FastAPI app + lifespan
│   ├── config.py                    # Settings (pydantic-settings)
│   ├── dependencies.py              # DI (db session, current_user)
│   ├── middleware/
│   │   ├── telegram_auth.py         # initData HMAC validation
│   │   ├── rate_limit.py            # Rate limiting via Redis
│   │   └── error_handler.py         # Global error handler
│   ├── routers/
│   │   ├── auth.py                  # POST /api/auth/telegram
│   │   ├── onboarding.py            # POST /api/onboarding/interview
│   │   ├── food.py                  # POST /api/food/log, GET /api/food/history
│   │   ├── insights.py              # GET /api/insights/today
│   │   ├── patterns.py              # GET /api/patterns
│   │   ├── lessons.py               # GET /api/lessons/{id}
│   │   ├── payments.py              # Telegram Stars + ЮKassa
│   │   └── invite.py                # POST /api/invite/generate
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── food_entry.py
│   │   ├── pattern.py
│   │   ├── insight.py
│   │   ├── lesson.py
│   │   └── subscription.py
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── services/
│   │   ├── auth_service.py          # Telegram initData validation
│   │   ├── food_service.py          # Food parsing + logging
│   │   ├── pattern_service.py       # Pattern detection orchestration
│   │   ├── insight_service.py       # Insight generation
│   │   ├── risk_service.py          # Risk prediction
│   │   ├── lesson_service.py        # CBT lesson delivery
│   │   ├── payment_service.py       # Telegram Stars + ЮKassa
│   │   └── invite_service.py        # Referral management
│   ├── ai/
│   │   ├── llm_client.py            # OpenAI API wrapper
│   │   ├── prompts/                 # System prompts (CBT coach, food parser)
│   │   ├── pattern_detector.py      # Time-series pattern analysis
│   │   ├── risk_predictor.py        # Daily risk scoring
│   │   ├── food_parser.py           # Russian food NLP
│   │   └── insight_generator.py     # LLM-based insight creation
│   └── workers/
│       ├── pattern_worker.py        # Async pattern detection job
│       └── insight_worker.py        # Async insight generation job
├── migrations/                      # Alembic migrations
├── tests/
├── requirements.txt
└── Dockerfile
```

**Tech Stack:**
- Python 3.12 + FastAPI
- SQLAlchemy 2.0 (async) — ORM
- Alembic — migrations
- Pydantic v2 — validation
- Redis (via `redis-py`) — caching + job queue
- `rq` (Redis Queue) — background job processing
- `httpx` — async HTTP client (for OpenAI, Telegram APIs)
- `openai` — OpenAI Python SDK

### 3. Bot Service

```
bot/
├── bot.py                           # python-telegram-bot entry
├── handlers/
│   ├── start.py                     # /start → Mini App button
│   ├── notifications.py             # Push notifications sender
│   └── deep_links.py                # Invite deep links
├── Dockerfile
└── requirements.txt
```

**Tech Stack:**
- `python-telegram-bot` v20+ (async)
- Webhook mode (via Nginx)

**Bot → Mini App flow:**
```python
async def start(update, context):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="Открыть НутриМайнд",
            web_app=WebAppInfo(url="https://app.nutrimind.ru")
        )
    ]])
    await update.message.reply_text(
        "Привет! Я НутриМайнд — AI-детектив пищевых привычек.",
        reply_markup=keyboard
    )
```

### 4. Worker Service

Отдельный процесс для тяжёлых AI-задач:

| Job Type | Trigger | SLA | Queue |
|----------|---------|-----|-------|
| `pattern_detection` | Cron (daily 03:00) + on 10th food entry | < 30s | `ai_heavy` |
| `insight_generation` | Cron (daily 06:00) | < 10s | `ai_light` |
| `risk_calculation` | Cron (daily 07:00) | < 5s | `ai_light` |
| `food_parse_ai` | On food log (when DB miss) | < 3s | `ai_light` |

## Data Model (PostgreSQL)

```sql
-- Core tables
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id     BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name      VARCHAR(255) NOT NULL,
    language_code   VARCHAR(10) DEFAULT 'ru',
    subscription_status VARCHAR(20) DEFAULT 'free',  -- free|standard|premium
    subscription_expires_at TIMESTAMPTZ,
    insights_received INT DEFAULT 0,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    interview_answers JSONB DEFAULT '[]',
    cluster_id      VARCHAR(50),
    risk_model      JSONB DEFAULT '{}',
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE food_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    raw_text        TEXT NOT NULL,
    parsed_items    JSONB DEFAULT '[]',
    total_calories  INT,
    mood            VARCHAR(20),      -- great|ok|meh|bad|awful
    context         VARCHAR(20),      -- home|work|street|restaurant
    logged_at       TIMESTAMPTZ DEFAULT NOW(),
    day_of_week     SMALLINT,         -- 0=Monday
    hour            SMALLINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE patterns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(20) NOT NULL,  -- time|mood|context|sequence|skip
    description_ru  TEXT NOT NULL,
    confidence      FLOAT NOT NULL,
    evidence        JSONB DEFAULT '[]',
    active          BOOLEAN DEFAULT TRUE,
    discovered_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE insights (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    pattern_id      UUID REFERENCES patterns(id),
    title           VARCHAR(255) NOT NULL,
    body            TEXT NOT NULL,
    action          TEXT,
    type            VARCHAR(20) NOT NULL,  -- pattern|risk|progress|cbt
    seen            BOOLEAN DEFAULT FALSE,
    is_locked       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cbt_lessons (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_order    SMALLINT UNIQUE NOT NULL,  -- 1-20
    title           VARCHAR(255) NOT NULL,
    content_md      TEXT NOT NULL,
    pattern_tags    TEXT[] DEFAULT '{}',
    duration_min    SMALLINT DEFAULT 5
);

CREATE TABLE user_lesson_progress (
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    lesson_id       UUID REFERENCES cbt_lessons(id),
    completed_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    plan            VARCHAR(20) NOT NULL,   -- standard|premium
    provider        VARCHAR(20) NOT NULL,   -- telegram_stars|yukassa
    provider_id     VARCHAR(255),           -- external payment ID
    status          VARCHAR(20) NOT NULL,   -- active|cancelled|expired
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    cancelled_at    TIMESTAMPTZ
);

CREATE TABLE invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inviter_id      UUID REFERENCES users(id),
    invite_code     VARCHAR(20) UNIQUE NOT NULL,
    invitee_id      UUID REFERENCES users(id),
    redeemed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_food_entries_user_logged ON food_entries(user_id, logged_at DESC);
CREATE INDEX idx_patterns_user_active ON patterns(user_id) WHERE active = TRUE;
CREATE INDEX idx_insights_user_created ON insights(user_id, created_at DESC);
CREATE INDEX idx_subscriptions_user_status ON subscriptions(user_id, status);
```

## Authentication Flow (Telegram initData)

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Telegram  │     │ Frontend  │     │ Backend   │
│ Client    │     │ (TWA)     │     │ (FastAPI) │
└─────┬────┘     └─────┬────┘     └─────┬────┘
      │                │                │
      │  Open Mini App │                │
      │───────────────►│                │
      │  (initData in  │                │
      │   window)      │                │
      │                │                │
      │                │  POST /api/auth/telegram
      │                │  { init_data: raw_string }
      │                │───────────────►│
      │                │                │
      │                │                │── HMAC-SHA256 validate
      │                │                │   using BOT_TOKEN
      │                │                │
      │                │                │── Find/create user
      │                │                │   by telegram_id
      │                │                │
      │                │  { token: JWT, │
      │                │    user: {...} }│
      │                │◄───────────────│
      │                │                │
      │                │  All subsequent requests:
      │                │  Authorization: Bearer <JWT>
      │                │───────────────►│
```

**initData Validation (backend):**
```python
import hashlib, hmac, urllib.parse

def validate_init_data(init_data_raw: str, bot_token: str) -> dict:
    parsed = dict(urllib.parse.parse_qsl(init_data_raw))
    received_hash = parsed.pop("hash")

    # Sort and concatenate
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # HMAC with bot token
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise AuthError("Invalid initData signature")

    return parsed
```

## Payment Architecture

### Telegram Stars (Primary — in-app)

```
User taps "Subscribe" in Mini App
  → Frontend calls Telegram SDK: showPopup() with invoice
  → Telegram processes payment (Stars)
  → Bot receives pre_checkout_query → answer OK
  → Bot receives successful_payment
  → Bot notifies Backend API → activate subscription
  → Frontend polls /api/auth/me → sees active subscription
```

### ЮKassa (Fallback — external)

```
User taps "Оплатить картой"
  → Frontend opens ЮKassa payment page (openLink)
  → User completes payment
  → ЮKassa webhook → POST /api/payments/yukassa/webhook
  → Backend validates + activates subscription
  → Frontend polls /api/auth/me → sees active subscription
```

## AI Pipeline Architecture

```
Food Log Input
      │
      ▼
┌─────────────────┐     ┌──────────────────┐
│ Food Parser      │────►│ Russian Food DB   │
│ (NLP + DB lookup)│     │ (PostgreSQL)      │
│                  │────►│ OpenAI API        │ (fallback)
└────────┬────────┘     └──────────────────┘
         │
         │ parsed FoodEntry saved
         ▼
┌─────────────────┐     Runs daily (cron) or
│ Pattern Detector │     after 10th entry
│ (time-series    │
│  analysis)      │
└────────┬────────┘
         │
         │ Pattern[] saved
         ├──────────────────────┐
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ Risk Predictor   │    │ Insight Generator│
│ (daily score)    │    │ (LLM-based)     │
│                  │    │                  │
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
   RiskScore saved        Insight saved
   Push notification      Dashboard card
   if risk > 0.6
```

## Infrastructure (Docker Compose)

```yaml
# docker-compose.yml (production)
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/var/www/app       # built SPA
      - ./certbot/conf:/etc/letsencrypt    # TLS certs
    depends_on:
      - api
      - bot

  api:
    build: ./backend
    env_file: .env
    expose:
      - "8000"
    depends_on:
      - postgres
      - redis

  bot:
    build: ./bot
    env_file: .env
    depends_on:
      - api
      - redis

  worker:
    build: ./backend
    command: rq worker ai_heavy ai_light --url redis://redis:6379
    env_file: .env
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: nutrimind
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

**Nginx config (ключевые маршруты):**
```
server {
    listen 443 ssl;
    server_name app.nutrimind.ru;

    # TLS (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/app.nutrimind.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.nutrimind.ru/privkey.pem;

    # Frontend SPA
    location / {
        root /var/www/app;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Bot webhook
    location /bot/webhook {
        proxy_pass http://bot:8080;
    }
}
```

## Security Architecture

| Layer | Measure | Implementation |
|-------|---------|----------------|
| Transport | TLS 1.3 | Nginx + Let's Encrypt |
| Auth | Telegram initData HMAC | Every API request validated |
| Tokens | JWT (HS256) | 15 min access + 7 day refresh |
| Data at rest | AES-256 | PostgreSQL TDE (pgcrypto for PII columns) |
| Secrets | Environment variables | Docker secrets / .env (never in code) |
| Rate limiting | Per-user + per-IP | Redis sliding window (100 req/min) |
| Input validation | Pydantic schemas | All endpoints validated |
| CORS | Whitelist | Only `https://app.nutrimind.ru` + Telegram origins |
| Logs | No PII | Structured JSON logs, telegram_id masked |
| 152-ФЗ | RU data residency | VPS in Moscow (AdminVPS/HOSTKEY) |

## Architecture Decision Records

### ADR-1: Telegram Mini App vs Native App

**Decision:** Telegram Mini App (TWA)
**Context:** Need to reach Russian users quickly with minimal friction
**Rationale:**
- Zero-friction auth (user already logged in to Telegram)
- No App Store/Google Play approval needed
- Telegram has 90M+ MAU in Russia
- Built-in payment (Telegram Stars) + distribution (bot sharing)
- Cross-platform by default (iOS, Android, Desktop)
**Trade-offs:** Limited access to device APIs (no background tasks, limited notifications)

### ADR-2: FastAPI (Python) vs Node.js Backend

**Decision:** FastAPI (Python)
**Context:** Backend needs to handle AI/ML workloads + standard CRUD
**Rationale:**
- Python ecosystem for AI/ML (numpy, pandas, scikit-learn)
- FastAPI async performance comparable to Node.js
- OpenAI SDK native Python support
- Pydantic for request validation
- Easier to hire ML-capable Python devs
**Trade-offs:** Slightly higher memory usage vs Node.js

### ADR-3: Redis Queue vs Celery for Background Jobs

**Decision:** RQ (Redis Queue)
**Context:** Need async processing for AI tasks
**Rationale:**
- Simple setup (just Redis, no broker config)
- Good enough for 10K concurrent users
- Easy monitoring (rq-dashboard)
- Celery is overkill for MVP
**Trade-offs:** Less feature-rich than Celery (no task chains, rate limiting built-in)

### ADR-4: Zustand vs Redux for Frontend State

**Decision:** Zustand
**Context:** TWA app state management
**Rationale:**
- Minimal boilerplate (vs Redux Toolkit)
- Built-in TypeScript support
- Small bundle size (1.1KB vs 7KB+ Redux)
- Sufficient for MVP scope (no complex state flows)
**Trade-offs:** Less ecosystem/middleware than Redux

### ADR-5: Monorepo Structure

**Decision:** Monorepo with separate Docker services
**Context:** Small team (1-3 devs), shared types, single deployment target
**Rationale:**
- Shared configuration (ESLint, TypeScript)
- Atomic commits across frontend + backend
- Single CI/CD pipeline
- Docker Compose orchestration
**Trade-offs:** Build complexity grows with team size
