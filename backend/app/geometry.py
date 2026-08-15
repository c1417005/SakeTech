"""Grid geometry: shelf occupancy, facing-aware adjacency, and an optional
image->grid homography for the iOS ingest path.

Coordinate convention (matches the map spec): origin top-left, +x right,
+y down. "north" = up (toward smaller y).
"""
from __future__ import annotations

import numpy as np


def shelf_cells(shelf: dict) -> list[tuple[int, int]]:
    """Cells occupied by a shelf. north/south extend along x; east/west along y."""
    x, y, length, facing = shelf["x"], shelf["y"], shelf["length"], shelf["facing"]
    if facing in ("north", "south"):
        return [(x + i, y) for i in range(length)]
    return [(x, y + i) for i in range(length)]


def shelf_front_cells(shelf: dict) -> list[tuple[int, int]]:
    """The cells a customer must stand in to be *looking at* the shelf.
    Only the facing side is valid (not 4-neighbourhood)."""
    facing = shelf["facing"]
    delta = {"north": (0, -1), "south": (0, 1),
             "east": (1, 0), "west": (-1, 0)}[facing]
    return [(cx + delta[0], cy + delta[1]) for cx, cy in shelf_cells(shelf)]


def shelf_at(cell_x: int, cell_y: int, objects: list[dict]) -> str | None:
    """Which shelf is the person (at cell) looking at? Backend-owned decision.

    If a corridor puts the person in front of two facing shelves, pick the first
    (deterministic). [TBD: 向かい合う棚を配列で返すか最近1つか -> currently 1つ]
    """
    for obj in objects:
        if obj.get("type") != "shelf":
            continue
        if (cell_x, cell_y) in shelf_front_cells(obj):
            return obj["id"]
    return None


# ---------- optional image->grid homography (iOS ingest) ----------
def compute_homography(image_pts, grid_pts) -> list[list[float]]:
    """Solve 3x3 homography (normalized image 0..1 -> grid cell coords) via DLT.
    Needs >= 4 correspondences."""
    if len(image_pts) < 4 or len(image_pts) != len(grid_pts):
        raise ValueError("need >=4 matched points")
    A = []
    for (x, y), (u, v) in zip(image_pts, grid_pts):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vh = np.linalg.svd(np.asarray(A, float))
    H = vh[-1].reshape(3, 3)
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return H.tolist()


def project_to_grid(H: list[list[float]], x: float, y: float) -> tuple[int, int]:
    """Apply homography to normalized image point -> integer grid cell."""
    p = np.asarray(H, float) @ np.array([x, y, 1.0])
    w = p[2] if abs(p[2]) > 1e-12 else 1e-12
    return int(round(p[0] / w)), int(round(p[1] / w))
