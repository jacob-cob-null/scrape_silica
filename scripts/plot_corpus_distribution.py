"""
scripts/plot_corpus_distribution.py

Generates isolated, publication-grade distribution plots for the Pax Silica Gold Corpus:
1. eval/platform_composition.png - Dedicated horizontal bar chart of platform composition.
2. eval/score_distribution.png   - Dedicated continuous score density histogram with operational tiers.
3. eval/corpus_distribution.png  - Vertical stacked figure (2x1) ensuring zero horizontal squishing.
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
    colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#64748b", "#94a3b8", "#475569"][:len(major_plats)]

    fig, ax = plt.subplots(figsize=(9.5, 5.0), dpi=160)
    bars = ax.barh(y_pos, major_plats.values, color=colors, edgecolor="#1e293b", alpha=0.88, height=0.68)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plat_labels, fontsize=10.5, fontweight="bold")
    ax.invert_yaxis()  # Top-down
    ax.set_xlabel("Number of Verified Records", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_title(f"Pax Silica Corpus: Platform Composition (N = {total:,})", fontsize=13, fontweight="bold", pad=12)
    ax.grid(True, linestyle="--", alpha=0.45, axis="x")

    for bar in bars:
        w = bar.get_width()
        pct = w / total * 100
        ax.text(w + (total * 0.012), bar.get_y() + bar.get_height() / 2,
                f"{w:,} ({pct:.1f}%)",
                va="center", fontsize=9.5, fontweight="bold", color="#1e293b")

    ax.set_xlim(0, max(major_plats.values) * 1.22)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Generated isolated platform composition figure: {out_path}")


def plot_score_distribution(df: pd.DataFrame, out_path: Path):
    scores = df["decision_rating"].dropna()

    fig, ax = plt.subplots(figsize=(10.5, 5.5), dpi=160)
    n, bins, patches = ax.hist(scores, bins=50, edgecolor="#1e293b", alpha=0.82, range=(0, 100))

    # Color code patches by operational tier
    for patch, bin_left in zip(patches, bins[:-1]):
        if bin_left >= 75:
            patch.set_facecolor("#10b981")  # Emerald Green (Core)
        elif bin_left >= 50:
            patch.set_facecolor("#f59e0b")  # Amber/Yellow (Discovery)
        else:
            patch.set_facecolor("#94a3b8")  # Slate Gray (Negatives)

    # Threshold markers
    ax.axvline(x=50, color="#d97706", linestyle="--", linewidth=2.0, label="Discovery Gate (t=50%)")
    ax.axvline(x=75, color="#059669", linestyle="-", linewidth=2.2, label="Recommended Core Gate (t=75%)")
    ax.axvline(x=78, color="#7c3aed", linestyle=":", linewidth=2.2, label="Peak F1 Optimum (t=78%)")

    ax.set_title("Pax Silica Corpus: Continuous Score Density & Operational Tiers", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Decision Rating (Closeness to Pax Silica Anchor %)", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Record Volume (Frequency)", fontsize=11, fontweight="bold", labelpad=8)
    ax.grid(True, linestyle="--", alpha=0.45)
    ax.set_ylim(0, max(n) * 1.15)
    ax.set_xlim(-1, 101)
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)

    # Annotations for tiers
    ax.text(25, max(n) * 0.52, "Filtered Negatives\n(33.8k rows / 33.1%)\nOff-Topic Noise",
            ha="center", fontsize=9, color="#334155",
            bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8", alpha=0.95, lw=1.2))
    ax.text(62, max(n) * 0.65, "Discovery Slice\n(44.6k rows / 43.6%)\nHigh-Recall Auditing",
            ha="center", fontsize=9, color="#92400e",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fef3c7", ec="#f59e0b", alpha=0.95, lw=1.2))
    ax.text(88, max(n) * 0.85, "Analytical Core\n(23.9k rows / 23.4%)\nHigh Precision (Policy)",
            ha="center", fontsize=9, color="#065f46",
            bbox=dict(boxstyle="round,pad=0.4", fc="#d1fae5", ec="#10b981", alpha=0.95, lw=1.2))

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Generated isolated score distribution figure: {out_path}")


def plot_combined_vertical(df: pd.DataFrame, out_path: Path):
    total = len(df)
    plat_counts = df["platform"].value_counts()
    major_plats = plat_counts[plat_counts >= 500].copy()
    other_sum = plat_counts[plat_counts < 500].sum()
    if other_sum > 0:
        major_plats["other (forums, bsky, etc.)"] = other_sum

    plat_labels = [p.replace("_", " ").title() for p in major_plats.index]
    y_pos = np.arange(len(major_plats))
    colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#64748b", "#94a3b8", "#475569"][:len(major_plats)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 10.5), dpi=160)

    # Panel 1: Platforms
    bars = ax1.barh(y_pos, major_plats.values, color=colors, edgecolor="#1e293b", alpha=0.88, height=0.68)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(plat_labels, fontsize=10, fontweight="bold")
    ax1.invert_yaxis()
    ax1.set_xlabel("Number of Verified Records", fontsize=10.5, fontweight="bold")
    ax1.set_title(f"Platform Composition (N = {total:,})", fontsize=12.5, fontweight="bold", pad=10)
    ax1.grid(True, linestyle="--", alpha=0.45, axis="x")

    for bar in bars:
        w = bar.get_width()
        pct = w / total * 100
        ax1.text(w + (total * 0.012), bar.get_y() + bar.get_height() / 2,
                 f"{w:,} ({pct:.1f}%)",
                 va="center", fontsize=9, fontweight="bold", color="#1e293b")

    ax1.set_xlim(0, max(major_plats.values) * 1.22)

    # Panel 2: Scores
    scores = df["decision_rating"].dropna()
    n, bins, patches = ax2.hist(scores, bins=50, edgecolor="#1e293b", alpha=0.82, range=(0, 100))

    for patch, bin_left in zip(patches, bins[:-1]):
        if bin_left >= 75:
            patch.set_facecolor("#10b981")
        elif bin_left >= 50:
            patch.set_facecolor("#f59e0b")
        else:
            patch.set_facecolor("#94a3b8")

    ax2.axvline(x=50, color="#d97706", linestyle="--", linewidth=2.0, label="Discovery Gate (t=50%)")
    ax2.axvline(x=75, color="#059669", linestyle="-", linewidth=2.2, label="Recommended Core Gate (t=75%)")
    ax2.axvline(x=78, color="#7c3aed", linestyle=":", linewidth=2.2, label="Peak F1 Optimum (t=78%)")

    ax2.set_title("Continuous Score Density & Operational Tiers", fontsize=12.5, fontweight="bold", pad=10)
    ax2.set_xlabel("Decision Rating (Closeness to Pax Silica Anchor %)", fontsize=10.5, fontweight="bold")
    ax2.set_ylabel("Record Volume (Frequency)", fontsize=10.5, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.45)
    ax2.set_ylim(0, max(n) * 1.15)
    ax2.set_xlim(-1, 101)
    ax2.legend(loc="upper left", fontsize=9, framealpha=0.95)

    ax2.text(25, max(n) * 0.52, "Filtered Negatives\n(33.8k rows / 33.1%)\nOff-Topic Noise",
             ha="center", fontsize=8.5, color="#334155",
             bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8", alpha=0.95, lw=1.2))
    ax2.text(62, max(n) * 0.65, "Discovery Slice\n(44.6k rows / 43.6%)\nHigh-Recall Auditing",
             ha="center", fontsize=8.5, color="#92400e",
             bbox=dict(boxstyle="round,pad=0.4", fc="#fef3c7", ec="#f59e0b", alpha=0.95, lw=1.2))
    ax2.text(88, max(n) * 0.85, "Analytical Core\n(23.9k rows / 23.4%)\nHigh Precision (Policy)",
             ha="center", fontsize=8.5, color="#065f46",
             bbox=dict(boxstyle="round,pad=0.4", fc="#d1fae5", ec="#10b981", alpha=0.95, lw=1.2))

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Generated combined vertical distribution figure: {out_path}")


def plot_all():
    df = pd.read_parquet(GOLD_PARQUET)
    plot_platform_composition(df, EVAL_DIR / "platform_composition.png")
    plot_score_distribution(df, EVAL_DIR / "score_distribution.png")
    plot_combined_vertical(df, EVAL_DIR / "corpus_distribution.png")


if __name__ == "__main__":
    plot_all()
