from typing import Literal, cast

from fastapi import APIRouter, Request

from backend.app.core.limiter import limiter
from backend.app.models import GenerateRequest, GenerateResponse
from backend.app.services.generator import generate_issue

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate-issue", response_model=GenerateResponse)
@limiter.limit("15/minute")
async def generate(request: Request, body: GenerateRequest) -> GenerateResponse:
    issue, source = await generate_issue(str(body.url), body.scan_issue, body.reference_issue)
    return GenerateResponse(
        generated_issue=issue,
        source=cast(Literal["ollama", "anthropic", "groq", "template"], source),
    )
