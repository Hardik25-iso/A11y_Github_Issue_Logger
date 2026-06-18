import json

from backend.app.models import ScanIssue

SYSTEM_PROMPT = """You are an accessibility bug triage expert.
Given a new accessibility finding and a list of candidate GitHub issues, score each candidate's relevance (1-10) and provide a one-sentence similarity explanation.
Higher scores mean closer matches — same WCAG criterion and component type is a strong signal.
Return only valid JSON matching the required schema. Do not use markdown fences."""


def similarity_ranking_prompt(issue: ScanIssue, candidates: list[dict]) -> str:
    payload = {
        "finding": {
            "title": issue.title,
            "wcag_criterion": issue.wcag_criterion,
            "severity": issue.severity,
            "impact": issue.impact,
            "tags": issue.tags,
        },
        "candidates": [
            {
                "number": c["number"],
                "title": c["title"],
                "body_excerpt": (c.get("body") or "")[:300],
            }
            for c in candidates
        ],
        "required_schema": {
            "ranked": [
                {
                    "number": "integer matching the candidate number",
                    "score": "float between 1.0 and 10.0",
                    "explanation": "one sentence explaining the similarity or difference",
                }
            ]
        },
    }
    return json.dumps(payload)
