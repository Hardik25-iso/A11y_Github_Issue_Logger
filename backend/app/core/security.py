import ipaddress
import re
import socket
from urllib.parse import urlsplit

from pydantic_core import PydanticCustomError

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}


def validate_public_url(url: str) -> str:
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")

    if parsed.scheme not in {"http", "https"} or not hostname:
        raise PydanticCustomError("public_url", "URL must be a valid HTTP or HTTPS address")
    if parsed.username or parsed.password:
        raise PydanticCustomError("public_url", "URLs containing credentials are not allowed")
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise PydanticCustomError("public_url", "Local and internal URLs are not allowed")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if not address.is_global:
        raise PydanticCustomError("public_url", "Local, private, and reserved IP addresses are not allowed")
    return url


def validate_resolved_public_url(url: str) -> str:
    validate_public_url(url)
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    try:
        results = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise PydanticCustomError("public_url", "URL hostname could not be resolved") from exc

    addresses = {item[4][0] for item in results}
    if not addresses:
        raise PydanticCustomError("public_url", "URL hostname could not be resolved")

    for raw_address in addresses:
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise PydanticCustomError("public_url", "URL resolved to an invalid IP address") from exc
        if not address.is_global:
            raise PydanticCustomError("public_url", "URL resolves to a local, private, or reserved address")
    return url


def validate_repository(repo: str) -> str:
    value = repo.strip()
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise PydanticCustomError("repository", "Repository must use the owner/name format")
    return value


# Link-local and cloud metadata ranges blocked even for operator-configured Ollama URL
_BLOCKED_PRIVATE_PREFIXES = ("169.254.", "100.64.")


def validate_ollama_base_url(url: str) -> None:
    """Validate that OLLAMA_BASE_URL cannot point to cloud metadata or link-local addresses."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"OLLAMA_BASE_URL must be http or https, got: {url}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise ValueError(f"OLLAMA_BASE_URL has no hostname: {url}")
    try:
        address = ipaddress.ip_address(hostname)
        if address.is_link_local or any(str(address).startswith(p) for p in _BLOCKED_PRIVATE_PREFIXES):
            raise ValueError(
                f"OLLAMA_BASE_URL resolves to a blocked address ({address}). "
                "Cloud metadata and link-local addresses are not allowed."
            )
    except ValueError as exc:
        if "OLLAMA_BASE_URL" in str(exc):
            raise
