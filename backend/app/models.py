"""Pydantic schemas = the API contract types.

The map types (Shelf/Marker/MapData) mirror frontend/src/types/map.ts EXACTLY.
That file is labeled "バックエンドとの API 契約そのもの" (the contract itself) and
must not diverge.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Facing = Literal["north", "south", "east", "west"]
SessionState = Literal["moving", "viewing", "hesitating"]
Confidence = Literal["low", "medium", "high"]


# ---------- Map (POST/GET /map) : mirrors types/map.ts ----------
class Shelf(BaseModel):
    type: Literal["shelf"] = "shelf"
    id: str
    name: str
    x: int
    y: int
    length: Literal[2, 3, 4]
    facing: Facing
    brand_ids: list[int] = Field(default_factory=list)


class Marker(BaseModel):
    type: Literal["entrance", "register"]
    id: str
    x: int
    y: int


class Grid(BaseModel):
    width: int
    height: int


class MapData(BaseModel):
    grid: Grid
    # Discriminated by "type": shelf vs entrance/register.
    objects: list[dict]  # kept permissive; validated in routes to match map.ts


# ---------- Sessions (GET /sessions) ----------
class Profile(BaseModel):
    """Server-side preference estimate (F-3). Optional / additive: the frontend
    T-07 base view ignores it; the client card (F-3) consumes it later."""
    tags: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    basis: list[str] = Field(default_factory=list)


class Session(BaseModel):
    # --- binding base fields (CLAUDE.md / map-spec / frontend T-07) ---
    session_id: str
    x: int
    y: int
    state: SessionState
    dwell_sec: int
    shelf_id: Optional[str] = None
    # --- additive optional fields (PRD F-3 / 顧客識別doc) ---
    elapsed_sec: Optional[int] = None
    appearance_tags: list[str] = Field(default_factory=list)
    profile: Optional[Profile] = None


# ---------- iOS ingest (POST /ingest) ----------
class Detection(BaseModel):
    """One person detection from the iOS device.
    Coords are normalized image space (0..1); the server maps to grid cells."""
    track_id: int
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    t: float = Field(..., description="client epoch seconds")
    appearance_tags: list[str] = Field(default_factory=list)


class IngestBatch(BaseModel):
    camera_id: str = "cam-1"
    detections: list[Detection]


# ---------- camera calibration (POST /admin/calibrate) ----------
class CalibrationRequest(BaseModel):
    """Point correspondences to solve a per-camera image->grid homography.

    Backend-owned and opt-in: this does NOT change the /map (map.ts) contract.
    image_points are normalized (0..1) image coords; grid_points are the matching
    grid-cell coords. Need >= 4 non-collinear pairs.
    [TBD: which UI/source produces these correspondences — see PR/report.]
    """
    camera_id: str = "cam-1"
    image_points: list[tuple[float, float]] = Field(..., min_length=4)
    grid_points: list[tuple[float, float]] = Field(..., min_length=4)


# ---------- Brands (GET /brands, GET /brands/{id}) ----------
Type4 = Literal["薫酒", "爽酒", "醇酒", "熟酒"]


class Brand(BaseModel):
    brand_id: int
    name: str
    brewery: Optional[str] = None
    area: Optional[str] = None
    # sakenowa flavor chart (may be missing for some brands)
    f1: Optional[float] = None
    f2: Optional[float] = None
    f3: Optional[float] = None
    f4: Optional[float] = None
    f5: Optional[float] = None
    f6: Optional[float] = None
    type4: Optional[Type4] = None
    easy_tags: list[str] = Field(default_factory=list)
    has_flavor: bool = False
