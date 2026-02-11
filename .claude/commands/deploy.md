# /deploy — Deploy to Production

Build, test, and deploy НутриМайнд to VPS.

## Usage
- `/deploy` — Full deploy (test → build → push → deploy)
- `/deploy --skip-tests` — Deploy without running tests
- `/deploy --dry-run` — Show what would be deployed without executing

## Pre-Deploy Checks
1. All tests pass: `pytest` + `npm run test`
2. Linters clean: `ruff check` + `npm run lint`
3. No uncommitted changes: `git status` is clean
4. On main branch (or approved feature branch)
5. Docker images build successfully

## Deploy Steps

### 1. Build
```bash
docker compose build
```

### 2. Test (unless --skip-tests)
```bash
docker compose exec api pytest -v
docker compose exec frontend npm run test
```

### 3. Push
```bash
git push origin main
```

### 4. Deploy to VPS
```bash
ssh deploy@<VPS_HOST> "cd /opt/nutrimind && git pull origin main && docker compose up -d --build"
```

### 5. Run Migrations
```bash
ssh deploy@<VPS_HOST> "cd /opt/nutrimind && docker compose exec -T api alembic upgrade head"
```

### 6. Health Check
```bash
curl -sf https://app.nutrimind.ru/api/health
# Expected: {"status": "ok", "version": "X.Y.Z"}
```

### 7. Smoke Test
- Open Mini App via Telegram bot
- Verify auth flow works
- Verify dashboard loads

## Rollback
If deploy fails or health check doesn't pass:
```bash
ssh deploy@<VPS_HOST> "cd /opt/nutrimind && git checkout <previous-tag> && docker compose up -d --build"
```

## Post-Deploy
- Check Sentry for new errors
- Monitor UptimeRobot for availability
- Check RQ Dashboard for worker health
- Verify logs: `docker compose logs -f api --since 5m`
