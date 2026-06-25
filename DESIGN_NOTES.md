# Design Notes

Design rationale for two capabilities: scanning authenticated pages, and
capturing element screenshots as bug evidence.

---

## 1. Scanning authenticated URLs (e.g. a page behind a login)

### The problem

Every scan runs in a fresh, cookie-less browser context (`scanner.py`,
`browser.new_context()`). If you hand the tool a URL that requires a login —
say `https://mail.google.com/mail/u/0/#inbox` — the headless browser has no
session, the site redirects it to its login page, and axe-core ends up
auditing the **login screen**, not the page you intended. You get real-looking
results for the wrong page. That silently violates the project's core rule:
never present results as something they are not.

### Options considered

| Approach | Mechanism | Verdict |
|---|---|---|
| Scripted login (username/password) | Tool types credentials and submits the login form | **Rejected.** Requires storing third-party credentials, breaks on MFA/CAPTCHA, high liability. |
| Session / storage-state injection | Caller supplies exported cookies + localStorage; Playwright loads them into the context | **Chosen.** Fits the existing security model; no credential storage. |
| Client-side browser extension | Scan runs inside the user's already-authenticated browser (how axe DevTools works) | Architecturally cleanest, but a much larger separate build. Future option. |

### What was implemented

`ScanRequest` accepts an optional `storage_state` — the same JSON format
Playwright produces with [`context.storage_state()`](https://playwright.dev/python/docs/auth):

```json
{ "cookies": [ ... ], "origins": [ { "origin": "...", "localStorage": [ ... ] } ] }
```

- It is **validated** (only `cookies`/`origins` keys, each a list; capped at 1 MB).
- It is loaded into a **single per-scan browser context that is discarded**
  immediately after the scan.
- It is **never persisted and never logged** — same posture as the
  bring-your-own-token decision for GitHub PATs.
- After navigation, if the page redirected to something that looks like a login
  wall (`_looks_like_login_wall`), the response carries a clear notice instead
  of pretending the login page is the requested page.

In the UI, this lives under an "advanced" disclosure on the scan screen.

### Honest caveat (important)

**Gmail specifically will likely still fail.** Google actively blocks headless
and automated browsers regardless of a valid session, so it is a good
*illustration* of the problem but not a realistic *target*. The realistic
targets are self-hosted apps, internal tools, and staging environments behind a
login — exactly the things a team wants to audit.

### How to produce a `storage_state`

```python
# One-time, run locally in a trusted environment:
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://your-app.example.com/login")
    input("Log in manually, then press Enter…")
    print(page.context.storage_state())   # paste this JSON into the scanner
```

---

## 2. Screenshot the offending element and attach it to the bug

### Capture

axe-core reports the CSS selector of each offending element, which the scanner
already extracts. During a live scan we locate that element, apply a red
highlight, and screenshot just that element to a base64 PNG
(`_capture_element_screenshot`). Capture is capped per scan and each attempt is
guarded by a timeout — a failed screenshot never blocks the scan.

A captured element screenshot is **genuine scan evidence**, which is exactly the
kind of artifact the project wants (unlike AI-generated text). Two honesty rules
follow directly:

- Screenshots are only produced on a **live scan**. In fallback/demo mode there
  is no real page, so there is **no screenshot** — never a fabricated one.
- The screenshot is shown in the review UI before logging, so a human sees the
  evidence that will be attached.

### Attaching it to the GitHub issue — the real constraint

> GitHub's REST API for creating issues **cannot upload images**. The
> drag-and-drop upload in the web UI posts to a private endpoint
> (`user-images.githubusercontent.com`) that is not in the public API, and
> base64 data-URIs do not render in issue markdown.

Options to get an image *into* the issue body:

| Option | Needs | Trade-off |
|---|---|---|
| Commit the image into the target repo, embed its raw URL | Only the existing PAT (+ `Contents: write`) | Writes a file into the repo |
| Upload to external storage (S3/Cloudinary) | An extra credential/service | More infra |
| Show only in the app | Nothing | Never reaches GitHub |

### What was implemented

The **commit-to-repo** path, because it reaches GitHub using only the PAT the
tool already uses. On logging, the screenshot is committed under
`.a11y-screenshots/` via the Contents API and its raw URL is embedded in the
issue body (`_upload_screenshot` + `markdown_body`).

It **degrades gracefully**: if the token lacks `Contents: write` (or any upload
error occurs), the issue is still created without the image rather than failing.
The review screen discloses that the screenshot will be committed and which
permission it needs.

---

## Testing

Both features are covered by backend tests: screenshot field propagation,
markdown embedding with/without a URL, upload success and permission-failure
fallback, login-wall detection, and storage-state validation (shape, types,
unknown keys). All run without a live browser or real GitHub access.
