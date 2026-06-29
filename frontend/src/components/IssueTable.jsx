import { useState } from "react";

/**
 * Accessibility issues as a ruled data table with listbox semantics:
 * roving tabindex, ↑/↓/Home/End to move, Enter/Space to select, aria-selected
 * on the chosen row, and a visible focus ring. Delivers the keyboard behaviour
 * the UI advertises.
 */
export default function IssueTable({ issues, selectedId, onSelect }) {
  const selectedIndex = issues.findIndex((i) => i.id === selectedId);
  const [active, setActive] = useState(selectedIndex >= 0 ? selectedIndex : 0);
  const rows = [];

  function focusRow(idx) {
    const clamped = Math.max(0, Math.min(idx, issues.length - 1));
    setActive(clamped);
    rows[clamped]?.focus();
  }

  function onKeyDown(e, idx) {
    switch (e.key) {
      case "ArrowDown": e.preventDefault(); focusRow(idx + 1); break;
      case "ArrowUp":   e.preventDefault(); focusRow(idx - 1); break;
      case "Home":      e.preventDefault(); focusRow(0); break;
      case "End":       e.preventDefault(); focusRow(issues.length - 1); break;
      case "Enter":
      case " ":         e.preventDefault(); onSelect(issues[idx]); break;
      default: break;
    }
  }

  return (
    <div className="table" role="listbox" aria-label="Accessibility issues">
      <div className="thead" aria-hidden="true">
        <span>Severity</span><span>Issue</span><span>WCAG</span><span>Count</span><span />
      </div>
      {issues.map((issue, idx) => {
        const selected = issue.id === selectedId;
        return (
          <div
            key={issue.id}
            ref={(el) => (rows[idx] = el)}
            role="option"
            aria-selected={selected}
            tabIndex={idx === active ? 0 : -1}
            className={`row${selected ? " sel" : ""}`}
            onClick={() => onSelect(issue)}
            onFocus={() => setActive(idx)}
            onKeyDown={(e) => onKeyDown(e, idx)}
          >
            <span className="row-sev">
              <span className={`sevtag ${issue.severity.toLowerCase()}`}>{issue.severity}</span>
            </span>
            <div className="row-main">
              <div className="row-title">{issue.title}</div>
              <div className="row-sel">{issue.selector}</div>
            </div>
            <span className="row-wcag">{issue.wcag_criterion}</span>
            <span className="row-occ">
              {issue.occurrences}<span aria-hidden="true">×</span>
            </span>
            <span className="row-chev" aria-hidden="true">›</span>
          </div>
        );
      })}
    </div>
  );
}
