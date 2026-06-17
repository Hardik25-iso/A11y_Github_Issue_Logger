from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.models import ScanRequest, ScanResponse
from backend.app.services.scanner import scan_url

router = APIRouter(prefix="/api", tags=["scan"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/scan", response_model=ScanResponse)
@limiter.limit("10/minute")
async def scan(request: Request, body: ScanRequest) -> ScanResponse:
    return await scan_url(str(body.url))
