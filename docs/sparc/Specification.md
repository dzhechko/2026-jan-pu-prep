# Specification: НутриМайнд

## User Stories (MVP)

### Epic 1: Onboarding & AI Interview

**US-1.1: Registration (Telegram Mini App)**
```
As a Telegram user,
I want to open the Mini App and be automatically authenticated,
So that I can start using the app with zero friction.

Acceptance Criteria:
Given I open НутриМайнд bot in Telegram and tap "Открыть"
When the Mini App loads
Then my Telegram initData is sent to the backend
And the backend validates HMAC signature
And a JWT token is issued
And I am redirected to AI Interview (if first time) or Dashboard (if returning)
```

**US-1.2: AI Interview**
```
As a new user,
I want to answer 2 questions about my eating habits,
So that the AI can start building my pattern profile.

Acceptance Criteria:
Given I have completed Telegram authentication and onboarding_complete is false
When I am presented with 2 interview questions (each with 4-6 predefined options)
Then I select answers and tap "Готово"
And my answers are saved to ai_profiles.interview_answers
And a cluster_id is assigned based on my answers within 2 seconds
And I am redirected to the dashboard with prompt "Запишите первый приём пищи"

Given I close the app mid-interview
Then my progress is saved and resumed on next open
```

### Epic 2: Food Logging

**US-2.1: Text-based Food Logging**
```
As a user,
I want to log what I ate by typing in Russian,
So that the AI can track my eating patterns.

Acceptance Criteria:
Given I am on the dashboard
When I tap "+" and type "борщ с хлебом"
Then the AI parses the food items
And shows estimated calories and food category (green/yellow/orange)
And the entry is saved with timestamp
```

**US-2.2: Contextual Logging**
```
As a user,
I want to log my mood and context when eating,
So that the AI can find correlations between emotions and eating.

Acceptance Criteria:
Given I am logging a meal
When I optionally select mood (😊😐😟😡😴) and context (дом/работа/улица/ресторан)
Then the mood and context are saved with the food entry
And used by AI Pattern Detector
```

### Epic 3: AI Pattern Detection

**US-3.1: Pattern Discovery**
```
As a user,
I want the AI to find my personal overeating patterns,
So that I understand WHY I overeat, not just what I eat.

Acceptance Criteria:
Given I have logged food for 3+ days (minimum 10 entries)
When the AI Pattern Detector runs (daily at 03:00 or triggered by 10th entry)
Then it identifies 1-5 patterns with confidence ≥ 0.5
And each pattern description is ≤ 50 words in plain Russian (no medical/technical terms)
And each pattern includes a confidence percentage
And the detection completes within 30 seconds
And the pattern appears on my Dashboard

Given I have fewer than 10 food entries
When the Pattern Detector runs
Then it shows cluster-based patterns with disclaimer "Предварительный анализ"
And confidence is capped at 0.4

Quality target: pattern detection recall ≥ 70% on labeled test dataset (50 profiles)
```

**US-3.2: Daily AI Insights**
```
As a user,
I want to receive a daily AI insight based on my data,
So that I learn something new about my habits each day.

Acceptance Criteria:
Given I am a registered user with 3+ days of data
When I open the dashboard
Then I see today's AI insight card within 100ms (pre-generated at 06:00, served from cache)
And the insight references at least 1 specific food entry or pattern from my data
And it includes exactly 1 concrete recommendation (verb + object + timing)
And insight text is 2-4 sentences (≤ 100 words)

Given the AI service is unavailable
When I open the dashboard
Then I see the most recent cached insight with note "Обновляется..."

Quality target: ≥ 60% user-rated positive (👍) on insight quality
```

**US-3.3: Risk Prediction (Trigger of the Day)**
```
As a user,
I want to know when I'm at high risk of overeating today,
So that I can prepare and prevent a binge.

Acceptance Criteria:
Given the AI has identified my patterns
When a high-risk time window is predicted
Then I see a "Trigger Alert" on the dashboard
And receive a push notification 30 min before the risk window
And the alert includes a CBT micro-exercise to prevent the binge
```

### Epic 4: CBT Lessons

**US-4.1: Daily CBT Mini-Lesson**
```
As a user,
I want a 5-minute daily CBT lesson,
So that I learn to change my relationship with food.

Acceptance Criteria:
Given I am a paid subscriber (or within free 3-insight limit)
When I tap on today's lesson
Then I see a lesson with text + interactive elements
And the lesson is relevant to my identified patterns
And it takes 3-7 minutes to complete
And my progress is saved (X/20 lessons)
```

