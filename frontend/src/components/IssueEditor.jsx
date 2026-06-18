import Badge from "./Badge";

const SOURCE_LABELS = {
  ollama: "Generated with Ollama",
  anthropic: "Generated with Anthropic",
  groq: "Generated with Groq AI",
  template: "Template fallback — AI unavailable",
};

const TEXT_FIELDS = [
  { key: "title", label: "Title", full: true },
  { key: "description", label: "Description", multiline: true, tall: true, full: true },
  { key: "expected_result", label: "Expected result", multiline: true },
  { key: "actual_result", label: "Actual result", multiline: true },
  { key: "environment", label: "Environment" },
  { key: "wcag_reference", label: "WCAG reference" },
];

export default function IssueEditor({ issue, onChange, readOnly = false, source = "template" }) {
  const set = (key, value) => !readOnly && onChange({ ...issue, [key]: value });

  return (
    <div className="editor">
      <div className="ai-banner">
        <Badge>{SOURCE_LABELS[source] || "AI Generated"}</Badge>
        <span style={{ color: "var(--text-muted)", fontSize: ".82rem" }}>
          GitHub — New Issue &nbsp;·&nbsp; {issue.severity} severity
          {source === "template" ? " — template fallback, review all fields" : ""}
        </span>
      </div>

      <div className="editor-grid">
        {TEXT_FIELDS.map(({ key, label, multiline, tall, full }) => (
          <div className={`editor-field${full ? " full" : ""}`} key={key}>
            <label htmlFor={`field-${key}`}>{label}</label>
            {multiline ? (
              <textarea
                id={`field-${key}`}
                className={tall ? "tall" : ""}
                readOnly={readOnly}
                value={issue[key]}
                onChange={(e) => set(key, e.target.value)}
              />
            ) : (
              <input
                id={`field-${key}`}
                type="text"
                readOnly={readOnly}
                value={issue[key]}
                onChange={(e) => set(key, e.target.value)}
              />
            )}
          </div>
        ))}

        <div className="editor-field">
          <label htmlFor="field-repro_steps">Reproduction steps</label>
          <textarea
            id="field-repro_steps"
            readOnly={readOnly}
            value={issue.repro_steps.join("\n")}
            onChange={(e) => set("repro_steps", e.target.value.split("\n"))}
            onBlur={(e) => set("repro_steps", e.target.value.split("\n").filter(Boolean))}
          />
        </div>

        <div className="editor-field">
          <label htmlFor="field-acceptance_criteria">Acceptance criteria</label>
          <textarea
            id="field-acceptance_criteria"
            readOnly={readOnly}
            value={issue.acceptance_criteria.join("\n")}
            onChange={(e) => set("acceptance_criteria", e.target.value.split("\n"))}
            onBlur={(e) => set("acceptance_criteria", e.target.value.split("\n").filter(Boolean))}
          />
        </div>

        <div className="editor-field full">
          <label htmlFor="field-labels">Labels (comma-separated)</label>
          <input
            id="field-labels"
            type="text"
            readOnly={readOnly}
            value={issue.labels.join(", ")}
            onChange={(e) =>
              set("labels", e.target.value.split(",").map((v) => v.trim()).filter(Boolean))
            }
          />
        </div>
      </div>
    </div>
  );
}
