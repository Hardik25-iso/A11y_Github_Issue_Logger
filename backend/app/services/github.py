import httpx
from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.models import GeneratedIssue, ScanIssue, SimilarIssue

GITHUB_API = "https://api.github.com"
MAX_SEARCH_RESULTS = 5
STOP_WORDS = {
    "and",
    "are",
    "for",
    "has",
    "must",
    "the",
    "with",
    "without",
}


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def default_repo() -> str:
    return get_settings().default_repo


def _response_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    message = payload.get("message") if isinstance(payload, dict) else None

    if response.status_code == 401:
        return "GitHub token is invalid or expired."
    if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
        reset = response.headers.get("x-ratelimit-reset")
        return f"GitHub rate limit exceeded. Try again later{f' after reset {reset}' if reset else ''}."
    if response.status_code == 403:
        return "GitHub rejected the request. Check token permissions and repository access."
    if response.status_code == 404:
        return "GitHub repository was not found or the token lacks access."
    if response.status_code == 422:
        return f"GitHub rejected the request. {message or 'Check the repository, labels, and issue payload.'}"
    return message or "GitHub request failed."


def _keywords(issue: ScanIssue) -> list[str]:
    raw_terms = [
        issue.wcag_criterion,
        issue.id,
        *issue.title.replace("/", " ").replace("-", " ").split(),
        *issue.selector.replace(".", " ").replace("#", " ").replace(">", " ").split(),
        *issue.tags,
    ]
    seen = set()
    terms = []
    for term in raw_terms:
        cleaned = term.lower().strip("`'\"()[]{}:;,")
        if len(cleaned) < 3 or cleaned in STOP_WORDS or cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(cleaned)
    return terms[:8]


def build_search_query(issue: ScanIssue, repo: str) -> str:
    return f"{' '.join(_keywords(issue))} repo:{repo} is:issue"


def _score_result(issue: ScanIssue, item: dict) -> tuple[float, str]:
    labels = [label.get("name", "") for label in item.get("labels", [])]
    haystack = " ".join(
        [
            item.get("title", ""),
            item.get("body") or "",
            " ".join(labels),
        ]
    ).lower()
    score = 0.0
    reasons = []

    if issue.wcag_criterion.lower() in haystack or issue.wcag_criterion.replace(".", "") in haystack:
        score += 3.0
        reasons.append("same WCAG criterion")

    title_terms = [term for term in _keywords(issue) if term not in {"accessibility", "wcag"}]
    matched_terms = [term for term in title_terms if term in haystack]
    if matched_terms:
        score += min(3.0, len(matched_terms) * 0.75)
        reasons.append(f"shared terms: {', '.join(matched_terms[:3])}")

    if "accessibility" in haystack or "a11y" in haystack:
        score += 1.0
        reasons.append("accessibility context")

    if item.get("state") == "open":
        score += 0.5
        reasons.append("open issue")

    score = max(1.0, min(10.0, round(score + 2.0, 1)))
    explanation = "Matched by " + "; ".join(reasons) + "." if reasons else "Low-confidence keyword match."
    return score, explanation


def _normalize_issue(item: dict, issue: ScanIssue) -> SimilarIssue | None:
    try:
        score, explanation = _score_result(issue, item)
        return SimilarIssue(
            number=item["number"],
            title=item["title"],
            state=item["state"],
            labels=[label.get("name", "") for label in item.get("labels", [])],
            assignee=(item.get("assignee") or {}).get("login"),
            created_at=item["created_at"],
            body=(item.get("body") or "")[:500],
            html_url=item["html_url"],
            similarity_score=score,
            similarity_explanation=explanation,
        )
    except (KeyError, TypeError):
        return None


def fallback_results(issue: ScanIssue) -> list[SimilarIssue]:
    return [
        SimilarIssue(
            number=42,
            title=f"Accessibility: resolve {issue.title.lower()}",
            state="open",
            labels=["accessibility", "bug", "needs-triage"],
            assignee=None,
            created_at="2026-05-20T09:30:00Z",
            body=f"A similar issue affects the primary navigation. WCAG {issue.wcag_criterion}.",
            html_url="https://github.com/example/repository/issues/42",
            similarity_score=8.7,
            similarity_explanation="Matches the same WCAG criterion and affected interaction pattern.",
        ),
        SimilarIssue(
            number=18,
            title="Improve accessible names across shared controls",
            state="closed",
            labels=["accessibility", "design-system"],
            assignee="octocat",
            created_at="2026-03-12T14:00:00Z",
            body="Shared controls need consistent accessible names and automated coverage.",
            html_url="https://github.com/example/repository/issues/18",
            similarity_score=6.4,
            similarity_explanation="Related remediation pattern, but it targets shared components more broadly.",
        ),
    ]


async def search_issues(issue: ScanIssue, repo: str) -> tuple[list[SimilarIssue], str, str]:
    if not repo:
        return fallback_results(issue), "Demo matches shown because no target repository is configured.", "fallback"

    params: dict[str, str | int] = {"q": build_search_query(issue, repo), "per_page": MAX_SEARCH_RESULTS}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{GITHUB_API}/search/issues", params=params, headers=_headers())
        if response.status_code >= 400:
            return fallback_results(issue), f"{_response_message(response)} Demo matches are shown.", "fallback"
        normalized = [_normalize_issue(item, issue) for item in response.json().get("items", [])[:MAX_SEARCH_RESULTS]]
        results = [r for r in normalized if r is not None]
        results.sort(key=lambda item: item.similarity_score, reverse=True)
        if not results:
            return [], f"No similar issues were found in {repo}.", "github"
        return results, f"Found {len(results)} related issues in {repo}, ranked by keyword similarity.", "github"
    except httpx.HTTPError:
        return fallback_results(issue), "GitHub search was unavailable; demo matches are shown.", "fallback"


def markdown_body(issue: GeneratedIssue) -> str:
    steps = "\n".join(f"{index}. {step}" for index, step in enumerate(issue.repro_steps, 1))
    criteria = "\n".join(f"- [ ] {item}" for item in issue.acceptance_criteria)
    return f"""## Description
{issue.description}

## Steps to reproduce
{steps}

## Expected result
{issue.expected_result}

## Actual result
{issue.actual_result}

## Acceptance criteria
{criteria}

## Environment
{issue.environment}

## WCAG reference
{issue.wcag_reference}

**Severity:** {issue.severity}

---
Generated by A11y GitHub Issue Logger.
"""


async def create_issue(repo: str, issue: GeneratedIssue) -> dict:
    if not get_settings().github_token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN is required to log an issue.")
    payload = {
        "title": issue.title,
        "body": markdown_body(issue),
        "labels": issue.labels,
        "assignees": [issue.assignee] if issue.assignee else [],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{GITHUB_API}/repos/{repo}/issues", json=payload, headers=_headers())
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_response_message(response))
    return response.json()
