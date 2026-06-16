import Badge from "./Badge";

export default function IssueCard({ issue, selected, onClick }) {
  return (
    <button
      className={`issue-card${selected ? " selected" : ""}`}
      onClick={onClick}
      type="button"
      aria-pressed={selected}
    >
      <div className="row-between">
        <Badge tone={issue.severity}>{issue.severity}</Badge>
        <span className="muted" style={{ fontSize: ".78rem", fontWeight: 600 }}>
          WCAG {issue.wcag_criterion}
        </span>
      </div>
      <h3>{issue.title}</h3>
      <p>{issue.impact}</p>
      <div className="card-footer">
        <span className="muted" style={{ fontSize: ".78rem" }}>
          {issue.occurrences} occurrence{issue.occurrences !== 1 ? "s" : ""}
        </span>
        <code title={issue.selector}>{issue.selector}</code>
      </div>
    </button>
  );
}
