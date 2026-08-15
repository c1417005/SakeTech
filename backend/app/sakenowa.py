"""Fetch sakenowa data, filter to Ishikawa, join flavor charts, derive type4.

The frontend must NOT call sakenowa directly (bulk payload + attribution rule);
the backend fetches, caches into SQLite, and serves a slimmed brand model.
Attribution: config.SAKENOWA_ATTRIBUTION.
"""
from __future__ import annotations

import json
import urllib.request

from app import config, db
from app.models import Brand


def _get(endpoint: str) -> dict:
    url = config.SAKENOWA_BASE + endpoint
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def derive_type4(f1: float, f3: float) -> str:
    """香りの高さ(f1 華やか) × 味の濃淡(f3 重厚) の2軸で4タイプへ。

    薫酒 = 香り高・淡麗 / 爽酒 = 香り低・淡麗
    醇酒 = 香り低・濃醇 / 熟酒 = 香り高・濃醇
    Thresholds are provisional (config.AROMA_HIGH / BODY_RICH) [TBD].
    """
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
    """Map flavor axes to plain-language tags shown on the shelf/client card."""
    tags = []
    if f["f1"] >= 0.30:
        tags.append("香り高い")
    if f["f5"] >= 0.45:
        tags.append("辛口寄り")
    elif f["f5"] <= 0.30:
        tags.append("甘口寄り")
    if f["f3"] >= 0.45:
        tags.append("コクがある")
    if f["f6"] >= 0.45:
        tags.append("すっきり軽快")
    if f["f2"] >= 0.55:
        tags.append("芳醇")
    return tags


def build_ishikawa_brands() -> list[dict]:
    """Return slimmed Brand dicts for Ishikawa brands (with flavor when present)."""
    areas = {a["id"]: a["name"] for a in _get("areas")["areas"]}
    breweries = _get("breweries")["breweries"]
    brands = _get("brands")["brands"]
    fc = {f["brandId"]: f for f in _get("flavor-charts")["flavorCharts"]}

    ishi_breweries = {b["id"]: b["name"] for b in breweries
                      if b["areaId"] == config.ISHIKAWA_AREA_ID}
    area_name = areas.get(config.ISHIKAWA_AREA_ID, "石川県")

    out: list[dict] = []
    for b in brands:
        if b["breweryId"] not in ishi_breweries:
            continue
        f = fc.get(b["id"])
        model = Brand(
            brand_id=b["id"],
            name=b["name"],
            brewery=ishi_breweries[b["breweryId"]],
            area=area_name,
        )
        if f:
            model.f1, model.f2, model.f3 = f["f1"], f["f2"], f["f3"]
            model.f4, model.f5, model.f6 = f["f4"], f["f5"], f["f6"]
            model.type4 = derive_type4(f["f1"], f["f3"])
            model.easy_tags = easy_tags(f)
            model.has_flavor = True
        out.append(model.model_dump())
    return out


def sync(force: bool = False) -> int:
    """Fetch + cache Ishikawa brands into SQLite. Returns count stored."""
    if not force and db.brand_count() > 0:
        return db.brand_count()
    brands = build_ishikawa_brands()
    db.upsert_brands(brands)
    return len(brands)
