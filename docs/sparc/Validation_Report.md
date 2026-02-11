# Requirements Testability Analysis: НутриМайнд

## Summary

- **Stories analyzed:** 11
- **Average score:** 74/100
- **Blocked (score <50):** 0
- **Needs rework (50-69):** 2
- **Ready with minor fixes (70-89):** 6
- **Excellent (90+):** 3

## Results

| Story | Title | Score | INVEST | SMART | Quality | Status |
|-------|-------|:-----:|:------:|:-----:|:-------:|--------|
| US-1.1 | Registration (Telegram initData) | 88/100 | 6/6 ✓ | 4/5 | 8/10 | ✅ READY |
| US-1.2 | AI Interview | 72/100 | 5/6 | 3/5 | 6/10 | ⚠️ REVIEW |
| US-2.1 | Text-based Food Logging | 85/100 | 6/6 ✓ | 4/5 | 7/10 | ✅ READY |
| US-2.2 | Contextual Logging | 78/100 | 6/6 ✓ | 3/5 | 6/10 | ✅ READY |
| US-3.1 | Pattern Discovery | 65/100 | 4/6 | 3/5 | 5/10 | 🔶 REWORK |
| US-3.2 | Daily AI Insights | 68/100 | 5/6 | 3/5 | 5/10 | 🔶 REWORK |
| US-3.3 | Risk Prediction | 82/100 | 6/6 ✓ | 4/5 | 7/10 | ✅ READY |
| US-4.1 | Daily CBT Mini-Lesson | 90/100 | 6/6 ✓ | 5/5 ✓ | 8/10 | ✅ READY |
| US-5.1 | Freemium Paywall | 92/100 | 6/6 ✓ | 5/5 ✓ | 8/10 | ✅ READY |
| US-5.2 | Subscription Management | 91/100 | 6/6 ✓ | 5/5 ✓ | 8/10 | ✅ READY |
| US-6.1 | Invite a Friend | 75/100 | 5/6 | 4/5 | 6/10 | ⚠️ REVIEW |

---

## Detailed Analysis

### US-1.1: Registration (Telegram initData) — 88/100 ✅ READY

#### INVEST Analysis (46/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | No dependencies, first action in flow |
| Negotiable | 8/8 | ✓ | Describes outcome (authenticated), not implementation |
| Valuable | 10/10 | ✓ | Clear benefit: "zero friction" |
| Estimable | 8/8 | ✓ | Well-defined scope: initData → JWT |
| Small | 8/8 | ✓ | Single endpoint + frontend init |
| Testable | 4/8 | ~ | AC mentions HMAC validation but no specific timing |

#### SMART Analysis (24/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | Telegram initData, HMAC, JWT — all specific |
| Measurable | 6/8 | ~ | Missing response time target |
| Achievable | 6/6 | ✓ | Standard TWA auth pattern |
| Relevant | 5/5 | ✓ | Core prerequisite for all features |
| Time-bound | 1/5 | ✗ | No timing specified for auth flow |

#### Quality (8/10)
- Traceability: 5/5 — Links to auth flow in Architecture.md
- Completeness: 3/5 — Happy path covered, missing error scenarios in AC

#### Suggestions
- Add AC: "Auth completes within 500ms including HMAC validation"
- Add AC: "Given expired initData (>300s), return 401 with INVALID_INIT_DATA"

---

### US-1.2: AI Interview — 72/100 ⚠️ REVIEW

#### INVEST Analysis (38/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 4/8 | ~ | Depends on US-1.1 (registration complete) |
| Negotiable | 8/8 | ✓ | Open to discussion on question format |
| Valuable | 10/10 | ✓ | Clear benefit: "AI can start building pattern profile" |
| Estimable | 8/8 | ✓ | 2-3 questions, predefined options |
| Small | 8/8 | ✓ | Single screen flow |
| Testable | 0/8 | ✗ | AC says "answers are saved" but no verification criteria |

#### SMART Analysis (20/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 4/6 | ~ | "2-3 questions" — should be exact: 2 |
| Measurable | 4/8 | ~ | "predefined options" — how many? |
| Achievable | 6/6 | ✓ | Simple form flow |
| Relevant | 5/5 | ✓ | Feeds AI profile |
| Time-bound | 1/5 | ✗ | No completion time target |

