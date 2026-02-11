# /myinsights — View Development Insights

Display captured development insights from the project's living knowledge base.

## Usage
- `/myinsights` — Show all insights
- `/myinsights <category>` — Filter by category
- `/myinsights recent` — Show last 10 insights

## Categories
- `bug-fix` — Root cause analysis of resolved bugs
- `architecture` — Design decisions and rationale
- `pattern` — Reusable patterns discovered
- `workaround` — Library/framework limitations and solutions
- `performance` — Optimization discoveries with metrics
- `tma-specific` — Telegram Mini App specific learnings

## Execution

1. Read `docs/insights.md`
2. If category filter provided, show only matching entries
3. Display insights in reverse chronological order
4. Show total count and category breakdown

## Adding Insights

Insights are captured automatically during development (see `.claude/rules/insights-capture.md`).

To manually add:
```
Append to docs/insights.md:

### [YYYY-MM-DD] Title
**Category:** category-name
**Context:** Brief situation description
**Insight:** What was learned
**Tags:** #tag1 #tag2
```

## Why This Matters
- Prevents re-discovering the same solutions
- Builds institutional knowledge for the project
- Helps onboard new contributors faster
- Captures Telegram Mini App gotchas that aren't in official docs
