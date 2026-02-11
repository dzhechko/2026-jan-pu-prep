# /feature — Feature Development Lifecycle

Start structured development of a feature following the Feature Lifecycle: Plan → Implement → Test → Review → Ship.

## Usage
`/feature <feature-name>`

Example: `/feature food-logging`, `/feature telegram-auth`, `/feature paywall`

## Process

### Step 1: Plan
1. Read the relevant user stories from `docs/sparc/Specification.md`
2. Read the algorithm/API from `docs/sparc/Pseudocode.md`
3. Read BDD scenarios from `docs/sparc/BDD_Scenarios.feature`
4. Read edge cases from `docs/sparc/Refinement.md`
5. Use the `planner` agent to create implementation plan
6. Create feature branch: `git checkout -b feat/<feature-name>`

### Step 2: Implement
Follow the plan from Step 1:
1. Database changes (migration + model) if needed
2. Backend (schema → service → router → register)
3. Frontend (entity → API client → feature component → route)
4. Follow all rules from CLAUDE.md, security.md, coding-style.md

### Step 3: Test
1. Write tests matching BDD scenarios
2. Backend: `pytest backend/tests/test_<feature>.py -v`
3. Frontend: `cd frontend && npm run test -- --grep <feature>`
4. Check coverage: `pytest --cov=app`

### Step 4: Review
1. Use `code-reviewer` agent to review all changes
2. Run linters: `ruff check backend/app/` and `cd frontend && npm run lint`
3. Fix all CRITICAL and WARNING issues

### Step 5: Ship
1. Commit: `git add <files> && git commit -m "feat(<scope>): <description>"`
2. Verify Docker build: `docker compose build`
3. Capture insights if any learned during development
4. Print summary of what was built and tested

## Feature Map

| Feature Name | User Stories | Key Files |
|-------------|-------------|-----------|
| telegram-auth | US-1.1 | middleware/telegram_auth.py, routers/auth.py |
| onboarding | US-1.2 | routers/onboarding.py, features/onboarding/ |
| food-logging | US-2.1, US-2.2 | ai/food_parser.py, routers/food.py, features/food-log/ |
| pattern-detector | US-3.1 | ai/pattern_detector.py, workers/pattern_worker.py |
| insights | US-3.2 | ai/insight_generator.py, routers/insights.py, features/insights/ |
| risk-predictor | US-3.3 | ai/risk_predictor.py, routers/patterns.py |
| cbt-lessons | US-4.1 | routers/lessons.py, features/lessons/ |
| paywall | US-5.1, US-5.2 | routers/payments.py, features/paywall/ |
| invite | US-6.1 | routers/invite.py, features/invite/ |
| data-privacy | US-7.1, US-7.2 | routers/profile.py, features/profile/ |
