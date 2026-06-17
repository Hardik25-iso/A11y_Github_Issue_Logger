# CLAUDE.md — A11y GitHub Issue Logger

Guidance for any AI coding agent working in this repository. Read this before making changes.

## What this project is

A full-stack app that turns automated WCAG accessibility findings into well-structured GitHub
issues, through a guided 4-step workflow: scan a public URL (Playwright + axe-core) → search a
configured GitHub repo for duplicates → AI-generate a structured issue → human review → create the
issue via the GitHub API. The AI assists; it never replaces manual accessibility testing, and
AI/template output is never presented as genuine scan evidence.

## Architecture (do not reorganize without being asked)

```
backend/app/
  core/        config (typed settings), security (SSRF/validation)
  models/      Pydantic v2 schemas — the data contracts
  routers/     thin HTTP endpoints: validate -> call service -> return typed response
  services/    scanner, github, generator, ai_client (the real logic)
  prompts/     versioned AI prompts
  main.py
frontend/src/
  pages/       the 4 wizard steps
  components/  reusable UI (Badge, Steps, IssueCard, IssueEditor)
  services/    api client
```

## Non-negotiable principles

1. **Honest labeling.** Every response carries a `source` (`live`/`fallback`,
   `ollama`/`anthropic`/`template`). Never let fallback/AI content masquerade as real scan data.
2. **Backend owns all integrations and secrets.** The frontend never holds GitHub/Anthropic
   credentials. Secrets live only in backend env vars and must never appear in logs, errors, or
   responses.
3. **Fallbacks are deterministic and testable.** If an external service fails, degrade to a stable,
   clearly-labeled fallback — never a crash.
4. **Human review is mandatory** before any issue is logged to GitHub.
5. **Typed data end to end.** axe output → `ScanIssue` → `SimilarIssue` → `GeneratedIssue` →
   Markdown. Validate AI output with Pydantic before trusting it.

## Commands (use these to verify, every time)

```bash
# Backend tests
AI_PROVIDER=template ENABLE_LIVE_SCAN=false GITHUB_TOKEN="" python -m pytest backend/tests -q

# Frontend
cd frontend && npx eslint src/ && npm test && npm run build
```

## How to work in this repo (efficiency rules)

- **One concern per task.** Do exactly what the current task asks. Do not opportunistically refactor
  working code, rename things, or "improve" unrelated files.
- **Verify before claiming done.** Run the relevant command above and paste the result. "Should
  work" is not done.
- **Small diffs.** Prefer the smallest change that satisfies the acceptance criteria.
- **Ask before adding a dependency** or changing the public API shape (routes, schemas).
- **Never touch `.env`, secrets, or commit anything matching `sk-ant-`, `ghp_`, `github_pat_`.**
- **If a change would break an existing test, stop and report** rather than editing the test to pass.
- Update `PROGRESS.md` when a task completes; keep its "Next steps" list current.
- When unsure about scope, state your plan in 3-5 bullets and wait for confirmation before large edits.
