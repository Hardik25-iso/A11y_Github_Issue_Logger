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
  }, []); // one-shot: fires on mount only if not already generated

  if (busy) {
    return (
      <section className="center" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <h1>Generating an actionable issue...</h1>
        <p>Combining scan evidence and reference context.</p>
      </section>
    );
  }

  return (
    <section>
      <p className="eyebrow">Generated draft</p>
      <h1>Review the proposed GitHub issue</h1>
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
        <button onClick={back}>Back</button>
        <button className="primary" disabled={!state.generated} onClick={next}>Review and log</button>
      </div>
    </section>
  );
}
