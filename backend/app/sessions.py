"""Live session tracking + a deterministic demo simulator.

A session is one anonymous visit (退店で消滅). We keep only transient state in
memory; nothing about a person is persisted. Two producers feed sessions:
  1. real iOS ingest  -> SessionStore.observe(...)
  2. demo/mock replay -> DemoSimulator.sessions(elapsed)

Both emit the same `Session` shape so GET /sessions is identical either way.
"""
from __future__ import annotations

import time

from app import config, geometry, inference, db
from app.models import Session


def _state_for(shelf_id, dwell_sec: float) -> str:
    if shelf_id is None:
        return "moving"
    if dwell_sec >= config.HESITATING_SEC:
        return "hesitating"
    if dwell_sec >= config.VIEWING_SEC:
        return "viewing"
    return "moving"


def _brands_of_shelf(objects, shelf_id):
    for o in objects:
        if o.get("type") == "shelf" and o["id"] == shelf_id:
            return o.get("brand_ids", [])
    return []


class SessionStore:
    """Fed by real iOS ingest. Recomputes state/dwell/profile per observation."""

    def __init__(self, ttl_sec: float = 30.0):
        self.ttl_sec = ttl_sec
        self._s: dict[str, dict] = {}

    def observe(self, objects, session_id, cell_x, cell_y, t,
                appearance_tags=None):
        s = self._s.get(session_id)
        if s is None:
            s = {"first_t": t, "shelf_id": None, "shelf_start": t,
                 "dwell_by_brand": {}, "appearance": [], "last_t": t}
            self._s[session_id] = s

        shelf_id = geometry.shelf_at(cell_x, cell_y, objects)
        dt = max(0.0, t - s["last_t"])

        if shelf_id != s["shelf_id"]:
            s["shelf_id"] = shelf_id
            s["shelf_start"] = t
        if shelf_id is not None:
            for bid in _brands_of_shelf(objects, shelf_id):
                s["dwell_by_brand"][bid] = s["dwell_by_brand"].get(bid, 0.0) + dt

        if appearance_tags:
            s["appearance"] = appearance_tags
        s["last_t"] = t
        s["x"], s["y"] = cell_x, cell_y

    def prune(self, now: float | None = None):
        now = now or time.time()
        for sid in [k for k, v in self._s.items() if now - v["last_t"] > self.ttl_sec]:
            del self._s[sid]

    def sessions(self) -> list[Session]:
        out = []
        for sid, s in self._s.items():
            dwell = s["last_t"] - s["shelf_start"] if s["shelf_id"] else 0.0
            out.append(Session(
                session_id=sid, x=s.get("x", 0), y=s.get("y", 0),
                state=_state_for(s["shelf_id"], dwell),
                dwell_sec=int(dwell), shelf_id=s["shelf_id"],
                elapsed_sec=int(s["last_t"] - s["first_t"]),
                appearance_tags=s.get("appearance", []),
                profile=inference.infer_profile(s["dwell_by_brand"]),
            ))
        return out


class DemoSimulator:
    """Closed-form replay of the demo scenario (入店 -> 1-3番棚を回遊 -> 4番で迷う).

    Given elapsed seconds it returns the session state deterministically, so
    every poll is idempotent and the demo never drifts. Drives the SAME
    inference pipeline as live ingest.
    """

    def __init__(self, objects: list[dict], appearance=None):
        self.objects = objects
        self.appearance = appearance or ["赤い上着", "黒いカバン"]
        shelves = [o for o in objects if o.get("type") == "shelf"]
        ent = next((o for o in objects if o.get("type") == "entrance"), None)
        start = (ent["x"], ent["y"]) if ent else (0, 7)
        # waypoints: (cell, shelf_id_or_None, seconds). Front cell of each shelf.
        self.segments = []
        if ent:
            self.segments.append((start, None, 3))
        for i, sh in enumerate(shelves):
            front = geometry.shelf_front_cells(sh)
            cell = front[len(front) // 2] if front else (sh["x"], sh["y"])
            # linger long at the last shelf so it reaches "hesitating"
            secs = 25 if i == len(shelves) - 1 else 7
            self.segments.append((cell, sh["id"], secs))
        self.total = sum(s[2] for s in self.segments)

    def sessions(self, elapsed: float) -> list[Session]:
        if not self.segments:
            return []
        e = elapsed % self.total  # loop the demo
        acc = 0.0
        dwell_by_brand: dict[int, float] = {}
        cur_cell, cur_shelf, cur_dwell = self.segments[0][0], None, 0.0
        first_t = 0.0
        for cell, shelf_id, secs in self.segments:
            seg_end = acc + secs
            spent = min(secs, max(0.0, e - acc))
            if shelf_id is not None and spent > 0:
                for bid in _brands_of_shelf(self.objects, shelf_id):
                    dwell_by_brand[bid] = dwell_by_brand.get(bid, 0.0) + spent
            if acc <= e < seg_end:
                cur_cell, cur_shelf, cur_dwell = cell, shelf_id, e - acc
                break
            acc = seg_end
        prof = inference.infer_profile(dwell_by_brand)
        return [Session(
            session_id="demo-a1b2", x=cur_cell[0], y=cur_cell[1],
            state=_state_for(cur_shelf, cur_dwell),
            dwell_sec=int(cur_dwell), shelf_id=cur_shelf,
            elapsed_sec=int(e), appearance_tags=self.appearance, profile=prof,
        )]
