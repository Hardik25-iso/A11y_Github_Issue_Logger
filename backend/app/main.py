from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.app.core.config import get_settings
from backend.app.core.logging import RequestIDMiddleware
from backend.app.routers import generation, github, scan, system
from backend.app.services.scanner import close_browser_pool, init_browser_pool

load_dotenv()
settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_browser_pool()
    yield
    await close_browser_pool()


app = FastAPI(title="A11y GitHub Issue Logger API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
_origins = list(settings.frontend_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.include_router(system.router)
app.include_router(scan.router)
app.include_router(github.router)
app.include_router(generation.router)
