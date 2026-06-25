import json
import re
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from backend.app.core.security import validate_public_url, validate_repository

_GITHUB_USERNAME = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
_LABEL_PATTERN = re.compile(r"^[a-zA-Z0-9 _\-.:]+$")
_GITHUB_TOKEN = re.compile(r"^(ghp_|ghs_|gho_|github_pat_)[A-Za-z0-9_]+$")

Severity = Literal["Critical", "High", "Medium", "Low"]


class ScanIssue(BaseModel):
    id: str
    title: str
    severity: Severity
    wcag_criterion: str
    wcag_url: str
    element: str
    selector: str
    impact: str
    description: str
    occurrences: int = Field(ge=1)
    tags: list[str]
    # Base64 PNG data URI of the offending element, captured only on a live
    # scan. None for fallback/demo issues — never fabricate scan evidence.
    screenshot: str | None = None


class ScanRequest(BaseModel):
    url: HttpUrl
    # Optional Playwright storage state (cookies + localStorage) for scanning a
    # page behind a login. Used once for the scan, never persisted or logged.
    storage_state: dict | None = None

    @field_validator("url")
    @classmethod
    def require_public_url(cls, value: HttpUrl) -> HttpUrl:
        validate_public_url(str(value))
        return value

    @field_validator("storage_state")
    @classmethod
    def validate_storage_state(cls, value: dict | None) -> dict | None:
        if value is None:
            return value
        allowed = {"cookies", "origins"}
        if not set(value).issubset(allowed):
            raise ValueError("storage_state may only contain 'cookies' and 'origins'")
        for key in allowed:
            if key in value and not isinstance(value[key], list):
                raise ValueError(f"storage_state '{key}' must be a list")
        if len(json.dumps(value)) > 1_000_000:
            raise ValueError("storage_state exceeds the maximum allowed size")
        return value


class ScanResponse(BaseModel):
    url: str
    issues: list[ScanIssue]
    summary: dict[str, int]
    source: Literal["live", "fallback"]
    notice: str | None = None


class SearchRequest(BaseModel):
    issue: ScanIssue
    repo: str | None = None
    github_token: str | None = None

    @field_validator("repo")
    @classmethod
    def validate_optional_repo(cls, value: str | None) -> str | None:
        return validate_repository(value) if value else value

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, value: str | None) -> str | None:
        if value is not None and (not _GITHUB_TOKEN.match(value) or len(value) > 256):
            raise ValueError("Invalid GitHub token format")
        return value


class SimilarIssue(BaseModel):
    number: int
    title: str
    state: str
    labels: list[str]
    assignee: str | None = None
    created_at: str
    body: str
    html_url: str
    similarity_score: float
    similarity_explanation: str


class SearchResponse(BaseModel):
    similar_issues: list[SimilarIssue]
    ai_summary: str
    source: Literal["github", "fallback"]


class GeneratedIssue(BaseModel):
    title: str = Field(max_length=256)
    description: str
    repro_steps: list[str] = Field(min_length=1)
    expected_result: str
    actual_result: str
    severity: Severity
    labels: list[str] = Field(max_length=10)
    acceptance_criteria: list[str] = Field(min_length=1)
    environment: str
    wcag_reference: str
    assignee: str = ""
    milestone: str = ""

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, values: list[str]) -> list[str]:
        for label in values:
            if not _LABEL_PATTERN.fullmatch(label.strip()) or len(label) > 50:
                raise ValueError(f"Invalid label: {label!r}")
        return [v.strip() for v in values]

    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, value: str) -> str:
        if value and not _GITHUB_USERNAME.fullmatch(value):
            raise ValueError(f"Invalid GitHub username: {value!r}")
        return value


class GenerateRequest(BaseModel):
    url: HttpUrl
    scan_issue: ScanIssue
    reference_issue: SimilarIssue | None = None

    @field_validator("url")
    @classmethod
    def require_public_url(cls, value: HttpUrl) -> HttpUrl:
        validate_public_url(str(value))
        return value


class GenerateResponse(BaseModel):
    generated_issue: GeneratedIssue
    source: Literal["ollama", "anthropic", "groq", "template"]


class LogRequest(BaseModel):
    repo: str
    issue_data: GeneratedIssue
    github_token: str | None = None
    # Optional base64 PNG data URI carried over from the scanned issue, embedded
    # into the logged issue. Bounded to keep repo commits small.
    screenshot: str | None = None

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, value: str) -> str:
        return validate_repository(value)

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, value: str | None) -> str | None:
        if value is not None and (not _GITHUB_TOKEN.match(value) or len(value) > 256):
            raise ValueError("Invalid GitHub token format")
        return value

    @field_validator("screenshot")
    @classmethod
    def validate_screenshot(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("data:image/png;base64,"):
            raise ValueError("Screenshot must be a PNG data URI")
        if len(value) > 6_000_000:  # ~4.5 MB decoded; bounds repo commit size
            raise ValueError("Screenshot exceeds the maximum allowed size")
        return value


class LogResponse(BaseModel):
    issue_number: int
    html_url: str
