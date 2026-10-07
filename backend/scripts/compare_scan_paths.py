"""Parity harness: prove local and remote browsers produce the same axe results.

Runs each URL several times through the scanner's own _run_axe (bypassing the
semaphore and the fallback, so a failure is an error, never demo data) and
records the normalized violations, browser version, wall time, and how many
requests went through the route guard.

    # Local Chromium (BROWSER_WS_ENDPOINT unset)
    python -m backend.scripts.compare_scan_paths run --out local.json
    # Remote browser
    BROWSER_WS_ENDPOINT=wss://... python -m backend.scripts.compare_scan_paths run --out remote.json
    # Compare: run-to-run noise inside each file, then local vs remote
    python -m backend.scripts.compare_scan_paths diff local.json remote.json

Exit code of `diff` is 1 when an exact-match URL differs or a live URL's
cross-path diff exceeds the local run-to-run noise.
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from backend.app.services import browser, scanner

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
FIXTURE_HOST = "fixture.a11y.test"

# URLs whose results must match exactly across paths; the rest are live sites
# where the cross-path diff only has to stay within run-to-run noise.
EXACT_URLS = [
    f"https://{FIXTURE_HOST}/violations.html",
    # Static page. (The W3C BAD demo was the first choice, but w3.org serves
    # a Cloudflare bot challenge whose CSP blocks axe injection.)
    "https://info.cern.ch/hypertext/WWW/TheProject.html",
]
LIVE_URLS = [
    "https://example.com/",
    "https://www.python.org/",
    "https://react.dev/",
]


def _issue_key(violation: dict) -> str:
    """Stable identity for one violation, independent of node order."""
    nodes = violation.get("nodes", [])
    targets = sorted(scanner._node_selector([node]) for node in nodes)
    issue = scanner.normalize_violations([violation])[0]
    return json.dumps(
        [issue.id, issue.severity, issue.wcag_criterion, issue.occurrences, targets]
    )


def _install_instrumentation(counter: dict) -> None:
    """Serve the fixture host from disk and count guarded requests."""
    real_route = scanner._guarded_route
    real_validate = scanner.validate_resolved_public_url

    def validate(url: str) -> str:
        if urlsplit(url).hostname == FIXTURE_HOST:
            return url
        return real_validate(url)

    async def route(route_obj):
        counter["requests"] += 1
        parsed = urlsplit(route_obj.request.url)
        if parsed.hostname == FIXTURE_HOST:
            path = FIXTURE_DIR / parsed.path.lstrip("/")
            if path.is_file():
                await route_obj.fulfill(path=str(path))
            else:
                await route_obj.abort()
            return
        await real_route(route_obj)

    scanner.validate_resolved_public_url = validate  # type: ignore[assignment]
    scanner._guarded_route = route  # type: ignore[assignment]


async def _browser_version() -> str:
    async with browser.browser_session() as session:
        return session.version


async def _run(urls: list[str], runs: int) -> dict:
    counter = {"requests": 0}
    _install_instrumentation(counter)
    axe_path = scanner.axe_script_path()
    await browser.init_browser_pool()
    report: dict = {
        "mode": "remote" if os.getenv("BROWSER_WS_ENDPOINT") else "local",
        "browser_version": await _browser_version(),
        "results": {},
    }
    for url in urls:
        report["results"][url] = []
        for attempt in range(runs):
            counter["requests"] = 0
            started = time.perf_counter()
            try:
                violations, final_url = await scanner._run_axe(url, axe_path)
                entry = {
                    "keys": sorted(_issue_key(v) for v in violations),
                    "final_url": final_url,
                }
            except Exception as exc:  # recorded, never silently skipped
                entry = {"error": f"{type(exc).__name__}: {exc}"[:300]}
            entry["seconds"] = round(time.perf_counter() - started, 2)
            entry["guarded_requests"] = counter["requests"]
            report["results"][url].append(entry)
            print(f"[{report['mode']}] run {attempt + 1}/{runs} {url}: "
                  f"{entry.get('error') or str(len(entry['keys'])) + ' violations'} "
                  f"in {entry['seconds']}s ({entry['guarded_requests']} guarded requests)")
    await browser.close_browser_pool()
    return report


def _symmetric_diff(a: list[str], b: list[str]) -> tuple[set, set]:
    return set(b) - set(a), set(a) - set(b)


def _max_noise(runs: list[dict]) -> int:
    """Largest symmetric difference between any two runs of the same path."""
    ok = [r["keys"] for r in runs if "keys" in r]
    worst = 0
    for i in range(len(ok)):
        for j in range(i + 1, len(ok)):
            added, removed = _symmetric_diff(ok[i], ok[j])
            worst = max(worst, len(added) + len(removed))
    return worst


def _timing(runs: list[dict]) -> str:
    seconds = sorted(r["seconds"] for r in runs)
    if not seconds:
        return "no runs"
    p95 = seconds[min(len(seconds) - 1, round(0.95 * (len(seconds) - 1)))]
    return f"p50 {statistics.median(seconds):.1f}s p95 {p95:.1f}s"


def _diff(local_path: str, remote_path: str) -> int:
    local = json.loads(Path(local_path).read_text())
    remote = json.loads(Path(remote_path).read_text())
    print(f"browser: {local['mode']}={local['browser_version']}  "
          f"{remote['mode']}={remote['browser_version']}")
    failed = False
    for url in dict.fromkeys([*local["results"], *remote["results"]]):
        local_runs = local["results"].get(url, [])
        remote_runs = remote["results"].get(url, [])
        print(f"\n== {url}")
        print(f"   {local['mode']}: {_timing(local_runs)}   {remote['mode']}: {_timing(remote_runs)}")
        # Errored runs (e.g. a flaky network) are shown and excluded; a URL
        # only fails outright when one side has no successful run at all.
        for side, runs in ((local["mode"], local_runs), (remote["mode"], remote_runs)):
            for run in runs:
                if "error" in run:
                    print(f"   errored {side} run excluded: {run['error'].splitlines()[0]}")
        local_ok = [r for r in local_runs if "keys" in r]
        remote_ok = [r for r in remote_runs if "keys" in r]
        if not local_ok or not remote_ok:
            print("   FAIL no successful run on one side")
            failed = True
            continue
        noise = max(_max_noise(local_ok), _max_noise(remote_ok))
        added, removed = _symmetric_diff(local_ok[0]["keys"], remote_ok[0]["keys"])
        cross = len(added) + len(removed)
        exact = url in EXACT_URLS
        ok = cross == 0 if exact else cross <= noise
        print(f"   {'PASS' if ok else 'FAIL'} cross-path diff={cross} run-to-run noise={noise}"
              f" ({'exact match required' if exact else 'must be <= noise'})")
        for key in sorted(added):
            print(f"     + {remote['mode']} only: {key}")
        for key in sorted(removed):
            print(f"     - {local['mode']} only: {key}")
        failed |= not ok
    print("\nRESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", required=True)
    run.add_argument("--runs", type=int, default=3)
    run.add_argument("--url", action="append", help="override the URL list (repeatable)")
    diff = sub.add_parser("diff")
    diff.add_argument("local")
    diff.add_argument("remote")
    args = parser.parse_args()

    if args.command == "diff":
        return _diff(args.local, args.remote)

    os.environ["ENABLE_LIVE_SCAN"] = "true"
    report = asyncio.run(_run(args.url or EXACT_URLS + LIVE_URLS, args.runs))
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sys.exit(main())
