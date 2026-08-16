"""A3: session state-machine, facing adjacency, and dwell-weighted basis
boundaries. These lock in the current (provisional/[TBD]) semantics so future
threshold tuning is a deliberate, test-visible change.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
from app import config, geometry, inference  # noqa: E402
from app.sessions import SessionStore, _state_for  # noqa: E402


def _shelf(**kw):
    base = {"type": "shelf", "id": "s", "name": "s", "x": 1, "y": 2,
            "length": 3, "facing": "south", "brand_ids": []}
    base.update(kw)
    return base


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    yield


# ---------- _state_for boundaries ----------
def test_state_for_boundaries():
    assert _state_for(None, 999) == "moving"                 # no shelf => moving
    assert _state_for("s", config.VIEWING_SEC - 0.1) == "moving"
    assert _state_for("s", config.VIEWING_SEC) == "viewing"  # inclusive boundary
    assert _state_for("s", config.HESITATING_SEC - 0.1) == "viewing"
    assert _state_for("s", config.HESITATING_SEC) == "hesitating"  # inclusive


# ---------- facing adjacency (all 4 directions + negatives) ----------
def test_front_cells_north_and_west():
    n = _shelf(facing="north")   # occupies (1,2),(2,2),(3,2); front = y-1
    assert set(geometry.shelf_front_cells(n)) == {(1, 1), (2, 1), (3, 1)}
    w = _shelf(x=4, y=1, length=2, facing="west")  # occupies (4,1),(4,2); front x-1
    assert set(geometry.shelf_front_cells(w)) == {(3, 1), (3, 2)}


def test_shelf_at_only_facing_side():
    s = _shelf(facing="south")   # front row y=3
    assert geometry.shelf_at(2, 3, [s]) == "s"    # in front
    assert geometry.shelf_at(2, 1, [s]) is None   # behind
    assert geometry.shelf_at(2, 2, [s]) is None   # on the shelf


def test_shelf_at_two_facing_shelves_is_deterministic_first():
    # Two shelves whose fronts share cell (2,3): south shelf at y=2 (front y=3)
    # and north shelf at y=4 (front y=3). shelf_at returns the first in list.
    south = _shelf(id="A", x=1, y=2, length=3, facing="south")
    north = _shelf(id="B", x=1, y=4, length=3, facing="north")
    assert (2, 3) in geometry.shelf_front_cells(south)
    assert (2, 3) in geometry.shelf_front_cells(north)
    assert geometry.shelf_at(2, 3, [south, north]) == "A"
    assert geometry.shelf_at(2, 3, [north, south]) == "B"


# ---------- SessionStore dwell accumulation + prune ----------
def test_observe_dwell_progresses_and_resets_on_shelf_change():
    store = SessionStore()
    objs = [_shelf(facing="south")]           # front cells: (1,3),(2,3),(3,3)
    front, aisle = (2, 3), (5, 5)
    t0 = 1000.0
    store.observe(objs, "p1", *front, t0)                       # arrive
    assert store.sessions()[0].state == "moving"               # dwell 0
    store.observe(objs, "p1", *front, t0 + config.VIEWING_SEC)
    assert store.sessions()[0].state == "viewing"
    store.observe(objs, "p1", *front, t0 + config.HESITATING_SEC)
    s = store.sessions()[0]
    assert s.state == "hesitating" and s.x == 2 and s.y == 3
    # step into the aisle => shelf None => moving, dwell resets
    store.observe(objs, "p1", *aisle, t0 + config.HESITATING_SEC + 1)
    assert store.sessions()[0].state == "moving"


def test_prune_ttl_boundary():
    store = SessionStore(ttl_sec=30.0)
    store.observe([_shelf()], "p1", 2, 3, 1000.0)
    store.prune(now=1000.0 + 30.0)     # exactly ttl => kept (uses strict >)
    assert any(s.session_id == "p1" for s in store.sessions())
    store.prune(now=1000.0 + 30.1)     # beyond ttl => dropped
    assert not store.sessions()


# ---------- dwell-weighted basis threshold ----------
def _seed_brand(bid, name):
    db.upsert_brands([{"brand_id": bid, "name": name, "has_flavor": False,
                       "easy_tags": []}])


def test_basis_requires_min_dwell(fresh_db):
    _seed_brand(1, "長居")
    _seed_brand(2, "一瞬")
    prof = inference.infer_profile({1: float(config.BASIS_MIN_DWELL_SEC),
                                    2: config.BASIS_MIN_DWELL_SEC - 0.1})
    assert prof is not None
    assert prof.basis == ["長居"]      # brand 2 below threshold excluded


def test_basis_capped_and_ordered_by_dwell(fresh_db):
    for bid, nm in [(1, "b1"), (2, "b2"), (3, "b3"), (4, "b4")]:
        _seed_brand(bid, nm)
    prof = inference.infer_profile({1: 6.0, 2: 30.0, 3: 12.0, 4: 20.0})
    # longest first, capped at MAX_BASIS
    assert prof.basis == ["b2", "b4", "b3"][:config.MAX_BASIS]
    assert len(prof.basis) == config.MAX_BASIS


def test_confidence_boundaries():
    assert inference._confidence(config.CONF_HIGH_BASIS, config.CONF_HIGH_DWELL) == "high"
    assert inference._confidence(config.CONF_HIGH_BASIS, config.CONF_HIGH_DWELL - 1) == "medium"
    assert inference._confidence(config.CONF_MED_BASIS, config.CONF_MED_DWELL) == "medium"
    assert inference._confidence(config.CONF_MED_BASIS, config.CONF_MED_DWELL - 1) == "low"
    assert inference._confidence(1, 999) == "low"   # too few basis brands
