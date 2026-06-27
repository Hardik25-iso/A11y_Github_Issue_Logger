import { REPO_URL } from "./SiteHeader";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-brand">
          <span className="brand-mark">A11Y</span>
          <span>
            Issue Logger — turn WCAG findings into engineering action.
            <br className="footer-br" />
            <span className="muted">No signup · your token, your repos · nothing stored.</span>
          </span>
        </div>
        <nav className="site-footer-links" aria-label="Footer">
          <a href="/#how">How it works</a>
          <a href="/#features">Features</a>
          <a href="/#faq">FAQ</a>
          <a href="/#privacy">Privacy</a>
          <a href="/#terms">Terms</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer">GitHub</a>
          <a href="https://www.w3.org/WAI/standards-guidelines/wcag/" target="_blank" rel="noreferrer">
            WCAG guidelines
          </a>
        </nav>
      </div>
    </footer>
  );
}
