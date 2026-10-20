"""Shared gold-layer schema.

The gold record has exactly four fields. Both the exporter and the evaluation
sample mirror this list so the two cannot drift apart.

See eval/LABELING_GUIDE.md for how the fields are produced and validated.
"""

# Column names and order of the gold output (data/gold/pax_silica_corpus.*).
GOLD_COLUMNS = ["platform", "decision_rating", "confidence", "content"]

# decision_rating and confidence are integers on a 0-100 scale.
RATING_MIN = 0
RATING_MAX = 100