#### Quality (6/10)
- Traceability: 3/5 — Referenced in PRD but no direct test link
- Completeness: 3/5 — Happy path only, no error/edge cases

#### Suggestions
- **Fix "2-3 questions"** → "2 questions" (per PRD)
- Add AC: "Given user completes both questions, profile is created within 2s"
- Add AC: "Given user closes app mid-interview, progress is saved and resumed on next open"
- Add AC: "Each question has 4-6 predefined answer options"

---

### US-2.1: Text-based Food Logging — 85/100 ✅ READY

#### INVEST Analysis (46/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | Can work without patterns/insights |
| Negotiable | 8/8 | ✓ | Describes outcome, not parsing implementation |
| Valuable | 10/10 | ✓ | Core value: track eating |
| Estimable | 8/8 | ✓ | Clear scope: input → parse → save |
| Small | 8/8 | ✓ | Single feature |
| Testable | 4/8 | ~ | "Estimated calories" — how accurate? |

#### SMART Analysis (23/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | Example input "борщ с хлебом", green/yellow/orange |
| Measurable | 5/8 | ~ | Categories defined, but calorie accuracy not specified |
| Achievable | 6/6 | ✓ | DB lookup + AI fallback |
| Relevant | 5/5 | ✓ | Core data collection |
| Time-bound | 1/5 | ✗ | No parsing time specified |

#### Quality (7/10)
- Traceability: 4/5 — Links to Food Parser algorithm in Pseudocode.md
- Completeness: 3/5 — Missing error handling in AC

#### Suggestions
- Add AC: "Food text is parsed within 3 seconds"
- Add AC: "If AI parser fails, entry is saved as raw text for manual review"
- Specify: "Calorie estimate accuracy target: ±20% for DB matches"

---

### US-2.2: Contextual Logging — 78/100 ✅ READY

#### INVEST Analysis (44/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 6/8 | ~ | Extends US-2.1 (food logging) |
| Negotiable | 8/8 | ✓ | UI is negotiable |
| Valuable | 10/10 | ✓ | "AI can find correlations" |
| Estimable | 8/8 | ✓ | Dropdown/buttons for mood + context |
| Small | 8/8 | ✓ | Extension to existing form |
| Testable | 4/8 | ~ | "Used by AI Pattern Detector" — not directly testable |

#### SMART Analysis (18/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | Exact emoji mapping and context options |
| Measurable | 4/8 | ~ | How to verify "used by AI"? |
| Achievable | 6/6 | ✓ | Simple enum fields |
| Relevant | 5/5 | ✓ | Feeds pattern detection |
| Time-bound | 0/5 | ✗ | No timing |

#### Quality (6/10)
- Traceability: 3/5 — Links to Pattern Detector algorithm
- Completeness: 3/5 — No error handling specified

#### Suggestions
- Add AC: "If mood is not selected, entry is saved with mood=null"
- Add AC: "Context and mood selections are persisted and shown in food history"
- Add testable AC: "After 3+ entries with mood, mood column appears in pattern analysis"

---

### US-3.1: Pattern Discovery — 65/100 🔶 REWORK

#### INVEST Analysis (34/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 4/8 | ~ | Depends on 3+ days of food logs (US-2.1) |
| Negotiable | 8/8 | ✓ | Pattern types are flexible |
| Valuable | 10/10 | ✓ | Core differentiator: "understand WHY" |
| Estimable | 4/8 | ~ | "at least 1 pattern" — what if data doesn't support any? |
| Small | 8/8 | ✓ | Single algorithm run |
| Testable | 0/8 | ✗ | **"Confidence percentage" — no threshold defined. "Simple Russian" — subjective** |

#### SMART Analysis (17/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 2/6 | ✗ | **"Simple Russian language" is vague** |
| Measurable | 3/8 | ✗ | **No accuracy/recall targets** |
| Achievable | 6/6 | ✓ | Algorithm defined in Pseudocode.md |
| Relevant | 5/5 | ✓ | Core product value |
| Time-bound | 1/5 | ✗ | No generation time specified |

#### Quality (5/10)
- Traceability: 3/5 — Algorithm exists but no test specification
- Completeness: 2/5 — Happy path only

