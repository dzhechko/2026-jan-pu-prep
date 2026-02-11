# Completion: НутриМайнд

## Project Structure (Monorepo)

```
nutrimind/
├── frontend/                    # React TWA app
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── backend/                     # FastAPI API
│   ├── app/
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
├── bot/                         # Telegram Bot
│   ├── bot.py
│   ├── handlers/
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/                       # Reverse proxy config
│   └── nginx.conf
├── docs/                        # SPARC documentation
│   └── sparc/
├── scripts/                     # Deployment & utility scripts
│   ├── deploy.sh
│   ├── backup.sh
│   └── seed_lessons.py
├── docker-compose.yml           # Production
├── docker-compose.dev.yml       # Development (hot reload)
├── .env.example
├── .gitignore
├── CLAUDE.md                    # AI development guide
└── README.md
```

## Deployment Procedure

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| VPS (Moscow DC) | 4 vCPU, 8GB RAM, 80GB SSD | Production server |
| Docker | 24+ | Container runtime |
| Docker Compose | v2+ | Orchestration |
| Domain | app.nutrimind.ru | HTTPS endpoint |
| Telegram Bot Token | via @BotFather | Bot + Mini App |
| OpenAI API Key | GPT-4o-mini | AI features |
| ЮKassa Shop ID + Key | (optional) | Card payments |

### Environment Variables (.env)

```bash
# App
APP_ENV=production
APP_VERSION=0.1.0
SECRET_KEY=<random-64-chars>

# Telegram
TELEGRAM_BOT_TOKEN=<from-botfather>
TELEGRAM_MINI_APP_URL=https://app.nutrimind.ru

# Database
DB_USER=nutrimind
DB_PASSWORD=<random-32-chars>
DB_NAME=nutrimind
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=<key>
OPENAI_MODEL=gpt-4o-mini

# ЮKassa (optional)
YUKASSA_SHOP_ID=<id>
YUKASSA_SECRET_KEY=<key>

# Monitoring
SENTRY_DSN=<dsn>
```

### Step-by-Step Deployment

```bash
# 1. Server setup
ssh root@<vps-ip>
apt update && apt install -y docker.io docker-compose-v2
usermod -aG docker deploy

# 2. Clone repository
git clone <repo-url> /opt/nutrimind
cd /opt/nutrimind

# 3. Configure environment
cp .env.example .env
nano .env  # fill in all secrets

# 4. SSL certificate (first time)
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d app.nutrimind.ru

# 5. Build and start
docker compose build
docker compose up -d

# 6. Run database migrations
docker compose exec api alembic upgrade head

# 7. Seed CBT lessons
docker compose exec api python scripts/seed_lessons.py

# 8. Register Telegram webhook
docker compose exec bot python -c "
import asyncio
from telegram import Bot
bot = Bot(token='<BOT_TOKEN>')
asyncio.run(bot.set_webhook('https://app.nutrimind.ru/bot/webhook'))
"

# 9. Configure Mini App in @BotFather
# /newapp → select bot → set URL: https://app.nutrimind.ru

# 10. Verify
curl https://app.nutrimind.ru/api/health
# Expected: {"status": "ok", "version": "0.1.0"}
```

### Rollback Procedure

```bash
# Quick rollback to previous version
docker compose down
git checkout <previous-tag>
docker compose build && docker compose up -d
docker compose exec api alembic downgrade -1
```

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_nutrimind
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: [5432:5432]
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
    steps:
      - uses: actions/checkout@v4

      - name: Backend tests
        working-directory: backend
        run: |
          pip install -r requirements.txt
          pytest --cov=app --cov-report=xml

      - name: Frontend tests
        working-directory: frontend
        run: |
          npm ci
          npm run test -- --coverage
          npm run build

      - name: Lint
        run: |
          cd backend && ruff check app/
          cd ../frontend && npm run lint

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: deploy
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/nutrimind
            git pull origin main
            docker compose build
            docker compose up -d
            docker compose exec -T api alembic upgrade head
            curl -sf https://app.nutrimind.ru/api/health
