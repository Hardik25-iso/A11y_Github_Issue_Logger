import { CheckIcon } from "./icons";

const STEP_LABELS = ["Scan", "Compare", "Generate", "Review & Log"];

export default function Steps({ step, onNavigate }) {
  return (
    <nav aria-label="Workflow progress" className="steps">
      {STEP_LABELS.map((label, index) => {
        const num = index + 1;
        const done = num < step;
        const active = num === step;
        const className = `step${done ? " done" : ""}${active ? " active" : ""}`;
        const inner = (
          <>
            <span className="step-num" aria-hidden="true">{num}</span>
            <span className="step-check" aria-hidden="true"><CheckIcon size={13} /></span>
            <span className="step-label">{label}</span>
          </>
        );

        if (done && onNavigate) {
          return (
            <button
              type="button"
              className={className}
              key={label}
              onClick={() => onNavigate(num)}
              aria-label={`Go back to step ${num}: ${label}`}
            >
              {inner}
            </button>
          );
        }

        return (
          <div className={className} key={label} aria-current={active ? "step" : undefined}>
            {inner}
          </div>
        );
      })}
      <span className="steps-caption" aria-hidden="true">
        Step {step} of {STEP_LABELS.length} · {STEP_LABELS[step - 1]}
      </span>
    </nav>
  );
}
