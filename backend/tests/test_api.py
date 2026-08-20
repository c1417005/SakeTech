"""End-to-end API tests (no network: brands are seeded directly)."""
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use a throwaway DB per test run.
import app.db as db  # noqa: E402
db.DB_PATH = Path("/tmp/kumu_test.db")
if db.DB_PATH.exists():
    db.DB_PATH.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

DEMO_MAP = {
    "grid": {"width": 10, "height": 8},
    "objects": [
        {"type": "entrance", "id": "ent-1", "x": 0, "y": 7},
        {"type": "shelf", "id": "shelf-1", "name": "1番棚", "x": 1, "y": 2,
         "length": 3, "facing": "south", "brand_ids": [100]},
        {"type": "shelf", "id": "shelf-4", "name": "4番棚", "x": 5, "y": 5,
         "length": 3, "facing": "north", "brand_ids": [100, 200]},
    ],
}

# Seed fake brands (avoids sakenowa network in tests).
db.init_db()
db.upsert_brands([
    {"brand_id": 100, "name": "手取川", "brewery": "吉田酒造", "area": "石川県",
     "f1": 0.43, "f2": 0.45, "f3": 0.21, "f4": 0.33, "f5": 0.35, "f6": 0.58,
     "type4": "薫酒", "easy_tags": ["香り高い"], "has_flavor": True},
    {"brand_id": 200, "name": "天狗舞", "brewery": "車多酒造", "area": "石川県",
     "f1": 0.19, "f2": 0.61, "f3": 0.52, "f4": 0.40, "f5": 0.26, "f6": 0.30,
     "type4": "醇酒", "easy_tags": ["甘口寄り", "コクがある"], "has_flavor": True},
])


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_map_roundtrip_and_validation():
    assert client.post("/map", json=DEMO_MAP).json()["saved"] is True
    got = client.get("/map").json()
    assert got["grid"]["width"] == 10
    assert any(o["id"] == "shelf-4" for o in got["objects"])
    # invalid: unknown object type -> 400
    bad = {"grid": {"width": 10, "height": 8},
           "objects": [{"type": "wall", "id": "w", "x": 0, "y": 0}]}
    assert client.post("/map", json=bad).status_code == 400


def test_get_map_empty_when_unregistered():
    db2 = Path("/tmp/kumu_empty.db")
    if db2.exists():
        db2.unlink()
    old = db.DB_PATH
    db.DB_PATH = db2
    db.init_db()
    r = client.get("/map").json()
    assert r["objects"] == []
    db.DB_PATH = old


def test_sessions_base_shape_via_ingest():
    import time
    client.post("/map", json=DEMO_MAP)
    # front of shelf-4 (facing north) is y-1 => cells (5,4),(6,4),(7,4)
    # normalized (0.6,0.5)*grid(10,8) => cell (6,4) = front of shelf-4.
    # Two observations 6s apart so dwell accrues and state -> viewing.
    now = time.time()
    for dt in (0.0, 6.0):
        batch = {"camera_id": "cam-1", "detections": [
            {"track_id": 1, "x": 0.6, "y": 0.5, "t": now + dt,
             "appearance_tags": ["赤い上着"]}]}
        assert client.post("/ingest", json=batch).json()["accepted"] == 1
    sessions = client.get("/sessions").json()
    assert len(sessions) == 1, sessions
    s = sessions[0]
    for k in ("session_id", "x", "y", "state", "dwell_sec"):  # binding base fields
        assert k in s
    assert s["shelf_id"] == "shelf-4"
    assert s["dwell_sec"] >= 4 and s["state"] in ("viewing", "hesitating")


def test_sessions_mock_demo_reaches_hesitating():
    client.post("/map", json=DEMO_MAP)
    # mock replay returns the scripted visitor; profile present
    s = client.get("/sessions?mock=true").json()
    assert len(s) == 1
    assert "profile" in s[0]
    assert s[0]["appearance_tags"]  # 見た目タグ


def test_brands_endpoint():
    b = client.get("/brands?ids=100,200").json()
    assert len(b) == 2
    one = client.get("/brands/200").json()
    assert one["name"] == "天狗舞" and one["type4"] == "醇酒"


if __name__ == "__main__":
    test_health()
    test_map_roundtrip_and_validation()
    test_get_map_empty_when_unregistered()
    test_sessions_base_shape_via_ingest()
    test_sessions_mock_demo_reaches_hesitating()
    test_brands_endpoint()
    print("OK: API e2e tests passed")
