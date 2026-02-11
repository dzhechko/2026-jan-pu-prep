# Pseudocode: НутриМайнд

## Data Structures

### User
```
type User = {
  id: UUID
  telegram_id: number
  telegram_username: string | null
  first_name: string
  created_at: Timestamp
  subscription_status: "free" | "standard" | "premium"
  subscription_expires_at: Timestamp | null
  insights_received: number  // для free tier paywall (max 3)
  onboarding_complete: boolean
  ai_profile: AIProfile | null
}
```

### AIProfile
```
type AIProfile = {
  user_id: UUID
  interview_answers: InterviewAnswer[]
  detected_patterns: Pattern[]
  risk_model: RiskModel
  cluster_id: string | null   // cold start: кластер похожих пользователей
  last_updated: Timestamp
}
```

### FoodEntry
```
type FoodEntry = {
  id: UUID
  user_id: UUID
  raw_text: string           // "борщ с хлебом"
  parsed_items: FoodItem[]   // [{name, calories, category}]
  mood: "great" | "ok" | "meh" | "bad" | "awful" | null
  context: "home" | "work" | "street" | "restaurant" | null
  logged_at: Timestamp
  day_of_week: number
  hour: number
}
```

### Pattern
```
type Pattern = {
  id: UUID
  user_id: UUID
  type: "time" | "mood" | "context" | "sequence" | "skip"
  description_ru: string     // "Стресс → пропуск обеда → переедание вечером"
  confidence: float          // 0.0 - 1.0
  evidence: Evidence[]       // ссылки на конкретные FoodEntry
  discovered_at: Timestamp
}
```

### Insight
```
type Insight = {
  id: UUID
  user_id: UUID
  pattern_id: UUID | null
  title: string
  body: string
  action: string             // рекомендация
  type: "pattern" | "risk" | "progress" | "cbt"
  seen: boolean
  created_at: Timestamp
}
```

### CBTLesson
```
type CBTLesson = {
  id: UUID
  order: number              // 1-20
  title: string
  content_md: string
  pattern_tags: string[]     // какие паттерны релевантны
  duration_min: number       // 3-7
}
```

## Core Algorithms

### Algorithm: AI Pattern Detector

```
INPUT: user_id, food_entries (last 7+ days)
OUTPUT: Pattern[]

STEPS:
1. LOAD all food_entries for user_id (last 30 days, min 3 days)
2. IF entries.length < 10:
     USE cold_start_patterns(user.cluster_id)
     RETURN cluster-based patterns with low confidence

3. GROUP entries by day_of_week, hour, mood, context

4. DETECT time_patterns:
   FOR each hour_bucket in [morning, lunch, afternoon, evening, night]:
     calories = SUM(entries in bucket)
     IF calories[evening] > 2 * calories[lunch]:
       ADD Pattern(type="sequence", desc="Пропуск обеда → переедание вечером", confidence=count/total_days)

5. DETECT mood_patterns:
   FOR each mood in [great, ok, meh, bad, awful]:
     avg_calories = AVG(calories WHERE mood = mood)
     IF avg_calories[bad] > 1.5 * avg_calories[ok]:
       ADD Pattern(type="mood", desc="Плохое настроение → переедание", confidence=...)

6. DETECT context_patterns:
   FOR each context in [home, work, street, restaurant]:
     analyze correlation between context and calorie spikes

7. DETECT skip_patterns:
   FOR each day:
     IF no entry between 11:00-14:00 AND entries[18:00-22:00] > daily_avg * 0.6:
       ADD Pattern(type="skip", desc="Пропуск обеда → вечерний срыв")

8. RANK patterns by confidence DESC
9. FILTER patterns WHERE confidence >= 0.5
10. RETURN top 5 patterns

COMPLEXITY: O(n) where n = number of food entries
```

### Algorithm: Risk Predictor

```
INPUT: user_id, current_datetime
OUTPUT: RiskScore { level: "low"|"medium"|"high", time_window: string, recommendation: string }

STEPS:
1. LOAD user patterns (from AI Profile)
2. LOAD today's entries so far
3. LOAD contextual factors:
   - day_of_week (weekday vs weekend)
   - sleep_logged (if available)
   - mood_today (if logged)

4. CALCULATE base_risk from patterns:
   FOR each pattern:
     IF pattern.type == "time" AND current_hour approaches pattern.trigger_hour:
       risk += pattern.confidence * 0.4
     IF pattern.type == "mood" AND today_mood == pattern.trigger_mood:
       risk += pattern.confidence * 0.3
     IF pattern.type == "skip" AND no_lunch_logged AND hour > 15:
       risk += pattern.confidence * 0.5

5. ADJUST for today's data:
   IF user already logged high-calorie meal today: risk *= 0.7
   IF user completed CBT lesson today: risk *= 0.8
   IF weekend AND user has weekend pattern: risk *= 1.3

6. NORMALIZE risk to 0.0-1.0
7. CLASSIFY:
   risk < 0.3 → "low"
   risk 0.3-0.6 → "medium"
   risk > 0.6 → "high"

8. GENERATE recommendation based on top contributing pattern
9. RETURN RiskScore

COMPLEXITY: O(p) where p = number of patterns (typically < 10)
```

### Algorithm: Food Text Parser (Russian)

