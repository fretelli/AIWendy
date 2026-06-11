import importlib.util
import logging
from pathlib import Path

import pytest
import requests


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "keeltrader_digest.py"


def load_module(monkeypatch):
    original_file_handler = logging.FileHandler

    class TmpFileHandler(original_file_handler):
        def __init__(self, filename, *args, **kwargs):
            super().__init__("/tmp/keeltrader-digest-test.log", *args, **kwargs)

    monkeypatch.setattr(logging, "FileHandler", TmpFileHandler)
    spec = importlib.util.spec_from_file_location("keeltrader_digest_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "MINIFLUX_RETRIES", 3)
    monkeypatch.setattr(module, "MINIFLUX_RETRY_BACKOFF_SECONDS", 0)
    return module


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {"ok": True}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        return self.payload


def test_miniflux_get_retries_timeout_then_returns_json(monkeypatch):
    module = load_module(monkeypatch)
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) < 3:
            raise requests.Timeout("slow miniflux")
        return FakeResponse(payload={"entries": [{"title": "ok"}]})

    monkeypatch.setattr(module.requests, "get", fake_get)

    result = module._miniflux_get("/entries", {"limit": 1})

    assert result == {"entries": [{"title": "ok"}]}
    assert len(calls) == 3
    assert calls[0][1]["timeout"] == (module.MINIFLUX_CONNECT_TIMEOUT, module.MINIFLUX_READ_TIMEOUT)


def test_miniflux_get_does_not_retry_4xx(monkeypatch):
    module = load_module(monkeypatch)
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse(status_code=401)

    monkeypatch.setattr(module.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        module._miniflux_get("/entries")

    assert len(calls) == 1


def test_miniflux_get_raises_after_retry_exhaustion(monkeypatch):
    module = load_module(monkeypatch)
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        raise requests.Timeout("still slow")

    monkeypatch.setattr(module.requests, "get", fake_get)

    with pytest.raises(requests.Timeout):
        module._miniflux_get("/entries")

    assert len(calls) == 3
