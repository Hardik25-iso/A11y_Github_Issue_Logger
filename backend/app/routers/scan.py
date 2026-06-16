from fastapi import APIRouter

from backend.app.models import ScanRequest, ScanResponse
from backend.app.services.scanner import scan_url

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest) -> ScanResponse:
    return await scan_url(str(request.url))

