"""AI model plan, phase A: one connection layer for the AI roles (CHAINSTOX_AI_MODELS_PLAN.md).

Fixed rules decide the readings and tested code does every calculation; models only extract, flag and explain.
This module is the single door to the models used for "review" and "qa":

* one OpenAI-compatible chat call for every provider (Google AI Studio, OpenRouter, Groq);
* settings per role in config/llm_models.json; a role is off until the owner enables it and names a model;
* keys only from environment variables or the git-ignored .env, never from the config file;
* every call returns a result with its provider, model and status; a timeout, 429, server error, spent daily
  limit, missing key or disabled role is "UNAVAILABLE" - never an exception, never a quiet substitute;
* a fallback model is used only where the role lists one, and the result says which model answered;
* a call log in .cache/llm/calls.jsonl records role, provider, model, status, latency and sizes - not prompts.

Extraction (qualitative_evidence.py) keeps its own native Gemini path and is not routed through here.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "llm_models.json"
LOG_DIR = ROOT / ".cache" / "llm"
# Owner 2026-11-27: review and explain may fall back too (e.g. to Qwen when Nemotron's free limit is reached). Every
# result names the model that actually answered, and fallback replies pass the same quote and number checks.
ROLES_WITH_FALLBACK = {"qa", "review", "explain", "reader"}

# transport(url, headers, body, timeout) -> (http_status, parsed_json_or_None). Injected in tests.
Transport = Callable[[str, dict[str, str], dict[str, Any], float], tuple[int, Any]]


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"providers": {}, "roles": {}}


def _dotenv_value(names: list[str], dotenv_path: Path) -> str | None:
    if not dotenv_path.exists():
        return None
    for raw in dotenv_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.removeprefix("export ").strip() in names:
            cleaned = value.strip().strip("'").strip('"').strip()
            if cleaned:
                return cleaned
    return None


def provider_key(provider: dict[str, Any], dotenv_path: Path | None = None) -> str | None:
    names = list(provider.get("key_env") or [])
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if dotenv_path is None and os.environ.get("CHAINSTOX_IGNORE_DOTENV", "0") == "1":
        return None
    return _dotenv_value(names, dotenv_path or (ROOT / ".env"))


def _http_transport(url: str, headers: dict[str, str], body: dict[str, Any], timeout: float) -> tuple[int, Any]:
    request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, None
    except (URLError, socket.timeout, TimeoutError):
        return 0, None
    except ValueError:
        return -1, None


def _unavailable(role: str, reason: str, provider: str | None = None, model: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"status": "UNAVAILABLE", "role": role, "provider": provider, "model": model, "text": None,
            "reason": reason, "called_at": _now(), **extra}


class Gateway:
    def __init__(self, config: dict[str, Any] | None = None, *, transport: Transport | None = None,
                 log_dir: Path = LOG_DIR, dotenv_path: Path | None = None, today: Callable[[], dt.date] | None = None):
        self.config = config if config is not None else load_config()
        self.transport = transport or _http_transport
        self.log_dir = log_dir
        self.dotenv_path = dotenv_path
        self.today = today or dt.date.today

    # ---- daily limit and call log -----------------------------------------------------------------
    def _log_path(self) -> Path:
        return self.log_dir / "calls.jsonl"

    def calls_today(self, role: str) -> int:
        day = self.today().isoformat()
        try:
            lines = self._log_path().read_text(encoding="utf-8").splitlines()
        except OSError:
            return 0
        count = 0
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("role") == role and (row.get("day") or str(row.get("called_at", ""))[:10]) == day and row.get("counted"):
                count += 1
        return count

    def _log(self, row: dict[str, Any]) -> None:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path().open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
        except OSError:
            pass

    # ---- the call ---------------------------------------------------------------------------------
    def role_status(self, role: str) -> dict[str, Any]:
        """Whether a role can be called right now, and why not (no network)."""
        spec = (self.config.get("roles") or {}).get(role)
        if not spec:
            return {"role": role, "ready": False, "reason": "unknown role"}
        if not spec.get("enabled"):
            return {"role": role, "ready": False, "reason": "role is off"}
        if not spec.get("model"):
            return {"role": role, "ready": False, "reason": "no model chosen"}
        provider = (self.config.get("providers") or {}).get(spec.get("provider"))
        if not provider:
            return {"role": role, "ready": False, "reason": f"unknown provider {spec.get('provider')}"}
        if not provider_key(provider, self.dotenv_path):
            return {"role": role, "ready": False, "reason": f"no key for {spec.get('provider')}"}
        limit = spec.get("daily_limit")
        if isinstance(limit, int) and self.calls_today(role) >= limit:
            return {"role": role, "ready": False, "reason": "daily limit reached"}
        return {"role": role, "ready": True, "provider": spec["provider"], "model": spec["model"]}

    def _attempts(self, role: str, spec: dict[str, Any]) -> list[tuple[str, str]]:
        attempts = [(spec["provider"], spec["model"])]
        if role in ROLES_WITH_FALLBACK:
            attempts += [(item.get("provider"), item.get("model")) for item in spec.get("fallback") or [] if item.get("provider") and item.get("model")]
        return attempts

    def chat(self, role: str, messages: list[dict[str, Any]], *, temperature: float = 0.0,
             response_format: dict[str, Any] | None = None, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """One chat call for a role. Always returns a dict with `status` OK or UNAVAILABLE and the model that answered."""
        ready = self.role_status(role)
        if not ready["ready"]:
            return _unavailable(role, ready["reason"])
        spec = self.config["roles"][role]
        timeout = float(spec.get("timeout_seconds") or 30)
        failures = []
        for provider_name, model in self._attempts(role, spec):
            provider = (self.config.get("providers") or {}).get(provider_name) or {}
            key = provider_key(provider, self.dotenv_path)
            if not provider or not key:
                failures.append(f"{provider_name}: no key")
                continue
            body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
            if response_format:
                body["response_format"] = response_format
            if tools:
                body["tools"] = tools
            url = provider["base_url"].rstrip("/") + "/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
            began = time.monotonic()
            status, payload = self.transport(url, headers, body, timeout)
            latency = int((time.monotonic() - began) * 1000)
            message = (((payload or {}).get("choices") or [{}])[0] or {}).get("message") or {} if isinstance(payload, dict) else {}
            ok = status == 200 and (message.get("content") or message.get("tool_calls"))
            reason = None if ok else ("timeout or network error" if status == 0 else "rate limited (429)" if status == 429
                                      else "invalid response" if status in (-1, 200) else f"HTTP {status}")
            self._log({"called_at": _now(), "day": self.today().isoformat(), "role": role, "provider": provider_name, "model": model, "status": "OK" if ok else "UNAVAILABLE",
                       "reason": reason, "latency_ms": latency, "prompt_chars": sum(len(str(m.get("content") or "")) for m in messages),
                       "answer_chars": len(message.get("content") or "") if ok else 0, "counted": True})
            if ok:
                return {"status": "OK", "role": role, "provider": provider_name, "model": (payload or {}).get("model") or model,
                        "requested_model": model, "text": message.get("content"), "tool_calls": message.get("tool_calls"),
                        "latency_ms": latency, "called_at": _now(), "fell_back": (provider_name, model) != (spec["provider"], spec["model"])}
            failures.append(f"{provider_name}/{model}: {reason}")
        return _unavailable(role, "; ".join(failures) or "no attempt possible", spec.get("provider"), spec.get("model"))


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="CHAINSTOX AI roles: show which are ready (no network).")
    parser.add_argument("--status", action="store_true", help="print each role's readiness as JSON")
    parser.parse_args(argv)
    gateway = Gateway()
    print(json.dumps({role: gateway.role_status(role) for role in (gateway.config.get("roles") or {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
