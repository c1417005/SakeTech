"""Auth tests: register -> login -> me, and the key guarantee that auth is
OPTIONAL / NON-BLOCKING (public endpoints work with no token), plus the opt-in
admin gate.

DB isolation: we keep our own throwaway DB and swap db.DB_PATH only for the
duration of each test (save/restore), so we never disturb test_api's global
path regardless of pytest collection order.
"""
import contextlib
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
import app.config as config  # noqa: E402

AUTH_DB = Path("/tmp/kumu_auth_test.db")

# Initialize our DB up front without leaving db.DB_PATH mutated globally.
_saved = db.DB_PATH
db.DB_PATH = AUTH_DB
if AUTH_DB.exists():
    AUTH_DB.unlink()
db.init_db()
db.DB_PATH = _saved

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@contextlib.contextmanager
def auth_db():
    old = db.DB_PATH
    db.DB_PATH = AUTH_DB
    try:
        yield
    finally:
        db.DB_PATH = old


def test_register_login_me():
    with auth_db():
        u = f"tester_{os.getpid()}"
        # register -> token
        r = client.post("/auth/register", json={"username": u, "password": "pw123"})
        assert r.status_code == 200, r.text
        tok = r.json()["token"]
        assert tok and r.json()["user"]["username"] == u

        # duplicate username -> 409
        assert client.post(
            "/auth/register", json={"username": u, "password": "x"}
        ).status_code == 409

        # login -> token
        r = client.post("/auth/login", json={"username": u, "password": "pw123"})
        assert r.status_code == 200, r.text
        tok2 = r.json()["token"]

        # wrong password -> 401
        assert client.post(
            "/auth/login", json={"username": u, "password": "nope"}
        ).status_code == 401

        # /me with token -> the user
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok2}"})
        assert me.status_code == 200 and me.json()["username"] == u

        # /me without token -> 401 (this endpoint is the auth check itself)
        assert client.get("/auth/me").status_code == 401
        # /me with garbage token -> 401
        assert client.get(
            "/auth/me", headers={"Authorization": "Bearer garbage"}
        ).status_code == 401


def test_public_endpoints_work_without_auth():
    """The whole point: no login UI required. Public endpoints never 401."""
    with auth_db():
        assert client.get("/health").status_code == 200
        assert client.get("/sessions").status_code == 200          # no token
        assert client.get("/map").status_code == 200               # no token
        m = {"grid": {"width": 10, "height": 8},
             "objects": [{"type": "entrance", "id": "e", "x": 0, "y": 7}]}
        assert client.post("/map", json=m).status_code == 200      # write, no token


def test_admin_open_by_default_gated_when_enabled():
    with auth_db():
        pts = {"camera_id": "cam-x",
               "image_points": [[0, 0], [1, 0], [1, 1], [0, 1]],
               "grid_points": [[0, 0], [9, 0], [9, 7], [0, 7]]}

        # default: KUMU_ADMIN_AUTH unset => admin open, no token needed
        os.environ.pop("KUMU_ADMIN_AUTH", None)
        assert not config.admin_auth_enabled()
        assert client.post("/admin/calibrate", json=pts).status_code == 200

        # enabled: admin now requires a valid token
        os.environ["KUMU_ADMIN_AUTH"] = "true"
        try:
            assert config.admin_auth_enabled()
            assert client.post("/admin/calibrate", json=pts).status_code == 401

            # obtain a token, then admin works again
            client.post("/auth/register",
                        json={"username": f"admin_{os.getpid()}", "password": "pw"})
            tok = client.post(
                "/auth/login",
                json={"username": f"admin_{os.getpid()}", "password": "pw"},
            ).json()["token"]
            r = client.post("/admin/calibrate", json=pts,
                            headers={"Authorization": f"Bearer {tok}"})
            assert r.status_code == 200, r.text
        finally:
            os.environ.pop("KUMU_ADMIN_AUTH", None)


def test_password_hashing_roundtrip():
    from app import auth
    h = auth.hash_password("secret")
    assert h != "secret" and h.startswith("pbkdf2_sha256$")
    assert auth.verify_password("secret", h)
    assert not auth.verify_password("wrong", h)
    assert not auth.verify_password("secret", "not-a-hash")


if __name__ == "__main__":
    test_register_login_me()
    test_public_endpoints_work_without_auth()
    test_admin_open_by_default_gated_when_enabled()
    test_password_hashing_roundtrip()
    print("OK: auth tests passed")
