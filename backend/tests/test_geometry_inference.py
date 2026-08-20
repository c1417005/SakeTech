"""Network-free unit tests for geometry, type4 derivation, and inference."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import geometry, sakenowa  # noqa: E402
from app.inference import _tags_from_flavor, _confidence  # noqa: E402


def _shelf(**kw):
    base = {"type": "shelf", "id": "s", "name": "s", "x": 1, "y": 2,
            "length": 3, "facing": "south", "brand_ids": []}
    base.update(kw)
    return base


def test_facing_front_cells_south():
    # shelf at (1,2) length3 facing south => occupies (1,2),(2,2),(3,2);
    # front (customer side) is south = y+1 => (1,3),(2,3),(3,3)
    s = _shelf(facing="south")
    assert set(geometry.shelf_front_cells(s)) == {(1, 3), (2, 3), (3, 3)}
    assert geometry.shelf_at(2, 3, [s]) == "s"      # in front
    assert geometry.shelf_at(2, 1, [s]) is None     # behind (north side)
    assert geometry.shelf_at(2, 2, [s]) is None     # on the shelf


def test_facing_east_extends_along_y():
    s = _shelf(x=4, y=1, length=2, facing="east")
    assert set(geometry.shelf_cells(s)) == {(4, 1), (4, 2)}
    assert set(geometry.shelf_front_cells(s)) == {(5, 1), (5, 2)}


def test_type4_derivation():
    # 天狗舞 f1=.19 f3=.52 -> 香り低・濃醇 = 醇酒
    assert sakenowa.derive_type4(0.19, 0.52) == "醇酒"
    # 香り高・淡麗 = 薫酒
    assert sakenowa.derive_type4(0.60, 0.20) == "薫酒"
    # 香り低・淡麗 = 爽酒
    assert sakenowa.derive_type4(0.10, 0.20) == "爽酒"
    # 香り高・濃醇 = 熟酒
    assert sakenowa.derive_type4(0.60, 0.60) == "熟酒"


def test_inference_tags_and_confidence():
    dry = {"f1": 0.7, "f2": 0.5, "f3": 0.4, "f4": 0.5, "f5": 0.75, "f6": 0.4}
    tags = _tags_from_flavor(dry)
    assert "辛口寄り" in tags and "香り高い" in tags
    assert _confidence(1, 5) == "low"
    assert _confidence(3, 35) == "high"


if __name__ == "__main__":
    test_facing_front_cells_south()
    test_facing_east_extends_along_y()
    test_type4_derivation()
    test_inference_tags_and_confidence()
    print("OK: geometry + type4 + inference tests passed")
