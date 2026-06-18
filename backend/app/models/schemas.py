import re
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from backend.app.core.security import validate_public_url, validate_repository

_GITHUB_USERNAME = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
_LABEL_PATTERN = re.compile(r"^[a-zA-Z0-9 _\-.:]+$")

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


class ScanRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def require_public_url(cls, value: HttpUrl) -> HttpUrl:
        validate_public_url(str(value))
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

    @field_validator("repo")
    @classmethod
    def validate_optional_repo(cls, value: str | None) -> str | None:
        return validate_repository(value) if value else value


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

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, value: str) -> str:
        return validate_repository(value)


class LogResponse(BaseModel):
    issue_number: int
    html_url: str
