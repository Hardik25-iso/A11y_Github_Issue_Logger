from fastapi import APIRouter, Request

from backend.app.core.limiter import limiter
from backend.app.models import LoginRequest, LoginResponse
from backend.app.services.auth import login_and_capture_session

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    return await login_and_capture_session(
        str(body.login_url), body.username, body.password, body.selectors
    )
