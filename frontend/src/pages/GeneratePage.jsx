import { useCallback, useEffect, useState } from "react";
import IssueEditor from "../components/IssueEditor";
import { postJson } from "../services/api";

export default function GeneratePage({ state, setState, back, next }) {
  const [busy, setBusy] = useState(!state.generated);
  const [error, setError] = useState("");

  const generate = useCallback(() => {
    setBusy(true);
    setError("");
    postJson("/api/generate-issue", {
      url: state.url,
      scan_issue: state.selected,
      reference_issue: state.reference === "none" ? null : state.reference,
    })
      .then((result) =>
        setState((value) => ({
          ...value,
          generated: result.generated_issue,
          generationSource: result.source,
        })),
      )
      .catch((requestError) => setError(requestError.message))
      .finally(() => setBusy(false));
  }, [state.url, state.selected, state.reference, setState]);

  useEffect(() => {
    if (state.generated) return;
    generate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentional one-shot: auto-generates on mount only if not already done

  if (busy) {
    return (
      <section aria-live="polite">
        <div className="loading-screen">
          <div className="spinner" aria-hidden="true" />
          <h1>Generating issue draft…</h1>
          <p>AI is combining scan evidence and reference context to produce a structured report.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <p className="eyebrow">AI Generated · Review Draft</p>
      <h1>Review the Generated GitHub Issue</h1>
      {error && (
        <div role="alert" className="alert error generate-error">
          <p>{error}</p>
          <button onClick={generate}>Retry generation</button>
        </div>
      )}
      {state.generated && (
        <IssueEditor
          issue={state.generated}
          source={state.generationSource}
          onChange={(generated) => setState((value) => ({ ...value, generated }))}
        />
      )}
      <div className="actions">
        <button className="ghost" onClick={back}>← Back</button>
        <button className="primary" disabled={!state.generated} onClick={next}>Review and log</button>
      </div>
    </section>
  );
}
