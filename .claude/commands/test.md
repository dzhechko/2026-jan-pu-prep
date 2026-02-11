# /test — Run Tests

Run tests for the project. Supports targeting specific areas or running the full suite.

## Usage
- `/test` — Run full test suite (backend + frontend)
- `/test backend` — Run backend tests only
- `/test frontend` — Run frontend tests only
- `/test <feature-name>` — Run tests for a specific feature
- `/test coverage` — Run with coverage report

## Execution

### Full Suite
```bash
# Backend
docker compose exec api pytest --cov=app --cov-report=term-missing -v

# Frontend
docker compose exec frontend npm run test -- --coverage
```

### Backend Only
```bash
docker compose exec api pytest backend/tests/ -v --tb=short
```

### Frontend Only
```bash
docker compose exec frontend npm run test
```

### Specific Feature
```bash
# Backend
docker compose exec api pytest backend/tests/test_<feature>.py -v

# Frontend
docker compose exec frontend npm run test -- --grep <feature>
```

### Coverage Report
```bash
docker compose exec api pytest --cov=app --cov-report=html
# Open backend/htmlcov/index.html

docker compose exec frontend npm run test -- --coverage
```

## Test Quality Checks
After running tests, verify:
1. No test failures
2. Coverage meets targets (80% backend, 70% frontend)
3. No skipped tests without reason
4. AI quality tests pass with labeled datasets

## BDD Scenario Mapping
When writing new tests, reference `docs/sparc/BDD_Scenarios.feature` for expected behavior. Each `@critical` scenario MUST have a corresponding test.
