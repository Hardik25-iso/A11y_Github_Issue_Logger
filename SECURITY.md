# Security

## SSRF Protection Model

All user-supplied URLs go through a multi-layer validation pipeline before any outbound request is made.

### Layers (in order)

| Layer | Where | What it does |
|---|---|---|
| Parse-time check | `security.validate_url_is_public()` | Rejects non-http/https schemes, localhost, RFC-1918 ranges, link-local (169.254.x.x), CGNAT (100.64.x.x) |
| DNS resolution check | `security.validate_resolved_public_url()` | Resolves the hostname and rejects if any returned address is private/loopback |
| Per-route Playwright guard | `scanner._guarded_route()` | Intercepts every sub-request the browser makes during the scan and aborts it if the resolved URL is non-public |
| Post-redirect revalidation | `scanner.scan_url()` | After `page.goto()`, re-validates `page.url` to catch open-redirect chains that land on an internal address |

### Residual risk: DNS rebinding (TOCTOU)

There is a time-of-check / time-of-use gap between the DNS resolution validation and the actual TCP connection that Playwright makes. A DNS rebinding attack — where the hostname resolves to a public IP during validation, then switches to a private IP for the real request — is theoretically possible if an attacker controls the DNS TTL.

**Mitigations in place:**
- The per-route Playwright guard performs a second DNS resolution at request time for every sub-request, substantially narrowing the window
- `ENABLE_LIVE_SCAN` is `false` by default; the scan endpoint returns demo data unless explicitly enabled

**Accepted risk:** Full SSRF-proof protection against DNS rebinding requires a dedicated egress proxy with its own IP-based ACLs (e.g. Smokescreen). This is out of scope for this deployment tier but documented here for operators who enable live scanning in a sensitive network environment.

## Secret Handling

- All credentials (`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`) live only in server-side environment variables
- The `/api/config` endpoint returns boolean flags (`github_configured`, `ai_configured`) — never the values
- The structured logger in `backend/app/core/logging.py` redacts `sk-ant-*`, `ghp_*`, `github_pat_*`, and `Bearer <token>` patterns before any log line is written
- `.env` is in `.gitignore`; `.env.example` contains only key names with no values

## Rate Limiting

- Global: 60 requests/minute per IP (all endpoints)
- Scan endpoint: 10 requests/minute per IP (Playwright is expensive)
- Implemented via `slowapi` backed by in-process memory; for multi-replica deployments, back with Redis

## GitHub Token Scope

The `GITHUB_TOKEN` only needs:
- `repo:read` — for searching issues
- `issues:write` — for creating issues

Do not grant broader scopes (no `admin`, no `delete_repo`).
