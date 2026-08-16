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
        # Additive: optional login. Absence of rows changes nothing for the
        # public endpoints; these tables only back /auth/* and optional admin.
        c.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT NOT NULL UNIQUE, "
            "password_hash TEXT NOT NULL, "
            "created_at REAL NOT NULL)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS auth_tokens ("
            "token TEXT PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "created_at REAL NOT NULL)"
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


# ----- users / auth tokens (optional login) -----
def create_user(username: str, password_hash: str, created_at: float) -> dict | None:
    """Insert a user. Returns the row dict, or None if the username is taken."""
    try:
        with _conn() as c:
            cur = c.execute(
                "INSERT INTO users(username, password_hash, created_at) "
                "VALUES(?, ?, ?)",
                (username, password_hash, created_at),
            )
            return {"id": cur.lastrowid, "username": username}
    except sqlite3.IntegrityError:
        return None


def get_user_by_username(username: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT id, username, password_hash FROM users WHERE username=?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT id, username FROM users WHERE id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_token(token: str, user_id: int, created_at: float):
    with _conn() as c:
        c.execute(
            "INSERT INTO auth_tokens(token, user_id, created_at) VALUES(?, ?, ?)",
            (token, user_id, created_at),
        )


def get_user_id_for_token(token: str | None) -> int | None:
    if not token:
        return None
    with _conn() as c:
        row = c.execute(
            "SELECT user_id FROM auth_tokens WHERE token=?", (token,)
        ).fetchone()
        return row["user_id"] if row else None


def delete_token(token: str):
    with _conn() as c:
        c.execute("DELETE FROM auth_tokens WHERE token=?", (token,))
