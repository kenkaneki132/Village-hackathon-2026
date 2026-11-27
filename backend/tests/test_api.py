"""API tests. Run:  cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest -q

No Anthropic key or network access needed: the Claude call is monkeypatched.
"""

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402

client = TestClient(main.app)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def fake_claude_result(expiration="2099-01-01"):
    r = copy.deepcopy(main.SYNTHETIC_DEMO_RESULT)
    r["level2"]["extracted_fields"]["expiration"] = expiration
    r["level4"]["compliance_flags"] = []
    return r


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(main, "_client", None)


def test_health_reports_configuration(no_key):
    h = client.get("/health").json()
    assert h["status"] == "ok"
    assert h["anthropic_key_configured"] is False
    assert "local_models" in h and "model" in h


def test_synthetic_result_works_without_key(no_key):
    r = client.post("/synthetic-test")
    assert r.status_code == 200
    body = r.json()
    for level in ("level1", "level2", "level3", "level4", "summary"):
        assert level in body


def test_verify_without_key_returns_503_not_crash(no_key, monkeypatch):
    monkeypatch.setattr(main, "run_local_pipeline", None)
    r = client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png")})
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


@pytest.mark.parametrize("ctype", ["text/plain", "application/pdf", "image/svg+xml"])
def test_verify_rejects_unsupported_types(ctype):
    r = client.post("/verify", files={"id_doc": ("x", b"abc", ctype)})
    assert r.status_code == 415


def test_verify_rejects_oversized_files(monkeypatch):
    monkeypatch.setattr(main, "MAX_FILE_SIZE_MB", 0.0001)
    r = client.post("/verify", files={"id_doc": ("id.png", PNG * 10, "image/png")})
    assert r.status_code == 413


def test_verify_rejects_empty_file():
    r = client.post("/verify", files={"id_doc": ("id.png", b"", "image/png")})
    assert r.status_code == 400


def test_verify_happy_path_with_mocked_claude(monkeypatch):
    async def fake_call(*a, **k):
        return fake_claude_result()
    monkeypatch.setattr(main, "call_claude", fake_call)
    monkeypatch.setattr(main, "run_local_pipeline", None)
    r = client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["local_models"] is None
    assert body["level4"]["expiration_status"]["status"] == "VALID"
    assert isinstance(body["processing_time_ms"], int)


def test_expired_id_is_forced_to_reject(monkeypatch):
    async def fake_call(*a, **k):
        return fake_claude_result(expiration="2001-01-01")
    monkeypatch.setattr(main, "call_claude", fake_call)
    monkeypatch.setattr(main, "run_local_pipeline", None)
    body = client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png")}).json()
    assert body["level4"]["overall_recommendation"] == "REJECT"
    assert body["summary"]["risk_level"] == "CRITICAL"
    assert body["level4"]["compliance_flags"][0]["category"] == "EXPIRATION"


def test_malformed_model_json_returns_502(monkeypatch):
    async def bad_call(*a, **k):
        raise ValueError("No JSON object found in Claude response")
    monkeypatch.setattr(main, "call_claude", bad_call)
    monkeypatch.setattr(main, "run_local_pipeline", None)
    assert client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png")}).status_code == 502


def test_local_stage_failure_does_not_break_request(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("model exploded")

    async def fake_call(*a, **k):
        return fake_claude_result()
    monkeypatch.setattr(main, "run_local_pipeline", boom)
    monkeypatch.setattr(main, "call_claude", fake_call)
    body = client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png")}).json()
    assert "model exploded" in body["local_models"]["error"]


def test_low_authenticity_plus_spoof_is_rejected_before_claude(monkeypatch):
    called = []

    async def local(*a, **k):
        return {"local": {"authenticity": {"score": 0.1}, "liveness": {"verdict": "SPOOF"}}}

    async def fake_call(*a, **k):
        called.append(1)
        return fake_claude_result()
    monkeypatch.setattr(main, "run_local_pipeline", local)
    monkeypatch.setattr(main, "call_claude", fake_call)
    r = client.post("/verify", files={"id_doc": ("id.png", PNG, "image/png"), "selfie": ("s.png", PNG, "image/png")})
    assert r.status_code == 400 and not called


@pytest.mark.parametrize("delta,status", [(-5, "EXPIRED"), (10, "EXPIRING_SOON"), (400, "VALID")])
def test_compute_expiration_details(delta, status):
    from datetime import date, timedelta
    d = (date.today() + timedelta(days=delta)).isoformat()
    assert main.compute_expiration_details(d)["status"] == status
    assert main.compute_expiration_details(None)["status"] == "UNKNOWN"
    assert main.compute_expiration_details("not-a-date")["status"] == "UNKNOWN"


def test_parse_claude_json_strips_fences():
    assert main.parse_claude_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        main.parse_claude_json("no json here")
