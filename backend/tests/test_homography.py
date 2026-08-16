"""A1: image->grid homography wiring.

Covers the geometry solver, the /admin/calibrate hook, and that /ingest uses a
calibrated homography when present but keeps the naive fallback otherwise.

Uses a monkeypatched per-test DB (db.DB_PATH is a shared mutable global; setting
it at module scope would corrupt other test modules, so we isolate via fixture).
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
from app import geometry  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

# Unit-square normalized image corners -> 10x8 grid corners (pure scale).
IMG = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
GRID = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]

DEMO_MAP = {
    "grid": {"width": 10, "height": 8},
    "objects": [{"type": "entrance", "id": "ent-1", "x": 0, "y": 7}],
}


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    yield


# ---------- geometry solver ----------
def test_compute_and_project_recovers_scale():
    H = geometry.compute_homography(IMG, GRID)
    assert geometry.project_to_grid(H, 0.5, 0.5) == (5, 4)
    assert geometry.project_to_grid(H, 0.0, 0.0) == (0, 0)
    assert geometry.project_to_grid(H, 1.0, 1.0) == (10, 8)


def test_compute_homography_needs_four_points():
    with pytest.raises(ValueError):
        geometry.compute_homography(IMG[:3], GRID[:3])


# ---------- /admin/calibrate hook ----------
def test_calibrate_persists_and_reads_back(fresh_db):
    r = client.post("/admin/calibrate",
                    json={"camera_id": "cam-A", "image_points": IMG, "grid_points": GRID})
    assert r.status_code == 200
    assert db.load_calibration("cam-A") is not None
    g = client.get("/admin/calibrate/cam-A")
    assert g.status_code == 200 and g.json()["homography"] is not None
    assert client.get("/admin/calibrate/cam-unknown").status_code == 404


def test_calibrate_rejects_too_few_points(fresh_db):
    r = client.post("/admin/calibrate",
                    json={"camera_id": "cam-A", "image_points": IMG[:3], "grid_points": GRID[:3]})
    assert r.status_code == 422  # pydantic min_length


# ---------- /ingest mapping ----------
def test_ingest_uses_homography_when_calibrated(fresh_db):
    client.post("/map", json=DEMO_MAP)
    client.post("/admin/calibrate",
                json={"camera_id": "cam-cal", "image_points": IMG, "grid_points": GRID})
    r = client.post("/ingest", json={
        "camera_id": "cam-cal",
        "detections": [{"track_id": 9001, "x": 0.5, "y": 0.5, "t": time.time()}],
    })
    assert r.status_code == 200 and r.json()["calibrated"] is True
    sess = {s["session_id"]: s for s in client.get("/sessions").json()}
    assert sess["sess-9001"]["x"] == 5 and sess["sess-9001"]["y"] == 4


def test_ingest_naive_fallback_when_uncalibrated(fresh_db):
    client.post("/map", json=DEMO_MAP)
    r = client.post("/ingest", json={
        "camera_id": "cam-none",  # never calibrated
        "detections": [{"track_id": 9002, "x": 0.9, "y": 0.9, "t": time.time()}],
    })
    assert r.status_code == 200 and r.json()["calibrated"] is False
    sess = {s["session_id"]: s for s in client.get("/sessions").json()}
    # naive: int(0.9*10)=9, int(0.9*8)=7 (unchanged MVP behavior)
    assert sess["sess-9002"]["x"] == 9 and sess["sess-9002"]["y"] == 7
