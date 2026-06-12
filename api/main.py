from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .cache import CACHEABLE_MODES, analysis_cache, cache_enabled, cache_key, ttl_for_mode
from .errors import AnalysisError
from .modes import public_modes
from .modes import command_for
from .rate_limit import RateLimitExceeded, enforce_rate_limit
from .runner import run_analysis
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, ModesResponse


app = FastAPI(
    title="Market Intelligence API",
    version="1.0.0",
    description="API wrapper for the Market Intelligence CLI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://alvin-lim.com", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="market-intelligence-api", version="v1", cache_enabled=cache_enabled())


@app.get("/v1/modes", response_model=ModesResponse)
def modes() -> ModesResponse:
    return ModesResponse(modes=public_modes())


def error_response(status_code: int, message: str, duration_ms: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "cached": False,
            "duration_ms": duration_ms,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "error": message,
        },
    )


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(request: Request, payload: AnalyzeRequest) -> AnalyzeResponse | JSONResponse:
    started = time.monotonic()
    try:
        enforce_rate_limit(request)
    except ValueError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return error_response(400, str(exc), duration_ms)
    except RateLimitExceeded as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return error_response(429, str(exc), duration_ms)

    try:
        normalized_mode, _args, normalized_input = command_for(payload.mode, payload.input)
    except ValueError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return error_response(400, str(exc), duration_ms)

    key = cache_key(normalized_mode, normalized_input)
    if cache_enabled() and normalized_mode in CACHEABLE_MODES:
        cached = analysis_cache.get(key)
        if cached is not None:
            duration_ms = int((time.monotonic() - started) * 1000)
            cached["cached"] = True
            cached["duration_ms"] = duration_ms
            cached["timestamp_utc"] = datetime.now(UTC).isoformat()
            return AnalyzeResponse(**cached)

    try:
        result = run_analysis(payload.mode, payload.input)
    except AnalysisError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return error_response(exc.status_code, exc.public_message, duration_ms)

    if cache_enabled() and normalized_mode in CACHEABLE_MODES:
        analysis_cache.set(key, result, ttl_for_mode(normalized_mode))

    return AnalyzeResponse(**result)
