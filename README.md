# A11y GitHub Issue Logger

Turn WCAG accessibility findings into structured, reviewable GitHub issues — in four steps.

Scan any public URL with axe-core, find existing issues in your GitHub repo to avoid duplicates, generate a complete issue draft, review it, and log it. No accessibility finding gets lost in a Slack thread or a spreadsheet again.

**🔗 Live demo: https://a11y-github-issue-logger.vercel.app**

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

## Advanced features

- **Element screenshots** — on a live scan, the offending element is highlighted
  and screenshotted as genuine evidence, shown in the review screen and embedded
  into the logged GitHub issue (committed to `.a11y-screenshots/` in the target
  repo; needs `Contents: write` on the token, degrades gracefully otherwise).
- **Authenticated scans** — paste a Playwright `storageState` JSON under the
  scan screen's advanced option to audit a page behind a login. The session is
  used once for the scan and never persisted or logged.

See [DESIGN_NOTES.md](DESIGN_NOTES.md) for the rationale and trade-offs behind both.

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
| `BROWSER_WS_ENDPOINT` | No | CDP endpoint of a hosted browser (e.g. Browserless). Blank = local Chromium |
| `BROWSER_MAX_CONCURRENCY` | No | Concurrent scans (default: `3`; `1` on the Browserless free tier) |
| `SCAN_TOTAL_TIMEOUT_S` | No | Per-scan cap for remote scans (default: `28`) |
| `FRONTEND_ORIGINS` | Production | Your frontend URL for CORS (e.g. `https://your-app.vercel.app`) |

**GitHub token setup:** Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens. Select your repo, grant **Issues: read and write**. No other scopes needed.

### AI providers

The tool works without any AI key — it falls back to a deterministic template that fills all required fields. To get smarter issue drafts:

- **Groq** (recommended, free): Sign up at [console.groq.com](https://console.groq.com), create an API key, set `AI_PROVIDER=groq` and `GROQ_API_KEY=your_key`.
- **Ollama** (local, free): Install [Ollama](https://ollama.com), run `ollama pull qwen3:8b`, set `AI_PROVIDER=ollama`.
- **Anthropic**: Set `AI_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your_key`.

---

## Deployment

### Backend → Render (free tier)

Render's free web service has 512 MB RAM, too little for Chromium, so this
deployment scans in a hosted browser over CDP and ships a slim image
(`Dockerfile.render`, no browser binaries).

1. Create a free [Browserless](https://www.browserless.io) account (no card
   required; 1,000 units/month, about one scan each) and copy your API token
2. In [Render](https://render.com), choose **New → Blueprint** and select this
   repository; Render reads `render.yaml`
3. Enter the secrets it prompts for (never commit these):
   - `BROWSER_WS_ENDPOINT` — `wss://production-sfo.browserless.io?token=YOUR_TOKEN`
   - `FRONTEND_ORIGINS` — your Vercel URL
   - `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`, and `GROQ_API_KEY` if you use Groq
4. Deploy, then check `https://<service>.onrender.com/health` reports `"browser": "remote"`
5. Point the `/api` rewrite in `frontend/vercel.json` at the Render URL

The free service sleeps after 15 minutes idle and takes about a minute to
wake. When the Browserless quota runs out, scans return clearly labeled demo
results with a "quota is used up" notice until it resets.

### Backend → Railway

The backend uses Docker (Playwright Chromium is bundled in the image).

1. Create a new project in [Railway](https://railway.app) and connect this repository
2. Railway auto-detects the `Dockerfile` and `railway.toml` at the repo root
3. Add secrets in the Railway dashboard (never commit these):
   - `GITHUB_TOKEN`
   - `GROQ_API_KEY` or `ANTHROPIC_API_KEY` (whichever provider you use)
   - `FRONTEND_ORIGINS` — set to your Vercel URL once deployed
4. Set `AI_PROVIDER` to your chosen provider (`groq`, `anthropic`, or `ollama`)
5. Deploy — Railway runs the health check at `/health` before marking the service live

### Frontend → Vercel

1. Import this repository in [Vercel](https://vercel.com)
2. Set root directory: `frontend/`
3. Add environment variable: `VITE_API_URL=https://your-railway-backend-url`
4. Deploy

> **Live scanning:** `ENABLE_LIVE_SCAN=true` is set automatically for the production environment in `railway.toml`. If you need to disable it, override it in the Railway dashboard.

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
