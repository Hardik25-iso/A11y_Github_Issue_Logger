import logging
import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Patterns that must never appear in log output
_SECRET_RE = re.compile(r"(Bearer\s+)(\S+)|(sk-ant-\S+|ghp_\S+|github_pat_\S+)", re.IGNORECASE)


def _redact(match: re.Match) -> str:
    if match.group(1):  # "Bearer <token>" — keep the prefix, redact only the token
        return f"{match.group(1)}[REDACTED]"
    return "[REDACTED]"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger("a11y_logger")


def _safe(message: str) -> str:
    """Redact secret-shaped strings before logging."""
    return _SECRET_RE.sub(_redact, message)


def log_info(message: str, **kwargs: object) -> None:
    logger.info(_safe(message), extra=kwargs)


def log_warning(message: str, **kwargs: object) -> None:
    logger.warning(_safe(message), extra=kwargs)


def log_error(message: str, exc: BaseException | None = None, **kwargs: object) -> None:
    logger.error(_safe(message), exc_info=exc is not None, extra=kwargs)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        log_info(
            f"{request.method} {request.url.path} {response.status_code} {duration_ms}ms rid={request_id}"
        )
        response.headers["X-Request-ID"] = request_id
        return response
