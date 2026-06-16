# A11y GitHub Issue Logger

A full-stack workflow tool that converts automated website accessibility findings into actionable, reviewable GitHub issues. Scan a public URL with axe-core, find related existing issues, generate a complete GitHub issue with AI, review it, and log it — all in one guided four-step workflow.

## How it works

```
Scan public URL (axe-core via Playwright)
  → Filter and select one accessibility violation
  → Search GitHub repository for similar issues
  → Generate a structured issue draft (Ollama / Anthropic / template)
  → Review and edit all fields
  → Log the approved issue to GitHub
```

AI assists but never acts autonomously. Human review is mandatory before any GitHub issue is created.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, custom CSS design system |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Scanning | Playwright (Chromium), axe-core (bundled) |
| AI | Ollama (local), Anthropic Claude, deterministic template fallback |
| GitHub | GitHub REST API v2022-11-28 |
| CI | GitHub Actions |

## Local development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Ollama (optional — for local AI generation)

### Setup

```bash
# Clone and configure
cp .env.example .env        # edit with your tokens

# Backend
pip install -r backend/requirements.txt
python -m playwright install chromium
uvicorn backend.app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Interactive API docs: `http://localhost:8000/docs`.

### Local AI (free, no API key)

```bash
ollama pull qwen3:8b
ollama serve
# set AI_PROVIDER=ollama in .env
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `AI_PROVIDER` | No | `ollama` · `anthropic` · `auto` · `template` (default) |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | No | Model name (default: `qwen3:8b`) |
| `AI_TIMEOUT_SECONDS` | No | Request timeout in seconds (default: `30`) |
| `ANTHROPIC_API_KEY` | Anthropic only | Anthropic API key |
| `ANTHROPIC_MODEL` | No | Model ID (default: `claude-sonnet-4-20250514`) |
| `GITHUB_TOKEN` | Issue logging | Fine-grained PAT with Issues read/write |
| `GITHUB_REPO_OWNER` | No | Default repository owner |
| `GITHUB_REPO_NAME` | No | Default repository name |
| `FRONTEND_ORIGINS` | Production | Comma-separated CORS origins for your frontend |
| `ENABLE_LIVE_SCAN` | No | `true` to enable Playwright scanning (default: `false`) |
| `SCAN_TIMEOUT_MS` | No | Browser navigation timeout (default: `30000`) |
| `BLOCK_HEAVY_SCAN_RESOURCES` | No | Block images/fonts during scans (default: `true`) |

**GitHub token permissions:** Repository → Issues (read and write). No other scopes needed.

Never commit `.env` or any file containing secrets.

## Deployment

### Frontend → Vercel

1. Import the repository in Vercel
2. Set root directory to `frontend/`
3. Framework: Vite (auto-detected via `vercel.json`)
4. Add environment variable: `VITE_API_URL=https://your-backend.railway.app`
5. Deploy

### Backend → Railway

1. Create a new project from this repository
2. Set root directory to `backend/` (or use the `railway.toml` at repo root)
3. Add all required environment variables in the Railway dashboard
4. Set `FRONTEND_ORIGINS=https://your-frontend.vercel.app`
5. Set `ENABLE_LIVE_SCAN=true` if the Railway plan supports Chromium
6. Deploy

**Note on live scanning:** Playwright Chromium requires a plan that allows installing system packages. Railway Hobby and Pro plans support this. If live scanning is not available, the app runs fully with fallback/demo scan results — all other features (GitHub search, AI generation, issue logging) work without Playwright.

### Backend → Render

Use the included `backend/render.yaml`. Add secrets in the Render dashboard (marked `sync: false`).

## Running tests

```bash
# Backend (from repo root)
python -m pytest backend/tests -q

# Frontend lint
cd frontend && npx eslint src/

# Frontend build
cd frontend && npm run build

# Frontend dependency audit
cd frontend && npm audit --audit-level=high
```

CI runs all of the above on every push and pull request via GitHub Actions.

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Frontend configuration (no secrets exposed) |
| `POST` | `/api/scan` | Scan a public URL with axe-core |
| `POST` | `/api/search-issues` | Search GitHub for similar issues |
| `POST` | `/api/generate-issue` | Generate a structured issue draft |
| `POST` | `/api/log-issue` | Create the issue on GitHub |

## Security

- All user-supplied URLs are validated against SSRF using both parse-time and DNS-resolution checks
- Playwright sub-resource requests are individually validated and can abort on private-IP redirects
- GitHub and Anthropic credentials live only in backend environment variables — never sent to the frontend
- The `/api/config` endpoint returns only boolean capability flags, never raw secrets
- AI-generated `labels` and `assignee` fields are validated against GitHub's format rules before being sent to the API

## Project structure

```
backend/
  app/
    core/         Settings, SSRF validation, security utilities
    models/       Pydantic request/response schemas
    routers/      FastAPI endpoint definitions
    services/     Scanner, GitHub, AI generation logic
    prompts/      Versioned AI prompt templates
    assets/       Bundled axe-core (axe.min.js)
  tests/          Backend unit and integration tests
  requirements.txt
  Procfile        Heroku/Railway process definition
  railway.toml    Railway deployment config
  render.yaml     Render deployment config

frontend/
  src/
    components/   Badge, IssueCard, IssueEditor, Steps
    pages/        ScanPage, ComparePage, GeneratePage, ReviewPage
    services/     Backend API client (api.js)
  vercel.json     Vercel deployment config

.github/
  workflows/
    ci.yml        GitHub Actions: test, lint, build, audit
```
