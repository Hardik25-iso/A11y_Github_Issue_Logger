import { useState } from "react";
import IssueEditor from "../components/IssueEditor";
import { postJson } from "../services/api";

function CheckCircleIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <circle cx="16" cy="16" r="16" fill="currentColor" opacity=".15" />
      <path d="M10 16l4 4 8-8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M5 2H2a1 1 0 00-1 1v9a1 1 0 001 1h9a1 1 0 001-1V9M8 1h5m0 0v5m0-5L6 8"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ReviewPage({ state, setState, back }) {
  const [repo, setRepo] = useState(state.repo || "");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function log() {
    setBusy(true);
    setError("");
    setState((v) => ({ ...v, repo }));
    try {
      setResult(await postJson("/api/log-issue", { repo, issue_data: state.generated }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(state.generated, null, 2));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard access denied — silent */
    }
  }

  if (result) {
    return (
      <section>
        <div className="success-card">
          <div className="success-icon" style={{ color: "var(--green-400)" }}>
            <CheckCircleIcon />
          </div>
          <h2>Issue #{result.issue_number} created</h2>
          <p>The accessibility issue has been logged to <strong>{repo}</strong>.</p>
          <a href={result.html_url} target="_blank" rel="noreferrer">
            Open on GitHub <ExternalLinkIcon />
          </a>
        </div>
        <div className="actions" style={{ justifyContent: "center" }}>
          <button onClick={() => window.location.reload()}>Start a new scan</button>
        </div>
      </section>
    );
  }

  return (
    <section>
      <p className="eyebrow">Final review</p>
      <h1>Ready to log</h1>
      <p style={{ color: "var(--text-secondary)", marginTop: 8, marginBottom: 24, fontSize: ".95rem" }}>
        Review all fields below. Changes made here will be logged as-is to GitHub.
      </p>

      <IssueEditor
        issue={state.generated}
        source={state.generationSource}
        onChange={() => {}}
        readOnly
      />

      <div className="repo-bar" style={{ marginTop: 20 }}>
        <label>
          Target repository
          <input
            type="text"
            placeholder="owner/repository"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            aria-label="GitHub repository in owner/name format"
          />
        </label>
        <button onClick={copy} aria-live="polite">
          {copied ? "✓ Copied" : "Copy JSON"}
        </button>
      </div>

      {error && <p className="alert error" role="alert">{error}</p>}

      <div className="actions">
        <button className="ghost" onClick={back}>← Back</button>
        <button
          className="primary"
          disabled={busy || !repo}
          onClick={log}
        >
          {busy ? (
            <>
              <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} aria-hidden="true" />
              Logging…
            </>
          ) : "Log issue to GitHub"}
        </button>
      </div>
    </section>
  );
}
