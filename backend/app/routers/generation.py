from typing import Literal, cast

from fastapi import APIRouter

from backend.app.models import GenerateRequest, GenerateResponse
from backend.app.services.generator import generate_issue

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate-issue", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    issue, source = await generate_issue(str(request.url), request.scan_issue, request.reference_issue)
    return GenerateResponse(
        generated_issue=issue,
        source=cast(Literal["ollama", "anthropic", "template"], source),
    )

