from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .modes import public_modes
from .runner import AnalysisError, run_analysis
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
    return HealthResponse(status="ok", service="market-intelligence-api")


@app.get("/v1/modes", response_model=ModesResponse)
def modes() -> ModesResponse:
    return ModesResponse(modes=public_modes())


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return AnalyzeResponse(**run_analysis(request.mode, request.input))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
