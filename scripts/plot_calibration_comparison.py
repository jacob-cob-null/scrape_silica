"""
scripts/plot_calibration_comparison.py

Generates publication-quality benchmark plots comparing:
1. Baseline Zero-Shot (4-Choice categorical classification)
2. Calibrated Binary Entailment (noul anchor closeness percentage)

Designed to eliminate AI-slop visual artifacts:
- No floating speech bubble boxes or arrows blocking the curves.
- Legends anchored cleanly outside the plot frame.
- Uncluttered minimalist spines and subtle horizontal-only grid lines.
- Direct, minimal data point labeling.
"""

from pathlib import Path
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT_PATH = REPO / "eval" / "model_comparison.png"


def plot_comparison():
    # Empirical data evaluated on 386 ground-truth rows (eval/laya_sample.csv)
    base_thresh = [20, 30, 40, 50, 60, 70]
    base_rec = [86.4, 60.6, 45.5, 22.7, 13.6, 10.6]
    base_f1 = [0.384, 0.523, 0.536, 0.333, 0.222, 0.182]

    noul_thresh = [40, 50, 60, 70, 75, 78, 80, 85]
    noul_rec = [93.9, 92.4, 87.9, 69.7, 62.1, 54.5, 47.0, 22.7]
    noul_f1 = [0.363, 0.394, 0.416, 0.482, 0.532, 0.554, 0.517, 0.333]

    # Clean publication styling
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=180)

    color_base = "#dc2626"   # Crimson
    color_noul = "#1d4ed8"   # Royal Blue
    color_f1 = "#059669"     # Emerald Green
    color_opt = "#7c3aed"    # Violet
    color_grid = "#e2e8f0"
    color_spine = "#cbd5e1"
    color_text = "#0f172a"
    color_sub = "#64748b"

    # =========================================================================
    # Subplot 1: Recall Across Operating Thresholds
    # =========================================================================
    ax1.plot(base_thresh, base_rec, color=color_base, linestyle="--", linewidth=2.2,
             marker="o", markersize=6.5, label="Baseline (4-Choice Zero-Shot)", zorder=3)
    ax1.plot(noul_thresh, noul_rec, color=color_noul, linestyle="-", linewidth=2.4,
             marker="s", markersize=6.5, label="Calibrated (noul Entailment)", zorder=3)

    # Reference line at default threshold (t=50%)
    ax1.axvline(x=50, color="#94a3b8", linestyle=":", linewidth=1.5, zorder=2)
    ax1.text(50.8, 5, "t = 50% (Default)", color=color_sub, fontsize=8.5, fontweight="600")

    # Direct data point labels (clean typography, no boxes or arrows blocking the curves)
    ax1.text(49.0, 16.5, "22.7%", color=color_base, fontsize=9.5, fontweight="bold", ha="right", va="center")
    ax1.text(50.0, 96.5, "92.4%", color=color_noul, fontsize=9.5, fontweight="bold", ha="center", va="bottom")

    ax1.set_title("Recall Across Operating Thresholds", fontsize=12.5, fontweight="bold", color=color_text, loc="left", pad=28)
    ax1.set_xlabel("Decision Threshold (%)", fontsize=10.5, fontweight="bold", color=color_text, labelpad=8)
    ax1.set_ylabel("Recall / Sensitivity (%)", fontsize=10.5, fontweight="bold", color=color_text, labelpad=8)
    ax1.set_xlim(15, 90)
    ax1.set_ylim(0, 105)

    # Spines & Grid
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color(color_spine)
    ax1.spines["bottom"].set_color(color_spine)
    ax1.grid(True, axis="y", linestyle="-", color=color_grid, linewidth=0.8, alpha=0.7)
    ax1.set_axisbelow(True)

    # Legend above the plot - NOTHING BLOCKS THE CHART
    ax1.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=2, frameon=False, fontsize=9.5)

    # =========================================================================
    # Subplot 2: F1 Score Optimization
    # =========================================================================
    ax2.plot(base_thresh, base_f1, color=color_base, linestyle="--", linewidth=2.2,
             marker="o", markersize=6.5, label="Baseline (4-Choice)", zorder=3)
    ax2.plot(noul_thresh, noul_f1, color=color_f1, linestyle="-", linewidth=2.4,
             marker="^", markersize=6.5, label="Calibrated (noul)", zorder=3)

    # Reference line at optimal threshold (t=78%)
    ax2.axvline(x=78, color=color_opt, linestyle=":", linewidth=1.5, zorder=2)
    ax2.text(78.8, 0.08, "t = 78% (Optimum)", color=color_opt, fontsize=8.5, fontweight="600")

    # Direct peak label above the optimal point
    ax2.plot(78, 0.554, marker="o", markersize=10, markerfacecolor="none", markeredgecolor=color_opt, markeredgewidth=2, zorder=4)
    ax2.text(78, 0.578, "Peak F1: 0.554", color=color_f1, fontsize=9.5, fontweight="bold", ha="center", va="bottom")

    ax2.set_title("F1 Score Optimization", fontsize=12.5, fontweight="bold", color=color_text, loc="left", pad=28)
    ax2.set_xlabel("Decision Threshold (%)", fontsize=10.5, fontweight="bold", color=color_text, labelpad=8)
    ax2.set_ylabel("F1 Score (Harmonic Mean)", fontsize=10.5, fontweight="bold", color=color_text, labelpad=8)
    ax2.set_xlim(15, 90)
    ax2.set_ylim(0.05, 0.65)

    # Spines & Grid
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color(color_spine)
    ax2.spines["bottom"].set_color(color_spine)
    ax2.grid(True, axis="y", linestyle="-", color=color_grid, linewidth=0.8, alpha=0.7)
    ax2.set_axisbelow(True)

    # Legend above the plot - NOTHING BLOCKS THE CHART
    ax2.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=2, frameon=False, fontsize=9.5)

    plt.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH, bbox_inches="tight")
    plt.close()
    print(f"Generated clean model comparison figure: {OUT_PATH}")


if __name__ == "__main__":
    plot_comparison()
