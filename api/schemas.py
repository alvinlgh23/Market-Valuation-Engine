from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    mode: str = Field(..., examples=["company"])
    input: str | None = Field(None, examples=["NVDA"])


class AnalyzeResponse(BaseModel):
    ok: bool
    mode: str
    input: str
    command: str
    output: str
    duration_ms: int
    cached: bool = False
    timestamp_utc: str
    truncated: bool = False
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    cache_enabled: bool


class ModesResponse(BaseModel):
    modes: list[dict[str, object]]