```
INPUT: raw_text (string, Russian)
OUTPUT: FoodItem[]

STEPS:
1. NORMALIZE text: lowercase, remove extra spaces
2. SPLIT by common delimiters: ",", "и", "с", "+"
3. FOR each food_phrase:
   a. SEARCH local food_database (Russian product names)
   b. IF exact match → use stored calories + category
   c. IF fuzzy match (Levenshtein < 3) → use with lower confidence
   d. IF no match → CALL AI API:
      prompt = "Определи калорийность и категорию: {food_phrase}. Ответь JSON."
      parse response
4. ASSIGN color category:
   caloric_density < 1.0 cal/g → green
   caloric_density 1.0-2.5 cal/g → yellow
   caloric_density > 2.5 cal/g → orange
5. RETURN FoodItem[]

COMPLEXITY: O(n) per item, AI API call if no DB match
```

### Algorithm: Insight Generator

```
INPUT: user_id
OUTPUT: Insight

STEPS:
1. LOAD user patterns (sorted by confidence DESC)
2. LOAD previously shown insights (avoid repeats)
3. SELECT insight_type based on rotation:
   - Day 1-3: pattern insights (from Pattern Detector)
   - Day 4-5: progress insights (compare this week vs last)
   - Day 6: CBT insight (link to relevant lesson)
   - Day 7: risk insight (weekly risk summary)
4. GENERATE insight text via LLM:
   prompt = f"""
   Ты — AI-коуч по питанию (CBT-подход). Русский язык.
   Паттерн пользователя: {pattern.description_ru}
   Данные: {relevant_food_entries}
   Создай короткий инсайт (2-3 предложения) и одну рекомендацию.
   Тон: поддерживающий, не осуждающий.
   """
5. SAVE insight to database
6. INCREMENT user.insights_received
7. IF user.insights_received > 3 AND user.subscription_status == "free":
     MARK insight as locked (paywall trigger)
8. RETURN insight
```

## API Contracts

### POST /api/auth/telegram
```
Request:
  Body: { init_data: string }  // raw initData string from Telegram WebApp

Response (200):
  { token: JWT, refresh_token: string, user: { id: UUID, first_name: string, onboarding_complete: boolean } }

Response (401):
  { error: { code: "INVALID_INIT_DATA", message: "Невалидная подпись Telegram" } }

Validation:
  1. Parse init_data as query string
  2. Extract "hash" field
  3. Sort remaining fields alphabetically
  4. Concatenate as "key=value\n" string
  5. HMAC-SHA256 with key = HMAC-SHA256("WebAppData", BOT_TOKEN)
  6. Compare calculated hash with received hash
  7. Check auth_date is not older than 300 seconds
  8. Find or create user by telegram_id from "user" field
```

### POST /api/onboarding/interview
```
Request:
  Headers: { Authorization: Bearer <token> }
  Body: { answers: [{ question_id: string, answer_id: string }] }

Response (200):
  { profile_initialized: true, cluster_id: string }
```

### POST /api/food/log
```
Request:
  Headers: { Authorization: Bearer <token> }
  Body: { raw_text: string, mood?: string, context?: string, logged_at?: Timestamp }

Response (201):
  { entry_id: UUID, parsed_items: FoodItem[], total_calories: number }
```

### GET /api/insights/today
```
Request:
  Headers: { Authorization: Bearer <token> }

Response (200):
  { insight: Insight, is_locked: boolean }

Response (200, locked):
  { insight: { title: "...", body: "Разблокируйте Premium..." }, is_locked: true }
```

### GET /api/patterns
```
Request:
  Headers: { Authorization: Bearer <token> }

Response (200):
  { patterns: Pattern[], risk_today: RiskScore }
```

### GET /api/lessons/{id}
```
Request:
  Headers: { Authorization: Bearer <token> }

Response (200):
  { lesson: CBTLesson, progress: { current: number, total: 20 } }

Response (403):
  { error: { code: "SUBSCRIPTION_REQUIRED", message: "Нужна подписка" } }
```

### POST /api/subscription/create
```
Request:
  Headers: { Authorization: Bearer <token> }
  Body: { plan: "standard" | "premium", payment_token: string }

Response (200):
  { subscription_id: UUID, expires_at: Timestamp }
```

### DELETE /api/subscription
```
Request:
  Headers: { Authorization: Bearer <token> }

Response (200):
  { cancelled: true, active_until: Timestamp }
```

### POST /api/invite/generate
```
Request:
  Headers: { Authorization: Bearer <token> }

Response (200):
  { invite_url: string, invite_code: string }
```

## State Transitions

### User Lifecycle
```
[Telegram User] → Open Mini App → [initData validated] → [Free User]
  → Complete AI Interview → [Active Free]
  → Receive 3 Insights → [Paywall Shown]
  → Subscribe (Stars/ЮKassa) → [Paid User]
  → Cancel → [Churned] → Win-back → [Paid User]
```

### Subscription States
```
[None] → Purchase → [Active] → Expire → [Expired] → Renew → [Active]
                   → Cancel → [Cancelled (active until period end)]
```

## Error Handling Strategy

| Category | HTTP Code | Response | Client Action |
|----------|:---------:|----------|---------------|
| Validation | 400 | `{ errors: [{field, message}] }` | Show field errors |
| Auth | 401 | `{ error: "UNAUTHORIZED" }` | Redirect to login |
| Forbidden | 403 | `{ error: "SUBSCRIPTION_REQUIRED" }` | Show paywall |
| Not Found | 404 | `{ error: "NOT_FOUND" }` | Show empty state |
| Rate Limit | 429 | `{ error: "RATE_LIMIT", retry_after: seconds }` | Retry with backoff |
| Server | 500 | `{ error: "INTERNAL" }` | Show generic error |
| AI Timeout | 504 | `{ error: "AI_TIMEOUT" }` | Show cached insight |
