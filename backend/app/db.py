"""Tiny SQLite persistence for the map and cached sakenowa brands.

Sessions are transient (退店で消滅) and live in memory, not here.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "kumu.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS brands "
            "(brand_id INTEGER PRIMARY KEY, data TEXT NOT NULL)"
        )


# ----- map (single map, key='map') -----
def save_map(data: dict):
    with _conn() as c:
        c.execute(
            "INSERT INTO kv(k, v) VALUES('map', ?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (json.dumps(data, ensure_ascii=False),),
        )


def load_map() -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT v FROM kv WHERE k='map'").fetchone()
        return json.loads(row["v"]) if row else None


# ----- per-camera image->grid homography calibration (key='calib:<camera_id>') -----
# Optional and backend-owned: absence means /ingest falls back to naive scaling.
def save_calibration(camera_id: str, matrix: list[list[float]]):
    with _conn() as c:
        c.execute(
            "INSERT INTO kv(k, v) VALUES(?, ?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (f"calib:{camera_id}", json.dumps(matrix)),
        )


def load_calibration(camera_id: str) -> list[list[float]] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT v FROM kv WHERE k=?", (f"calib:{camera_id}",)
        ).fetchone()
        return json.loads(row["v"]) if row else None


# ----- brands cache -----
def upsert_brands(brands: list[dict]):
    with _conn() as c:
        c.executemany(
            "INSERT INTO brands(brand_id, data) VALUES(?, ?) "
            "ON CONFLICT(brand_id) DO UPDATE SET data=excluded.data",
            [(b["brand_id"], json.dumps(b, ensure_ascii=False)) for b in brands],
        )


def get_brand(brand_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT data FROM brands WHERE brand_id=?", (brand_id,)).fetchone()
        return json.loads(row["data"]) if row else None


def list_brands(q: str | None = None) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT data FROM brands").fetchall()
    items = [json.loads(r["data"]) for r in rows]
    if q:
        items = [b for b in items if q in b["name"]]
    return items


def brand_count() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM brands").fetchone()["n"]
