import { Link } from "react-router-dom";
import SiteFooter from "../components/SiteFooter";
import SiteHeader from "../components/SiteHeader";

export default function NotFound() {
  return (
    <div className="page-wrapper">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <SiteHeader variant="marketing" />
      <main id="main-content" className="notfound">
        <p className="eyebrow">Error · 404</p>
        <h1>This page took a detour.</h1>
        <p className="notfound-sub">
          The page you&rsquo;re looking for doesn&rsquo;t exist. Let&rsquo;s get you back on track.
        </p>
        <div className="hero-actions">
          <Link className="btn-link primary" to="/">Back to home</Link>
          <Link className="btn-link ghost" to="/app">Launch app →</Link>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
