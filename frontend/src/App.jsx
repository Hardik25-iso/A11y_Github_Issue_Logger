import { useEffect, useState } from "react";
import Steps from "./components/Steps";
import ComparePage from "./pages/ComparePage";
import GeneratePage from "./pages/GeneratePage";
import ReviewPage from "./pages/ReviewPage";
import ScanPage from "./pages/ScanPage";
import { getJson } from "./services/api";

export default function App() {
  const [step, setStep] = useState(1);
  const [state, setState] = useState({});

  useEffect(() => {
    getJson("/api/config")
      .then((config) =>
        setState((v) => ({ ...v, repo: v.repo || config.default_repo }))
      )
      .catch(() => {});
  }, []);

  return (
    <div className="page-wrapper">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <header>
        <a
          className="brand"
          href="/"
          onClick={(e) => { e.preventDefault(); setStep(1); }}
          aria-label="A11Y Issue Logger — go to step 1"
        >
          <span className="brand-mark">A11Y</span>
          Issue Logger
        </a>
        <span className="header-meta">WCAG · Accessibility · GitHub</span>
      </header>

      <main id="main-content">
        <Steps step={step} />

        {step === 1 && (
          <ScanPage state={state} setState={setState} next={() => setStep(2)} />
        )}
        {step === 2 && (
          <ComparePage
            state={state}
            setState={setState}
            back={() => setStep(1)}
            next={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <GeneratePage
            state={state}
            setState={setState}
            back={() => setStep(2)}
            next={() => setStep(4)}
          />
        )}
        {step === 4 && (
          <ReviewPage state={state} setState={setState} back={() => setStep(3)} />
        )}
      </main>

      <footer>
        Built to turn WCAG findings into engineering action. &nbsp;·&nbsp;
        <a href="https://www.w3.org/WAI/standards-guidelines/wcag/" target="_blank" rel="noreferrer" style={{ color: "var(--accent)", textDecoration: "underline" }}>
          WCAG guidelines
        </a>
      </footer>
    </div>
  );
}
