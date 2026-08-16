"""Seed a demo map from real Ishikawa sakenowa brands.

Builds a 10x8 store with an entrance, register, and 4 shelves whose brands are
picked from the cached Ishikawa set (濃厚芳醇=醇酒ゾーンに寄るストーリー).

Run:  python -m app.seed_demo
Then: GET /sessions?mock=true  replays 入店->1-3番棚->4番で迷う.
"""
from __future__ import annotations

from app import db, sakenowa

# Demo brands (verified present in Ishikawa sakenowa data w/ flavor charts).
DEMO_BRAND_IDS = {
    "shelf-1": [470],        # 手取川 (すっきり寄り)
    "shelf-2": [488],        # 福正宗
    "shelf-3": [469],        # 天狗舞 (芳醇)
    "shelf-4": [469, 1041],  # 天狗舞 + 菊姫 (濃醇=迷いポイント)
}

DEMO_MAP = {
    "grid": {"width": 10, "height": 8},
    "objects": [
        {"type": "entrance", "id": "ent-1", "x": 0, "y": 7},
        {"type": "register", "id": "reg-1", "x": 9, "y": 7},
        {"type": "shelf", "id": "shelf-1", "name": "1番棚", "x": 1, "y": 2,
         "length": 3, "facing": "south", "brand_ids": DEMO_BRAND_IDS["shelf-1"]},
        {"type": "shelf", "id": "shelf-2", "name": "2番棚", "x": 5, "y": 2,
         "length": 3, "facing": "south", "brand_ids": DEMO_BRAND_IDS["shelf-2"]},
        {"type": "shelf", "id": "shelf-3", "name": "3番棚", "x": 1, "y": 5,
         "length": 3, "facing": "north", "brand_ids": DEMO_BRAND_IDS["shelf-3"]},
        {"type": "shelf", "id": "shelf-4", "name": "4番棚", "x": 5, "y": 5,
         "length": 3, "facing": "north", "brand_ids": DEMO_BRAND_IDS["shelf-4"]},
    ],
}


def main():
    db.init_db()
    n = sakenowa.sync()
    print(f"sakenowa brands cached: {n}")
    db.save_map(DEMO_MAP)
    print("demo map saved (4 shelves, entrance, register)")


if __name__ == "__main__":
    main()
