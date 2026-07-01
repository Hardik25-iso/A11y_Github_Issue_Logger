import { Link } from "react-router-dom";
import SiteFooter from "../components/SiteFooter";
import SiteHeader, { REPO_URL } from "../components/SiteHeader";
import {
  CopyIcon,
  EyeIcon,
  LayersIcon,
  SearchIcon,
  ShieldIcon,
  SparklesIcon,
} from "../components/icons";

const STEPS = [
  {
    n: "01",
    title: "Scan",
    body: "Point it at any public URL. A headless browser loads the page and runs an axe-core WCAG audit, normalized into findings with severity, the affected selector, user impact, and occurrence count.",
  },
  {
    n: "02",
    title: "Match",
    body: "Before you file anything, it searches your GitHub repo for existing issues on the same criterion and element — so you reference the duplicate instead of creating another one.",
  },
  {
    n: "03",
    title: "Draft",
    body: "AI turns the raw finding into a structured issue — title, reproduction steps, expected/actual, acceptance criteria, labels — validated against a schema, with a deterministic template fallback if AI is unavailable.",
  },
  {
    n: "04",
    title: "Review & log",
    body: "You read and edit every field, then log it to GitHub with your own token. Nothing reaches your repo until you approve it.",
  },
];

const FEATURES = [
  { Icon: SearchIcon, title: "Real axe-core scans", body: "WCAG 2.1 / 2.2 rules run against the live, rendered page via Playwright — not a static guess." },
  { Icon: CopyIcon, title: "Duplicate detection", body: "Searches the target repo by criterion, rule, selector and tags so you don't file the same bug twice." },
  { Icon: SparklesIcon, title: "AI drafting, honest fallback", body: "Structured issues from Anthropic, Ollama, or Groq — with a deterministic template when no provider is configured." },
  { Icon: LayersIcon, title: "Provider-independent", body: "Swap the AI backend via config. Every response is validated before it's trusted; sources are always labeled." },
  { Icon: EyeIcon, title: "Human review required", body: "The tool assists; it never auto-files. A person approves the final issue before anything is logged." },
  { Icon: ShieldIcon, title: "Passes its own audit", body: "The app is keyboard-navigable, AA-contrast, and runs axe against itself in CI on every push." },
];

const FAQS = [
  {
    q: "Do I need to create an account?",
    a: "No. There's no signup and no login. You bring a GitHub token at the moment you log an issue, and that's it.",
  },
  {
    q: "What data do you store about me?",
    a: "Effectively nothing. Scans run per-request, your GitHub token is used only for that one request and is never persisted or logged, and there's no user database. A short “recent scans” list lives only in your own browser.",
  },
  {
    q: "What token do you need, and why?",
    a: "A GitHub personal access token with permission to create issues in your target repo. It's required only at the final “log” step, sent to the backend for that single API call, and discarded. Element screenshots additionally need Contents: write, and degrade gracefully without it.",
  },
  {
    q: "Which WCAG version does it check?",
    a: "axe-core's WCAG 2.1 and 2.2 rule sets (A and AA). Automated rules catch a meaningful slice of issues — the tool is built to assist manual testing with keyboards and screen readers, not replace it.",
  },
  {
    q: "Can it scan pages behind a login?",
    a: "Yes, via an advanced option: paste a Playwright storage-state (cookies + localStorage) for a single scan. It's used once and never stored. Some providers block automated browsers even with a valid session.",
  },
  {
    q: "What does it cost?",
    a: "It's free to run with your own GitHub token, and open source. AI drafting is optional — wire in a provider and you pay that provider directly, or use the built-in template mode, which costs nothing. The public demo is best-effort, not a guaranteed hosted service.",
  },
];

