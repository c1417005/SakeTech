"""Phase B / B1: end-to-end real-data path (NOT mock).

Posts detection batches in the exact shape the iOS app sends (POST /ingest),
then reads GET /sessions with mock disabled and asserts the backend derives
grid position + state (moving/viewing/hesitating) from the real data. This is
the contract the iOS dashboard depends on once it stops calling ?mock=true.
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
from app import config, routes  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

# One south-facing shelf; its front cells are (1,3),(2,3),(3,3) on a 10x8 grid.
MAP = {
    "grid": {"width": 10, "height": 8},
    "objects": [
        {"type": "entrance", "id": "ent-1", "x": 0, "y": 7},
        {"type": "shelf", "id": "shelf-1", "name": "1番棚", "x": 1, "y": 2,
         "length": 3, "facing": "south", "brand_ids": [100]},
    ],
}


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    routes.live_store._s.clear()          # isolate from the module-global store
    client.post("/map", json=MAP)
    yield
    routes.live_store._s.clear()


def _ingest(track_id, x, y, t, tags=None):
    return client.post("/ingest", json={"camera_id": "cam-1", "detections": [
        {"track_id": track_id, "x": x, "y": y, "t": t,
         "appearance_tags": tags or ["赤い上着"]},
    ]})


def _row(track_id):
    rows = {r["session_id"]: r for r in client.get("/sessions").json()}  # mock=false
    return rows.get(f"sess-{track_id}")


def test_real_ingest_drives_state_moving_to_hesitating(fresh):
    t0 = time.time()
    # (0.25,0.40) -> naive cell (int(2.5), int(3.2)) = (2,3) = shelf-1 front cell.
    _ingest(1, 0.25, 0.40, t0)
    assert _row(1)["state"] == "moving"                      # just arrived, dwell 0
    _ingest(1, 0.25, 0.40, t0 + config.VIEWING_SEC)
    assert _row(1)["state"] == "viewing"
    _ingest(1, 0.25, 0.40, t0 + config.HESITATING_SEC)
    r = _row(1)
    assert r["state"] == "hesitating"
    assert (r["x"], r["y"]) == (2, 3) and r["shelf_id"] == "shelf-1"
    assert r["appearance_tags"] == ["赤い上着"]


def test_real_ingest_in_aisle_is_moving(fresh):
    _ingest(2, 0.85, 0.10, time.time())     # cell (8,0): not any shelf's front
    r = _row(2)
    assert r["state"] == "moving" and r["shelf_id"] is None


def test_ingest_response_reports_accepted_and_calibration(fresh):
    r = _ingest(3, 0.25, 0.40, time.time())
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 1 and body["calibrated"] is False   # naive path


def test_sessions_default_is_live_not_mock(fresh):
    # With no ingest, live sessions is empty; mock=true would fabricate rows.
    assert client.get("/sessions").json() == []
    assert len(client.get("/sessions?mock=true").json()) >= 1
