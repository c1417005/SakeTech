"""CORS allowlist tests: dev origins allowed, unknown origins rejected."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# CORS tests only hit /health and a preflight (no DB access), so we do not
# override the shared db.DB_PATH here — doing so would corrupt other tests that
# rely on the global mutable path.
from fastapi.testclient import TestClient  # noqa: E402

from app.config import DEFAULT_CORS_ORIGINS  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def test_allowed_origin_gets_cors_header():
    origin = DEFAULT_CORS_ORIGINS[0]
    r = client.get("/health", headers={"origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin


def test_unknown_origin_is_not_reflected():
    r = client.get("/health", headers={"origin": "https://evil.example.com"})
    assert r.status_code == 200
    # No allowlist match => no ACAO header echoing the evil origin, and never "*".
    acao = r.headers.get("access-control-allow-origin")
    assert acao != "https://evil.example.com"
    assert acao != "*"


def test_preflight_allowed_origin():
    origin = DEFAULT_CORS_ORIGINS[0]
    r = client.options(
        "/map",
        headers={
            "origin": origin,
            "access-control-request-method": "POST",
        },
    )
    assert r.headers.get("access-control-allow-origin") == origin
