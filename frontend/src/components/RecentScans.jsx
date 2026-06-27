import { useSyncExternalStore } from "react";
import { clearHistory, getHistory, subscribe } from "../services/history";

export function useHistory() {
  return useSyncExternalStore(subscribe, getHistory, getHistory);
}

/** Session/local recent scans — honest, browser-only, clearable. */
export default function RecentScans({ onPick }) {
  const history = useHistory();
  if (history.length === 0) return null;

  return (
    <section className="recent" aria-label="Recent scans in this browser">
      <div className="recent-head">
        <p className="eyebrow" style={{ marginBottom: 0 }}>Recent scans · this browser</p>
        <button type="button" className="ghost recent-clear" onClick={clearHistory}>Clear</button>
      </div>
      <ul className="recent-list">
        {history.map((entry) => (
          <li className="recent-item" key={entry.id}>
            <button type="button" className="recent-url" onClick={() => onPick?.(entry.url)} title={`Reuse ${entry.url}`}>
              {entry.url}
            </button>
            <span className="recent-meta">
              <span className={`badge ${entry.source === "live" ? "open" : "closed"}`}>
                {entry.source === "live" ? "live" : "demo"}
              </span>
              <span className="muted">{entry.total} issue{entry.total === 1 ? "" : "s"}</span>
              {entry.logged.length > 0 && (
                <span className="recent-logged">
                  {entry.logged.map((l) => (
                    <a key={l.number} href={l.htmlUrl} target="_blank" rel="noreferrer">#{l.number}</a>
                  ))}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
