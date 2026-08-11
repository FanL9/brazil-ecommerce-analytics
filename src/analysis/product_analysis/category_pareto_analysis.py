"""Generate the two Stage 4 category Pareto charts from the final CSV."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(PROJECT_ROOT / "outputs" / ".matplotlib-cache"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd


CSV_PATH = (
    PROJECT_ROOT / "outputs" / "data" / "06_product_analysis"
    / "category_pareto.csv"
)
FIGURE_DIR = PROJECT_ROOT / "visualizations" / "product"
PARETO_FIGURE = FIGURE_DIR / "category_sales_pareto.png"
STRUCTURE_FIGURE = FIGURE_DIR / "category_head_long_tail_structure.png"

HEAD_COLOR = "#2878B5"
TAIL_COLOR = "#A7B0BA"
LINE_COLOR = "#D97904"
REFERENCE_COLOR = "#C23B33"
GRID_COLOR = "#D9DEE3"


def configure_plotting() -> str:
    """Select an available CJK font and apply the project chart baseline."""

    preferred = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    font_name = next((name for name in preferred if name in installed), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": font_name,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#777777",
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": GRID_COLOR,
            "grid.alpha": 0.65,
            "grid.linewidth": 0.7,
            "savefig.dpi": 300,
        }
    )
    return font_name


def load_and_validate_data() -> pd.DataFrame:
    """Load the final Pareto CSV and fail fast on grain or total mismatches."""

    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Pareto CSV not found: {CSV_PATH}")

    expected_columns = [
        "category_name",
        "sales_amount",
        "sales_share",
        "cumulative_sales_amount",
        "cumulative_sales_share",
        "sales_rank",
        "category_type",
    ]
    data = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    if data.columns.tolist() != expected_columns:
        raise ValueError(
            f"Unexpected Pareto CSV columns: {data.columns.tolist()}"
        )
    if data.empty or data.isna().any().any():
        raise ValueError("Pareto CSV is empty or contains NULL values.")
    if data["category_name"].duplicated().any():
        raise ValueError("Pareto CSV contains duplicate category names.")
    if data["sales_rank"].tolist() != list(range(1, len(data) + 1)):
        raise ValueError("Pareto CSV is not ordered by consecutive sales_rank.")
    if set(data["category_type"]) != {"head", "long_tail"}:
        raise ValueError("Pareto CSV category_type must contain head and long_tail.")
    if abs(float(data["sales_share"].sum()) - 1.0) > 1e-10:
        raise ValueError("Pareto CSV sales shares do not reconcile to 1.")
    if abs(float(data.iloc[-1]["cumulative_sales_share"]) - 1.0) > 1e-10:
        raise ValueError("Final cumulative sales share does not equal 1.")
    return data


def create_pareto_figure(data: pd.DataFrame) -> None:
    """Create the ranked sales bars and cumulative sales-share line."""

    head = data.loc[data["category_type"] == "head"]
    head_count = len(head)
    head_share = float(head["sales_share"].sum())
    ranks = data["sales_rank"]
    colors = data["category_type"].map(
        {"head": HEAD_COLOR, "long_tail": TAIL_COLOR}
    )

    figure, sales_axis = plt.subplots(figsize=(16, 8.5))
    sales_axis.bar(
        ranks,
        data["sales_amount"] / 1_000_000,
        color=colors,
        width=0.82,
        edgecolor="white",
        linewidth=0.25,
        zorder=2,
    )
    sales_axis.set_title("品类商品销售额帕累托图", fontsize=19, pad=18)
    sales_axis.set_xlabel("品类（按商品销售额降序）", fontsize=11)
    sales_axis.set_ylabel("商品销售额（百万 BRL）", fontsize=11)
    sales_axis.set_xlim(0.2, len(data) + 0.8)
    sales_axis.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.1f}"))
    sales_axis.grid(axis="x", visible=False)

    cumulative_axis = sales_axis.twinx()
    cumulative_axis.grid(False)
    cumulative_axis.plot(
        ranks,
        data["cumulative_sales_share"],
        color=LINE_COLOR,
        linewidth=2.6,
        marker="o",
        markersize=2.6,
        zorder=4,
    )
    cumulative_axis.axhline(
        0.8,
        color=REFERENCE_COLOR,
        linestyle="--",
        linewidth=1.5,
        zorder=3,
    )
    cumulative_axis.axvline(
        head_count + 0.5,
        color="#6C757D",
        linestyle=":",
        linewidth=1.2,
        zorder=3,
    )
    cumulative_axis.set_ylabel("累计商品销售额占比", fontsize=11)
    cumulative_axis.set_ylim(0, 1.045)
    cumulative_axis.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))

    tick_ranks = list(range(1, head_count + 1)) + [24, 36, 48, 60, 72]
    tick_ranks = sorted(set(rank for rank in tick_ranks if rank <= len(data)))
    category_by_rank = data.set_index("sales_rank")["category_name"]
    tick_labels = [
        category_by_rank.loc[rank] if rank <= head_count else f"#{rank}"
        for rank in tick_ranks
    ]
    sales_axis.set_xticks(tick_ranks, labels=tick_labels, rotation=58, ha="right")
    sales_axis.tick_params(axis="x", labelsize=8)

    threshold_row = head.iloc[-1]
    cumulative_axis.scatter(
        [threshold_row["sales_rank"]],
        [threshold_row["cumulative_sales_share"]],
        s=70,
        color=REFERENCE_COLOR,
        edgecolor="white",
        linewidth=1.0,
        zorder=5,
    )
    cumulative_axis.annotate(
        f"前 {head_count} 个品类\n累计 {head_share:.2%}",
        xy=(threshold_row["sales_rank"], threshold_row["cumulative_sales_share"]),
        xytext=(head_count + 7, 0.69),
        arrowprops={"arrowstyle": "->", "color": REFERENCE_COLOR},
        fontsize=10,
        color="#5B2B27",
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "#D9A3A0"},
    )

    legend_items = [
        Patch(facecolor=HEAD_COLOR, label="头部品类"),
        Patch(facecolor=TAIL_COLOR, label="长尾品类"),
        Line2D([0], [0], color=LINE_COLOR, linewidth=2.6, label="累计销售额占比"),
        Line2D(
            [0], [0], color=REFERENCE_COLOR, linestyle="--", linewidth=1.5,
            label="80% 参考线",
        ),
    ]
    sales_axis.legend(
        handles=legend_items,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.01),
        ncols=4,
        frameon=False,
        fontsize=9,
    )
    figure.text(
        0.5,
        0.01,
        "数据源：outputs/data/06_product_analysis/category_pareto.csv；商品销售额不含运费，不等同于 GMV。",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout(rect=(0.02, 0.045, 0.98, 0.96))
    figure.savefig(PARETO_FIGURE, bbox_inches="tight", pad_inches=0.12)
    plt.close(figure)


def create_structure_figure(data: pd.DataFrame) -> None:
    """Create category-count and sales-amount comparisons for head and tail."""

    summary = (
        data.groupby("category_type", as_index=False)
        .agg(
            category_count=("category_name", "size"),
            sales_amount=("sales_amount", "sum"),
            sales_share=("sales_share", "sum"),
        )
        .set_index("category_type")
        .loc[["head", "long_tail"]]
        .reset_index()
    )
    summary["category_share"] = summary["category_count"] / len(data)
    labels = ["头部品类", "长尾品类"]
    colors = [HEAD_COLOR, TAIL_COLOR]

    figure, axes = plt.subplots(1, 2, figsize=(13.5, 6.6))
    count_bars = axes[0].bar(
        labels,
        summary["category_count"],
        color=colors,
        width=0.58,
        edgecolor="white",
        linewidth=0.8,
        zorder=2,
    )
    axes[0].set_title("品类数量结构", fontsize=15, pad=12)
    axes[0].set_ylabel("品类数", fontsize=10)
    axes[0].set_ylim(0, summary["category_count"].max() * 1.24)
    axes[0].grid(axis="x", visible=False)
    for bar, count, share in zip(
        count_bars, summary["category_count"], summary["category_share"]
    ):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{int(count)} 个\n{share:.2%}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    sales_values = summary["sales_amount"] / 1_000_000
    sales_bars = axes[1].bar(
        labels,
        sales_values,
        color=colors,
        width=0.58,
        edgecolor="white",
        linewidth=0.8,
        zorder=2,
    )
    axes[1].set_title("商品销售额结构", fontsize=15, pad=12)
    axes[1].set_ylabel("商品销售额（百万 BRL）", fontsize=10)
    axes[1].set_ylim(0, sales_values.max() * 1.24)
    axes[1].grid(axis="x", visible=False)
    for bar, amount, share in zip(
        sales_bars, summary["sales_amount"], summary["sales_share"]
    ):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.22,
            f"{amount / 1_000_000:.2f} 百万\n{share:.2%}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    figure.suptitle("头部与长尾品类销售结构", fontsize=19, fontweight="bold")
    head_row = summary.loc[summary["category_type"] == "head"].iloc[0]
    tail_row = summary.loc[summary["category_type"] == "long_tail"].iloc[0]
    figure.text(
        0.5,
        0.02,
        f"头部 {int(head_row['category_count'])} 个品类贡献 "
        f"{head_row['sales_share']:.2%} 商品销售额；长尾 "
        f"{int(tail_row['category_count'])} 个品类贡献 "
        f"{tail_row['sales_share']:.2%}。",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    figure.tight_layout(rect=(0.03, 0.06, 0.97, 0.91), w_pad=4.0)
    figure.savefig(STRUCTURE_FIGURE, bbox_inches="tight", pad_inches=0.14)
    plt.close(figure)


def main() -> int:
    font_name = configure_plotting()
    data = load_and_validate_data()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    create_pareto_figure(data)
    create_structure_figure(data)
    print(f"Chart font: {font_name}")
    print(f"Created: {PARETO_FIGURE.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Created: {STRUCTURE_FIGURE.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
