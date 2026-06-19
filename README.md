# A11y GitHub Issue Logger

Turn WCAG accessibility findings into structured, reviewable GitHub issues — in four steps.

Scan any public URL with axe-core, find existing issues in your GitHub repo to avoid duplicates, generate a complete issue draft, review it, and log it. No accessibility finding gets lost in a Slack thread or a spreadsheet again.

---

## How it works

```
1. Scan   →  Enter a URL. axe-core audits the page and lists WCAG violations.
2. Search →  Pick one violation. The tool searches your GitHub repo for duplicates.
3. Draft  →  AI writes a structured issue: title, steps to reproduce, expected/actual, acceptance criteria.
4. Log    →  You review every field, edit anything, then log directly to GitHub.
```

Human review is mandatory. The tool drafts; you decide.

---

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+

### 1. Clone and configure

```bash
git clone https://github.com/your-username/a11y-github-issue-logger.git
cd a11y-github-issue-logger
cp .env.example .env
```

Open `.env` and fill in your GitHub token and repo name (see [Configuration](#configuration) below).

### 2. Start the backend

```bash
pip install -r backend/requirements.txt
python -m playwright install chromium
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## Configuration

Create a `.env` file in the repo root (copy from `.env.example`).

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Yes | Fine-grained PAT with **Issues: read/write** on your repo |
| `GITHUB_REPO_OWNER` | Yes | Your GitHub username or org |
| `GITHUB_REPO_NAME` | Yes | The repo where issues will be logged |
| `AI_PROVIDER` | No | `groq` · `anthropic` · `ollama` · `template` (default: `template`) |
| `GROQ_API_KEY` | Groq only | Free API key from [console.groq.com](https://console.groq.com) |
| `ANTHROPIC_API_KEY` | Anthropic only | Anthropic API key |
| `OLLAMA_BASE_URL` | Ollama only | Default: `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama only | Default: `qwen3:8b` |
| `ENABLE_LIVE_SCAN` | No | `true` to enable real Playwright scanning (default: `false`) |
| `FRONTEND_ORIGINS` | Production | Your frontend URL for CORS (e.g. `https://your-app.vercel.app`) |

**GitHub token setup:** Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens. Select your repo, grant **Issues: read and write**. No other scopes needed.

### AI providers

The tool works without any AI key — it falls back to a deterministic template that fills all required fields. To get smarter issue drafts:

- **Groq** (recommended, free): Sign up at [console.groq.com](https://console.groq.com), create an API key, set `AI_PROVIDER=groq` and `GROQ_API_KEY=your_key`.
- **Ollama** (local, free): Install [Ollama](https://ollama.com), run `ollama pull qwen3:8b`, set `AI_PROVIDER=ollama`.
- **Anthropic**: Set `AI_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your_key`.

---

## Deployment

### Frontend → Vercel

1. Import this repository in [Vercel](https://vercel.com)
2. Set root directory: `frontend/`
3. Add environment variable: `VITE_API_URL=https://your-backend-url`
4. Deploy

### Backend → Railway

1. Create a new project from this repository in [Railway](https://railway.app)
2. Add all variables from `.env.example` in the Railway dashboard
3. Set `FRONTEND_ORIGINS=https://your-app.vercel.app`
4. Set `ENABLE_LIVE_SCAN=true` (Railway supports Chromium on Hobby and Pro plans)
5. Deploy

### Backend → Render

Use the included `backend/render.yaml`. Add secrets in the Render dashboard.

> **Live scanning note:** Playwright Chromium requires a host that allows installing system packages. If your plan doesn't support it, set `ENABLE_LIVE_SCAN=false` — all other features (GitHub search, AI generation, issue logging) work without it, and the app returns clearly-labeled demo results.

---

## Running tests

```bash
# Backend
python -m pytest backend/tests -q

# Frontend lint
cd frontend && npx eslint src/

# Frontend build
cd frontend && npm run build

# End-to-end (requires dev server running)
cd frontend && npx playwright test
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Frontend config (no secrets exposed) |
| `POST` | `/api/scan` | Scan a public URL with axe-core |
| `POST` | `/api/search-issues` | Search GitHub for similar issues |
| `POST` | `/api/generate-issue` | Generate a structured issue draft |
| `POST` | `/api/log-issue` | Create the issue on GitHub |

Interactive docs: `http://localhost:8000/docs`

---

## Security

- User-supplied URLs are validated against SSRF using DNS resolution — private IPs, loopback, and cloud metadata endpoints are blocked.
- GitHub and AI credentials live only in backend environment variables and are never sent to the frontend.
- The `/api/config` endpoint returns only boolean capability flags, never raw secrets.
- AI-generated content is validated with Pydantic before being trusted.

---

## Project structure

```
backend/app/
  core/       Settings, SSRF validation
  models/     Pydantic request/response schemas
  routers/    FastAPI endpoints
  services/   Scanner, GitHub, AI generation
  prompts/    AI prompt templates

frontend/src/
  pages/      ScanPage, ComparePage, GeneratePage, ReviewPage
  components/ Badge, IssueCard, IssueEditor, Steps
  services/   Backend API client
```

---

## License

MIT
