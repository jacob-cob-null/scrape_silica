"""
scripts/plot_calibration_comparison.py

Generates evaluation comparison plots between:
1. Baseline Zero-Shot (4-Choice categorical classification: direct + core)
2. Calibrated Binary Entailment (noul anchor closeness percentage)

Saves the figure to eval/model_comparison.png.
"""

from pathlib import Path
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT_PATH = REPO / "eval" / "model_comparison.png"


def plot_comparison():
    # Empirical data evaluated on 386 ground-truth rows (eval/laya_sample.csv)
    # Baseline: 4-Choice Zero-Shot
    base_thresh = [20, 30, 40, 50, 60, 70]
    base_rec = [86.4, 60.6, 45.5, 22.7, 13.6, 10.6]
    base_f1 = [0.384, 0.523, 0.536, 0.333, 0.222, 0.182]

    # Calibrated: noul Entailment
    noul_thresh = [40, 50, 60, 70, 75, 78, 80, 85]
    noul_rec = [93.9, 92.4, 87.9, 69.7, 62.1, 54.5, 47.0, 22.7]
    noul_f1 = [0.363, 0.394, 0.416, 0.482, 0.532, 0.554, 0.517, 0.333]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=150)

    # Subplot 1: Recall vs Threshold
    ax1.plot(base_thresh, base_rec, 'r--o', label='Baseline (4-Choice Zero-Shot)', linewidth=2)
    ax1.plot(noul_thresh, noul_rec, 'b-s', label='Calibrated (noul Entailment)', linewidth=2)
    ax1.axvline(x=50, color='gray', linestyle=':', label='Default Threshold (50%)')
    ax1.set_title('Recall Across Operating Thresholds', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Decision Threshold (%)', fontsize=10)
    ax1.set_ylabel('Recall / Sensitivity (%)', fontsize=10)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.annotate('Baseline Recall Collapse\n(22.7% @ t=50)', xy=(50, 22.7), xytext=(30, 10),
                 arrowprops=dict(facecolor='red', shrink=0.05, width=1, headwidth=6), fontsize=8, color='darkred')
    ax1.annotate('Calibrated Recovery\n(92.4% @ t=50)', xy=(50, 92.4), xytext=(55, 82),
                 arrowprops=dict(facecolor='blue', shrink=0.05, width=1, headwidth=6), fontsize=8, color='darkblue')

    # Subplot 2: F1 Score Comparison
    ax2.plot(base_thresh, base_f1, 'r--o', label='Baseline (4-Choice)', linewidth=2)
    ax2.plot(noul_thresh, noul_f1, 'g-^', label='Calibrated (noul)', linewidth=2)
    ax2.axvline(x=78, color='purple', linestyle=':', label='Optimal F1 Threshold (78%)')
    ax2.set_title('F1 Score Optimization', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Decision Threshold (%)', fontsize=10)
    ax2.set_ylabel('F1 Score (Harmonic Mean)', fontsize=10)
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.annotate('Peak F1 = 0.554\n(t=78%)', xy=(78, 0.554), xytext=(65, 0.40),
                 arrowprops=dict(facecolor='purple', shrink=0.05, width=1, headwidth=6), fontsize=8, color='purple')

    plt.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH)
    print(f"Generated comparison figure: {OUT_PATH}")


if __name__ == "__main__":
    plot_comparison()
