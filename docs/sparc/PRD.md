# PRD: НутриМайнд — AI-Детектив пищевых привычек

## Executive Summary

НутриМайнд — мобильное приложение для управления весом, которое использует AI для выявления персональных паттернов переедания и CBT (когнитивно-поведенческую терапию) для их изменения. В отличие от калькуляторов калорий, НутриМайнд отвечает на вопрос "ПОЧЕМУ вы переедаете", а не "ЧТО вы съели".

**Целевой рынок:** Россия (50M+ людей с избыточным весом)
**Бизнес-модель:** Freemium → Subscription (499 ₽/мес)
**Уникальное отличие:** Единственное приложение с CBT + AI coaching на русском языке

## Problem Statement

95% диет проваливаются в течение 1 года. Существующие приложения (MyFitnessPal, FatSecret, Lifesum) считают калории, но не помогают понять и изменить поведенческие паттерны — корневую причину переедания. Noom доказал что CBT-подход работает (78% success rate), но стоит $17-42/мес и недоступен на русском.

## Target Users

### Primary: "Хронический диетчик" (50% рынка)
- Женщины 30-55 лет, средний доход, городские
- JTBD: "Помоги мне понять ПОЧЕМУ я переедаю и сломать цикл йо-йо"
- Триггер: Фото на событии, визит к врачу, новый год

### Secondary: "Осознанный оптимизатор" (25%)
- 25-45 лет, выше среднего доход, tech-savvy
- JTBD: "Data-driven подход к здоровью с видимым прогрессом"
- Триггер: Wearable показал плохие метрики

### Tertiary: "Health-curious" (25%)
- 35-60 лет, BMI 27+, готовы инвестировать в здоровье
- JTBD: "Решить проблему веса раз и навсегда без диет"
- Триггер: Рекомендация врача, неуспех предыдущих методов

## Product Vision

> НутриМайнд — ваш персональный AI-детектив, который расследует причины переедания и помогает изменить привычки через психологию, а не ограничения.

## Core Value Proposition

| Для кого | Проблема | Решение | Результат |
|----------|---------|---------|-----------|
| Людей с лишним весом в РФ | Диеты не работают, калькуляторы калорий не меняют поведение | AI находит персональные паттерны переедания + CBT-уроки меняют привычки | Устойчивое снижение веса через понимание себя |

## Feature Matrix

### MVP (v0.1) — 8 недель

| # | Feature | Priority | CJM Screen |
|---|---------|:--------:|:----------:|
| F1 | AI-интервью (onboarding) | P0 | Onboarding |
| F2 | Food logging (текст + фото) | P0 | Dashboard |
| F3 | AI Pattern Detector (анализ паттернов переедания) | P0 | Aha + Dashboard |
| F4 | AI-инсайты (ежедневные, на основе данных) | P0 | Dashboard |
| F5 | Risk Predictor ("триггер дня") | P0 | Dashboard |
| F6 | CBT мини-уроки (20 уроков) | P0 | Dashboard |
| F7 | Freemium paywall (после 3 инсайтов) | P0 | Paywall |
| F8 | Invite (парный AI-анализ) | P1 | Invite |
| F9 | Push-уведомления (risk alerts, lesson reminders) | P1 | — |
| F10 | Базовый профиль пользователя | P0 | — |

### v1.0 — 16 недель

| # | Feature | Priority |
|---|---------|:--------:|
| F11 | Group support (community) | P1 |
| F12 | Progress analytics (вес, настроение, срывы) | P1 |
| F13 | AI Coach (чат с CBT-промптами) | P1 |
| F14 | Streak/achievement система | P2 |
| F15 | Расширенная база RU продуктов | P1 |

### v2.0 — 24+ недель

| # | Feature | Priority |
|---|---------|:--------:|
| F16 | Wearable integration (Apple Watch, Mi Band) | P2 |
| F17 | Meal planning на основе паттернов | P2 |
| F18 | B2B2C (employer wellness programs) | P3 |
| F19 | Telehealth (консультации с нутрициологом) | P3 |

## User Journeys (CJM C: AI-Детектив)

### Journey 1: First Session (Awareness → Aha)
```
Landing ("Разберись почему срываешься")
  → Sign up (email/phone)
  → AI-интервью (2 вопроса о привычках)
  → Первый food log
  → [день 3-5] AI Aha: "Найден паттерн!"
  → 3 бесплатных инсайта
  → Paywall: "Разблокируй полный AI-анализ" (499 ₽/мес)
```

