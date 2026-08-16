"""Phase C / C1: /ingest hardening + SessionStore thread-safety.

FastAPI serves sync path operations from a worker threadpool, so observe()
(/ingest) and sessions()/prune() (/sessions) run concurrently. Without a lock
the shared dict can raise "dictionary changed size during iteration"; the stress
test below reproduces that pattern and asserts it no longer happens.
"""
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
from app import config, routes  # noqa: E402
from app.main import app  # noqa: E402
from app.sessions import SessionStore  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

MAP = {
    "grid": {"width": 10, "height": 8},
    "objects": [{"type": "shelf", "id": "shelf-1", "name": "1番棚", "x": 1, "y": 2,
                 "length": 3, "facing": "south", "brand_ids": []}],
}


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    routes.live_store._s.clear()
    client.post("/map", json=MAP)
    yield
    routes.live_store._s.clear()


# ---------- /ingest hardening ----------
def test_ingest_rejects_oversized_batch(fresh):
    n = config.MAX_INGEST_DETECTIONS + 1
    dets = [{"track_id": i, "x": 0.25, "y": 0.4, "t": time.time()} for i in range(n)]
    r = client.post("/ingest", json={"camera_id": "cam-1", "detections": dets})
    assert r.status_code == 413


def test_ingest_accepts_empty_batch(fresh):
    r = client.post("/ingest", json={"camera_id": "cam-1", "detections": []})
    assert r.status_code == 200 and r.json()["accepted"] == 0


def test_ingest_at_limit_is_ok(fresh):
    n = config.MAX_INGEST_DETECTIONS
    dets = [{"track_id": i, "x": 0.25, "y": 0.4, "t": time.time()} for i in range(n)]
    r = client.post("/ingest", json={"camera_id": "cam-1", "detections": dets})
    assert r.status_code == 200 and r.json()["accepted"] == n


# ---------- SessionStore thread-safety ----------
def test_sessionstore_concurrent_reads_and_writes_are_safe():
    store = SessionStore()
    objs = MAP["objects"]           # empty brand_ids => sessions() needs no DB
    errors: list[Exception] = []

    def writer():
        for i in range(3000):
            try:
                store.observe(objs, f"p{i % 40}", 2, 3, 1000.0 + i)
            except Exception as e:      # noqa: BLE001
                errors.append(e)

    def reader():
        for i in range(3000):
            try:
                store.sessions()
                store.prune(now=2000.0 + i)   # also mutates under the lock
            except Exception as e:          # noqa: BLE001
                errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(3)] + \
              [threading.Thread(target=reader) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent access raised: {errors[:3]}"
