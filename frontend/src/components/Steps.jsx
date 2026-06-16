const STEP_LABELS = ["Scan", "Compare", "Generate", "Review & Log"];

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Steps({ step }) {
  return (
    <nav aria-label="Workflow progress" className="steps">
      {STEP_LABELS.map((label, index) => {
        const num = index + 1;
        const done = num < step;
        const active = num === step;
        return (
          <div
            className={`step${done ? " done" : ""}${active ? " active" : ""}`}
            key={label}
            aria-current={active ? "step" : undefined}
          >
            <span className="step-num" aria-hidden="true">{num}</span>
            <span className="step-check" aria-hidden="true"><CheckIcon /></span>
            {label}
          </div>
        );
      })}
    </nav>
  );
}
