import { Link } from "react-router-dom";

export const REPO_URL = "https://github.com/Hardik25-iso/A11y_Github_Issue_Logger";

/**
 * Shared top bar. `marketing` shows section nav + Launch app; `app` shows a
 * slim workspace bar with a New scan reset. The brand always links home.
 */
export default function SiteHeader({ variant = "marketing", onNewScan }) {
  return (
    <header>
      <Link className="brand" to="/" aria-label="A11y Issue Logger — home">
        <span className="brand-mark">A11Y</span>
        Issue Logger
      </Link>

      {variant === "marketing" ? (
        <nav className="site-nav" aria-label="Primary">
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
          <a href="#faq">FAQ</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer">GitHub</a>
          <Link className="btn-link primary nav-cta" to="/app">Launch app →</Link>
        </nav>
      ) : (
        <nav className="site-nav" aria-label="Workspace">
          <a href={REPO_URL} target="_blank" rel="noreferrer">GitHub</a>
          <button type="button" onClick={onNewScan}>New scan</button>
        </nav>
      )}
    </header>
  );
}
