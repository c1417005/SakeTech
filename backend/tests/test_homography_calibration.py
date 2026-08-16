"""A1 (completeness): persist the raw correspondence points, report a
reprojection-error quality signal, reject degenerate configurations, and keep
the legacy bare-matrix storage readable.

Complements test_homography.py (solver + wiring); here we focus on the
calibration *record* (points + error) and degenerate handling.
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
# All four grid points on the line y=0 => degenerate (no valid homography).
COLLINEAR_GRID = [(0.0, 0.0), (3.0, 0.0), (6.0, 0.0), (9.0, 0.0)]


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    yield


# ---------- reprojection error (quality signal) ----------
def test_reprojection_error_zero_for_exact_fit():
    H = geometry.compute_homography(IMG, GRID)
    assert geometry.reprojection_error(H, IMG, GRID) < 1e-6


def test_reprojection_error_grows_with_noise():
    H = geometry.compute_homography(IMG, GRID)
    noisy = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (1.0, 9.0)]  # last pt off
    assert geometry.reprojection_error(H, IMG, noisy) > 0.1


# ---------- degenerate configuration handling ----------
def test_compute_homography_rejects_collinear_points():
    with pytest.raises(ValueError):
        geometry.compute_homography(IMG, COLLINEAR_GRID)


def test_calibrate_endpoint_rejects_degenerate_with_400(fresh_db):
    r = client.post("/admin/calibrate", json={
        "camera_id": "cam-deg",
        "image_points": IMG,
        "grid_points": COLLINEAR_GRID,
    })
    assert r.status_code == 400
    # nothing persisted for a rejected calibration
    assert db.load_calibration("cam-deg") is None


# ---------- raw points are persisted and read back ----------
def test_calibrate_persists_points_and_error(fresh_db):
    r = client.post("/admin/calibrate", json={
        "camera_id": "cam-P",
        "image_points": IMG,
        "grid_points": GRID,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["reprojection_error"] < 1e-6
    assert len(body["image_points"]) == 4 and len(body["grid_points"]) == 4

    g = client.get("/admin/calibrate/cam-P").json()
    # the correspondence points survive the round-trip (auditable / re-solvable)
    assert [tuple(p) for p in g["image_points"]] == IMG
    assert [tuple(p) for p in g["grid_points"]] == GRID
    assert g["reprojection_error"] < 1e-6
    assert g["updated_at"] is not None

    rec = db.load_calibration_record("cam-P")
    assert rec["image_points"] is not None and rec["matrix"] is not None


# ---------- legacy bare-matrix storage stays readable ----------
def test_legacy_bare_matrix_is_still_loadable(fresh_db):
    H = geometry.compute_homography(IMG, GRID)
    db.save_calibration("cam-legacy", H)  # legacy shape: bare 3x3 list
    assert db.load_calibration("cam-legacy") == H
    rec = db.load_calibration_record("cam-legacy")
    assert rec["matrix"] == H
    assert rec["image_points"] is None  # unknown provenance, but no crash


def test_ingest_projects_through_record_calibration(fresh_db):
    client.post("/map", json={
        "grid": {"width": 10, "height": 8},
        "objects": [{"type": "entrance", "id": "ent-1", "x": 0, "y": 7}],
    })
    client.post("/admin/calibrate", json={
        "camera_id": "cam-rec", "image_points": IMG, "grid_points": GRID,
    })
    r = client.post("/ingest", json={
        "camera_id": "cam-rec",
        "detections": [{"track_id": 7001, "x": 0.5, "y": 0.5, "t": time.time()}],
    })
    assert r.status_code == 200 and r.json()["calibrated"] is True
    sess = {s["session_id"]: s for s in client.get("/sessions").json()}
    assert sess["sess-7001"]["x"] == 5 and sess["sess-7001"]["y"] == 4
