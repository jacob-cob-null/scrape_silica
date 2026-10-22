"""
scripts/plot_corpus_distribution.py

Generates visual distribution plots for the Pax Silica Gold Corpus:
1. Platform Composition (Horizontal Bar Chart)
2. Continuous Decision Rating Density (Shaded by Operational Tiers: Negatives, Discovery, Core)

Saves figure to eval/corpus_distribution.png.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
GOLD_PARQUET = REPO / "data" / "gold" / "pax_silica_corpus.parquet"
OUT_PATH = REPO / "eval" / "corpus_distribution.png"


def plot_corpus():
    df = pd.read_parquet(GOLD_PARQUET)
    total = len(df)

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=150)

    # -------------------------------------------------------------
    # Subplot 1: Platform Distribution (Horizontal Bar Chart)
    # -------------------------------------------------------------
    plat_counts = df["platform"].value_counts()
    # Group rare platforms (< 500) into 'Other'
    major_plats = plat_counts[plat_counts >= 500]
    other_sum = plat_counts[plat_counts < 500].sum()
    if other_sum > 0:
        major_plats["other (forums, bsky, etc.)"] = other_sum

    plat_labels = [p.replace("_", " ").title() for p in major_plats.index]
    y_pos = np.arange(len(major_plats))
    colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#64748b", "#94a3b8"][:len(major_plats)]

    bars = ax1.barh(y_pos, major_plats.values, color=colors, edgecolor="black", alpha=0.85)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(plat_labels, fontsize=10, fontweight="bold")
    ax1.invert_yaxis()  # Top-down
    ax1.set_xlabel("Number of Verified Records", fontsize=10)
    ax1.set_title(f"Platform Composition (N = {total:,})", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5, axis="x")

    # Add text labels on bars
    for bar in bars:
        w = bar.get_width()
        pct = w / total * 100
        ax1.text(w + (total * 0.01), bar.get_y() + bar.get_height()/2, f"{w:,} ({pct:.1f}%)",
                 va="center", fontsize=8.5, fontweight="bold")

    ax1.set_xlim(0, max(major_plats.values) * 1.22)

    # -------------------------------------------------------------
    # Subplot 2: Relevance Score Density & Operational Tiers
    # -------------------------------------------------------------
    scores = df["decision_rating"].dropna()
    n, bins, patches = ax2.hist(scores, bins=50, edgecolor="black", alpha=0.8, range=(0, 100))

    # Color code patches by tier
    for patch, bin_left in zip(patches, bins[:-1]):
        if bin_left >= 75:
            patch.set_facecolor("#10b981")  # Emerald Green (Core)
        elif bin_left >= 50:
            patch.set_facecolor("#f59e0b")  # Amber/Yellow (Discovery)
        else:
            patch.set_facecolor("#94a3b8")  # Slate Gray (Negatives)

    # Threshold markers
    ax2.axvline(x=50, color="#d97706", linestyle="--", linewidth=1.8, label="Discovery Gate (t=50%)")
    ax2.axvline(x=75, color="#059669", linestyle="-", linewidth=2.0, label="Recommended Core Gate (t=75%)")
    ax2.axvline(x=78, color="#7c3aed", linestyle=":", linewidth=2.0, label="Peak F1 Optimum (t=78%)")

    ax2.set_title("Continuous Score Density & Operational Tiers", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Decision Rating (Closeness to Pax Silica Anchor %)", fontsize=10)
    ax2.set_ylabel("Record Volume (Frequency)", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.set_ylim(0, max(n) * 1.12)
    ax2.legend(loc="upper left", fontsize=8.5, framealpha=0.95)

    # Annotations for tiers
    ax2.text(25, max(n) * 0.52, "Filtered Negatives\n(33.8k rows / 33.1%)\nOff-Topic Noise",
             ha="center", fontsize=8, color="#475569", bbox=dict(boxstyle="round,pad=0.3", fc="#f1f5f9", ec="#94a3b8", alpha=0.95))
    ax2.text(62, max(n) * 0.65, "Discovery Slice\n(44.6k rows / 43.6%)\nHigh-Recall Auditing",
             ha="center", fontsize=8, color="#b45309", bbox=dict(boxstyle="round,pad=0.3", fc="#fef3c7", ec="#f59e0b", alpha=0.95))
    ax2.text(88, max(n) * 0.85, "Analytical Core\n(23.9k rows / 23.4%)\nHigh Precision (Policy)",
             ha="center", fontsize=8, color="#065f46", bbox=dict(boxstyle="round,pad=0.3", fc="#d1fae5", ec="#10b981", alpha=0.95))

    plt.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH)
    print(f"Generated corpus distribution figure: {OUT_PATH}")


if __name__ == "__main__":
    plot_corpus()
