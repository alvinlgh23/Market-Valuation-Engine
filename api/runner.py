from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .errors import AnalysisError, AnalysisTimeoutError, ProviderRateLimitError, ProviderUnavailableError
from .modes import command_for


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_OUTPUT_CHARS = 60_000


PROVIDER_RATE_LIMIT_MARKERS = (
    "429",
    "too many requests",
    "rate limit",
    "rate-limited",
    "rate limited",
)

PROVIDER_FAILURE_MARKERS = (
    "failed download",
    "connection error",
    "connection aborted",
    "connection reset",
    "read timed out",
    "timeout",
    "temporarily unavailable",
    "name resolution",
    "network is unreachable",
)


def _int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _provider_error_for(detail: str) -> AnalysisError | None:
    lowered = detail.lower()
    if any(marker in lowered for marker in PROVIDER_RATE_LIMIT_MARKERS):
        return ProviderRateLimitError()
    if any(marker in lowered for marker in PROVIDER_FAILURE_MARKERS):
        return ProviderUnavailableError()
    return None


def run_analysis(mode: str, input_value: str | None = None) -> dict[str, object]:
    normalized_mode, args, normalized_input = command_for(mode, input_value)
    timeout = _int_from_env("ANALYSIS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    max_output = _int_from_env("MAX_OUTPUT_CHARS", DEFAULT_MAX_OUTPUT_CHARS)
    command = [sys.executable, "model.py", *args]
    started = time.monotonic()

    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalysisTimeoutError() from exc

    duration_ms = int((time.monotonic() - started) * 1000)
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if completed.returncode != 0:
        detail = stderr or stdout or f"Process exited with code {completed.returncode}."
        provider_error = _provider_error_for(detail)
        if provider_error is not None:
            raise provider_error
        raise AnalysisError(detail[:2000])

    raw_output = stdout or stderr
    provider_error = _provider_error_for(raw_output)
    if provider_error is not None:
        raise provider_error

    truncated = len(raw_output) > max_output
    output = raw_output[:max_output]
    if truncated:
        output = f"{output}\n\n[Output truncated at {max_output} characters.]"

    return {
        "ok": True,
        "mode": normalized_mode,
        "input": normalized_input,
        "command": " ".join(["python", "model.py", *args]),
        "output": output,
        "duration_ms": duration_ms,
        "truncated": truncated,
        "cached": False,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "error": None,
    }
