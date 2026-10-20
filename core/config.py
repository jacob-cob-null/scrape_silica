from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BRONZE_DIR = DATA_DIR / "bronze"
BRONZE_AUTO_DIR = BRONZE_DIR / "automated"
BRONZE_DROP_DIR = BRONZE_DIR / "drop_folder"
BRONZE_ZEESCHUIMER_DIR = BRONZE_DIR / "zeeschuimer"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

# Ensure directories exist
for d in [BRONZE_AUTO_DIR, BRONZE_DROP_DIR, BRONZE_ZEESCHUIMER_DIR, SILVER_DIR, GOLD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
# TIER 1 — Brand / Project Identity (safe to search alone)
#   Direct mentions of the project. Always high-signal.
# ──────────────────────────────────────────────────────────────
TIER_1_BRAND = [
    "Pax Silica", "PaxSilica", "Pax-Silica",
    "Pax Silica Economic Security Zone",
]

# ──────────────────────────────────────────────────────────────
# TIER 2 — Location & Industry Anchors (safe to search alone)
#   Specific enough to yield relevant results without pairing.
# ──────────────────────────────────────────────────────────────
TIER_2_ANCHORS = [
    # Locations
    "New Clark City", "Clark Freeport", "Clark Special Economic Zone",
    "Luzon Economic Corridor", "Luzon corridor", "Tarlac",
    # Agencies
    "BCDA", "PEZA",
    # Industry (Philippine-specific)
    "AI industrial hub", "chip supply chain",
    "critical minerals", "rare earth",
]

# ──────────────────────────────────────────────────────────────
# TIER 3 — Context Terms (MUST be paired with a T1/T2 anchor)
#   Too broad alone. Paired with anchors, they capture sentiment.
# ──────────────────────────────────────────────────────────────
TIER_3_CONTEXT = [
    # Tech & Infrastructure
    "semiconductor", "foundry", "data center", "AI hub",
    # Socio-Political
    "displacement", "indigenous", "ancestral land",
    "US military", "EDCA", "water shortage", "reclassification",
    # Filipino Local Terms
    "Aeta", "pinagbili", "polusyon", "base militar",
    # Government & Policy
    "POGO", "deforestation"
]

# ──────────────────────────────────────────────────────────────
# QUERY BUILDER — Generates the final search list
# ──────────────────────────────────────────────────────────────

# Step 1: All T1 and T2 terms are safe to search independently
ALL_KEYWORDS = list(TIER_1_BRAND) + list(TIER_2_ANCHORS)

# Step 2: Pair primary anchors with every T3 context term
#   This creates queries like: "New Clark City" semiconductor
#   which implicitly acts as an AND search on most platforms.
_PRIMARY_ANCHORS = ["Pax Silica", "New Clark City", "Luzon Economic Corridor"]
for anchor in _PRIMARY_ANCHORS:
    for ctx in TIER_3_CONTEXT:
        ALL_KEYWORDS.append(f'"{anchor}" {ctx}')

# Deduplicate while preserving order
_seen = set()
_deduped = []
for kw in ALL_KEYWORDS:
    if kw not in _seen:
        _seen.add(kw)
        _deduped.append(kw)
ALL_KEYWORDS = _deduped