#### Issues (Must Fix)
1. **"Simple Russian language"** → Replace with: "Pattern description is ≤50 words, uses no medical/technical terms"
2. **No accuracy target** → Add: "Pattern detection recall ≥70% on labeled test dataset"
3. **No timing** → Add: "Pattern analysis completes within 30 seconds"
4. **Missing edge case** → Add: "Given fewer than 10 food entries, show cold-start cluster patterns with disclaimer 'Предварительный анализ'"

#### Suggested Rewrite
```
Acceptance Criteria:
Given I have logged food for 3+ days (minimum 10 entries)
When the AI Pattern Detector runs (daily at 03:00 or triggered by 10th entry)
Then it identifies 1-5 patterns with confidence ≥ 0.5
And each pattern description is ≤ 50 words in plain Russian
And each pattern includes a confidence percentage
And the detection completes within 30 seconds

Given I have fewer than 10 food entries
When the Pattern Detector runs
Then it shows cluster-based patterns with disclaimer "Предварительный анализ"
And confidence is capped at 0.4
```

---

### US-3.2: Daily AI Insights — 68/100 🔶 REWORK

#### INVEST Analysis (38/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 4/8 | ~ | Depends on pattern detection (US-3.1) |
| Negotiable | 8/8 | ✓ | Insight format is flexible |
| Valuable | 10/10 | ✓ | Daily value delivery |
| Estimable | 8/8 | ✓ | LLM call + template |
| Small | 8/8 | ✓ | Single insight per day |
| Testable | 0/8 | ✗ | **"Personalized" and "actionable" are vague and unmeasurable** |

#### SMART Analysis (17/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 2/6 | ✗ | **"Personalized" — how measured? "Actionable" — subjective** |
| Measurable | 3/8 | ✗ | **No quality metric** |
| Achievable | 6/6 | ✓ | LLM generation proven |
| Relevant | 5/5 | ✓ | Core engagement driver |
| Time-bound | 1/5 | ✗ | No generation/delivery time |

#### Quality (5/10)
- Traceability: 3/5 — Links to Insight Generator algorithm
- Completeness: 2/5 — No error or edge case handling

#### Issues (Must Fix)
1. **"Personalized"** → Replace with: "Insight references at least 1 specific food entry or pattern from user's data"
2. **"Actionable recommendation"** → Replace with: "Includes exactly 1 concrete action (verb + object + timing)"
3. **No quality gate** → Add: "User can rate insight (👍/👎), target: ≥60% positive"
4. **No timing** → Add: "Insight pre-generated by 06:00 daily, served from cache in <100ms"

#### Suggested Rewrite
```
Acceptance Criteria:
Given I am a registered user with 3+ days of data
When I open the dashboard
Then I see today's AI insight card within 100ms (pre-generated)
And the insight references at least 1 specific entry or pattern from my data
And it includes exactly 1 concrete recommendation (verb + object + timing)
And insight text is 2-4 sentences (≤ 100 words)

Given the AI service is unavailable
When I open the dashboard
Then I see the most recent cached insight with note "обновляется..."
```

---

### US-3.3: Risk Prediction — 82/100 ✅ READY

#### INVEST Analysis (44/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 6/8 | ~ | Depends on patterns (US-3.1) |
| Negotiable | 8/8 | ✓ | Alert format negotiable |
| Valuable | 10/10 | ✓ | Proactive prevention |
| Estimable | 8/8 | ✓ | Algorithm defined |
| Small | 8/8 | ✓ | Score calculation + notification |
| Testable | 4/8 | ~ | "High-risk" defined but push timing needs specificity |

#### SMART Analysis (23/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | "Trigger Alert", push notification, CBT micro-exercise |
| Measurable | 5/8 | ~ | "30 min before" is good, but risk threshold not in AC |
| Achievable | 6/6 | ✓ | Risk algorithm defined |
| Relevant | 5/5 | ✓ | Core differentiator |
| Time-bound | 1/5 | ✗ | Push delivery SLA not specified |

#### Quality (7/10)
- Traceability: 4/5 — Links to Risk Predictor algorithm
- Completeness: 3/5 — Missing: what if no patterns yet?

