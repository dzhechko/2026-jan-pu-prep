# НутриМайнд — AI-powered Weight Management Telegram Mini App

AI-платформа для управления весом, встроенная в Telegram Mini App. Сочетает когнитивно-поведенческую терапию (КПТ) с интеллектуальным трекингом питания, детекцией паттернов и персональными инсайтами.

**Целевая аудитория:** женщины 30–55 лет, которые хотят понять *почему* они переедают, а не просто считать калории.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Client                       │
│              (Mini App WebView + Bot Chat)               │
└────────────┬──────────────────────┬──────────────────────┘
             │ HTTPS                │ Bot API
             ▼                      ▼
┌────────────────────┐   ┌────────────────────┐
│   Frontend (Vite)  │   │   Telegram Bot     │
│   React 18 + TS    │   │   python-telegram  │
│   TailwindCSS      │   │   -bot 21          │
│   Port 5173        │   └────────┬───────────┘
└────────┬───────────┘            │
         │ /api/*                 │
         ▼                        ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                 │
│     SQLAlchemy 2.0 (async) + Pydantic   │
│              Port 8000                   │
├──────────────┬──────────────────────────┤
│              │                          │
│   ┌─────────▼──────┐  ┌──────────────┐ │
│   │  PostgreSQL 16  │  │   Redis 7    │ │
│   │  Port 5432      │  │   Port 6379  │ │
│   └────────────────┘  └──────┬───────┘ │
│                              │         │
│                    ┌─────────▼───────┐ │
│                    │   RQ Worker     │ │
│                    │  (AI tasks)     │ │
│                    └─────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Стек технологий

| Слой | Технология |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite 5 + TailwindCSS 3 |
| State management | Zustand 4 с persist |
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| База данных | PostgreSQL 16 + Redis 7 |
| Бот | python-telegram-bot 21 |
| AI | OpenAI GPT-4o-mini через RQ workers |
| Аутентификация | Telegram initData HMAC-SHA256 |
| Инфраструктура | Docker Compose (6 сервисов) |
| Тесты | pytest + pytest-asyncio (backend), Vitest (frontend) |

---

## Функциональность

### Реализованные фичи (10 PR)

| # | Фича | Описание | PR |
|---|-------|---------|-----|
| 1 | **Telegram Auth** | Валидация initData через HMAC-SHA256, JWT-токены | #1 |
| 2 | **Onboarding** | AI-интервью из 2 вопросов, кластеризация профиля | #2 |
| 3 | **Food Logging** | Логирование еды на русском, парсинг, настроение/контекст | #3 |
| 4 | **Pattern Detection** | Статистический анализ паттернов питания (время, настроение, пропуски) | #4 |
| 5 | **Daily Insights** | Ротация инсайтов: паттерн → прогресс → КПТ → риск (7 дней) | #5 |
| 6 | **Risk Predictor** | Скоринг риска переедания (время суток, настроение, пропуски, выходные) | #6 |
| 7 | **CBT Lessons** | 20 уроков КПТ на русском, рекомендации по паттернам | #7 |
| 8 | **Paywall** | Freemium: 3 бесплатных инсайта, подписка 499 ₽/мес | #8 |
| 9 | **Invite System** | Реферальные коды, 7 дней Premium обоим участникам | #9 |
| 10 | **Data Privacy** | Экспорт данных (JSON), удаление аккаунта (152-ФЗ) | #10 |

---

## Быстрый старт

### Требования

- Docker и Docker Compose
- Node.js 20+ (для фронтенд-разработки)
- Telegram Bot Token от [@BotFather](https://t.me/botfather)

### 1. Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=<ваш-токен-от-botfather>
SECRET_KEY=<случайная-строка-64-символа>
DB_PASSWORD=<пароль-бд>

# Для AI-функций
OPENAI_API_KEY=<ваш-openai-ключ>

# Опционально
TELEGRAM_MINI_APP_URL=https://your-app-url.com
YUKASSA_SHOP_ID=<id-магазина>
YUKASSA_SECRET_KEY=<секретный-ключ>
SENTRY_DSN=<dsn-для-мониторинга>
```

### 2. Запуск dev-окружения

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Запустится 6 сервисов:

| Сервис | Порт | Описание |
|--------|------|----------|
| **api** | 8000 | FastAPI с hot-reload |
| **frontend** | 5173 | Vite dev server |
| **bot** | — | Telegram бот (polling mode) |
| **worker** | — | RQ worker (ai_heavy, ai_light) |
| **postgres** | 5432 | PostgreSQL 16 |
| **redis** | 6379 | Redis 7 |

### 3. Миграция базы данных

```bash
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
```

### 4. Проверка

```bash
# Health check
curl http://localhost:8000/api/health
# → {"status":"ok","version":"0.1.0"}

# Readiness (DB + Redis)
curl http://localhost:8000/api/health/ready
# → {"status":"ok","db":"ok","redis":"ok"}

# Swagger UI
open http://localhost:8000/docs

# Frontend
open http://localhost:5173
```

### 5. Запуск тестов

```bash
# Backend (167 тестов)
docker compose -f docker-compose.dev.yml exec api pytest -v

# Frontend (3 теста)
cd frontend && npm test
```

---

## API Endpoints

### Аутентификация
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/auth/telegram` | Аутентификация через Telegram initData |

### Онбординг
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/onboarding/interview` | Отправка ответов AI-интервью |
| GET | `/api/onboarding/status` | Статус прохождения онбординга |

### Питание
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/food/log` | Залогировать приём пищи |
| GET | `/api/food/history` | История питания с пагинацией |

### Паттерны
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/patterns` | Обнаруженные паттерны питания |
| POST | `/api/patterns/{id}/feedback` | Обратная связь по паттерну |

### Инсайты
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/insights/today` | Сегодняшние инсайты |

### Уроки КПТ
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/lessons` | Список всех уроков с прогрессом |
| GET | `/api/lessons/recommended` | Рекомендуемый урок по паттернам |
| GET | `/api/lessons/{id}` | Содержимое урока |
| POST | `/api/lessons/{id}/complete` | Отметить урок пройденным |

### Подписка
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/payments/subscribe` | Оформить подписку (499 ₽/мес) |
| GET | `/api/payments/subscription` | Статус подписки |
| DELETE | `/api/payments/subscription` | Отменить подписку |

### Приглашения
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/invite/generate` | Создать реферальный код |
| POST | `/api/invite/redeem` | Активировать код (7 дней Premium) |
| GET | `/api/invite/my-invites` | История приглашений |

### Приватность данных
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/privacy/export` | Экспорт всех данных (JSON) |
| POST | `/api/privacy/delete` | Удаление аккаунта (подтверждение "УДАЛИТЬ") |

### Мониторинг
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | Shallow health check |
| GET | `/api/health/ready` | Deep check (DB + Redis) |

---

## Структура проекта

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, роутеры, middleware
│   │   ├── config.py               # Pydantic Settings
│   │   ├── database.py             # Async SQLAlchemy engine/session
│   │   ├── dependencies.py         # Dependency injection (get_db, get_user)
│   │   ├── models/
│   │   │   ├── user.py             # User + AIProfile
│   │   │   ├── food.py             # FoodEntry
│   │   │   ├── pattern.py          # Pattern
│   │   │   ├── insight.py          # Insight
│   │   │   ├── lesson.py           # CBTLesson + UserLessonProgress
│   │   │   ├── subscription.py     # Subscription
│   │   │   └── invite.py           # Invite
│   │   ├── schemas/
│   │   │   ├── auth.py             # TelegramAuthRequest/Response
│   │   │   ├── onboarding.py       # InterviewRequest/Response
│   │   │   ├── food.py             # FoodLogRequest/Response
│   │   │   ├── pattern.py          # PatternResponse
│   │   │   ├── insight.py          # InsightResponse
│   │   │   ├── lesson.py           # LessonResponse
│   │   │   ├── payment.py          # SubscribeRequest/Response
│   │   │   ├── invite.py           # InviteGenerate/Redeem/Response
│   │   │   └── privacy.py          # Export/DeleteResponse
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── onboarding.py
│   │   │   ├── food.py
│   │   │   ├── patterns.py
│   │   │   ├── insights.py
│   │   │   ├── lessons.py
│   │   │   ├── payments.py
│   │   │   ├── invite.py
│   │   │   └── privacy.py
│   │   └── services/
│   │       ├── auth_service.py      # HMAC-SHA256 валидация initData
│   │       ├── onboarding_service.py
│   │       ├── food_service.py
│   │       ├── pattern_service.py   # Статистический детектор паттернов
│   │       ├── insight_service.py   # 7-дневная ротация инсайтов
│   │       ├── risk_service.py      # Скоринг риска переедания
│   │       ├── lesson_service.py    # 20 КПТ-уроков, рекомендации
│   │       ├── payment_service.py
│   │       ├── invite_service.py    # Реферальная система
│   │       └── privacy_service.py   # Экспорт/удаление (152-ФЗ)
│   ├── tests/
│   │   ├── conftest.py              # Фикстуры (async DB, test client)
│   │   ├── test_health.py
│   │   ├── test_auth.py
│   │   ├── test_onboarding.py
│   │   ├── test_food.py
│   │   ├── test_patterns.py
│   │   ├── test_insights.py
│   │   ├── test_risk.py
│   │   ├── test_lessons.py
│   │   ├── test_payments.py
│   │   ├── test_invites.py
│   │   └── test_privacy.py
│   ├── alembic/                     # Миграции БД
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx              # Роутинг
│   │   │   └── main.tsx             # Точка входа
│   │   ├── features/
│   │   │   ├── auth/                # Telegram-аутентификация
│   │   │   ├── onboarding/          # Экраны онбординга
│   │   │   ├── dashboard/           # Главный экран
│   │   │   ├── food-logging/        # Логирование еды
│   │   │   ├── patterns/            # Обнаруженные паттерны
│   │   │   ├── insights/            # Инсайты дня
│   │   │   ├── lessons/             # КПТ-уроки
│   │   │   ├── paywall/             # Экран подписки
│   │   │   ├── invite/              # Реферальная программа
│   │   │   └── profile/             # Профиль + приватность
│   │   ├── shared/
│   │   │   ├── api/client.ts        # Axios instance + JWT interceptor
│   │   │   ├── stores/              # Zustand stores
│   │   │   └── ui/                  # Переиспользуемые компоненты
│   │   └── __tests__/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── bot/
│   ├── main.py                      # Telegram bot (webhook/polling)
│   └── Dockerfile
│
├── nginx/
│   └── nginx.conf                   # Reverse proxy
│
├── docs/sparc/                      # SPARC PRD документация
│   ├── Specification.md
│   ├── Pseudocode.md
│   ├── Architecture.md
│   ├── Refinement.md
│   └── Completion.md
│
├── docker-compose.dev.yml
├── docker-compose.yml
└── .env.example
```

---

## Модель данных

```
┌──────────┐     ┌──────────────┐     ┌───────────┐
│   User   │────<│  FoodEntry   │     │  Pattern  │
│          │     │              │     │           │
│ tg_id    │     │ raw_text     │     │ type      │
│ sub_stat │     │ parsed_items │     │ conf      │
│ onboard  │     │ calories     │     │ descr_ru  │
└────┬─────┘     │ mood/context │     │ evidence  │
     │           │ day/hour     │     └─────┬─────┘
     │           └──────────────┘           │
     │                                      │
     │      ┌──────────────┐     ┌──────────▼──┐
     ├─────<│  AIProfile   │     │   Insight   │
     │      │              │     │             │
     │      │ answers      │     │ title/body  │
     │      │ cluster_id   │     │ action      │
     │      │ risk_model   │     │ is_locked   │
     │      └──────────────┘     └─────────────┘
     │
     │      ┌──────────────┐     ┌─────────────────────┐
     ├─────<│ Subscription │     │ UserLessonProgress  │
     │      │              │     │                     │
     │      │ plan         │     │ user_id + lesson_id │
     │      │ status       │     │ completed_at        │
     │      │ expires_at   │     └──────────┬──────────┘
     │      └──────────────┘                │
     │                              ┌───────▼──────┐
     │      ┌──────────────┐        │  CBTLesson   │
     └─────<│   Invite     │        │              │
            │              │        │ title        │
            │ invite_code  │        │ content_md   │
            │ inviter_id   │        │ pattern_tags │
            │ invitee_id   │        │ duration_min │
            └──────────────┘        └──────────────┘
```

---

## AI Pipeline

### Паттерн-детекция (без LLM)

Статистический анализ запускается при каждом 10-м логе или ежедневно:

1. **Time patterns** — кластеризация по часам (утро, день, вечер, ночь)
2. **Mood patterns** — корреляция настроения с калорийностью
3. **Context patterns** — частота переедания в определённых контекстах
4. **Skip patterns** — обнаружение пропусков приёмов пищи
5. **Weekend patterns** — разница будни vs выходные

Все описания на русском языке, ≤ 50 слов, без медицинского жаргона.

### Риск-предиктор (без LLM)

Скоринг 0–100 на основе:
- Текущее время суток и историческая калорийность
- Последнее зафиксированное настроение
- Пропуски приёмов пищи сегодня
- День недели (выходные/будни)

### Инсайты (7-дневная ротация)

| День | Тип | Источник |
|------|-----|----------|
| 1 | pattern | Обнаруженный паттерн |
| 2 | progress | Прогресс за неделю |
| 3 | cbt | Совет из КПТ-урока |
| 4 | risk | Предупреждение о риске |
| 5–7 | mix | Ротация из предыдущих |

Шаблоны на русском языке, генерируются локально без LLM.

### КПТ-уроки

20 уроков, сгруппированных по темам:
- Уроки 1–4: Основы осознанности
- Уроки 5–8: Эмоциональное питание
- Уроки 9–12: Когнитивные искажения
- Уроки 13–16: Стратегии преодоления
- Уроки 17–20: Долгосрочные привычки

Рекомендации основаны на совпадении `pattern_tags` урока с обнаруженными паттернами пользователя.

---

## Безопасность

- **Аутентификация**: Telegram initData HMAC-SHA256 → JWT-токены
- **Rate limiting**: Redis-backed лимиты на эндпоинтах
- **SQL injection**: SQLAlchemy ORM с параметризованными запросами
- **XSS**: React JSX с автоматическим escaping
- **CORS**: Настраиваемый список origins
- **Secrets**: `.env` в `.gitignore`, без секретов в коде
- **152-ФЗ**: Экспорт данных и полное удаление аккаунта

---

## Тестирование

```
170 тестов (167 backend + 3 frontend)

Backend (pytest + pytest-asyncio):
  test_health.py        — Health check endpoints
  test_auth.py          — Telegram HMAC-SHA256 auth
  test_onboarding.py    — AI interview flow
  test_food.py          — Food logging & history
  test_patterns.py      — Pattern detection
  test_insights.py      — Insight generation & rotation
  test_risk.py          — Risk scoring
  test_lessons.py       — CBT lessons & progress
  test_payments.py      — Subscription lifecycle
  test_invites.py       — Invite generation & redemption
  test_privacy.py       — Data export & deletion

Frontend (Vitest + Testing Library):
  App.test.tsx          — Routing & rendering
```

---

## Статистика проекта

| Метрика | Значение |
|---------|----------|
| Сервисы Docker | 6 |
| API-эндпоинтов | 23 |
| Моделей БД | 9 таблиц |
| Тестов | 170 |
| Backend Python LOC | ~4 800 |
| Frontend TS/TSX LOC | ~4 300 |
| Общий LOC | ~15 000 |
| Pull Requests | 10 |

---

## Документация

Полная SPARC PRD документация в `docs/sparc/`:

- **Specification.md** — Пользовательские истории, эпики, критерии приёмки
- **Pseudocode.md** — Алгоритмы, потоки данных, конечные автоматы
- **Architecture.md** — Системный дизайн, ADR, модель данных
- **Refinement.md** — Граничные случаи, тестирование, производительность
- **Completion.md** — Деплой, CI/CD, мониторинг

---

## Лицензия

Proprietary. All rights reserved.