export default function Landing() {
  return (
    <div className="page-wrapper landing">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <SiteHeader variant="marketing" />

      <main id="main-content">
        {/* Hero */}
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <p className="eyebrow">WCAG · axe-core · GitHub</p>
            <h1>
              Find accessibility bugs.
              <span className="hero-accent">File them like an engineer.</span>
            </h1>
            <p className="hero-sub">
              Scan any public page for WCAG violations, check your repo for duplicates, and turn each
              finding into a structured, reviewable GitHub issue — with a human in the loop before
              anything is logged.
            </p>
            <div className="hero-actions">
              <Link className="btn-link primary" to="/app">Launch app →</Link>
              <a className="btn-link ghost" href="#how">See how it works</a>
            </div>
            <p className="hero-trust muted">
              Free with your own GitHub token · no signup · nothing stored.
            </p>
          </div>

          {/* Decorative UI preview — a styled mock of the results screen, not live data. */}
          <div className="hero-mock" aria-hidden="true">
            <div className="hero-mock-bar">
              <span className="dot" /><span className="dot" /><span className="dot" />
              <span className="hero-mock-url">github.com/acme/store</span>
            </div>
            <div className="hero-mock-body">
              <div className="hero-mock-summary">
                <div className="hm-pill critical"><b>2</b><span>Critical</span></div>
                <div className="hm-pill high"><b>3</b><span>High</span></div>
                <div className="hm-pill medium"><b>2</b><span>Medium</span></div>
                <div className="hm-pill low"><b>1</b><span>Low</span></div>
              </div>
              <div className="hero-mock-card">
                <span className="badge critical">Critical</span>
                <p className="hm-title">Images must have alternative text</p>
                <code>main .hero img</code>
              </div>
              <div className="hero-mock-card muted-card">
                <span className="badge high">High</span>
                <p className="hm-title">Buttons must have discernible text</p>
                <code>header button.search</code>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="landing-section">
          <p className="eyebrow">How it works</p>
          <h2 className="landing-h2">Four steps from a URL to a logged issue</h2>
          <ol className="how-flow">
            {STEPS.map(({ n, title, body }) => (
              <li className="how-step" key={n}>
                <span className="how-num">{n}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Features */}
        <section id="features" className="landing-section">
          <p className="eyebrow">Features</p>
          <h2 className="landing-h2">Built like a tool you'd trust in review</h2>
          <div className="feature-grid">
            {FEATURES.map(({ Icon, title, body }) => (
              <div className="feature-card" key={title}>
                <span className="feature-icon"><Icon size={20} /></span>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Trust */}
        <section id="trust" className="landing-section trust">
          <div className="trust-text">
            <p className="eyebrow">Why it's safe</p>
            <h2 className="landing-h2">Honest by design</h2>
            <p className="trust-lead">
              Two things most accessibility bots can't claim: a person reviews every issue before
              it's filed, and the app passes its own automated accessibility audit in CI.
            </p>
          </div>
          <ul className="trust-list">
            <li>
              <span className="feature-icon"><EyeIcon size={20} /></span>
              <div><strong>Human review before logging.</strong> AI and templates draft; you approve. Nothing is filed automatically.</div>
            </li>
            <li>
              <span className="feature-icon"><ShieldIcon size={20} /></span>
              <div><strong>Self-audited accessibility.</strong> Keyboard, focus, contrast and axe checks run against this very app on every push.</div>
            </li>
            <li>
              <span className="feature-icon"><LayersIcon size={20} /></span>
              <div><strong>Nothing stored server-side.</strong> No accounts, no database. Your token is used per-request and discarded.</div>
            </li>
          </ul>
        </section>

        {/* FAQ */}
        <section id="faq" className="landing-section">
          <p className="eyebrow">FAQ</p>
          <h2 className="landing-h2">Questions, answered straight</h2>
          <div className="faq-list">
            {FAQS.map(({ q, a }) => (
              <details className="faq-item" key={q}>
                <summary>
                  <span>{q}</span>
                  <span className="faq-marker" aria-hidden="true">+</span>
                </summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="landing-cta">
          <h2 className="landing-h2">Audit a page in about a minute.</h2>
          <p className="muted">No account, no install. Bring a URL.</p>
          <div className="hero-actions" style={{ justifyContent: "center" }}>
            <Link className="btn-link primary" to="/app">Launch app →</Link>
            <a className="btn-link ghost" href={REPO_URL} target="_blank" rel="noreferrer">View source</a>
          </div>
        </section>

        {/* Legal */}
        <section id="privacy" className="landing-legal">
          <h2 className="landing-legal-h">Privacy</h2>
          <p>
            This tool does not use accounts, cookies for tracking, or a user database. URLs you scan
            are processed per-request to run the audit and are not retained server-side. Your GitHub
            token is transmitted only to perform the GitHub actions you trigger, is never written to
            logs or storage, and is discarded after the request. A small &ldquo;recent scans&rdquo;
            list is kept only in your browser&rsquo;s local storage and you can clear it at any time.
          </p>
        </section>
        <section id="terms" className="landing-legal">
          <h2 className="landing-legal-h">Terms &amp; usage</h2>
          <p>
            Provided as-is, without warranty, as an open-source assistant for accessibility work.
            Only scan URLs you&rsquo;re authorized to test. Automated checks catch a subset of WCAG
            issues and don&rsquo;t replace manual testing with assistive technology. Requests are
            rate-limited and subject to fair use.
          </p>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