#### Suggestions
- Add AC: "Push notification delivered within 60 seconds of risk threshold crossing"
- Add AC: "Given no patterns detected, risk feature shows 'Собираю данные...' placeholder"
- Specify: "Risk levels: low (<0.3), medium (0.3-0.6), high (>0.6)"

---

### US-4.1: Daily CBT Mini-Lesson — 90/100 ✅ READY

#### INVEST Analysis (48/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | Can function without other features |
| Negotiable | 8/8 | ✓ | Lesson content/format flexible |
| Valuable | 10/10 | ✓ | Core CBT therapy delivery |
| Estimable | 8/8 | ✓ | 20 lessons, 3-7 min each |
| Small | 8/8 | ✓ | Content delivery + progress |
| Testable | 6/8 | ✓ | "3-7 minutes", "X/20 progress", "relevant to patterns" |

#### SMART Analysis (26/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | "Text + interactive elements", duration defined |
| Measurable | 6/8 | ✓ | X/20 progress, 3-7 min duration |
| Achievable | 6/6 | ✓ | Static content + simple tracking |
| Relevant | 5/5 | ✓ | Core therapy component |
| Time-bound | 3/5 | ~ | Duration defined, but no load time |

#### Quality (8/10)
- Traceability: 4/5 — Links to CBTLesson data structure
- Completeness: 4/5 — Covers progress, duration, relevance

#### Suggestions (Minor)
- Add AC: "Lesson content loads within 1 second"
- Clarify: "relevant to my identified patterns" → "lesson tagged with at least 1 of user's active pattern types"

---

### US-5.1: Freemium Paywall — 92/100 ✅ READY

#### INVEST Analysis (50/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | Standalone paywall component |
| Negotiable | 8/8 | ✓ | UI and copy negotiable |
| Valuable | 10/10 | ✓ | Revenue driver |
| Estimable | 8/8 | ✓ | Well-scoped UI + payment integration |
| Small | 8/8 | ✓ | Single screen + API |
| Testable | 8/8 | ✓ | "After 3 insights", exact price, dismiss option |

#### SMART Analysis (26/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | "3 insights", "499 ₽/мес", "Premium includes" |
| Measurable | 8/8 | ✓ | Exact trigger count, exact price |
| Achievable | 6/6 | ✓ | Standard paywall pattern |
| Relevant | 5/5 | ✓ | Core monetization |
| Time-bound | 1/5 | ✗ | No page load or payment processing time |

#### Quality (8/10)
- Traceability: 4/5 — Links to subscription state machine
- Completeness: 4/5 — Covers trigger, content, subscribe, dismiss

#### Suggestions (Minor)
- Add AC: "Payment processing completes within 10 seconds"
- Add AC: "Given payment fails, show error and retry option"

---

### US-5.2: Subscription Management — 91/100 ✅ READY

#### INVEST Analysis (50/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | Standalone settings page |
| Negotiable | 8/8 | ✓ | UI flexible |
| Valuable | 10/10 | ✓ | Trust builder: "never feel trapped" |
| Estimable | 8/8 | ✓ | Settings page + cancel API |
| Small | 8/8 | ✓ | Single page |
| Testable | 8/8 | ✓ | "1 tap cancel", "effective immediately", "email confirmation" |

#### SMART Analysis (25/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 6/6 | ✓ | "1 tap", "no dark patterns", "immediately" |
| Measurable | 6/8 | ✓ | Tap count, immediate effect |
| Achievable | 6/6 | ✓ | Standard pattern |
| Relevant | 5/5 | ✓ | Addresses Noom's #1 complaint |
| Time-bound | 2/5 | ~ | "Immediately" is specific enough |

#### Quality (8/10)
- Traceability: 4/5 — Links to subscription states in Pseudocode.md
- Completeness: 4/5 — Happy path + cancellation covered

#### Suggestions (Minor)
- Clarify: "email confirmation" → Since Telegram Mini App, change to "Telegram message confirmation" (no email)
- Add AC: "Subscription page loads within 1 second showing current plan and renewal date"

---

### US-6.1: Invite a Friend — 75/100 ⚠️ REVIEW

