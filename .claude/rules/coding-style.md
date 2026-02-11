# Coding Style — НутриМайнд

## Python (Backend)
- Python 3.12+, strict type hints on all functions
- Formatter: ruff format. Linter: ruff check
- Async by default: use `async def` for all route handlers and service methods
- SQLAlchemy 2.0 style: `select()` not `query()`, async sessions
- Pydantic v2 models for all request/response schemas
- Naming: snake_case for files, functions, variables. PascalCase for classes
- Imports: stdlib → third-party → local (ruff handles ordering)
- No bare except. Always specify exception type
- Docstrings only for public API functions (Google style)

## TypeScript (Frontend)
- Strict TypeScript: `strict: true` in tsconfig
- No `any` type. Use `unknown` if type is truly unknown
- React: functional components only, hooks for state and effects
- Naming: camelCase for variables/functions, PascalCase for components/types
- File naming: kebab-case (e.g., `food-log-form.tsx`)
- Exports: named exports preferred over default exports
- Props: define interface for every component props

## API Conventions
- Base path: `/api/v1/`
- Request/response body: camelCase JSON
- Database columns: snake_case (Pydantic alias_generator handles conversion)
- HTTP methods: GET (read), POST (create), PUT (full update), PATCH (partial), DELETE
- Pagination: `?limit=20&offset=0`
- Timestamps: ISO 8601 UTC (`2026-01-15T10:30:00Z`)
- Error format: `{ "error": { "code": "ERROR_CODE", "message": "Human readable" } }`

## SQL / Database
- Table names: plural snake_case (`food_entries`, not `food_entry`)
- Primary keys: `id UUID DEFAULT gen_random_uuid()`
- Foreign keys: `{table_singular}_id` (e.g., `user_id`)
- Timestamps: always `TIMESTAMPTZ` (with timezone)
- Indexes: name pattern `idx_{table}_{columns}`
- One Alembic migration per logical change, descriptive name

## Git
- Branch naming: `feat/short-description`, `fix/short-description`, `chore/short-description`
- Commit messages: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
- One logical change per commit
- No commits with failing tests
