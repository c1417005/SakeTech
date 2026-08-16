"""Server-side preference estimation (PRD F-3 / 顧客識別doc).

Input: how long a session dwelled near each shelf (=> its brands).
Output: Profile(tags, confidence, basis). Computed on the server so the
frontend never changes when the logic changes.
"""
from __future__ import annotations

from app import config, db
from app.models import Profile


def _weighted_flavor(dwell_by_brand: dict[int, float]) -> tuple[dict, float, list[tuple[str, float]]]:
    """Dwell-weighted average flavor vector over brands that have flavor data."""
    acc = {k: 0.0 for k in ("f1", "f2", "f3", "f4", "f5", "f6")}
    total_w = 0.0
    contributors: list[tuple[str, float]] = []  # (brand name, dwell)
    for brand_id, dwell in dwell_by_brand.items():
        b = db.get_brand(brand_id)
        if not b:
            continue
        contributors.append((b["name"], dwell))
        if not b.get("has_flavor"):
            continue
        for k in acc:
            acc[k] += (b[k] or 0.0) * dwell
        total_w += dwell
    if total_w > 0:
        acc = {k: v / total_w for k, v in acc.items()}
    return acc, total_w, contributors


def _tags_from_flavor(f: dict) -> list[str]:
    """Rank axes by distance from neutral (0.5); emit up to MAX_PROFILE_TAGS."""
    candidates: list[tuple[float, str]] = []
    # (strength, label)
    candidates.append((f["f5"] - 0.5, "辛口寄り"))
    candidates.append((0.5 - f["f5"], "甘口寄り"))
    candidates.append((f["f1"] - 0.5, "香り高い"))
    candidates.append((f["f3"] - 0.5, "コクがある"))
    candidates.append((f["f6"] - 0.5, "すっきり軽快"))
    candidates.append((f["f2"] - 0.5, "芳醇"))
    positive = sorted((c for c in candidates if c[0] > 0.05), reverse=True)
    return [label for _, label in positive[:config.MAX_PROFILE_TAGS]]


def _confidence(n_basis: int, total_dwell: float) -> str:
    if n_basis >= config.CONF_HIGH_BASIS and total_dwell >= config.CONF_HIGH_DWELL:
        return "high"
    if n_basis >= config.CONF_MED_BASIS and total_dwell >= config.CONF_MED_DWELL:
        return "medium"
    return "low"


def infer_profile(dwell_by_brand: dict[int, float]) -> Profile | None:
    """Build a Profile from per-brand dwell seconds, or None if nothing to say."""
    if not dwell_by_brand:
        return None
    flavor, total_w, contributors = _weighted_flavor(dwell_by_brand)

    # basis = brands lingered at past the minimum, longest first
    basis_pairs = sorted(
        [(name, d) for name, d in contributors if d >= config.BASIS_MIN_DWELL_SEC],
        key=lambda p: p[1], reverse=True,
    )
    basis = [name for name, _ in basis_pairs[:config.MAX_BASIS]]

    tags = _tags_from_flavor(flavor) if total_w > 0 else []
    conf = _confidence(len(basis), sum(dwell_by_brand.values()))
    if conf == "low":
        # UX rule: don't assert on thin evidence.
        tags = ["推定中"] if not tags else tags
    if not tags and not basis:
        return None
    return Profile(tags=tags, confidence=conf, basis=basis)
