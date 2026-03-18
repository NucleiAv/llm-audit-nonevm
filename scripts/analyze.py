"""
Generate all six figures for the paper from results/scores.csv.

Figures produced:
  fig1_detection_rate_by_strategy.png  - grouped bar chart, DR by strategy and model
  fig2_strategy_heatmap.png            - heatmap of DR by vuln class x strategy-model
  fig3_fpr_comparison.png              - FPR by strategy and model
  fig4_coverage_gap.png                - horizontal bar chart: tools per blockchain
  fig5_pipeline_diagram.png            - experimental pipeline process diagram
  fig6_eqs_distribution.png            - EQS violin plot by strategy
"""

import logging
from pathlib import Path

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).parent.parent
SCORES_CSV = REPO_ROOT / "results" / "scores.csv"
FIGURES_DIR = REPO_ROOT / "figures"

MODEL_LABELS = {"gpt-4o": "GPT-4o", "claude-3-7": "Claude 3.7", "codellama": "CodeLlama"}
MODEL_COLORS = {"gpt-4o": "#2166ac", "claude-3-7": "#4dac26", "codellama": "#888888"}
STRATEGY_LABELS = {"zero_shot": "Zero-Shot", "cot": "Chain-of-Thought", "rag": "RAG"}
CHAIN_LABELS = {"solana": "Solana (Rust/Anchor)", "algorand": "Algorand (PyTEAL)"}

VULN_CLASS_SHORT = {
    "v1_missing_signer": "V1 Missing Signer",
    "v2_account_confusion": "V2 Acct Confusion",
    "v3_arithmetic_overflow": "V3 Arith Overflow",
    "v4_bump_seed": "V4 Bump Seed",
    "v5_stale_cpi": "V5 Stale CPI",
    "v6_logsig_abuse": "V6 LogicSig Abuse",
    "v7_group_tx": "V7 Group Tx",
    "v8_unchecked_fields": "V8 Unchecked Fields",
}

DPI = 300
COLUMN_WIDTH_INCHES = 3.46  # 88mm IEEE column


def load_scores() -> pd.DataFrame:
    if not SCORES_CSV.exists():
        raise FileNotFoundError(f"{SCORES_CSV} not found. Run score_outputs.py first.")
    df = pd.read_csv(SCORES_CSV)
    df["DR"] = pd.to_numeric(df["DR"], errors="coerce")
    df["EQS"] = pd.to_numeric(df["EQS"], errors="coerce")
    df["RC"] = pd.to_numeric(df["RC"], errors="coerce")
    df["FPR"] = pd.to_numeric(df["FPR"], errors="coerce")
    return df


