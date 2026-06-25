from fastapi import APIRouter, Request

from backend.app.core.limiter import limiter
from backend.app.models import ScanRequest, ScanResponse
from backend.app.services.scanner import scan_url

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
@limiter.limit("10/minute")
async def scan(request: Request, body: ScanRequest) -> ScanResponse:
    return await scan_url(str(body.url), body.storage_state)
