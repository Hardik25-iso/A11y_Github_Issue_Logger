from typing import Literal, cast

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.models import LogRequest, LogResponse, SearchRequest, SearchResponse
from backend.app.services.github import create_issue, search_issues

router = APIRouter(prefix="/api", tags=["github"])


@router.post("/search-issues", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    repo = request.repo or get_settings().default_repo
    issues, summary, source = await search_issues(request.issue, repo)
    return SearchResponse(
        similar_issues=issues,
        ai_summary=summary,
        source=cast(Literal["github", "fallback"], source),
    )


@router.post("/log-issue", response_model=LogResponse)
async def log_issue(request: LogRequest) -> LogResponse:
    result = await create_issue(request.repo, request.issue_data)
    return LogResponse(issue_number=result["number"], html_url=result["html_url"])
