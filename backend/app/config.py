"""Tunable constants. Values marked TBD are provisional defaults chosen by the
backend; they are called out in docs/backend-design.md and need human sign-off.
"""

# Grid is fixed by the map spec (10x8).
GRID_WIDTH = 10
GRID_HEIGHT = 8

# --- session state thresholds (dwell seconds) --- [TBD: confirm with team]
VIEWING_SEC = 4       # >= this in front of a shelf => "viewing"
HESITATING_SEC = 20   # >= this in front of one shelf => "hesitating"

# --- preference inference --- [TBD]
# A brand counts toward the profile "basis" once the session has dwelled this
# long near its shelf.
BASIS_MIN_DWELL_SEC = 5
MAX_PROFILE_TAGS = 3
MAX_BASIS = 3

# confidence tiers by (#basis brands, total dwell sec)
CONF_HIGH_BASIS = 3
CONF_HIGH_DWELL = 30
CONF_MED_BASIS = 2
CONF_MED_DWELL = 12

# --- type4 derivation thresholds (sakenowa f-values are ~0..1) --- [TBD]
AROMA_HIGH = 0.30     # f1 (華やか) >= => high aroma
BODY_RICH = 0.40      # f3 (重厚) >= => rich body

# --- appearance tags --- [TBD: MVP = clothing color only]
APPEARANCE_FIELDS = ["upper_color", "lower_color", "bag_color"]

SAKENOWA_BASE = "https://muro.sakenowa.com/sakenowa-data/api/"
ISHIKAWA_AREA_ID = 17
SAKENOWA_ATTRIBUTION = "この銘柄情報は「さけのわデータ」(https://sakenowa.com) を利用しています。"
