import json

from backend.app.models import GeneratedIssue, ScanIssue, SimilarIssue

SYSTEM_PROMPT = """You are an expert accessibility engineer.
Create a specific, actionable GitHub issue from the supplied scan evidence.
Return only valid JSON matching the supplied schema. Do not use markdown fences."""


def issue_generation_prompt(url: str, issue: ScanIssue, reference: SimilarIssue | None) -> str:
    payload = {
        "scanned_url": url,
        "scan_issue": issue.model_dump(),
        "reference_issue": reference.model_dump() if reference else None,
        "requirements": {
            "description": "Explain the technical failure, user impact, and occurrence count.",
            "repro_steps": "Provide 4-6 specific steps using the scanned URL.",
            "acceptance_criteria": "Provide 2-3 measurable resolution criteria.",
            "severity": "Preserve the scan severity.",
        },
        "required_schema": GeneratedIssue.model_json_schema(),
    }
    return json.dumps(payload)