#### INVEST Analysis (38/50)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Independent | 8/8 | ✓ | Standalone referral feature |
| Negotiable | 8/8 | ✓ | Invite mechanism flexible |
| Valuable | 10/10 | ✓ | Growth driver + social proof |
| Estimable | 8/8 | ✓ | Link generation + tracking |
| Small | 4/8 | ~ | Involves both inviter + invitee flows |
| Testable | 0/8 | ✗ | **"Select a contact" implies native contact access (not available in TWA)** |

#### SMART Analysis (22/30)

| Criterion | Score | Pass | Notes |
|-----------|:-----:|:----:|-------|
| Specific | 4/6 | ~ | "Personalized invite link" — what's personalized? |
| Measurable | 6/8 | ✓ | "1 week Premium free" is measurable |
| Achievable | 4/6 | ~ | **Contact selection not available in TWA — need Telegram share** |
| Relevant | 5/5 | ✓ | Growth mechanism |
| Time-bound | 3/5 | ~ | "1 week" is time-bound for reward |

#### Quality (6/10)
- Traceability: 3/5 — Links to invite API in Pseudocode.md
- Completeness: 3/5 — Missing: what if invitee already registered? Link expiration?

#### Issues (Must Fix)
1. **"Select a contact"** → In Telegram Mini App, use `Telegram.WebApp.switchInlineQuery()` or share link via Telegram native share
2. **"Personalized invite link"** → Specify: "Link contains invite_code, e.g., t.me/nutrimind_bot?start=invite_ABC123"
3. **Missing edge cases:** invitee already registered, self-invite, expired link

#### Suggested Rewrite
```
Acceptance Criteria:
Given I am on the invite screen
When I tap "Пригласить"
Then a Telegram share dialog opens with pre-filled message + deep link
And the deep link format is t.me/nutrimind_bot?start=invite_{CODE}

Given my friend opens the invite link and completes registration
Then both users receive 7 days of Premium subscription
And a confirmation message is sent to both via Telegram Bot

Given the invitee is already registered
Then the invite is rejected with message "Пользователь уже зарегистрирован"
And no Premium reward is granted
```

---

## Flagged Vague Terms

| Term | Found In | Suggested Replacement |
|------|----------|-----------------------|
| "simple Russian language" | US-3.1 | "≤50 words, no medical/technical terms" |
| "personalized" | US-3.2 | "references at least 1 specific user data point" |
| "actionable recommendation" | US-3.2 | "1 concrete action: verb + object + timing" |
| "select a contact" | US-6.1 | "Telegram native share dialog" |
| "personalized invite link" | US-6.1 | "deep link: t.me/bot?start=invite_{CODE}" |
| "email confirmation" | US-5.2 | "Telegram Bot message confirmation" |

## Cross-Cutting Concerns Not Covered

| Concern | Status | Recommendation |
|---------|--------|----------------|
| Offline behavior | ❌ Missing | Add US for offline food logging queue |
| Data export (152-ФЗ) | ❌ Missing | Add US: "As a user, I want to export my data as JSON" |
| Data deletion (152-ФЗ) | ❌ Missing | Add US: "As a user, I want to delete my account and all data" |
| Error states (global) | ⚠️ Partial | Defined in Pseudocode.md but not in user stories |
| Accessibility | ❌ Missing | Telegram handles most, but contrast/font size should be noted |

## Recommendations

### Priority Fixes (Before Development)

1. **US-3.1 (Pattern Discovery):** Add measurable accuracy target, timing, and cold-start AC → rescore to ~80
2. **US-3.2 (Daily AI Insights):** Define "personalized" and "actionable" measurably, add timing → rescore to ~80
3. **US-6.1 (Invite):** Fix contact selection for TWA, add deep link format → rescore to ~85
4. **US-5.2:** Change "email confirmation" to "Telegram message" (no email in TWA flow)

### New Stories Needed (152-ФЗ Compliance)

5. **US-7.1: Data Export** — "As a user, I want to download all my data as JSON within 24 hours of request"
6. **US-7.2: Account Deletion** — "As a user, I want to delete my account and all associated data permanently within 72 hours"

### After Fixes: Projected Scores

| Story | Current | Projected |
|-------|:-------:|:---------:|
| US-3.1 | 65 | ~82 |
| US-3.2 | 68 | ~80 |
| US-6.1 | 75 | ~85 |
| **Average** | **74** | **~82** |
