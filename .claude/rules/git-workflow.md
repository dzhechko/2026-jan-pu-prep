# Git Workflow — НутриМайнд

## Branch Strategy
- `main` — production-ready, protected
- `develop` — integration branch (optional for solo dev)
- `feat/<name>` — feature branches from main
- `fix/<name>` — bugfix branches from main
- `chore/<name>` — maintenance tasks

## Commit Convention
Format: `<type>(<scope>): <description>`

Types:
- `feat` — new feature
- `fix` — bug fix
- `refactor` — code restructuring without behavior change
- `test` — adding or updating tests
- `docs` — documentation changes
- `chore` — build, deps, config changes
- `style` — formatting only (no logic change)

Scopes: `frontend`, `backend`, `bot`, `infra`, `docs`

Examples:
- `feat(backend): add telegram initData validation endpoint`
- `fix(frontend): handle expired JWT in API interceptor`
- `chore(infra): add redis to docker-compose`

## Rules
- Never force push to main
- Never commit secrets, .env files, or API keys
- Never commit with failing linter or tests
- Atomic commits: one logical change per commit
- Write meaningful commit messages (what + why, not just what)

## PR Convention
- Title: same as primary commit message
- Body: Summary (1-3 bullets) + Test Plan
- Squash merge to main
- Delete branch after merge