### Epic 5: Paywall

**US-5.1: Freemium Paywall**
```
As a free user,
I want to experience 3 AI insights before being asked to pay,
So that I see the value before committing.

Acceptance Criteria:
Given I have received 3 AI insights
When I try to access the 4th insight
Then I see the paywall screen with pricing (499 ₽/мес)
And I can see what Premium includes
And I can subscribe via in-app purchase
And I can dismiss and continue with limited features
```

**US-5.2: Subscription Management**
```
As a paid subscriber,
I want to manage my subscription easily,
So that I never feel trapped (unlike Noom).

Acceptance Criteria:
Given I am a paid subscriber
When I go to Settings → Subscription
Then I see my current plan and renewal date
And I can cancel in 1 tap (no dark patterns)
And cancellation is effective immediately (no hidden charges)
And I receive Telegram Bot message confirming cancellation
```

### Epic 6: Invite System

**US-6.1: Invite a Friend**
```
As a user,
I want to invite a friend for paired AI analysis,
So that we can support each other.

Acceptance Criteria:
Given I am on the invite screen
When I tap "Пригласить"
Then a Telegram share dialog opens with pre-filled message and deep link
And the deep link format is t.me/nutrimind_bot?start=invite_{CODE}

Given my friend opens the invite link and completes registration
Then both users receive 7 days of Premium subscription
And both receive Telegram Bot confirmation message

Given the invitee is already registered
Then the invite is rejected with message "Пользователь уже зарегистрирован"
And no Premium reward is granted
```

### Epic 7: Data Privacy (152-ФЗ)

**US-7.1: Data Export**
```
As a user,
I want to download all my data,
So that I exercise my right of access under 152-ФЗ.

Acceptance Criteria:
Given I am an authenticated user
When I tap "Экспорт данных" in Settings
Then within 24 hours I receive a Telegram message with JSON file
And the file contains: profile, food entries, patterns, insights, lesson progress
```

**US-7.2: Account Deletion**
```
As a user,
I want to delete my account and all associated data permanently,
So that I exercise my right to erasure under 152-ФЗ.

Acceptance Criteria:
Given I am an authenticated user
When I tap "Удалить аккаунт" in Settings and confirm by typing "УДАЛИТЬ"
Then all my data is cascade-deleted from all tables within 72 hours
And my active subscription is cancelled
And I receive final Telegram confirmation
And I am logged out of the Mini App
```

## Feature Priority Matrix

| Feature | Impact | Effort | Priority | MVP? |
|---------|:------:|:------:|:--------:|:----:|
| Registration (Telegram initData) | High | Low | P0 | Yes |
| AI Interview (2 questions) | High | Low | P0 | Yes |
| Food logging (text) | High | Medium | P0 | Yes |
| AI Pattern Detector | Critical | High | P0 | Yes |
| AI Daily Insights | Critical | Medium | P0 | Yes |
| Risk Predictor | High | Medium | P0 | Yes |
| CBT Lessons (20) | High | Medium | P0 | Yes |
| Paywall + payments | Critical | Medium | P0 | Yes |
| Push notifications | Medium | Low | P1 | Yes |
| User profile | Medium | Low | P0 | Yes |
| Invite system | Medium | Medium | P1 | Yes |
| Data export (152-ФЗ) | High | Low | P0 | Yes |
| Account deletion (152-ФЗ) | High | Low | P0 | Yes |
| Photo food logging | Medium | High | P2 | No |
| AI Coach (chat) | High | High | P1 | No |
| Community/groups | Medium | High | P2 | No |

## Non-Functional Specifications

### Performance
- API: < 200ms p95 for CRUD operations
- AI Insight generation: < 5 seconds
- App cold start: < 3 seconds
- Food search: < 500ms

### Security
- Authentication: Telegram initData HMAC-SHA256 validation → JWT + refresh tokens
- No password needed (Telegram identity)
- Data at rest: AES-256 (PostgreSQL TDE)
- Data in transit: TLS 1.3
- PII: never in logs, masked in admin panels
- 152-ФЗ: data stored on RU-based servers

### Scalability
- Horizontal: stateless API behind load balancer
- Database: read replicas for analytics queries
- AI: async job queue for pattern detection
- Target: 10,000 concurrent users on single VPS → scale to 3 VPS at 50K users