### Journey 2: Daily Engagement (Retention)
```
Push: "Сегодня высокий риск срыва в 18:00"
  → Открыть Dashboard
  → Посмотреть AI-инсайт дня
  → Залогировать еду
  → Пройти CBT мини-урок (5 мин)
  → Отметить настроение
```

### Journey 3: Invite (Referral)
```
Увидеть "Парный AI-анализ"
  → Отправить invite-ссылку
  → Подруга регистрируется
  → Оба получают Premium неделю бесплатно
  → AI сравнивает паттерны двух пользователей
```

## Success Metrics

| Metric | Target (M3) | Target (M6) | Target (M12) |
|--------|:-----------:|:-----------:|:------------:|
| Total Users | 5,000 | 25,000 | 100,000 |
| Paid Subscribers | 200 | 1,500 | 6,000 |
| Free→Paid Conversion | 4% | 5% | 6% |
| D7 Retention | 40% | 45% | 50% |
| D30 Retention | 20% | 25% | 30% |
| Monthly Churn (paid) | 12% | 10% | 8% |
| NPS | 30 | 40 | 50 |
| AI Insight accuracy (user-rated) | 60% | 70% | 80% |

## Business Model

| Revenue Stream | Pricing | Timeline |
|---------------|---------|----------|
| Subscription (Standard) | 499 ₽/мес, 3990 ₽/год | MVP |
| Subscription (Premium) | 999 ₽/мес, 7990 ₽/год | v1.0 |
| B2B2C (employer plans) | Per-seat pricing | v2.0 |

**Unit Economics Target:**
- ARPU: $8/мес → LTV: $48-96
- CAC: $5-15 → LTV:CAC: 6-10:1
- Gross Margin: 85%+ (no human coaches)
- Break-even: 2,000 paid users (Month 9-12)

## Constraints

### Platform
- **Telegram Mini App** (TWA — Telegram Web App)
- Frontend: React + `@telegram-apps/sdk`
- Backend: Node.js / Python (FastAPI)
- Telegram Bot как entry point → кнопка "Открыть" → Mini App

### Architecture
- Distributed Monolith in Monorepo
- Docker + Docker Compose
- VPS deployment (AdminVPS/HOSTKEY)
- MCP servers for AI integration

### Auth & Payments
- Auth: Telegram `initData` validation (zero-friction, user уже залогинен)
- Payments: Telegram Stars API (in-app) + ЮKassa (external fallback)
- No email/phone registration needed

### Security
- 152-ФЗ compliance (RU personal data law)
- Health data encryption at rest (AES-256)
- Telegram initData HMAC validation on every request
- No plaintext PII in logs

### Regulatory
- НЕ медицинское устройство (lifestyle app, не диагностика)
- Disclaimer: "не является медицинской консультацией"

## Non-Functional Requirements

| Category | Requirement | Target |
|----------|-----------|--------|
| Performance | API response time | < 200ms p95 |
| Performance | AI insight generation | < 5s |
| Availability | Uptime | 99.5% |
| Scalability | Concurrent users | 10,000+ |
| Security | Telegram initData HMAC validation | Every request |
| Security | Data encryption | AES-256 at rest, TLS 1.3 in transit |
| Localization | Language | Русский (primary) |
| Platform | Telegram Mini App | SDK v7+ |
| Mobile | Via Telegram | iOS 15+ / Android 10+ / Desktop |

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| MVP (v0.1) | 8 weeks | 10 core features, web + mobile |
| Beta | 4 weeks | 500 beta users, iterate |
| Launch (v1.0) | 4 weeks | Public launch, 5 additional features |
| Growth (v1.x) | Ongoing | Iterations based on data |
| v2.0 | Week 24+ | Wearables, B2B, telehealth |

## Open Questions

1. AI model choice: OpenAI API vs self-hosted LLM (latency vs cost vs privacy)?
2. Русская food database: build vs partner (FatSecret API, Open Food Facts)?
3. Payment processor: ЮKassa vs CloudPayments vs Stripe (для РФ)?
4. Compliance: нужен ли DPO (Data Protection Officer) с первого дня?