```

## Development Environment

### docker-compose.dev.yml

```yaml
services:
  api:
    build: ./backend
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    volumes:
      - ./backend/app:/code/app    # hot reload
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    command: npm run dev -- --host 0.0.0.0
    volumes:
      - ./frontend/src:/app/src    # hot reload
    ports:
      - "5173:5173"

  bot:
    build: ./bot
    command: python bot.py --polling  # polling mode for dev
    volumes:
      - ./bot:/code

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: nutrimind_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Local TWA Testing

```bash
# Option 1: Telegram Test Environment
# Use test bot token from @BotFather (test mode)
# Open: https://t.me/<test_bot>?startapp

# Option 2: Browser with mock
# frontend/.env.development
VITE_MOCK_TELEGRAM=true
# This enables mock initData for local development
```

## Monitoring Setup

### Prometheus + Grafana (Optional for MVP)

```yaml
# Add to docker-compose.yml for monitoring
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
```

### MVP Monitoring (Minimal)

| Tool | Purpose | Setup |
|------|---------|-------|
| Sentry | Error tracking (backend + frontend) | `pip install sentry-sdk[fastapi]` |
| UptimeRobot | Uptime monitoring (free) | Monitor `/api/health` every 5 min |
| Docker logs | Application logs | `docker compose logs -f api` |
| pg_stat | Database metrics | Built into PostgreSQL |
| RQ Dashboard | Worker job monitoring | `pip install rq-dashboard` |

### Logging Format

```python
# Structured JSON logging
import structlog

logger = structlog.get_logger()

# Example log entry (no PII)
logger.info(
    "food_logged",
    user_hash=hash_telegram_id(user.telegram_id),
    items_count=len(parsed_items),
    total_calories=total_calories,
    parse_method="db"  # or "ai"
)
```

## Database Backup Strategy

```bash
# scripts/backup.sh — runs via cron daily at 02:00
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups/nutrimind

docker compose exec -T postgres pg_dump \
  -U ${DB_USER} ${DB_NAME} \
  | gzip > ${BACKUP_DIR}/nutrimind_${TIMESTAMP}.sql.gz

# Keep last 30 daily backups
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete

# Optional: upload to S3-compatible storage
# aws s3 cp ${BACKUP_DIR}/nutrimind_${TIMESTAMP}.sql.gz s3://nutrimind-backups/
```

## Launch Checklist

### Pre-Launch (Before Beta)

- [ ] All P0 features implemented and tested
- [ ] Telegram Bot registered and configured
- [ ] Mini App URL set in @BotFather
- [ ] SSL certificate active (Let's Encrypt)
- [ ] Database migrations applied
- [ ] 20 CBT lessons seeded
- [ ] Russian food database seeded (500+ items)
- [ ] OpenAI API key with billing configured
- [ ] Sentry configured for error tracking
- [ ] UptimeRobot monitoring `/api/health`
- [ ] Backup cron job active
- [ ] `.env` secrets rotated from development
- [ ] Rate limiting enabled
- [ ] CORS whitelist configured
- [ ] initData validation tested with real Telegram
- [ ] Load test: 100 concurrent users

### Beta Launch (500 users)

- [ ] Invite-only access via bot deep links
- [ ] Feedback collection mechanism (in-app or Telegram chat)
- [ ] Daily monitoring of error rates and AI quality
- [ ] A/B test paywall timing (insight 3 vs 5)
- [ ] Cold-start cluster quality review

### Public Launch

- [ ] Telegram Ads campaign configured
- [ ] Landing page / Telegram channel for organic traffic
- [ ] ЮKassa payments tested end-to-end
- [ ] Telegram Stars payments tested end-to-end
- [ ] Privacy policy page (`/privacy`)
- [ ] Terms of service page (`/terms`)
- [ ] 152-ФЗ compliance verified
- [ ] Support channel in Telegram
- [ ] Scalability test: 1000 concurrent users
