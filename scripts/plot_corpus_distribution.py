"""
scripts/plot_corpus_distribution.py

Generates publication-quality distribution plots for the Pax Silica Gold Corpus:
1. eval/platform_composition.png - Clean editorial horizontal bar chart.
2. eval/score_distribution.png   - Continuous density histogram with unblocked operational tiers.
3. eval/corpus_distribution.png  - Vertical stacked publication layout.

Visual standards (anti-AI-slop):
- Zero floating speech bubbles or bounding boxes obscuring data bars.
- Dedicated zone header banners placed above the plot area.
- Monochromatic / editorial palette (McKinsey / The Economist style).
- Borderless minimalist axes (no top/right/left spines) with subtle horizontal-only grids.
- Outside-the-plot legends for zero data occlusion.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
GOLD_PARQUET = REPO / "data" / "gold" / "pax_silica_corpus.parquet"
EVAL_DIR = REPO / "eval"


def plot_platform_composition(df: pd.DataFrame, out_path: Path):
    total = len(df)
    plat_counts = df["platform"].value_counts()
    major_plats = plat_counts[plat_counts >= 500].copy()
    other_sum = plat_counts[plat_counts < 500].sum()
    if other_sum > 0:
        major_plats["other (forums, bsky, etc.)"] = other_sum

    plat_labels = [p.replace("_", " ").title() for p in major_plats.index]
    y_pos = np.arange(len(major_plats))

    # Sequential professional slate-indigo palette
    colors = [
        "#1e3a8a",  # Deep navy (YouTube Comments - 53.6%)
        "#2563eb",  # Royal Blue (Reddit - 19.7%)
        "#3b82f6",  # Tech Blue (TikTok - 16.5%)
        "#60a5fa",  # Sky Blue (RSS - 4.6%)
        "#818cf8",  # Indigo Accent (YouTube Video - 2.8%)
        "#94a3b8",  # Slate (Bluesky - 2.2%)
        "#cbd5e1",  # Light Slate (GDELT - 0.5%)
        "#e2e8f0",  # Soft Gray (Other - 0.2%)
    ][:len(major_plats)]

    fig, ax = plt.subplots(figsize=(10.0, 4.8), dpi=180)
    bars = ax.barh(y_pos, major_plats.values, color=colors, height=0.62, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plat_labels, fontsize=10.5, fontweight="bold", color="#0f172a")
    ax.invert_yaxis()

    # Clean axes & minimalist spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors="#64748b", labelsize=9.5)
    ax.set_xlabel("Number of Verified Records", fontsize=10.5, fontweight="bold", color="#0f172a", labelpad=10)

    # Title & Subtitle in top left
    ax.text(0.0, 1.15, "Pax Silica Corpus: Platform Distribution",
            transform=ax.transAxes, fontsize=13, fontweight="bold", color="#0f172a")
    ax.text(0.0, 1.06, f"Verified composition across N = {total:,} multi-platform records",
            transform=ax.transAxes, fontsize=9.5, color="#64748b")

    for bar in bars:
        w = bar.get_width()
        pct = w / total * 100
        ax.text(w + (total * 0.012), bar.get_y() + bar.get_height() / 2,
                f"{w:,}  ({pct:.1f}%)",
                va="center", fontsize=9.5, fontweight="bold", color="#1e293b")

    ax.set_xlim(0, max(major_plats.values) * 1.22)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Generated clean platform composition figure: {out_path}")


def plot_score_distribution(df: pd.DataFrame, out_path: Path):
    scores = df["decision_rating"].dropna()

    fig, ax = plt.subplots(figsize=(11.0, 5.6), dpi=180)
    n, bins, patches = ax.hist(scores, bins=50, range=(0, 100), edgecolor="white", linewidth=0.6, zorder=3)

    c_neg = "#94a3b8"  # Slate
    c_disc = "#f59e0b" # Amber
    c_core = "#10b981" # Emerald

    for patch, bin_left in zip(patches, bins[:-1]):
        if bin_left >= 75:
            patch.set_facecolor(c_core)
        elif bin_left >= 50:
            patch.set_facecolor(c_disc)
        else:
            patch.set_facecolor(c_neg)

    # Threshold markers
    ax.axvline(x=50, color="#d97706", linestyle="--", linewidth=1.8, label="Discovery Gate (t = 50%)", zorder=4)
    ax.axvline(x=75, color="#059669", linestyle="-", linewidth=2.0, label="Core Gate (t = 75%)", zorder=4)
    ax.axvline(x=78, color="#7c3aed", linestyle=":", linewidth=2.0, label="Peak F1 Optimum (t = 78%)", zorder=4)

    # Spines & Grid
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.grid(True, axis="y", linestyle="-", color="#f1f5f9", linewidth=0.8)
    ax.set_axisbelow(True)

    ax.set_xlim(-1, 101)
    ax.set_ylim(0, max(n) * 1.32)
    ax.set_xlabel("Decision Rating (Closeness to Pax Silica Anchor %)", fontsize=10.5, fontweight="bold", color="#0f172a", labelpad=8)
    ax.set_ylabel("Record Volume (Frequency)", fontsize=10.5, fontweight="bold", color="#0f172a", labelpad=8)
    ax.tick_params(colors="#64748b", labelsize=9.5)

    # Title & Subtitle in top left
    ax.text(0.0, 1.20, "Continuous Relevance Score Density & Operational Tiers",
            transform=ax.transAxes, fontsize=13, fontweight="bold", color="#0f172a")
    ax.text(0.0, 1.13, f"LAYA noul cross-encoder entailment distribution across N = {len(df):,} verified records",
            transform=ax.transAxes, fontsize=9.5, color="#64748b")

    # Legend outside the plot - NOTHING BLOCKS THE CHART
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=3, frameon=False, fontsize=9.5)

    # Clean zone header labels in dedicated top band (NO floating speech bubbles inside histogram)
    header_y = max(n) * 1.20
    ax.text(25, header_y, "FILTERED NEGATIVES (<50%)\n33.8k records · 33.1%",
            ha="center", va="top", fontsize=9, fontweight="bold", color="#475569")
    ax.text(62.5, header_y, "DISCOVERY SLICE (50%–74%)\n44.6k records · 43.6%",
            ha="center", va="top", fontsize=9, fontweight="bold", color="#b45309")
    ax.text(87.5, header_y, "ANALYTICAL CORE (≥75%)\n23.9k records · 23.4%",
            ha="center", va="top", fontsize=9, fontweight="bold", color="#065f46")

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Generated clean score distribution figure: {out_path}")


def plot_combined_vertical(df: pd.DataFrame, out_path: Path):
    total = len(df)
    plat_counts = df["platform"].value_counts()
    major_plats = plat_counts[plat_counts >= 500].copy()
    other_sum = plat_counts[plat_counts < 500].sum()
    if other_sum > 0:
        major_plats["other (forums, bsky, etc.)"] = other_sum

    plat_labels = [p.replace("_", " ").title() for p in major_plats.index]
    y_pos = np.arange(len(major_plats))
    colors = [
        "#1e3a8a", "#2563eb", "#3b82f6", "#60a5fa",
        "#818cf8", "#94a3b8", "#cbd5e1", "#e2e8f0"
    ][:len(major_plats)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.0, 10.0), dpi=180)

    # Panel 1: Platforms
    bars = ax1.barh(y_pos, major_plats.values, color=colors, height=0.62, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(plat_labels, fontsize=10, fontweight="bold", color="#0f172a")
    ax1.invert_yaxis()
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_visible(False)
    ax1.spines["bottom"].set_color("#cbd5e1")
    ax1.tick_params(axis="y", length=0)
    ax1.tick_params(axis="x", colors="#64748b", labelsize=9)
    ax1.set_xlabel("Number of Verified Records", fontsize=10, fontweight="bold", color="#0f172a", labelpad=8)
    ax1.text(0.0, 1.14, "Platform Distribution", transform=ax1.transAxes, fontsize=12.5, fontweight="bold", color="#0f172a")
    ax1.text(0.0, 1.05, f"Composition across N = {total:,} records", transform=ax1.transAxes, fontsize=9, color="#64748b")

    for bar in bars:
        w = bar.get_width()
        pct = w / total * 100
        ax1.text(w + (total * 0.012), bar.get_y() + bar.get_height() / 2,
                 f"{w:,}  ({pct:.1f}%)",
                 va="center", fontsize=9, fontweight="bold", color="#1e293b")

    ax1.set_xlim(0, max(major_plats.values) * 1.22)

    # Panel 2: Scores
    scores = df["decision_rating"].dropna()
    n, bins, patches = ax2.hist(scores, bins=50, range=(0, 100), edgecolor="white", linewidth=0.6, zorder=3)

    c_neg = "#94a3b8"
    c_disc = "#f59e0b"
    c_core = "#10b981"

    for patch, bin_left in zip(patches, bins[:-1]):
        if bin_left >= 75:
            patch.set_facecolor(c_core)
        elif bin_left >= 50:
            patch.set_facecolor(c_disc)
        else:
            patch.set_facecolor(c_neg)

    ax2.axvline(x=50, color="#d97706", linestyle="--", linewidth=1.8, label="Discovery Gate (t = 50%)", zorder=4)
    ax2.axvline(x=75, color="#059669", linestyle="-", linewidth=2.0, label="Core Gate (t = 75%)", zorder=4)
    ax2.axvline(x=78, color="#7c3aed", linestyle=":", linewidth=2.0, label="Peak F1 Optimum (t = 78%)", zorder=4)

    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color("#cbd5e1")
    ax2.spines["bottom"].set_color("#cbd5e1")
    ax2.grid(True, axis="y", linestyle="-", color="#f1f5f9", linewidth=0.8)
    ax2.set_axisbelow(True)

    ax2.set_xlim(-1, 101)
    ax2.set_ylim(0, max(n) * 1.32)
    ax2.set_xlabel("Decision Rating (Closeness to Pax Silica Anchor %)", fontsize=10, fontweight="bold", color="#0f172a", labelpad=8)
    ax2.set_ylabel("Record Volume (Frequency)", fontsize=10, fontweight="bold", color="#0f172a", labelpad=8)
    ax2.tick_params(colors="#64748b", labelsize=9)

    ax2.text(0.0, 1.18, "Continuous Score Density & Operational Tiers", transform=ax2.transAxes, fontsize=12.5, fontweight="bold", color="#0f172a")
    ax2.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=3, frameon=False, fontsize=9)

    header_y = max(n) * 1.20
    ax2.text(25, header_y, "FILTERED NEGATIVES (<50%)\n33.8k records · 33.1%",
             ha="center", va="top", fontsize=8.5, fontweight="bold", color="#475569")
    ax2.text(62.5, header_y, "DISCOVERY SLICE (50%–74%)\n44.6k records · 43.6%",
             ha="center", va="top", fontsize=8.5, fontweight="bold", color="#b45309")
    ax2.text(87.5, header_y, "ANALYTICAL CORE (≥75%)\n23.9k records · 23.4%",
             ha="center", va="top", fontsize=8.5, fontweight="bold", color="#065f46")

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Generated clean combined vertical distribution figure: {out_path}")


def plot_all():
    df = pd.read_parquet(GOLD_PARQUET)
    plot_platform_composition(df, EVAL_DIR / "platform_composition.png")
    plot_score_distribution(df, EVAL_DIR / "score_distribution.png")
    plot_combined_vertical(df, EVAL_DIR / "corpus_distribution.png")


if __name__ == "__main__":
    plot_all()
