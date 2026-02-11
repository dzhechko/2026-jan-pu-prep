# Security Rules — НутриМайнд

## Authentication
- Every API endpoint MUST validate Telegram initData via HMAC-SHA256
- JWT access tokens expire in 15 minutes, refresh tokens in 7 days
- Never store BOT_TOKEN in frontend code or client-accessible locations
- initData must be no older than 300 seconds (auth_date check)

## Data Protection (152-ФЗ)
- All user data stored on Russian-based VPS (Moscow datacenter)
- PII columns encrypted with pgcrypto (interview_answers, raw food text)
- Never log: telegram_id (hash it), first_name, food text, interview answers
- Support data export (GET /api/profile/export) and deletion (DELETE /api/profile)
- Hard delete with CASCADE — no soft deletes for personal data

## Input Validation
- All API inputs validated via Pydantic schemas before processing
- Food text: max 500 characters, strip HTML tags, sanitize
- Mood: enum only (great|ok|meh|bad|awful)
- Context: enum only (home|work|street|restaurant)
- invite_code: alphanumeric 8-20 chars only

## Rate Limiting (Redis sliding window)
- POST /api/auth/telegram: 10/min per IP
- POST /api/food/log: 30/hour per user
- GET /api/insights/*: 60/hour per user
- POST /api/invite/generate: 5/day per user
- Global: 100/min per user

## Secrets Management
- All secrets in .env file (never committed to git)
- Docker secrets for production deployment
- Required secrets: TELEGRAM_BOT_TOKEN, SECRET_KEY, DB_PASSWORD, OPENAI_API_KEY
- Optional: YUKASSA_SHOP_ID, YUKASSA_SECRET_KEY, SENTRY_DSN

## CORS
- Whitelist only: https://app.nutrimind.ru and Telegram WebApp origins
- No wildcard CORS headers

## Dependencies
- Pin all dependency versions in requirements.txt and package.json lock files
- Run `pip-audit` and `npm audit` before each release
