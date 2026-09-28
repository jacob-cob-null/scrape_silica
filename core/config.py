import os
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
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

# Ensure directories exist
for d in [BRONZE_AUTO_DIR, BRONZE_DROP_DIR, SILVER_DIR, GOLD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Tiers (Keywords)
TIER_1_KEYWORDS = ["Pax Silica", "Golden Node", "#PaxSilica"]
TIER_2_LOCATIONS = ["New Clark City", "Luzon Economic Corridor", "Tarlac", "BCDA"]
TIER_2_TOPICS = ["semiconductor", "AI hub", "data center", "power grid", "water"]
