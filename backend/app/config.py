"""Tunable constants. Values marked TBD are provisional defaults chosen by the
backend; they are called out in docs/backend-design.md and need human sign-off.
"""

import os


def _env_int(name: str, default: int) -> int:
    """Read an int from env; fall back to default on unset/blank/invalid."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float from env; fall back to default on unset/blank/invalid."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


# Grid is fixed by the map spec (10x8).
GRID_WIDTH = 10
GRID_HEIGHT = 8

# The [TBD] tunables below are overridable via env (KUMU_*) so ops can adjust
# them per store without a redeploy. Defaults are unchanged when env is unset.

# --- session state thresholds (dwell seconds) --- [TBD: confirm with team]
VIEWING_SEC = _env_int("KUMU_VIEWING_SEC", 4)         # >= this in front of a shelf => "viewing"
HESITATING_SEC = _env_int("KUMU_HESITATING_SEC", 20)  # >= this in front of one shelf => "hesitating"

# --- preference inference --- [TBD]
# A brand counts toward the profile "basis" once the session has dwelled this
# long near its shelf.
BASIS_MIN_DWELL_SEC = _env_int("KUMU_BASIS_MIN_DWELL_SEC", 5)
MAX_PROFILE_TAGS = _env_int("KUMU_MAX_PROFILE_TAGS", 3)
MAX_BASIS = _env_int("KUMU_MAX_BASIS", 3)

# confidence tiers by (#basis brands, total dwell sec)
CONF_HIGH_BASIS = _env_int("KUMU_CONF_HIGH_BASIS", 3)
CONF_HIGH_DWELL = _env_int("KUMU_CONF_HIGH_DWELL", 30)
CONF_MED_BASIS = _env_int("KUMU_CONF_MED_BASIS", 2)
CONF_MED_DWELL = _env_int("KUMU_CONF_MED_DWELL", 12)

# --- type4 derivation thresholds (sakenowa f-values are ~0..1) --- [TBD]
AROMA_HIGH = _env_float("KUMU_AROMA_HIGH", 0.30)  # f1 (華やか) >= => high aroma
BODY_RICH = _env_float("KUMU_BODY_RICH", 0.40)    # f3 (重厚) >= => rich body

# --- appearance tags --- [TBD: MVP = clothing color only]
APPEARANCE_FIELDS = ["upper_color", "lower_color", "bag_color"]

SAKENOWA_BASE = "https://muro.sakenowa.com/sakenowa-data/api/"
ISHIKAWA_AREA_ID = 17
SAKENOWA_ATTRIBUTION = "この銘柄情報は「さけのわデータ」(https://sakenowa.com) を利用しています。"

# --- CORS ---
# Only the browser-based frontend is subject to CORS; the iOS app uses a native
# HTTP client and is unaffected. Default to local Vite dev/preview origins so
# `pnpm dev` works out of the box. In production set KUMU_CORS_ORIGINS to a
# comma-separated allowlist of real origins (e.g. "https://kumu.example.com").
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",   # vite dev
    "http://127.0.0.1:5173",
    "http://localhost:4173",   # vite preview
    "http://127.0.0.1:4173",
]


def cors_origins() -> list[str]:
    """Allowed CORS origins: KUMU_CORS_ORIGINS (comma-separated) or dev defaults."""
    raw = os.environ.get("KUMU_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return list(DEFAULT_CORS_ORIGINS)
