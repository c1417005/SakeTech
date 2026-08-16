"""A2: sakenowa mapping accuracy + robustness (no real network).

Covers type4 derivation, tolerant easy_tags, defensive Ishikawa extraction
(partial/malformed records), and sync() falling back to cache on upstream failure.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db as db  # noqa: E402
from app import sakenowa  # noqa: E402

AREA = sakenowa.config.ISHIKAWA_AREA_ID  # 17


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "kumu.db")
    db.init_db()
    yield


# ---------- derive_type4 ----------
def test_derive_type4_quadrants():
    assert sakenowa.derive_type4(0.9, 0.1) == "薫酒"   # aroma high, light
    assert sakenowa.derive_type4(0.1, 0.1) == "爽酒"   # low, light
    assert sakenowa.derive_type4(0.1, 0.9) == "醇酒"   # low, rich
    assert sakenowa.derive_type4(0.9, 0.9) == "熟酒"   # high, rich


def test_derive_type4_none_when_axis_missing():
    assert sakenowa.derive_type4(None, 0.5) is None
    assert sakenowa.derive_type4(0.5, None) is None


# ---------- easy_tags tolerance ----------
def test_easy_tags_tolerates_missing_axes():
    assert sakenowa.easy_tags({}) == []            # no axes -> no tags, no crash
    assert "香り高い" in sakenowa.easy_tags({"f1": 0.4})
    assert "甘口寄り" in sakenowa.easy_tags({"f5": 0.2})
    assert "辛口寄り" in sakenowa.easy_tags({"f5": 0.5})


# ---------- build_ishikawa_brands (monkeypatched upstream) ----------
_PAYLOADS = {
    "areas": {"areas": [{"id": AREA, "name": "石川県"}, {"id": 1, "name": "北海道"}]},
    "breweries": {"breweries": [
        {"id": 100, "name": "A酒造", "areaId": AREA},
        {"id": 200, "name": "B酒造", "areaId": 1},          # other prefecture
    ]},
    "brands": {"brands": [
        {"id": 1, "name": "薫", "breweryId": 100},           # ishikawa + full flavor
        {"id": 2, "name": "他県", "breweryId": 200},          # not ishikawa -> skip
        {"id": 3, "breweryId": 100},                          # missing name -> skip
        {"id": 4, "name": "部分", "breweryId": 100},          # partial flavor
        {"id": 5, "name": "無風味", "breweryId": 100},        # no flavor chart
    ]},
    "flavor-charts": {"flavorCharts": [
        {"brandId": 1, "f1": 0.5, "f2": 0.6, "f3": 0.5, "f4": 0.2, "f5": 0.5, "f6": 0.3},
        {"brandId": 4, "f1": 0.1, "f3": None},                # f3 missing
    ]},
}


def test_build_ishikawa_filters_and_tolerates(monkeypatch):
    monkeypatch.setattr(sakenowa, "_get", lambda ep: _PAYLOADS[ep])
    out = {b["brand_id"]: b for b in sakenowa.build_ishikawa_brands()}

    assert set(out) == {1, 4, 5}          # non-ishikawa (2) and nameless (3) skipped
    assert out[1]["type4"] == "熟酒" and out[1]["has_flavor"] is True
    assert "香り高い" in out[1]["easy_tags"] and "芳醇" in out[1]["easy_tags"]
    assert out[4]["type4"] is None and out[4]["has_flavor"] is True   # f1 present, f3 missing
    assert out[5]["type4"] is None and out[5]["has_flavor"] is False  # no flavor chart


# ---------- sync() fallback ----------
def test_sync_falls_back_to_cache_on_failure(fresh_db, monkeypatch):
    def _boom():
        raise OSError("sakenowa unreachable")

    # empty cache + upstream down => returns 0, does NOT raise
    monkeypatch.setattr(sakenowa, "build_ishikawa_brands", _boom)
    assert sakenowa.sync(force=True) == 0

    # cache present + upstream down => keeps cached brands
    db.upsert_brands([{"brand_id": 42, "name": "cached", "easy_tags": []}])
    assert sakenowa.sync(force=True) == 1


def test_sync_success_upserts(fresh_db, monkeypatch):
    monkeypatch.setattr(sakenowa, "build_ishikawa_brands",
                        lambda: [{"brand_id": 7, "name": "x", "easy_tags": []}])
    assert sakenowa.sync(force=True) == 1
    assert db.brand_count() == 1
