from typing import Literal, cast

from fastapi import APIRouter, Request

from backend.app.core.config import get_settings
from backend.app.core.limiter import limiter
from backend.app.models import LogRequest, LogResponse, SearchRequest, SearchResponse
from backend.app.services.github import create_issue, search_issues

router = APIRouter(prefix="/api", tags=["github"])


@router.post("/search-issues", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    repo = body.repo or get_settings().default_repo
    issues, summary, source = await search_issues(body.issue, repo, body.github_token)
    return SearchResponse(
        similar_issues=issues,
        ai_summary=summary,
        source=cast(Literal["github", "fallback"], source),
    )


@router.post("/log-issue", response_model=LogResponse)
@limiter.limit("5/minute")
async def log_issue(request: Request, body: LogRequest) -> LogResponse:
    result = await create_issue(body.repo, body.issue_data, body.github_token)
    return LogResponse(issue_number=result["number"], html_url=result["html_url"])
