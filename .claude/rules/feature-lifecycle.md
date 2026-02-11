# Feature Lifecycle Rule

## Purpose
Enforce structured feature development through a consistent lifecycle: Plan → Implement → Test → Review → Ship.

## Lifecycle Phases

### 1. Plan
- Read relevant SPARC docs (Specification, Pseudocode, Architecture)
- Identify affected files and components
- Check BDD scenarios in `docs/sparc/BDD_Scenarios.feature`
- Create feature branch: `feat/<feature-name>`

### 2. Implement
- Follow implementation priority from CLAUDE.md
- Backend first (models → schemas → services → routers)
- Frontend second (entities → shared → features)
- Write code following coding-style.md rules
- Follow security.md rules for all new endpoints

### 3. Test
- Write unit tests alongside implementation (TDD preferred)
- Backend: pytest with async fixtures
- Frontend: vitest with React Testing Library
- Run full test suite before marking complete
- Check coverage targets: 80% backend, 70% frontend

### 4. Review
- Run linters: `ruff check` (backend), `npm run lint` (frontend)
- Check for security issues (no hardcoded secrets, input validation)
- Verify edge cases from Refinement.md are handled
- Self-review diff before committing

### 5. Ship
- Commit with conventional commit message
- Verify Docker build succeeds
- Update docs/insights.md if any learnings captured
- Mark feature as complete

## Rules
- Never skip the Plan phase for P0 features
- Every new API endpoint needs at least 3 tests (happy path, error, edge case)
- Every new frontend component needs at least 1 test
- Features touching AI pipeline need quality test with labeled data
