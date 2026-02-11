# Refinement: НутриМайнд

## Edge Cases & Error Handling

### Authentication Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E1 | User opens Mini App outside Telegram (direct URL) | Show "Откройте через Telegram" message + link to bot |
| E2 | initData expired (> 5 min old) | Return 401 → frontend re-requests via TWA SDK |
| E3 | User deleted Telegram account | JWT becomes invalid on next refresh → clean session |
| E4 | Bot blocked by user | Cannot send push notifications → degrade gracefully |
| E5 | Multiple devices same account | JWT works on all → last active device gets pushes |

### Food Logging Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E6 | Empty text input | Validation error: "Введите что вы съели" |
| E7 | Non-food text ("привет", "123") | AI parser returns low confidence → ask: "Уточните что вы съели" |
| E8 | Very long text (> 500 chars) | Truncate to 500 chars, parse first items |
| E9 | Mixed languages ("борщ и pizza") | Parse each item separately, support transliteration |
| E10 | Duplicate entry (same food < 1 min) | Warn: "Вы уже записали это. Добавить ещё раз?" |
| E11 | Future timestamp | Reject: logged_at cannot be > now + 1 hour |
| E12 | No internet during logging | Queue locally → sync when connection restored |
| E13 | AI food parser timeout (> 5s) | Save raw_text, parse async, notify when ready |

### AI Pipeline Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E14 | User has < 3 days of data | Use cold-start cluster patterns with disclaimer |
| E15 | User logs only 1 meal/day | Insufficient data warning, encourage more logging |
| E16 | All meals same calories/mood | No patterns detected → show general CBT tips |
| E17 | OpenAI API down | Serve cached insights, queue generation for retry |
| E18 | Pattern confidence drops below 0.3 | Mark pattern as inactive, stop showing in insights |
| E19 | User disputes a pattern ("это неправда") | Flag pattern, lower confidence by 0.2, log feedback |
| E20 | 100+ food entries, patterns not found | Expand analysis window to 60 days, try cross-correlations |

### Payment Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E21 | Telegram Stars payment fails | Show error + offer ЮKassa fallback |
| E22 | Subscription expires mid-session | Graceful degradation: finish current action, show paywall on next |
| E23 | Double payment (Stars + ЮKassa) | Detect duplicate → refund second, extend subscription |
| E24 | ЮKassa webhook delayed (> 1 hour) | Poll ЮKassa API every 5 min for pending payments |
| E25 | User requests refund | Cancel subscription immediately, refund via original method |

## Testing Strategy

### Test Pyramid

```
          ┌─────────┐
          │  E2E (5) │  Playwright (critical paths only)
         ─┴─────────┴─
        ┌─────────────┐
        │Integration(20)│  pytest + testcontainers
       ─┴─────────────┴─
      ┌───────────────────┐
      │   Unit Tests (100+) │  pytest (backend) + vitest (frontend)
     ─┴───────────────────┴─
```

### Unit Tests (Target: 80%+ coverage)

**Backend (pytest):**

| Module | Tests | Key Scenarios |
|--------|:-----:|---------------|
| `auth_service` | 8 | initData validation (valid, expired, tampered, missing fields) |
| `food_parser` | 15 | Russian food parsing (борщ, пельмени, сложные блюда, edge cases) |
| `pattern_detector` | 12 | Time patterns, mood patterns, skip patterns, insufficient data |
| `risk_predictor` | 8 | Low/medium/high risk, all contributing factors |
| `insight_generator` | 6 | Rotation logic, paywall trigger, LLM prompt construction |
| `payment_service` | 10 | Stars flow, ЮKassa flow, expiration, cancellation |
| Pydantic schemas | 15 | All request/response validation |

**Frontend (vitest + React Testing Library):**

| Component | Tests | Key Scenarios |
|-----------|:-----:|---------------|
| `FoodLogForm` | 8 | Input, submit, validation, loading state |
| `InsightCard` | 5 | Normal, locked (paywall), loading, error |
| `RiskBadge` | 3 | Low/medium/high display |
| `LessonViewer` | 5 | Content rendering, progress, completion |
| `PaywallScreen` | 4 | Pricing display, CTA, dismiss |
| Zustand stores | 10 | State mutations, persistence |

### Integration Tests (pytest + testcontainers)

| Test Suite | Scope |
|-----------|-------|
| `test_auth_flow` | Telegram initData → JWT → protected endpoint |
| `test_food_logging_flow` | Log food → parse → save → retrieve history |
| `test_pattern_detection_flow` | Seed 30 days data → run detector → verify patterns |
| `test_insight_flow` | Patterns → insight generation → paywall at 4th |
| `test_payment_flow` | Subscribe → verify access → cancel → verify downgrade |
| `test_invite_flow` | Generate code → redeem → verify premium for both |

### E2E Tests (Playwright)

