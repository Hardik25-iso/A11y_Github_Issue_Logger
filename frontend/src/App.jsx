import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing";
import NotFound from "./pages/NotFound";

// The workspace is heavier than the marketing page — load it on demand so the
// landing route stays light.
const Workspace = lazy(() => import("./pages/Workspace"));

function RouteFallback() {
  return (
    <div className="page-wrapper">
      <main id="main-content" className="loading-screen" style={{ minHeight: "100vh" }}>
        <div className="spinner" aria-hidden="true" />
        <p role="status">Loading the workspace…</p>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/app"
        element={
          <Suspense fallback={<RouteFallback />}>
            <Workspace />
          </Suspense>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
