import { useMemo, useState } from "react";
import IssueCard from "../components/IssueCard";
import { postJson } from "../services/api";

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
  const [filter, setFilter] = useState("All");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const issues = useMemo(
    () => state.scan?.issues?.filter((i) => filter === "All" || i.severity === filter) ?? [],
    [state.scan, filter],
  );

  const liveMessage = busy
    ? "Running accessibility scan…"
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
    try {
      const body = { url };
      if (storageState) body.storage_state = storageState;
      const result = await postJson("/api/scan", body);
      setState((v) => ({ ...v, url, scan: result, selected: null, similar: null, reference: null, generated: null }));
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
              <>⚡ Run Accessibility Scan</>
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

        <details className="auth-scan">
          <summary>Scan a page behind a login (advanced)</summary>
          <p className="auth-scan-help">
            Paste a Playwright <code>storageState</code> JSON (cookies + localStorage) to scan an
            authenticated page. It is used only for this scan and never stored or logged. Note: some
            providers (e.g. Google) block automated browsers even with a valid session.
          </p>
          <textarea
            value={authState}
            onChange={(e) => setAuthState(e.target.value)}
            placeholder='{"cookies": [...], "origins": [...]}'
            aria-label="Session storage state JSON for authenticated scanning"
            spellCheck="false"
          />
        </details>
      </form>

      {error && (
        <p id="scan-error" className="alert error" role="alert">{error}</p>
      )}

      {busy && (
        <div className="loading-screen" style={{ minHeight: "32vh" }}>
          <div className="spinner" aria-hidden="true" />
          <h1>Running accessibility scan…</h1>
          <p>Loading the page in a headless browser and running the axe-core audit. This can take a few seconds.</p>
        </div>
      )}

      {!busy && state.scan && (
        <>
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

          <div className="summary" aria-label="Issue summary by severity">
            {SEVERITIES.map((s) => (
              <div className={`summary-pill ${s.toLowerCase()}`} key={s}>
                <span className="summary-count">{state.scan.summary[s]}</span>
                <span className="summary-label">{s}</span>
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
            <div className="issue-grid" role="list" aria-label="Accessibility issues">
              {issues.map((issue) => (
                <div role="listitem" key={issue.id}>
                  <IssueCard
                    issue={issue}
                    selected={state.selected?.id === issue.id}
                    onClick={() =>
                      setState((v) => ({
                        ...v,
                        selected: issue,
                        similar: null,
                        reference: null,
                        generated: null,
                      }))
                    }
                  />
                </div>
              ))}
            </div>
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