| # | Critical Path | Steps |
|---|--------------|-------|
| E2E-1 | Onboarding | Open app → AI interview → first food log → dashboard |
| E2E-2 | Daily usage | Open dashboard → see insight → log food → complete lesson |
| E2E-3 | Paywall conversion | Receive 3 insights → see paywall → subscribe (mock) |
| E2E-4 | Invite friend | Generate invite → open link → verify referral |
| E2E-5 | Subscription cancel | Settings → cancel → verify downgrade |

**Note:** TWA-specific testing requires Telegram test environment or mocked `@telegram-apps/sdk`.

### AI Quality Tests

| Test | Method | Target |
|------|--------|--------|
| Food parser accuracy | 200 labeled Russian food descriptions | > 85% exact match |
| Pattern detection recall | 50 synthetic user profiles with known patterns | > 70% patterns found |
| Insight relevance | Human review of 100 generated insights | > 60% rated "useful" |
| Risk prediction calibration | Compare predicted vs actual overeating events | AUC > 0.65 |

## Performance Optimization

### API Response Times

| Endpoint | Target | Optimization |
|----------|:------:|-------------|
| `POST /api/auth/telegram` | < 100ms | In-memory HMAC, no DB call if JWT valid |
| `POST /api/food/log` | < 300ms | DB lookup first, AI parser async if miss |
| `GET /api/insights/today` | < 100ms | Pre-generated (cron), served from cache |
| `GET /api/patterns` | < 200ms | Cached in Redis (TTL 1 hour) |
| `GET /api/lessons/{id}` | < 50ms | Static content, aggressive caching |

### Caching Strategy (Redis)

| Key Pattern | TTL | Invalidation |
|-------------|:---:|-------------|
| `user:{id}:profile` | 5 min | On profile update |
| `user:{id}:insight:today` | 1 hour | On new insight generated |
| `user:{id}:patterns` | 1 hour | On pattern detection run |
| `user:{id}:risk:today` | 30 min | On new food log |
| `lesson:{id}` | 24 hours | On content update |
| `food_db:{hash}` | 7 days | On DB update |

### Frontend Performance

| Metric | Target | Method |
|--------|:------:|--------|
| First Contentful Paint | < 1.5s | Vite code splitting, preload critical CSS |
| Time to Interactive | < 2.5s | Lazy load non-critical features |
| Bundle size (gzipped) | < 150KB | Tree shaking, no heavy libraries |
| API waterfall | Max 2 sequential | Parallel requests on dashboard load |

### Database Optimization

| Query | Optimization |
|-------|-------------|
| Food entries by user (last 30 days) | Composite index `(user_id, logged_at DESC)` |
| Active patterns by user | Partial index `WHERE active = TRUE` |
| Insight history | Index `(user_id, created_at DESC)` + LIMIT |
| Subscription status check | Index `(user_id, status)` |
| Pattern detection aggregation | Materialized view refreshed daily |

## Security Hardening

### Input Validation Rules

| Field | Rules |
|-------|-------|
| `raw_text` (food) | Max 500 chars, strip HTML, no SQL injection patterns |
| `mood` | Enum: `great\|ok\|meh\|bad\|awful` |
| `context` | Enum: `home\|work\|street\|restaurant` |
| `init_data` | HMAC validated, max age 300s, telegram_id must be integer |
| `invite_code` | Alphanumeric, 8-20 chars |
| `plan` | Enum: `standard\|premium` |

### Rate Limits

| Endpoint | Limit | Window |
|----------|:-----:|:------:|
| `POST /api/auth/telegram` | 10 | 1 min |
| `POST /api/food/log` | 30 | 1 hour |
| `GET /api/insights/*` | 60 | 1 hour |
| `POST /api/invite/generate` | 5 | 1 day |
| Global per-user | 100 | 1 min |

### Data Privacy (152-ФЗ Compliance)

| Requirement | Implementation |
|-------------|---------------|
| Data residency in Russia | VPS in Moscow datacenter |
| User consent | Consent screen on first launch, stored in DB |
| Data export (right of access) | `GET /api/profile/export` → JSON download |
| Data deletion (right to erasure) | `DELETE /api/profile` → cascade delete all user data |
| PII in logs | telegram_id hashed, no names/food text in logs |
| Encryption at rest | pgcrypto for sensitive columns (interview answers, food text) |

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric | Tool | Alert Threshold |
|--------|------|:---------------:|
| API response time (p95) | Prometheus + Grafana | > 500ms |
| Error rate (5xx) | Prometheus | > 1% |
| AI API latency | Custom metric | > 10s |
| AI API error rate | Custom metric | > 5% |
| Active users (DAU) | PostgreSQL query | Drop > 20% day-over-day |
| Worker queue depth | RQ Dashboard | > 100 pending jobs |
| Disk usage | Node Exporter | > 80% |
| PostgreSQL connections | pg_stat | > 80% of max |

### Health Checks

```
GET /api/health          → { status: "ok", version: "0.1.0" }
GET /api/health/ready    → checks DB + Redis + OpenAI connectivity
GET /api/health/live     → basic process alive check
```
