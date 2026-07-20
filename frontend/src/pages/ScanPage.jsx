import { useMemo, useState } from "react";
import IssueTable from "../components/IssueTable";
import RecentScans from "../components/RecentScans";
import { BoltIcon } from "../components/icons";
import { postJson } from "../services/api";
import { recordScan } from "../services/history";

const SEVERITIES = ["Critical", "High", "Medium", "Low"];

const EXAMPLE_URLS = [
  { label: "bbc.co.uk",       url: "https://www.bbc.co.uk" },
  { label: "w3.org",          url: "https://www.w3.org" },
  { label: "wikipedia.org",   url: "https://en.wikipedia.org" },
  { label: "example.com",     url: "https://example.com" },
];

export default function ScanPage({ state, setState, next }) {
  const [url, setUrl] = useState(state.url || "");
  const [authState, setAuthState] = useState("");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [loginUrl, setLoginUrl] = useState("");
  const [loginUser, setLoginUser] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [selUser, setSelUser] = useState("");
  const [selPass, setSelPass] = useState("");
  const [selSubmit, setSelSubmit] = useState("");
  const [loginProof, setLoginProof] = useState(null);
  const [filter, setFilter] = useState("All");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const issues = useMemo(
    () => state.scan?.issues?.filter((i) => filter === "All" || i.severity === filter) ?? [],
    [state.scan, filter],
  );

  const liveMessage = busy
    ? needsLogin
      ? "Signing in, then running the accessibility scan…"
      : "Running accessibility scan…"
    : state.scan
      ? `${issues.length} ${issues.length === 1 ? "issue" : "issues"} ${filter === "All" ? "found" : `match the ${filter} filter`}.`
      : "";

  async function scan(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    let storageState = null;
    if (authState.trim()) {
      try {
        storageState = JSON.parse(authState);
      } catch {
        setError("Session state is not valid JSON. Paste the output of a Playwright storageState file.");
        setBusy(false);
        return;
      }
    }
    let proof = null;
    try {
      if (needsLogin && !storageState) {
        const selectors = {};
        if (selUser.trim()) selectors.username = selUser.trim();
        if (selPass.trim()) selectors.password = selPass.trim();
        if (selSubmit.trim()) selectors.submit = selSubmit.trim();
        const login = await postJson("/api/login", {
          login_url: loginUrl,
          username: loginUser,
          password: loginPass,
          ...(Object.keys(selectors).length ? { selectors } : {}),
        });
        if (!login.success) {
          setError(login.notice || "Login failed — the page still shows a login form.");
          return;
        }
        // Credentials are done with: keep only the session + the proof shot.
        setLoginPass("");
        storageState = login.storage_state;
        proof = { screenshot: login.screenshot, finalUrl: login.final_url, notice: login.notice };
      }
      const body = { url };
      if (storageState) body.storage_state = storageState;
      const result = await postJson("/api/scan", body);
      setLoginProof(proof);
      setState((v) => ({ ...v, url, scan: result, selected: null, similar: null, reference: null, generated: null }));
      recordScan({ url, source: result.source, total: result.issues?.length ?? 0 });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <p className="visually-hidden" role="status" aria-live="polite">{liveMessage}</p>
      <div className="hero">
        <p className="eyebrow">Accessibility · GitHub Integration</p>
        <h1>
          Scan. Identify.
          <span className="hero-accent">Log with AI.</span>
        </h1>
        <p className="hero-sub">
          Enter a URL to run an automated WCAG accessibility audit. The tool identifies
          violations, searches your GitHub repository for similar open issues, then drafts
          a complete, production-ready GitHub issue with AI.
        </p>
      </div>

      <form className="scan-card" onSubmit={scan}>
        <label htmlFor="url-input">Page URL to audit</label>
        <div className="input-row">
          <input
            id="url-input"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/page-to-audit"
            required
            aria-describedby={error ? "scan-error" : undefined}
          />
          <button className="primary" type="submit" disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} aria-hidden="true" />
                Scanning…
              </>
            ) : (
              <><BoltIcon size={17} aria-hidden="true" />Run Accessibility Scan</>
            )}
          </button>
        </div>
        <div className="url-chips" aria-label="Example URLs to try">
          <span className="url-chips-label">Try:</span>
          {EXAMPLE_URLS.map(({ label, url: chipUrl }) => (
            <button
              key={chipUrl}
              type="button"
              className="chip"
              onClick={() => setUrl(chipUrl)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="auth-scan">
          <label className="auth-toggle" htmlFor="needs-login">
            <input
              id="needs-login"
              type="checkbox"
              checked={needsLogin}
              onChange={(e) => {
                setNeedsLogin(e.target.checked);
                if (!e.target.checked) setLoginProof(null);
              }}
            />
            This page needs a login
          </label>

          {needsLogin && (
            <div className="login-fields">
              <p className="auth-scan-help">
                The tool opens the login page in its own browser, signs in with these details, then
                scans the page you asked for as the logged-in user. Credentials are used once to log
                in and are never stored, logged, or included in any response — only the session
                cookies are kept for the scan. <strong>Limitations:</strong> only simple
                username/password forms are supported. SSO (Google/GitHub), 2FA/MFA, and
                CAPTCHA-protected logins are not.
              </p>
              <div className="login-grid">
                <div>
                  <label htmlFor="login-url">Login page URL</label>
                  <input
                    id="login-url"
                    type="url"
                    value={loginUrl}
                    onChange={(e) => setLoginUrl(e.target.value)}
                    placeholder="https://example.com/login"
                    required={needsLogin && !authState.trim()}
                  />
                </div>
                <div>
                  <label htmlFor="login-username">Username or email</label>
                  <input
                    id="login-username"
                    type="text"
                    value={loginUser}
                    onChange={(e) => setLoginUser(e.target.value)}
                    autoComplete="username"
                    required={needsLogin && !authState.trim()}
                  />
                </div>
                <div>
                  <label htmlFor="login-password">Password</label>
                  <input
                    id="login-password"
                    type="password"
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    autoComplete="current-password"
                    required={needsLogin && !authState.trim()}
                  />
                </div>
              </div>

              <details className="auth-advanced">
                <summary>Advanced: custom selectors or session state</summary>
                <p className="auth-scan-help">
                  If field auto-detection fails on an unusual login form, provide the CSS selectors
                  for its fields. Alternatively, paste a Playwright <code>storageState</code> JSON to
                  skip the login step entirely.
                </p>
                <div className="login-grid">
                  <div>
                    <label htmlFor="sel-username">Username field selector</label>
                    <input
                      id="sel-username"
                      type="text"
                      value={selUser}
                      onChange={(e) => setSelUser(e.target.value)}
                      placeholder="input[name=email]"
                      spellCheck="false"
                    />
                  </div>
                  <div>
                    <label htmlFor="sel-password">Password field selector</label>
                    <input
                      id="sel-password"
                      type="text"
                      value={selPass}
                      onChange={(e) => setSelPass(e.target.value)}
                      placeholder="input[type=password]"
                      spellCheck="false"
                    />
                  </div>
                  <div>
                    <label htmlFor="sel-submit">Submit button selector</label>
                    <input
                      id="sel-submit"
                      type="text"
                      value={selSubmit}
                      onChange={(e) => setSelSubmit(e.target.value)}
                      placeholder="button[type=submit]"
                      spellCheck="false"
                    />
                  </div>
                </div>
                <label htmlFor="storage-state">Session storage state JSON (optional)</label>
                <textarea
                  id="storage-state"
                  value={authState}
                  onChange={(e) => setAuthState(e.target.value)}
                  placeholder='{"cookies": [...], "origins": [...]}'
                  spellCheck="false"
                />
              </details>
            </div>
          )}
        </div>
      </form>

      {!state.scan && !busy && <RecentScans onPick={setUrl} />}

      {error && (
        <p id="scan-error" className="alert error" role="alert">{error}</p>
      )}

      {busy && (
        <div className="loading-screen" style={{ minHeight: "32vh" }}>
          <div className="spinner" aria-hidden="true" />
          <h1>{needsLogin ? "Signing in, then scanning…" : "Running accessibility scan…"}</h1>
          <p>
            {needsLogin
              ? "Logging in to the page in a headless browser, then running the axe-core audit on the authenticated page. This can take a little longer."
              : "Loading the page in a headless browser and running the axe-core audit. This can take a few seconds."}
          </p>
        </div>
      )}

      {!busy && state.scan && (
        <>
          {loginProof && (
            <section className="login-proof" aria-labelledby="login-proof-title">
              <div className="login-proof-head">
                <h2 id="login-proof-title">Login verified</h2>
                <span className="source-badge live" aria-label="Scanned with an authenticated session">
                  Authenticated session
                </span>
              </div>
              <p className="result-url">Signed-in page: {loginProof.finalUrl}</p>
              {loginProof.notice && (
                <div className="alert" role="status">{loginProof.notice}</div>
              )}
              <img
                className="login-proof-shot"
                src={loginProof.screenshot}
                alt={`Full-page screenshot of ${loginProof.finalUrl} captured after logging in, as proof the login succeeded`}
              />
            </section>
          )}

          {state.scan.notice && (
            <div className="alert" role="status">{state.scan.notice}</div>
          )}

          <div className="results-header">
            <div>
              <h2>Accessibility Audit Results</h2>
              <p className="result-url">{state.scan.url}</p>
            </div>
            {state.scan.source === "live" ? (
              <span className="source-badge live" aria-label="Source: live axe-core scan">
                Live scan · axe-core
              </span>
            ) : (
              <span className="source-badge demo" aria-label="Source: demo data, not a live scan">
                Demo data · not a live scan
              </span>
            )}
          </div>

          <div className="stats" aria-label="Issue summary by severity">
            <div className="stat total">
              <span className="stat-tick" aria-hidden="true" />
              <span className="stat-num">{state.scan.issues.length}</span>
              <span className="stat-k">Total</span>
            </div>
            {SEVERITIES.map((s) => (
              <div className={`stat ${s.toLowerCase()}`} key={s}>
                <span className="stat-tick" aria-hidden="true" />
                <span className="stat-num">{state.scan.summary[s]}</span>
                <span className="stat-k">{s}</span>
              </div>
            ))}
          </div>

          <div className="section-head">
            <div>
              <p className="eyebrow">Detected Issues ({issues.length})</p>
              <h2>Select one issue to find similar GitHub issues</h2>
            </div>
            <label htmlFor="severity-filter">
              <span className="muted" style={{ fontSize: ".72rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".1em" }}>Filter</span>
              <select
                id="severity-filter"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                style={{ marginTop: 6, display: "block" }}
              >
                <option>All</option>
                {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
          </div>

          {issues.length === 0 ? (
            <div className="empty-state">
              <p>No issues match the current filter.</p>
            </div>
          ) : (
            <IssueTable
              issues={issues}
              selectedId={state.selected?.id}
              onSelect={(issue) =>
                setState((v) => ({
                  ...v,
                  selected: issue,
                  similar: null,
                  reference: null,
                  generated: null,
                }))
              }
            />
          )}

          <div className="actions">
            <button
              className="primary"
              disabled={!state.selected}
              onClick={next}
              aria-describedby={!state.selected ? "select-hint" : undefined}
            >
              Find Similar GitHub Issues →
            </button>
          </div>
          {!state.selected && (
            <p id="select-hint" className="muted" style={{ textAlign: "right", fontSize: ".78rem", marginTop: -16 }}>
              Select an issue above to continue
            </p>
          )}
        </>
      )}
    </section>
  );
}
