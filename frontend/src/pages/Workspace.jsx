import { useEffect, useState } from "react";
import SiteFooter from "../components/SiteFooter";
import SiteHeader from "../components/SiteHeader";
import Steps from "../components/Steps";
import { getJson } from "../services/api";
import ComparePage from "./ComparePage";
import GeneratePage from "./GeneratePage";
import ReviewPage from "./ReviewPage";
import ScanPage from "./ScanPage";

/** The 4-step wizard, framed as the product workspace at /app. */
export default function Workspace() {
  const [step, setStep] = useState(1);
  const [state, setState] = useState({});

  useEffect(() => {
    getJson("/api/config")
      .then((config) => setState((v) => ({ ...v, repo: v.repo || config.default_repo })))
      .catch(() => {});
  }, []);

  const reset = () => {
    setState((v) => ({ repo: v.repo }));
    setStep(1);
  };

  return (
    <div className="page-wrapper">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <SiteHeader variant="app" onNewScan={reset} />

      <main id="main-content">
        <Steps step={step} onNavigate={setStep} />

        {step === 1 && (
          <ScanPage state={state} setState={setState} next={() => setStep(2)} />
        )}
        {step === 2 && (
          <ComparePage state={state} setState={setState} back={() => setStep(1)} next={() => setStep(3)} />
        )}
        {step === 3 && (
          <GeneratePage state={state} setState={setState} back={() => setStep(2)} next={() => setStep(4)} />
        )}
        {step === 4 && (
          <ReviewPage state={state} setState={setState} back={() => setStep(3)} reset={reset} />
        )}
      </main>

      <SiteFooter />
    </div>
  );
}
