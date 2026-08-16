"""KUMU backend API.

Contract sources (do not diverge):
  - POST/GET /map        : frontend/src/types/map.ts  (MapData)
  - GET /sessions        : CLAUDE.md base + additive optional profile (PRD F-3)
  - POST /ingest         : iOS -> server (this repo owns it)
  - GET /brands[/{id}]   : shelf brand linking (F-4/T-06), Ishikawa/sakenowa
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import ValidationError

from app import auth, config, db, geometry, sakenowa
from app.models import (
    MapData, Shelf, Marker, Session, IngestBatch, Brand, CalibrationRequest,
    RegisterRequest, LoginRequest, UserOut, AuthToken,
)
from app.sessions import SessionStore, DemoSimulator

router = APIRouter()

# In-memory live sessions (fed by /ingest). Demo mode is closed-form.
live_store = SessionStore()
_demo_start = time.time()


# ---------- auth dependencies (optional / non-blocking) ----------
def current_user(authorization: str | None = Header(default=None)) -> dict:
    """Resolve the logged-in user from a bearer token, or 401. Used by /auth/me."""
    uid = db.get_user_id_for_token(auth.bearer_token(authorization))
    user = db.get_user_by_id(uid) if uid is not None else None
    if user is None:
        raise HTTPException(401, "authentication required")
    return user


def require_admin(authorization: str | None = Header(default=None)):
    """Gate /admin/* ONLY when KUMU_ADMIN_AUTH is enabled.

    Disabled (default): a no-op, so admin endpoints behave exactly as before and
    nothing in the running product is blocked. Enabled: require a valid token.
    """
    if not config.admin_auth_enabled():
        return None
    uid = db.get_user_id_for_token(auth.bearer_token(authorization))
    if uid is None:
        raise HTTPException(401, "authentication required")
    return uid


def _mock_enabled(mock: bool | None) -> bool:
    if mock is not None:
        return mock
    return os.environ.get("KUMU_MOCK", "").lower() in ("1", "true", "yes")


def _validate_map(body: dict) -> dict:
    """Ensure objects match map.ts (Shelf | Marker). Raises 400 on mismatch."""
    try:
        MapData.model_validate(body)
        for o in body.get("objects", []):
            if o.get("type") == "shelf":
                Shelf.model_validate(o)
            elif o.get("type") in ("entrance", "register"):
                Marker.model_validate(o)
            else:
                raise ValueError(f"unknown object type: {o.get('type')}")
    except (ValidationError, ValueError) as e:
        raise HTTPException(400, f"invalid map: {e}")
    return body


# ---------- auth (optional login; public endpoints never require it) ----------
@router.post("/auth/register", response_model=AuthToken)
def register(req: RegisterRequest):
    now = time.time()
    user = db.create_user(req.username, auth.hash_password(req.password), now)
    if user is None:
        raise HTTPException(409, "username already taken")
    token = auth.new_token()
    db.create_token(token, user["id"], now)
    return AuthToken(token=token, user=UserOut(**user))


@router.post("/auth/login", response_model=AuthToken)
def login(req: LoginRequest):
    user = db.get_user_by_username(req.username)
    if user is None or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "invalid username or password")
    token = auth.new_token()
    db.create_token(token, user["id"], time.time())
    return AuthToken(token=token, user=UserOut(id=user["id"], username=user["username"]))


@router.get("/auth/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return UserOut(**user)


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = auth.bearer_token(authorization)
    if token:
        db.delete_token(token)
    return {"ok": True}


# ---------- map ----------
@router.post("/map")
def post_map(body: dict):
    _validate_map(body)
    db.save_map(body)
    return {"saved": True}


@router.get("/map")
def get_map():
    m = db.load_map()
    if m is None:
        # F-1: unregistered map => empty start, not an error.
        return {"grid": {"width": 10, "height": 8}, "objects": []}
    return m


# ---------- sessions ----------
@router.get("/sessions", response_model=list[Session])
def get_sessions(mock: bool | None = Query(default=None)):
    if _mock_enabled(mock):
        m = db.load_map() or {"objects": []}
        sim = DemoSimulator(m.get("objects", []))
        return sim.sessions(time.time() - _demo_start)
    live_store.prune()
    return live_store.sessions()


def _clamp_cell(cx: int, cy: int, gw: int, gh: int) -> tuple[int, int]:
    return max(0, min(gw - 1, cx)), max(0, min(gh - 1, cy))


# ---------- iOS ingest ----------
@router.post("/ingest")
def post_ingest(batch: IngestBatch):
    """iOS sends normalized detections; server maps to grid + updates sessions.

    Mapping: if a per-camera homography has been calibrated (POST /admin/calibrate),
    project normalized image coords -> grid cells through it; otherwise fall back to
    the MVP naive scaling (normalized * grid size). Behavior is unchanged for
    uncalibrated cameras.
    """
    if len(batch.detections) > config.MAX_INGEST_DETECTIONS:
        raise HTTPException(
            413, f"too many detections: {len(batch.detections)} "
                 f"> {config.MAX_INGEST_DETECTIONS}")
    m = db.load_map() or {"objects": [], "grid": {"width": 10, "height": 8}}
    gw = m.get("grid", {}).get("width", 10)
    gh = m.get("grid", {}).get("height", 8)
    objects = m.get("objects", [])
    now = time.time()
    H = db.load_calibration(batch.camera_id)  # None => naive fallback
    for d in batch.detections:
        if H is not None:
            cx, cy = geometry.project_to_grid(H, d.x, d.y)
        else:
            cx, cy = int(d.x * gw), int(d.y * gh)
        cx, cy = _clamp_cell(cx, cy, gw, gh)
        live_store.observe(objects, f"sess-{d.track_id}", cx, cy, d.t or now,
                           appearance_tags=d.appearance_tags)
    return {"accepted": len(batch.detections), "calibrated": H is not None}


# ---------- camera calibration (backend-owned; does not touch map.ts) ----------
@router.post("/admin/calibrate")
def post_calibrate(req: CalibrationRequest, _=Depends(require_admin)):
    """Solve + persist a per-camera image->grid homography from >=4 point pairs.

    [TBD] The *source* of these correspondences (a calibration UI / who marks the
    points) is still open; this endpoint is the backend hook so the mapping is
    ready and testable without changing the frontend /map contract.
    """
    if len(req.image_points) != len(req.grid_points):
        raise HTTPException(400, "image_points and grid_points length mismatch")
    image_pts = [tuple(p) for p in req.image_points]
    grid_pts = [tuple(p) for p in req.grid_points]
    try:
        H = geometry.compute_homography(image_pts, grid_pts)
    except ValueError as e:
        raise HTTPException(400, f"calibration failed: {e}")
    err = geometry.reprojection_error(H, image_pts, grid_pts)
    # Persist the raw correspondences alongside the matrix so the calibration can
    # be re-displayed / edited / re-solved later, plus the fit quality.
    record = {
        "matrix": H,
        "image_points": req.image_points,
        "grid_points": req.grid_points,
        "reprojection_error": err,
        "updated_at": time.time(),
    }
    db.save_calibration_record(req.camera_id, record)
    return {
        "camera_id": req.camera_id,
        "homography": H,
        "reprojection_error": err,
        "image_points": req.image_points,
        "grid_points": req.grid_points,
    }


@router.get("/admin/calibrate/{camera_id}")
def get_calibrate(camera_id: str, _=Depends(require_admin)):
    rec = db.load_calibration_record(camera_id)
    if rec is None:
        raise HTTPException(404, "no calibration for camera")
    return {
        "camera_id": camera_id,
        "homography": rec["matrix"],
        "reprojection_error": rec.get("reprojection_error"),
        "image_points": rec.get("image_points"),
        "grid_points": rec.get("grid_points"),
        "updated_at": rec.get("updated_at"),
    }


# ---------- brands (sakenowa / Ishikawa) ----------
@router.get("/brands", response_model=list[Brand])
def get_brands(q: str | None = Query(default=None), ids: str | None = Query(default=None)):
    if db.brand_count() == 0:
        sakenowa.sync()
    if ids:
        wanted = {int(i) for i in ids.split(",") if i.strip().isdigit()}
        return [b for b in db.list_brands() if b["brand_id"] in wanted]
    return db.list_brands(q)


@router.get("/brands/{brand_id}", response_model=Brand)
def get_brand(brand_id: int):
    if db.brand_count() == 0:
        sakenowa.sync()
    b = db.get_brand(brand_id)
    if not b:
        raise HTTPException(404, "brand not found")
    return b


@router.get("/attribution")
def attribution():
    from app.config import SAKENOWA_ATTRIBUTION
    return {"text": SAKENOWA_ATTRIBUTION}


# ---------- admin ----------
@router.post("/admin/sync-sakenowa")
def sync_sakenowa(force: bool = Query(default=True), _=Depends(require_admin)):
    n = sakenowa.sync(force=force)
    return {"stored_brands": n}
