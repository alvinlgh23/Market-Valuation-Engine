"""AI model plan, phase A: the connection layer never raises, always names the model, and falls back only where allowed."""
import datetime as dt
import json

import llm_gateway as lg

TODAY = dt.date(2026, 11, 26)


def config(**roles):
    base = {"providers": {"google": {"base_url": "https://g.example/v1", "key_env": ["TEST_G_KEY"]},
                          "groq": {"base_url": "https://q.example/v1/", "key_env": ["TEST_Q_KEY"]}},
            "roles": {"qa": {"enabled": True, "provider": "groq", "model": "fast-1", "timeout_seconds": 5, "daily_limit": 3,
                             "fallback": [{"provider": "google", "model": "flash-1"}]},
                      "review": {"enabled": True, "provider": "groq", "model": "think-1", "timeout_seconds": 5, "daily_limit": 3,
                                 "fallback": [{"provider": "google", "model": "flash-1"}]}}}
    for name, spec in roles.items():
        base["roles"][name].update(spec)
    return base


def ok(text="hi", model=None):
    return 200, {"model": model, "choices": [{"message": {"content": text}}]}


def gateway(tmp_path, monkeypatch, replies, cfg=None, keys=("TEST_G_KEY", "TEST_Q_KEY")):
    for name in ("TEST_G_KEY", "TEST_Q_KEY"):
        monkeypatch.delenv(name, raising=False)
    for name in keys:
        monkeypatch.setenv(name, "secret-" + name)
    seen = []

    def transport(url, headers, body, timeout):
        seen.append({"url": url, "auth": headers["Authorization"], "model": body["model"], "timeout": timeout})
        reply = replies.pop(0)
        return reply(url, body) if callable(reply) else reply

    gw = lg.Gateway(cfg or config(), transport=transport, log_dir=tmp_path / "llm", dotenv_path=tmp_path / "missing.env", today=lambda: TODAY)
    return gw, seen


def test_a_successful_call_names_the_provider_and_model(tmp_path, monkeypatch):
    gw, seen = gateway(tmp_path, monkeypatch, [ok("answer", model="fast-1-2026")])
    result = gw.chat("qa", [{"role": "user", "content": "why?"}])
    assert result["status"] == "OK" and result["text"] == "answer"
    assert result["provider"] == "groq" and result["model"] == "fast-1-2026" and result["requested_model"] == "fast-1"
    assert result["fell_back"] is False
    assert seen[0]["url"] == "https://q.example/v1/chat/completions" and seen[0]["auth"] == "Bearer secret-TEST_Q_KEY"


def test_timeouts_rate_limits_and_bad_replies_become_unavailable_never_an_exception(tmp_path, monkeypatch):
    for reply in [(0, None), (429, None), (500, None), (-1, None), (200, {"choices": []})]:
        gw, _ = gateway(tmp_path / str(reply[0]), monkeypatch, [reply], cfg=config(review={"fallback": []}))
        result = gw.chat("review", [{"role": "user", "content": "x"}])
        assert result["status"] == "UNAVAILABLE" and result["text"] is None


def test_review_falls_back_when_its_main_model_is_rate_limited_and_says_so(tmp_path, monkeypatch):
    """Owner 2026-11-27: Qwen picks up review and explain when Nemotron's free limit is reached."""
    gw, seen = gateway(tmp_path, monkeypatch, [(429, None), ok("from qwen")])
    review = gw.chat("review", [{"role": "user", "content": "x"}])
    assert review["status"] == "OK" and review["model"] == "flash-1" and review["fell_back"] is True
    assert [call["model"] for call in seen] == ["think-1", "flash-1"]

    gw, seen = gateway(tmp_path / "none", monkeypatch, [(429, None)], cfg=config(review={"fallback": []}))
    assert gw.chat("review", [{"role": "user", "content": "x"}])["status"] == "UNAVAILABLE" and len(seen) == 1

    gw, seen = gateway(tmp_path / "empty", monkeypatch, [(429, None)], cfg=config(review={"fallback": [{"provider": "google", "model": ""}]}))
    assert gw.chat("review", [{"role": "user", "content": "x"}])["status"] == "UNAVAILABLE" and len(seen) == 1   # no model named: skipped


def test_roles_are_off_without_a_model_a_key_or_the_switch(tmp_path, monkeypatch):
    gw, seen = gateway(tmp_path, monkeypatch, [], cfg=config(qa={"enabled": False}))
    assert gw.chat("qa", [])["reason"] == "role is off"
    gw, _ = gateway(tmp_path, monkeypatch, [], cfg=config(qa={"model": ""}))
    assert gw.chat("qa", [])["reason"] == "no model chosen"
    gw, _ = gateway(tmp_path, monkeypatch, [], keys=())
    assert gw.chat("qa", [])["reason"] == "no key for groq"
    assert gw.chat("nonsense", [])["reason"] == "unknown role"
    assert seen == []


def test_the_shipped_config_holds_no_keys_and_every_enabled_role_names_a_model():
    shipped = lg.load_config()
    assert shipped["roles"] and all(spec["model"] for spec in shipped["roles"].values() if spec["enabled"])
    text = lg.CONFIG_PATH.read_text()
    assert "sk-" not in text and "gsk_" not in text and "AIza" not in text and "Bearer" not in text


def test_the_daily_limit_stops_calls_and_the_log_holds_no_prompt_text(tmp_path, monkeypatch):
    gw, seen = gateway(tmp_path, monkeypatch, [ok(), ok(), ok()])
    for _ in range(3):
        assert gw.chat("qa", [{"role": "user", "content": "my secret question"}])["status"] == "OK"
    blocked = gw.chat("qa", [{"role": "user", "content": "one more"}])
    assert blocked["status"] == "UNAVAILABLE" and blocked["reason"] == "daily limit reached" and len(seen) == 3
    log = (tmp_path / "llm" / "calls.jsonl").read_text()
    assert "my secret question" not in log and "secret-TEST" not in log
    assert all(json.loads(line)["model"] == "fast-1" for line in log.splitlines())


def test_keys_can_come_from_a_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_Q_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nexport TEST_Q_KEY='from-file'\n")
    assert lg.provider_key({"key_env": ["TEST_Q_KEY"]}, env) == "from-file"
    assert lg.provider_key({"key_env": ["TEST_Q_KEY"]}, tmp_path / "none.env") is None
