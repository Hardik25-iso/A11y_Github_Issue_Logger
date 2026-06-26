import { useEffect, useState } from "react";
import Badge from "../components/Badge";
import { postJson } from "../services/api";

export default function ComparePage({ state, setState, back, next }) {
  const [repo, setRepo] = useState(state.repo || "");
  const [busy, setBusy] = useState(!state.similar);
  const [error, setError] = useState("");

  useEffect(() => {
    if (state.similar) return;
    doSearch(repo);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentional one-shot: auto-searches on mount only if not already fetched

  function doSearch(targetRepo) {
    setBusy(true);
    setError("");
    postJson("/api/search-issues", { issue: state.selected, repo: targetRepo || null })
      .then((similar) => setState((v) => ({ ...v, similar, repo: targetRepo })))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  }

  async function search() {
    setState((v) => ({ ...v, reference: null }));
    doSearch(repo);
  }

  const similar = state.similar;

  return (
    <section>
      <div className="section-head">
        <div>
          <p className="eyebrow">Duplicate Prevention · GitHub Search</p>
          <h1>Similar GitHub Issues</h1>
        </div>
      </div>

      <div className="repo-bar">
        <label>
          Target repository
          <input
            type="text"
            placeholder="owner/repository"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            aria-label="GitHub repository in owner/name format"
          />
        </label>
        <button onClick={search} disabled={busy}>
          {busy ? "Searching…" : "Search repository"}
        </button>
      </div>

      {error && <p className="alert error" role="alert">{error}</p>}

      <div className="compare">
        <div className="panel sticky">
          <p className="panel-eyebrow">Current A11y Issue</p>
          <Badge tone={state.selected.severity}>{state.selected.severity}</Badge>
          <h2 style={{ marginTop: 12, fontSize: "1.1rem" }}>{state.selected.title}</h2>
          <p style={{ marginTop: 8, fontSize: ".9rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>
            {state.selected.impact}
          </p>
          <dl>
            <dt>WCAG criterion</dt>
            <dd>{state.selected.wcag_criterion}</dd>
            <dt>Affected element</dt>
            <dd><code>{state.selected.element || state.selected.selector}</code></dd>
            <dt>Occurrences</dt>
            <dd>{state.selected.occurrences}</dd>
          </dl>
          {state.selected.screenshot && (
            <figure className="element-screenshot">
              <img src={state.selected.screenshot} alt={`Captured element for: ${state.selected.title}`} />
              <figcaption>Captured from the live scan · highlighted in red</figcaption>
            </figure>
          )}
        </div>

        <div className="panel">
          <div className="row-between" style={{ marginBottom: 14, gap: 10, flexWrap: "wrap" }}>
            <p className="panel-eyebrow" style={{ marginBottom: 0 }}>
              Matching GitHub Issues in {state.repo || "repository"}
            </p>
            {!busy && similar && (similar.source === "github" ? (
              <span className="source-badge live" aria-label="Source: live GitHub search">
                Live GitHub
              </span>
            ) : (
              <span className="source-badge demo" aria-label="Source: sample data, GitHub search unavailable">
                Sample data · GitHub unavailable
              </span>
            ))}
          </div>

          {busy && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "20px 0", color: "var(--text-muted)" }}>
              <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} aria-hidden="true" />
              <span role="status">Searching GitHub…</span>
            </div>
          )}

          {!busy && similar?.ai_summary && (
            <div className="alert" role="status" style={{ margin: "0 0 16px" }}>{similar.ai_summary}</div>
          )}

          {!busy && similar && (
            <div className="reference-list">
              {similar.similar_issues.map((item) => (
                <button
                  type="button"
                  className={`reference${state.reference?.number === item.number ? " selected" : ""}`}
                  onClick={() => setState((v) => ({ ...v, reference: item }))}
                  key={item.number}
                >
                  <div className="row-between">
                    <h4>#{item.number} {item.title}</h4>
                    <Badge tone={item.state}>{item.state}</Badge>
                  </div>
                  <p>{item.similarity_explanation}</p>
                  <div className="reference-footer">
                    <span className="score">{item.similarity_score}/10 match</span>
                    {item.assignee && (
                      <span className="muted" style={{ fontSize: ".78rem" }}>@{item.assignee}</span>
                    )}
                  </div>
                </button>
              ))}

              {similar.similar_issues.length === 0 && (
                <div className="empty-state" style={{ padding: "32px 0" }}>
                  <p>No similar issues found. Create a fresh issue below.</p>
                </div>
              )}

              <button
                type="button"
                className={`reference scratch-ref${state.reference === "none" ? " selected" : ""}`}
                onClick={() => setState((v) => ({ ...v, reference: "none" }))}
              >
                ＋ Create from scratch — no reference issue
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="actions">
        <button className="ghost" onClick={back}>← Back</button>
        <button
          className="primary"
          disabled={!state.reference}
          onClick={next}
        >
          Generate GitHub Issue →
        </button>
      </div>
    </section>
  );
}
