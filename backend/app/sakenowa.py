"""Fetch sakenowa data, filter to Ishikawa, join flavor charts, derive type4.

The frontend must NOT call sakenowa directly (bulk payload + attribution rule);
the backend fetches, caches into SQLite, and serves a slimmed brand model.
Attribution: config.SAKENOWA_ATTRIBUTION.

Robustness (A2): the upstream API can be down or return partial records, so the
mapping tolerates missing keys/flavor axes and `sync()` never crashes the API —
on failure it keeps whatever is already cached.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from app import config, db
from app.models import Brand

log = logging.getLogger(__name__)

# Errors that mean "upstream unavailable / malformed" — recoverable by falling
# back to cache. urllib.error.URLError and socket timeouts are OSError subclasses;
# json decode errors are ValueError subclasses.
_FETCH_ERRORS = (OSError, ValueError, KeyError, TypeError)

FLAVOR_AXES = ("f1", "f2", "f3", "f4", "f5", "f6")


def _get(endpoint: str) -> dict:
    url = config.SAKENOWA_BASE + endpoint
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _num(v) -> float | None:
    """Coerce a sakenowa f-value to float, or None if missing/non-numeric."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def derive_type4(f1: float | None, f3: float | None) -> str | None:
    """香りの高さ(f1 華やか) × 味の濃淡(f3 重厚) の2軸で4タイプへ。

    薫酒 = 香り高・淡麗 / 爽酒 = 香り低・淡麗
    醇酒 = 香り低・濃醇 / 熟酒 = 香り高・濃醇
    Thresholds are provisional (config.AROMA_HIGH / BODY_RICH) [TBD].
    Returns None when either axis is missing (do not guess a type without data).
    """
    if f1 is None or f3 is None:
        return None
    aroma_high = f1 >= config.AROMA_HIGH
    rich = f3 >= config.BODY_RICH
    if aroma_high and not rich:
        return "薫酒"
    if not aroma_high and not rich:
        return "爽酒"
    if not aroma_high and rich:
        return "醇酒"
    return "熟酒"


def easy_tags(f: dict) -> list[str]:
    """Map flavor axes to plain-language tags shown on the shelf/client card.

    Tolerant of missing axes (partial flavor charts) — an absent axis simply
    contributes no tag rather than raising.
    """
    f1, f2, f3 = _num(f.get("f1")), _num(f.get("f2")), _num(f.get("f3"))
    f5, f6 = _num(f.get("f5")), _num(f.get("f6"))
    tags: list[str] = []
    if f1 is not None and f1 >= 0.30:
        tags.append("香り高い")
    if f5 is not None:
        if f5 >= 0.45:
            tags.append("辛口寄り")
        elif f5 <= 0.30:
            tags.append("甘口寄り")
    if f3 is not None and f3 >= 0.45:
        tags.append("コクがある")
    if f6 is not None and f6 >= 0.45:
        tags.append("すっきり軽快")
    if f2 is not None and f2 >= 0.55:
        tags.append("芳醇")
    return tags


def build_ishikawa_brands() -> list[dict]:
    """Return slimmed Brand dicts for Ishikawa brands (with flavor when present).

    Defensive against partial upstream records: entries missing an id / name /
    brewery link are skipped rather than crashing the whole sync.
    """
    areas = {a["id"]: a.get("name") for a in _get("areas").get("areas", []) if "id" in a}
    breweries = _get("breweries").get("breweries", [])
    brands = _get("brands").get("brands", [])
    fc = {f["brandId"]: f
          for f in _get("flavor-charts").get("flavorCharts", []) if "brandId" in f}

    ishi_breweries = {b["id"]: b.get("name", "") for b in breweries
                      if "id" in b and b.get("areaId") == config.ISHIKAWA_AREA_ID}
    area_name = areas.get(config.ISHIKAWA_AREA_ID, "石川県")

    out: list[dict] = []
    for b in brands:
        bid, name, brewery_id = b.get("id"), b.get("name"), b.get("breweryId")
        if bid is None or not name or brewery_id not in ishi_breweries:
            continue
        model = Brand(
            brand_id=bid,
            name=name,
            brewery=ishi_breweries[brewery_id],
            area=area_name,
        )
        f = fc.get(bid)
        if f:
            model.f1, model.f2, model.f3, model.f4, model.f5, model.f6 = (
                _num(f.get(a)) for a in FLAVOR_AXES
            )
            model.type4 = derive_type4(model.f1, model.f3)
            model.easy_tags = easy_tags(f)
            # Only claim flavor data when at least one axis actually resolved.
            model.has_flavor = any(getattr(model, a) is not None for a in FLAVOR_AXES)
        out.append(model.model_dump())
    return out


def sync(force: bool = False) -> int:
    """Fetch + cache Ishikawa brands into SQLite. Returns count stored.

    On upstream failure (network down / malformed payload) it logs and keeps the
    existing cache instead of raising, so /brands degrades gracefully.
    """
    if not force and db.brand_count() > 0:
        return db.brand_count()
    try:
        brands = build_ishikawa_brands()
    except _FETCH_ERRORS as e:
        log.warning("sakenowa sync failed (%s); serving cached brands", e)
        return db.brand_count()
    db.upsert_brands(brands)
    return len(brands)
