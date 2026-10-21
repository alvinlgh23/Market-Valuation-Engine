from __future__ import annotations


class AnalysisError(Exception):
    status_code = 502
    public_message = "Analysis failed. Please try again."


class AnalysisTimeoutError(AnalysisError):
    status_code = 504
    public_message = "Analysis timed out. Please try again."


class ProviderRateLimitError(AnalysisError):
    status_code = 503
    public_message = "Market data provider is temporarily rate-limited. Please try again later."


class ProviderUnavailableError(AnalysisError):
    status_code = 503
    public_message = "Market data provider is temporarily unavailable. Please try again later."
