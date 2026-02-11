# Solution Strategy: НутриМайнд

## Problem Statement (SCQA)

- **Situation:** 50M+ россиян с избыточным весом используют приложения-калькуляторы калорий (FatSecret, Lifesum, YAZIO), которые не решают корневую проблему — поведенческие паттерны переедания.
- **Complication:** Noom доказал что CBT-подход работает (78% пользователей теряют вес), но стоит $17-42/мес, не локализован для РФ, и его coaching воспринимается как "бот". На рынке РФ нет ни одного приложения с психологическим подходом к питанию.
- **Question:** Как создать доступное AI-powered приложение с CBT-подходом для российского рынка, которое решает проблему "почему" люди переедают, а не просто считает калории?
- **Answer:** НутриМайнд — AI-Детектив, который анализирует персональные данные пользователя и находит уникальные паттерны переедания, предсказывает риски срывов и даёт CBT-based рекомендации на русском языке.

## First Principles Analysis

### Фундаментальные истины
1. **Переедание — поведенческая проблема**, не информационная. Люди знают что есть, но не знают ПОЧЕМУ едят неправильно.
2. **CBT доказанно работает** для изменения пищевых привычек (мета-анализы, Noom's 78% success rate).
3. **AI может масштабировать персонализацию** лучше human coaches (паттерн-детекция в данных, 24/7 доступность).
4. **Российский рынок price-sensitive**: средняя готовность платить за health app ~500 руб/мес, в 5-8x ниже US.
5. **Data = Moat**: чем больше данных о пищевом поведении → точнее AI → лучше результаты → больше retention.

### Что это означает для продукта
- Фокус на "ПОЧЕМУ" (паттерны), а не "ЧТО" (калории)
- AI-coaching вместо human coaching → unit economics на порядок лучше
- Русская база продуктов + понимание местного контекста = барьер входа для Noom
- Freemium с proof of value перед paywall (CJM C: после 3 AI-инсайтов)

## Root Cause Analysis (5 Whys)

**Проблема:** Люди не могут поддерживать здоровый вес длительно.

1. **Why?** → Они срываются с диет через 2-4 недели
2. **Why?** → Диеты не учитывают индивидуальные триггеры переедания
3. **Why?** → Нет инструмента для выявления персональных паттернов
4. **Why?** → Существующие приложения считают калории, а не анализируют поведение
5. **Root Cause:** → **Отсутствие доступного AI-инструмента для поведенческого анализа пищевых привычек на русском языке**

## Game Theory Analysis

### Key Players

| Player | Primary Interest | Likely Reaction |
|--------|-----------------|-----------------|
| Noom | Protect global market, expand to new regions | Вряд ли выйдет в РФ (санкции, малый рынок). Может запартнериться с локальным игроком |
| MyFitnessPal | User base, ad revenue | Не инвестирует в CBT/AI coaching — другая бизнес-модель |
| Lifesum/YAZIO | Premium subscriptions | Могут скопировать AI-фичи через 12-18 мес если увидят traction |
| Локальные apps | Калории, простота | Нет экспертизы в CBT, нет AI pipeline |
| Users | Результат по доступной цене | Switch cost низкий → легко привлечь, но и легко потерять |

### Nash Equilibrium
Оптимальная стратегия: **Niche differentiation** (CBT + AI на русском) + **aggressive pricing** (499 ₽/мес). Incumbents не будут реагировать на специфический RU-niche, а копирование CBT+AI pipeline займёт 12-18 мес.

### Рекомендация
> **Стратегия входа:** Feature-led differentiation (AI pattern detection — чего нет ни у кого на RU рынке) + price advantage (10x дешевле Noom).

## Second-Order Effects

| Timeframe | Effect | Probability | Mitigation |
|-----------|--------|:-----------:|------------|
| 0-6 мес | Early adopters из "осознанного" сегмента | High | Content marketing в Telegram/YouTube |
| 6-12 мес | Копирование AI-фичей конкурентами | Medium | Data moat: 6 мес данных = ~1M записей → accuracy gap |
| 12-18 мес | Потенциальный выход Noom/WW в РФ через партнёра | Low | К этому моменту brand + community moat |
| 12-24 мес | Регуляция digital health в РФ (152-ФЗ, мед.данные) | Medium | GDPR-compliant архитектура с первого дня |

### Feedback Loops
- **Positive:** Больше users → больше data → точнее AI → лучше результаты → больше referrals ↻
- **Negative:** Быстрый рост → generic AI → плохие инсайты → churn ↻
- **Tipping Point:** Positive > Negative при ~10,000 active users (достаточно данных для meaningful patterns)

## Contradictions Resolved (TRIZ)

| # | Contradiction | Type | TRIZ Principle | Resolution |
|---|---------------|------|----------------|------------|
| 1 | AI должен быть ПЕРСОНАЛЬНЫМ (для точности) и РАБОТАТЬ С МАЛЫМИ ДАННЫМИ (новый пользователь) | Technical | #23 Feedback + #1 Segmentation | Cold start: используем кластеры похожих пользователей → персонализация по мере накопления данных |
| 2 | Цена должна быть ВЫСОКОЙ (для unit economics) и НИЗКОЙ (для RU рынка) | Physical | Separation in Time | Freemium → proof of value (3 инсайта) → conversion на эмоциях. Низкий ARPU × high volume |
| 3 | Onboarding должен быть КОРОТКИМ (для retention) и ГЛУБОКИМ (для AI calibration) | Physical | Separation in Space | Onboarding = 2 вопроса (быстро). Глубокая калибровка — через food logging в первые 3 дня (фоном) |
| 4 | Coaching должен быть ГЛУБОКИМ (для эффективности) и МАСШТАБИРУЕМЫМ (для unit economics) | Technical | #28 Mechanics Substitution | LLM-based coach с CBT-промптами → глубокий, но $0.01/сессия вместо $5/сессия human coach |

## Recommended Approach

### MVP Scope (из CJM C: AI-Детектив)

**6 экранов:**
1. **Landing:** "Разберись почему ты срываешься" → AI-интервью
2. **Onboarding:** 2 вопроса + начало сбора данных
3. **Aha Moment:** AI показывает персональный паттерн срывов
4. **Dashboard:** AI-инсайты + триггер дня + прогресс
5. **Paywall:** После 3-го инсайта → 499 ₽/мес
6. **Invite:** Парный AI-анализ с другом

**Core AI Pipeline:**
- Food log → Time-series analysis → Pattern detection
- Mood + context + food → Correlation engine
- Historical data → Risk scoring (сегодняшний риск срыва)
- CBT lesson engine → Персональные уроки на основе найденных паттернов

### Non-MVP (v2+)
- GLP-1 integration (если регуляция позволит)
- Wearable integration (Apple Watch, Mi Band)
- Group challenges
- Employer/insurance partnerships (B2B2C)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| AI даёт generic инсайты (как Noom coach) | High | Critical | TRIZ #1: cold start через кластеры; качественный CBT-промптинг; A/B тестирование инсайтов |
| Низкая конверсия Free→Paid | Medium | High | CJM C paywall после proof of value (3 инсайта); A/B testing paywall timing |
| Неточная русская база продуктов | Medium | Medium | Community-driven DB + AI food recognition; партнёрство с nutrition DB |
| Регуляторные изменения (мед.данные) | Low | High | GDPR-compliant архитектура; данные на RU серверах (152-ФЗ); консультация юриста |
| Noom выходит в РФ | Low | Medium | Data moat + community + brand advantage за 12-18 мес head start |