def fig1_detection_rate(df: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(COLUMN_WIDTH_INCHES * 2.5, 3.5), sharey=True)
    strategies = ["zero_shot", "cot", "rag"]
    models = ["gpt-4o", "claude-3-7", "codellama"]
    x = np.arange(len(strategies))
    width = 0.25

    for ax, chain in zip(axes, ["solana", "algorand"]):
        chain_df = df[df["chain"] == chain]
        for i, model in enumerate(models):
            means = []
            stds = []
            for strategy in strategies:
                vals = chain_df[(chain_df["strategy"] == strategy) & (chain_df["model"] == model)]["DR"].dropna()
                means.append(vals.mean() * 100 if len(vals) > 0 else 0)
                stds.append(vals.std() * 100 if len(vals) > 1 else 0)
            ax.bar(
                x + i * width,
                means,
                width,
                yerr=stds,
                label=MODEL_LABELS[model],
                color=MODEL_COLORS[model],
                capsize=3,
                error_kw={"linewidth": 0.8},
            )
        ax.set_title(CHAIN_LABELS[chain], fontsize=10)
        ax.set_xticks(x + width)
        ax.set_xticklabels([STRATEGY_LABELS[s] for s in strategies], fontsize=8)
        ax.set_ylim(0, 105)
        ax.set_ylabel("Detection Rate (%)", fontsize=9)
        ax.yaxis.set_tick_params(labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout()
    out_path = out_dir / "fig1_detection_rate_by_strategy.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def fig2_strategy_heatmap(df: pd.DataFrame, out_dir: Path) -> None:
    strategy_model_cols = [
        f"{s}_{m}" for s in ["zero_shot", "cot", "rag"] for m in ["gpt-4o", "claude-3-7", "codellama"]
    ]
    vuln_classes = list(VULN_CLASS_SHORT.keys())

    matrix = np.zeros((len(vuln_classes), len(strategy_model_cols)))
    for row_i, vc in enumerate(vuln_classes):
        for col_j, sm in enumerate(strategy_model_cols):
            parts = sm.rsplit("_", 2)
            strategy = "_".join(parts[:-2]) if len(parts) > 2 else parts[0]
            # Split strategy_model by known model names
            for model in ["gpt-4o", "claude-3-7", "codellama"]:
                if sm.endswith(model):
                    strategy = sm[: -len(model) - 1]
                    break
            else:
                model = parts[-1]
                strategy = "_".join(parts[:-1])
            subset = df[(df["vuln_class"] == vc) & (df["strategy"] == strategy) & (df["model"] == model)]["DR"].dropna()
            matrix[row_i, col_j] = subset.mean() * 100 if len(subset) > 0 else 0

    col_labels = [
        f"{STRATEGY_LABELS[s][:3]}\n{MODEL_LABELS[m][:6]}"
        for s in ["zero_shot", "cot", "rag"]
        for m in ["gpt-4o", "claude-3-7", "codellama"]
    ]
    row_labels = [VULN_CLASS_SHORT[vc] for vc in vuln_classes]

    heat_df = pd.DataFrame(matrix, index=row_labels, columns=col_labels)
    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_INCHES * 2.5, 4))
    sns.heatmap(
        heat_df,
        ax=ax,
        annot=True,
        fmt=".0f",
        cmap="Greens",
        vmin=0,
        vmax=100,
        linewidths=0.3,
        annot_kws={"size": 7},
        cbar_kws={"label": "Detection Rate (%)"},
    )
    ax.set_title("Detection Rate by Vulnerability Class and Strategy-Model", fontsize=9)
    ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    out_path = out_dir / "fig2_strategy_heatmap.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def fig3_fpr_comparison(df: pd.DataFrame, out_dir: Path) -> None:
    fpr_df = df[df["FPR"].notna()]
    strategies = ["zero_shot", "cot", "rag"]
    models = ["gpt-4o", "claude-3-7", "codellama"]
    x = np.arange(len(strategies))
    width = 0.25

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_INCHES * 1.8, 3))
    for i, model in enumerate(models):
        means = []
        for strategy in strategies:
            vals = fpr_df[(fpr_df["strategy"] == strategy) & (fpr_df["model"] == model)]["FPR"].dropna()
            means.append(vals.mean() if len(vals) > 0 else 0)
        ax.bar(x + i * width, means, width, label=MODEL_LABELS[model], color=MODEL_COLORS[model])

    ax.axhline(y=0.10, linestyle="--", color="red", linewidth=1, label="FPR = 0.10 threshold")
    ax.set_xticks(x + width)
    ax.set_xticklabels([STRATEGY_LABELS[s] for s in strategies], fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("False Positive Rate", fontsize=9)
    ax.set_title("False Positive Rate by Strategy and Model", fontsize=10)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    out_path = out_dir / "fig3_fpr_comparison.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def fig4_coverage_gap(out_dir: Path) -> None:
    ecosystems = ["Ethereum", "Solana", "Algorand"]
    tool_counts = [113, 12, 0]
    colors = ["#888888", "#f4a261", "#e63946"]

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_INCHES * 1.8, 2.5))
    bars = ax.barh(ecosystems, tool_counts, color=colors, height=0.5)
    for bar, count in zip(bars, tool_counts):
        ax.text(
            bar.get_width() + 1.5,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
            fontsize=9,
        )
    ax.set_xlabel("Published LLM-Based Audit Tools", fontsize=9)
    ax.set_title("EVM vs Non-EVM LLM Tool Coverage", fontsize=10)
    ax.set_xlim(0, 130)
    ax.tick_params(labelsize=9)

    legend_patches = [
        mpatches.Patch(color="#888888", label="Covered (Ethereum)"),
        mpatches.Patch(color="#f4a261", label="Partially covered (Solana)"),
        mpatches.Patch(color="#e63946", label="Uncovered (Algorand)"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right")
    ax.text(
        0.01, -0.18,
        "Source: Li et al. (2025), arXiv:2504.07419",
        transform=ax.transAxes,
        fontsize=6,
        color="grey",
    )
    fig.tight_layout()
    out_path = out_dir / "fig4_coverage_gap.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def fig5_pipeline_diagram(out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_INCHES * 2.5, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, label, color="#d0e4f7"):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.05",
            linewidth=0.8,
            edgecolor="#333333",
            facecolor=color,
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=7, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={"arrowstyle": "->", "linewidth": 0.8, "color": "#333333"},
        )

    box(0.2, 4.5, 2.0, 0.8, "Contract Corpus\n(24 instances)", color="#e8f4e8")
    box(0.2, 3.0, 2.0, 0.8, "RAG Corpus\n(5 documents)", color="#fff3cd")
    box(3.0, 4.0, 2.0, 1.6, "Prompting\nStrategies\nZero-Shot / CoT / RAG", color="#d0e4f7")
    box(6.0, 4.8, 1.5, 0.6, "GPT-4o", color="#c8e6c9")
    box(6.0, 3.9, 1.5, 0.6, "Claude 3.7", color="#c8e6c9")
    box(6.0, 3.0, 1.5, 0.6, "CodeLlama", color="#c8e6c9")
    box(8.2, 3.8, 1.6, 0.8, "JSON Output\n(216 files)", color="#ffe0b2")
    box(3.5, 1.5, 3.0, 1.0, "Scoring\n(DR, FPR, EQS, RC)", color="#f3e5f5")
    box(3.5, 0.2, 3.0, 0.8, "Results Table &\n6 Figures", color="#fce4ec")

    arrow(2.2, 4.9, 3.0, 4.8)
    arrow(2.2, 3.4, 3.0, 4.2)
    arrow(5.0, 4.8, 6.0, 5.1)
    arrow(5.0, 4.5, 6.0, 4.2)
    arrow(5.0, 4.2, 6.0, 3.3)
    arrow(7.5, 4.8, 8.2, 4.2)
    arrow(7.5, 4.2, 8.2, 4.2)
    arrow(7.5, 3.3, 8.2, 4.0)
    arrow(8.4, 3.8, 8.4, 2.5)
    arrow(8.4, 2.5, 6.5, 2.0)
    arrow(5.0, 1.5, 5.0, 1.0)

    ax.set_title("Experimental Pipeline", fontsize=10)
    fig.tight_layout()
    out_path = out_dir / "fig5_pipeline_diagram.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def fig6_eqs_distribution(df: pd.DataFrame, out_dir: Path) -> None:
    eqs_df = df[df["EQS"].notna() & (df["DR"] == 1)]
    strategies = ["zero_shot", "cot", "rag"]

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_INCHES * 1.8, 3))
    data_by_strategy = [
        eqs_df[eqs_df["strategy"] == s]["EQS"].dropna().tolist() for s in strategies
    ]
    parts = ax.violinplot(data_by_strategy, positions=range(len(strategies)), showmedians=True)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(["#2166ac", "#4dac26", "#e66101"][i])
        pc.set_alpha(0.7)

    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels([STRATEGY_LABELS[s] for s in strategies], fontsize=9)
    ax.set_ylim(0.5, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylabel("Explanation Quality Score (1-5)", fontsize=9)
    ax.set_title("EQS Distribution by Strategy (DR=1 runs only)", fontsize=9)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    out_path = out_dir / "fig6_eqs_distribution.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logging.info("saved %s", out_path)


def main() -> None:
    FIGURES_DIR.mkdir(exist_ok=True)
    df = load_scores()
    logging.info("loaded %d rows from scores.csv", len(df))

    fig1_detection_rate(df, FIGURES_DIR)
    fig2_strategy_heatmap(df, FIGURES_DIR)
    fig3_fpr_comparison(df, FIGURES_DIR)
    fig4_coverage_gap(FIGURES_DIR)
    fig5_pipeline_diagram(FIGURES_DIR)
    fig6_eqs_distribution(df, FIGURES_DIR)

    logging.info("all figures generated in %s", FIGURES_DIR)


if __name__ == "__main__":
    main()
