# Insights Capture Rule

## Purpose
Automatically capture development insights, debugging solutions, and architectural decisions during the coding process. These insights build a living knowledge base for the project.

## When to Capture
After completing any of these activities, save an insight:
- Solving a non-trivial bug (root cause + fix)
- Making an architectural decision (ADR-style: context, decision, consequences)
- Discovering a pattern or anti-pattern in the codebase
- Finding a workaround for a library/framework limitation
- Performance optimization (before/after metrics)
- Telegram Mini App specific gotchas

## How to Capture
Append to `docs/insights.md` with this format:

```markdown
### [YYYY-MM-DD] Title
**Category:** bug-fix | architecture | pattern | workaround | performance | tma-specific
**Context:** Brief description of the situation
**Insight:** What was learned
**Tags:** #relevant #tags
```

## Categories
- `bug-fix` — Root cause analysis of resolved bugs
- `architecture` — Design decisions and their rationale
- `pattern` — Reusable patterns discovered during development
- `workaround` — Library/framework limitations and solutions
- `performance` — Optimization discoveries with metrics
- `tma-specific` — Telegram Mini App specific learnings

## Rules
- Keep each insight concise (3-5 sentences max)
- Include concrete details (file paths, error messages, metrics)
- Tag with relevant technologies (#fastapi, #react, #telegram, #openai, etc.)
- Never include secrets, tokens, or PII in insights
