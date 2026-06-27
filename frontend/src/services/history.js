/**
 * Recent-scans history — local to THIS browser only (localStorage).
 * Not a server-side account: it just reflects the user's own actions so the
 * workspace feels stateful without inventing data. Capped and clearable.
 */
const KEY = "a11y.history.v1";
const MAX = 8;
const listeners = new Set();

function load() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(KEY));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

let cache = load();

function commit(next) {
  cache = next.slice(0, MAX);
  try {
    window.localStorage.setItem(KEY, JSON.stringify(cache));
  } catch {
    /* storage unavailable (private mode / quota) — keep in-memory only */
  }
  listeners.forEach((fn) => fn());
}

export function getHistory() {
  return cache;
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function clearHistory() {
  commit([]);
}

export function recordScan({ url, source, total }) {
  const entry = {
    id: `${Date.now()}`,
    url,
    source: source || "live",
    total: total ?? 0,
    logged: [],
    at: new Date().toISOString(),
  };
  // Collapse an immediate re-scan of the same URL into one entry.
  const rest = cache.filter((e) => e.url !== url);
  commit([entry, ...rest]);
}

export function recordLoggedIssue({ url, number, htmlUrl }) {
  const next = cache.map((e) =>
    e.url === url ? { ...e, logged: [{ number, htmlUrl }, ...e.logged] } : e,
  );
  commit(next);
}
