import socket

import pytest
from pydantic_core import PydanticCustomError

from backend.app.core.security import validate_resolved_public_url


def fake_getaddrinfo(addresses):
    def resolver(hostname, port, type=socket.SOCK_STREAM):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 0)) for address in addresses]

    return resolver


def test_validate_resolved_public_url_accepts_public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo(["93.184.216.34"]))
    assert validate_resolved_public_url("https://example.com") == "https://example.com"


def test_validate_resolved_public_url_rejects_private_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo(["10.0.0.5"]))
    with pytest.raises(PydanticCustomError):
        validate_resolved_public_url("https://example.com")


def test_validate_resolved_public_url_rejects_unresolvable_host(monkeypatch):
    def resolver(hostname, port, type=socket.SOCK_STREAM):
        raise socket.gaierror("not found")

    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    with pytest.raises(PydanticCustomError):
        validate_resolved_public_url("https://missing.example")

