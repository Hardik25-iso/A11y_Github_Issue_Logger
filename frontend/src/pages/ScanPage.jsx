import { useMemo, useState } from "react";
import IssueCard from "../components/IssueCard";
import { postJson } from "../services/api";

const SEVERITIES = ["Critical", "High", "Medium", "Low"];

export default function ScanPage({ state, setState, next }) {
  const [url, setUrl] = useState(state.url || "https://example.com");
  const [filter, setFilter] = useState("All");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const issues = useMemo(
    () => state.scan?.issues?.filter((i) => filter === "All" || i.severity === filter) ?? [],
    [state.scan, filter],
  );

  async function scan(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await postJson("/api/scan", { url });
      setState((v) => ({ ...v, url, scan: result, selected: null, similar: null, reference: null, generated: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="hero">
        <p className="eyebrow">Accessibility intelligence for engineering teams</p>
        <h1>Turn accessibility findings into actionable GitHub issues.</h1>
        <p className="hero-sub">
          Scan a public page, find related work in your repository, and generate a complete,
          reviewable issue — all in one focused workflow.
        </p>
      </div>

      <form className="scan-card" onSubmit={scan}>
        <label htmlFor="url-input">Public page URL</label>
        <div className="input-row">
          <input
            id="url-input"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            required
            aria-describedby={error ? "scan-error" : undefined}
          />
          <button className="primary" type="submit" disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} aria-hidden="true" />
                Scanning…
              </>
            ) : "Scan page"}
          </button>
        </div>
      </form>

      {error && (
        <p id="scan-error" className="alert error" role="alert">{error}</p>
      )}

      {state.scan && (
        <>
          {state.scan.notice && (
            <div className="alert" role="status">{state.scan.notice}</div>
          )}

          <div className="summary" aria-label="Issue summary by severity">
            {SEVERITIES.map((s) => (
              <div className={`summary-pill ${s.toLowerCase()}`} key={s}>
                <span className="summary-label">{s}</span>
                <span className="summary-count">{state.scan.summary[s]}</span>
              </div>
            ))}
          </div>

          <div className="section-head">
            <div>
              <p className="eyebrow">Scan results</p>
              <h2>Select one issue to investigate</h2>
            </div>
            <label htmlFor="severity-filter">
              <span className="muted" style={{ fontSize: ".8rem", fontWeight: 600 }}>Filter by severity</span>
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
              Find similar issues →
            </button>
          </div>
          {!state.selected && (
            <p id="select-hint" className="muted" style={{ textAlign: "right", fontSize: ".82rem", marginTop: -16 }}>
              Select an issue above to continue
            </p>
          )}
        </>
      )}
    </section>
  );
}
