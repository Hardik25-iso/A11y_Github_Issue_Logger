from backend.app.models import GeneratedIssue, ScanIssue, SimilarIssue
from backend.app.prompts.issue_generation import SYSTEM_PROMPT, issue_generation_prompt
from backend.app.services.ai_client import AIProviderError, generate_json


def template_issue(url: str, issue: ScanIssue) -> GeneratedIssue:
    return GeneratedIssue(
        title=f"[A11y][WCAG {issue.wcag_criterion}] {issue.title}",
        description=(
            f"The page at {url} contains {issue.occurrences} occurrence(s) of {issue.title.lower()}. "
            f"{issue.description} {issue.impact} The affected selector is `{issue.selector}`."
        ),
        repro_steps=[
            f"Open {url} in a supported browser.",
            "Open the browser developer tools and run an axe accessibility scan.",
            f"Locate the element matching `{issue.selector}`.",
            f"Inspect the reported WCAG {issue.wcag_criterion} violation.",
        ],
        expected_result=f"The element satisfies WCAG {issue.wcag_criterion} and exposes the required accessible information.",
        actual_result=f"The element fails WCAG {issue.wcag_criterion}: {issue.description}",
        severity=issue.severity,
        labels=["accessibility", "bug", f"wcag-{issue.wcag_criterion}", "needs-triage"],
        acceptance_criteria=[
            f"All affected elements satisfy WCAG {issue.wcag_criterion}.",
            "The page passes an automated axe scan for this rule.",
            "The fix is verified with keyboard and screen reader testing.",
        ],
        environment="Desktop browser; automated axe-core scan; verify with NVDA or VoiceOver",
        wcag_reference=issue.wcag_url,
    )


async def generate_issue(url: str, issue: ScanIssue, reference: SimilarIssue | None) -> tuple[GeneratedIssue, str]:
    try:
        data, provider = await generate_json(SYSTEM_PROMPT, issue_generation_prompt(url, issue, reference))
        return GeneratedIssue.model_validate(data), provider
    except (AIProviderError, ValueError):
        return template_issue(url, issue), "template"
