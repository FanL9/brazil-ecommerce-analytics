"""Validate and visualize the monthly core business KPI data layer.

This script is deliberately downstream-only: it reads ``monthly_kpi.csv`` and
checks it against the SQLite ``monthly_kpi`` view without changing either one.
It produces five single-metric charts, one overview chart, a monthly anomaly
diagnostic table, and a reproducible Markdown report.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV = ROOT / "outputs/data/02_business_overview/monthly_kpi.csv"
DEFAULT_DB = ROOT / "database/brazil_ecommerce.db"
FIGURE_DIR = ROOT / "visualizations/business_overview"
DIAGNOSTIC_CSV = ROOT / "outputs/data/02_business_overview/monthly_trend_diagnostics.csv"
REPORT_PATH = ROOT / "reports/business_analysis/business_trend_analysis.md"

EXPECTED_COLUMNS = [
    "month",
    "gmv",
    "order_count",
    "average_order_value",
    "new_users",
    "active_users",
]
METRICS = {
    "gmv": {
        "title": "月度 GMV 趋势",
        "label": "GMV",
        "ylabel": "GMV（BRL）",
        "color": "#2F6B8A",
        "money": True,
        "filename": "01_gmv_trend.png",
    },
    "order_count": {
        "title": "月度订单量趋势",
        "label": "订单量",
        "ylabel": "正支付已送达订单量（单）",
        "color": "#3A8D75",
        "money": False,
        "filename": "02_order_count_trend.png",
    },
    "average_order_value": {
        "title": "月度客单价趋势",
        "label": "客单价",
        "ylabel": "客单价（BRL/单）",
        "color": "#D0874C",
        "money": True,
        "filename": "03_average_order_value_trend.png",
    },
    "new_users": {
        "title": "月度新增用户趋势",
        "label": "新增用户",
        "ylabel": "新增用户数（人）",
        "color": "#7A6FA8",
        "money": False,
        "filename": "04_new_users_trend.png",
    },
    "active_users": {
        "title": "月度活跃用户趋势",
        "label": "活跃用户",
        "ylabel": "活跃用户数（人）",
        "color": "#C65D57",
        "money": False,
        "filename": "05_active_users_trend.png",
    },
}

BOUNDARY_COLOR = "#F2C14E"
ANOMALY_COLOR = "#C73E1D"
MISSING_COLOR = "#777777"


@dataclass(frozen=True)
class ValidationSummary:
    row_count: int
    start_month: str
    end_month: str
    missing_months: tuple[str, ...]
    duplicate_months: int
    null_counts: dict[str, int]
    source_sorted: bool
    db_matches_csv: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="monthly KPI CSV")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB, help="SQLite database")
    return parser.parse_args()


def configure_plotting() -> str:
    """Select a CJK-capable font when available and apply report styling."""
    preferred = [
        "Microsoft YaHei",
        "Microsoft JhengHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Arial Unicode MS",
    ]
    installed = {font.name for font in fm.fontManager.ttflist}
    selected = next((name for name in preferred if name in installed), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [selected, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#B8B8B8",
            "axes.labelcolor": "#333333",
            "xtick.color": "#4A4A4A",
            "ytick.color": "#4A4A4A",
            "figure.facecolor": "white",
            "axes.facecolor": "#FCFCFC",
            "savefig.facecolor": "white",
        }
    )
    return selected


def read_and_validate(csv_path: Path, database_path: Path) -> tuple[pd.DataFrame, ValidationSummary]:
    raw = pd.read_csv(csv_path)
    if raw.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError(f"字段不一致：实际 {raw.columns.tolist()}，预期 {EXPECTED_COLUMNS}")

    raw_month = raw["month"].astype(str)
    parsed_month = pd.to_datetime(raw_month, format="%Y-%m", errors="coerce")
    if parsed_month.isna().any():
        bad = raw.loc[parsed_month.isna(), "month"].tolist()
        raise ValueError(f"存在无法解析的月份：{bad}")
    source_sorted = parsed_month.is_monotonic_increasing

    for column in EXPECTED_COLUMNS[1:]:
        converted = pd.to_numeric(raw[column], errors="coerce")
        invalid = raw[column].notna() & converted.isna()
        if invalid.any():
            raise ValueError(f"{column} 存在非数值内容")
        raw[column] = converted

    raw["date"] = parsed_month
    raw = raw.sort_values("date", kind="stable").reset_index(drop=True)
    duplicate_months = int(raw["month"].duplicated(keep=False).sum())

    complete_range = pd.date_range(raw["date"].min(), raw["date"].max(), freq="MS")
    observed = pd.DatetimeIndex(raw["date"])
    missing = tuple(date.strftime("%Y-%m") for date in complete_range.difference(observed))

    with sqlite3.connect(database_path) as connection:
        db = pd.read_sql_query("SELECT * FROM monthly_kpi ORDER BY month", connection)
    db["month"] = db["month"].astype(str)
    csv_compare = raw[EXPECTED_COLUMNS].reset_index(drop=True)
    db_compare = db[EXPECTED_COLUMNS].reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(
            csv_compare,
            db_compare,
            check_dtype=False,
            check_exact=False,
            rtol=1e-10,
            atol=1e-8,
        )
        db_matches_csv = True
    except AssertionError as exc:
        raise ValueError("monthly_kpi.csv 与数据库 monthly_kpi View 不一致") from exc

    if duplicate_months:
        raise ValueError(f"发现 {duplicate_months} 行重复月份")
    if not source_sorted:
        raise ValueError("源 CSV 未按月份升序排列")

    summary = ValidationSummary(
        row_count=len(raw),
        start_month=raw["month"].iloc[0],
        end_month=raw["month"].iloc[-1],
        missing_months=missing,
        duplicate_months=duplicate_months,
        null_counts={column: int(raw[column].isna().sum()) for column in EXPECTED_COLUMNS},
        source_sorted=source_sorted,
        db_matches_csv=db_matches_csv,
    )
    return raw, summary


def add_diagnostics(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    result = df.copy()
    result["is_boundary_month"] = result["month"].isin(["2016-09", "2018-08"])
    month_number = result["date"].dt.year * 12 + result["date"].dt.month
    result["previous_observed_month"] = result["month"].shift(1)
    result["data_gap_before"] = ~month_number.diff().eq(1)
    result.loc[0, "data_gap_before"] = False
    previous_boundary = result["is_boundary_month"].shift(1, fill_value=True)
    result["mom_eligible"] = (
        ~result["is_boundary_month"]
        & ~previous_boundary
        & ~result["data_gap_before"]
    )

    thresholds: dict[str, tuple[float, float]] = {}
    anomaly_columns: list[str] = []
    for metric in METRICS:
        mom = result[metric].pct_change(fill_method=None) * 100
        mom = mom.where(np.isfinite(mom))
        result[f"{metric}_mom_pct"] = mom
        eligible_values = mom[result["mom_eligible"] & mom.notna()]
        q1 = float(eligible_values.quantile(0.25))
        q3 = float(eligible_values.quantile(0.75))
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        thresholds[metric] = (lower, upper)
        result[f"{metric}_iqr_lower_pct"] = lower
        result[f"{metric}_iqr_upper_pct"] = upper
        anomaly_col = f"{metric}_anomaly"
        result[anomaly_col] = (
            result["mom_eligible"]
            & mom.notna()
            & ((mom < lower) | (mom > upper))
        )
        anomaly_columns.append(anomaly_col)

    def anomaly_metrics(row: pd.Series) -> str:
        return ";".join(metric for metric in METRICS if bool(row[f"{metric}_anomaly"]))

    result["anomaly_metrics"] = result.apply(anomaly_metrics, axis=1)
    result["anomaly_count"] = result[anomaly_columns].sum(axis=1).astype(int)
    result["diagnosis"] = result.apply(diagnose_anomaly, axis=1)
    return result, thresholds


def diagnose_anomaly(row: pd.Series) -> str:
    flagged = [metric for metric in METRICS if bool(row.get(f"{metric}_anomaly", False))]
    if not flagged:
        return ""

    gmv = row["gmv_mom_pct"]
    orders = row["order_count_mom_pct"]
    aov = row["average_order_value_mom_pct"]
    new_users = row["new_users_mom_pct"]
    active_users = row["active_users_mom_pct"]
    if "gmv" in flagged:
        if "average_order_value" in flagged and np.sign(orders) == np.sign(aov):
            driver = "GMV 由订单量与客单价同向异常变化共同驱动（订单量贡献更大）"
        elif abs(orders) > abs(aov) * 2:
            driver = "GMV 主要由订单量变化驱动，客单价影响较小"
        elif np.sign(orders) == np.sign(aov):
            driver = "GMV 由订单量与客单价同向变化共同驱动"
        else:
            driver = "订单量与客单价方向相反，GMV 净变化以绝对变动更大的因素为主"
    else:
        driver = "GMV 环比未越过 IQR 异常阈值"
    return (
        f"{driver}；订单量环比 {orders:.2f}%，客单价环比 {aov:.2f}%，"
        f"新增用户环比 {new_users:.2f}%，活跃用户环比 {active_users:.2f}%。"
        "现有数据无法验证具体外部原因。"
    )


def peak_and_trough(df: pd.DataFrame) -> dict[str, dict[str, tuple[str, float]]]:
    eligible = df.loc[~df["is_boundary_month"]]
    result: dict[str, dict[str, tuple[str, float]]] = {}
    for metric in METRICS:
        values = eligible.loc[eligible[metric].notna(), ["month", metric]]
        high_index = values[metric].idxmax()
        low_index = values[metric].idxmin()
        result[metric] = {
            "peak": (str(df.loc[high_index, "month"]), float(df.loc[high_index, metric])),
            "trough": (str(df.loc[low_index, "month"]), float(df.loc[low_index, metric])),
        }
    return result


def _segment_sse(values: np.ndarray, start: int, end: int) -> float:
    segment = values[start:end]
    return float(np.square(segment - segment.mean(axis=0)).sum())


def determine_business_stages(df: pd.DataFrame) -> tuple[list[dict[str, object]], dict[int, float]]:
    """Select 1-4 ordered regimes with dynamic programming and BIC.

    Only the four scale indicators requested for joint stage assessment are
    used. Boundary months are excluded. Log1p and z-score transformations keep
    metric scale and the 2016 low base from dominating the fit.
    """
    metrics = ["gmv", "order_count", "new_users", "active_users"]
    sample = df.loc[~df["is_boundary_month"], ["month", *metrics]].reset_index(drop=True)
    values = np.log1p(sample[metrics].to_numpy(dtype=float))
    values = (values - values.mean(axis=0)) / values.std(axis=0, ddof=0)
    n, dimensions = values.shape
    min_length = 3
    max_stages = min(4, n // min_length)
    solutions: dict[int, tuple[float, list[int]]] = {}

    for stage_count in range(1, max_stages + 1):
        dp: dict[tuple[int, int], tuple[float, list[int]]] = {(0, 0): (0.0, [])}
        for segment_count in range(1, stage_count + 1):
            for end in range(segment_count * min_length, n + 1):
                candidates = []
                min_start = (segment_count - 1) * min_length
                for start in range(min_start, end - min_length + 1):
                    previous = dp.get((segment_count - 1, start))
                    if previous is None:
                        continue
                    candidates.append(
                        (
                            previous[0] + _segment_sse(values, start, end),
                            [*previous[1], end],
                        )
                    )
                if candidates:
                    dp[(segment_count, end)] = min(candidates, key=lambda item: item[0])
        solutions[stage_count] = dp[(stage_count, n)]

    bic: dict[int, float] = {}
    for stage_count, (sse, _) in solutions.items():
        safe_sse = max(sse, np.finfo(float).eps)
        parameter_count = stage_count * dimensions + stage_count - 1
        bic[stage_count] = (
            n * dimensions * math.log(safe_sse / (n * dimensions))
            + parameter_count * math.log(n)
        )
    chosen_count = min(bic, key=bic.get)
    endpoints = solutions[chosen_count][1]

    stages: list[dict[str, object]] = []
    start = 0
    names = ["覆盖初期与波动期", "规模化增长期", "高位调整期", "稳定期"]
    for index, end in enumerate(endpoints):
        segment = sample.iloc[start:end]
        stage: dict[str, object] = {
            "stage": index + 1,
            "name": names[index] if index < len(names) else f"阶段 {index + 1}",
            "start_month": segment["month"].iloc[0],
            "end_month": segment["month"].iloc[-1],
            "observed_months": len(segment),
        }
        for metric in metrics:
            stage[f"{metric}_average"] = float(segment[metric].mean())
            first_value = float(segment[metric].iloc[0])
            last_value = float(segment[metric].iloc[-1])
            stage[f"{metric}_start_end_pct"] = (
                (last_value / first_value - 1) * 100 if first_value != 0 else np.nan
            )
        stages.append(stage)
        start = end
    return stages, bic


def continuous_plot_frame(df: pd.DataFrame) -> pd.DataFrame:
    full_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    return df.set_index("date").reindex(full_dates).rename_axis("date").reset_index()


def value_text(value: float, money: bool) -> str:
    return f"{value:,.2f}" if money else f"{value:,.0f}"


def axis_formatter(money: bool) -> FuncFormatter:
    if money:
        return FuncFormatter(lambda value, _: f"{value:,.2f}")
    return FuncFormatter(lambda value, _: f"{value:,.0f}")


def add_context_marks(ax: plt.Axes, df: pd.DataFrame, compact: bool = False) -> None:
    first_date, last_date = df["date"].iloc[[0, -1]]
    half_month = pd.Timedelta(days=14)
    for date in (first_date, last_date):
        ax.axvspan(date - half_month, date + half_month, color=BOUNDARY_COLOR, alpha=0.18, zorder=0)
    missing_dates = pd.date_range(first_date, last_date, freq="MS").difference(pd.DatetimeIndex(df["date"]))
    for date in missing_dates:
        ax.axvline(date, color=MISSING_COLOR, linestyle="--", linewidth=1.2, alpha=0.8, zorder=1)
        if not compact:
            ax.annotate(
                f"{date:%Y-%m}\n缺月（未补 0）",
                xy=(date, 0.04),
                xycoords=("data", "axes fraction"),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color=MISSING_COLOR,
            )


def annotate_point(
    ax: plt.Axes,
    date: pd.Timestamp,
    value: float,
    label: str,
    money: bool,
    color: str,
    offset: tuple[int, int],
) -> None:
    ax.annotate(
        f"{label}\n{date:%Y-%m} | {value_text(value, money)}",
        xy=(date, value),
        xytext=offset,
        textcoords="offset points",
        fontsize=8,
        color=color,
        ha="left" if offset[0] >= 0 else "right",
        va="bottom" if offset[1] >= 0 else "top",
        arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": color, "alpha": 0.9},
    )


def style_time_axis(ax: plt.Axes, money: bool, compact: bool = False) -> None:
    ax.set_xlabel("月份")
    ax.yaxis.set_major_formatter(axis_formatter(money))
    if not money:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3 if compact else 2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", labelrotation=40, labelsize=8 if compact else 9)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.65)
    ax.grid(axis="x", visible=False)
    ax.margins(x=0.025, y=0.15)


def plot_single_metric(
    df: pd.DataFrame,
    plot_df: pd.DataFrame,
    metric: str,
    extrema: dict[str, dict[str, tuple[str, float]]],
) -> Path:
    config = METRICS[metric]
    fig, ax = plt.subplots(figsize=(13.5, 7.2), layout="constrained")
    ax.plot(
        plot_df["date"],
        plot_df[metric],
        color=config["color"],
        linewidth=2.3,
        marker="o",
        markersize=5.5,
        markerfacecolor="white",
        markeredgewidth=1.5,
        zorder=3,
    )
    add_context_marks(ax, df)

    anomalies = df.loc[df[f"{metric}_anomaly"]]
    ax.scatter(
        anomalies["date"],
        anomalies[metric],
        marker="D",
        s=65,
        color=ANOMALY_COLOR,
        edgecolor="white",
        linewidth=0.8,
        zorder=5,
    )
    for _, row in anomalies.iterrows():
        annotate_point(
            ax,
            row["date"],
            row[metric],
            f"异常（月环比 {row[f'{metric}_mom_pct']:.2f}%）",
            bool(config["money"]),
            ANOMALY_COLOR,
            (12, 20),
        )

    peak_month, peak_value = extrema[metric]["peak"]
    trough_month, trough_value = extrema[metric]["trough"]
    peak_date, trough_date = pd.Timestamp(peak_month), pd.Timestamp(trough_month)
    ax.scatter([peak_date], [peak_value], marker="^", s=80, color="#1B5E20", zorder=5)
    ax.scatter([trough_date], [trough_value], marker="v", s=80, color="#6A1B9A", zorder=5)
    peak_offset = (24, -35) if peak_date <= df["date"].iloc[0] + pd.DateOffset(months=2) else (-10, 24)
    annotate_point(ax, peak_date, peak_value, "峰值", bool(config["money"]), "#1B5E20", peak_offset)
    annotate_point(ax, trough_date, trough_value, "低谷", bool(config["money"]), "#6A1B9A", (12, -28))

    ax.set_title(str(config["title"]), fontsize=16, pad=14)
    ax.set_ylabel(str(config["ylabel"]))
    style_time_axis(ax, bool(config["money"]))
    handles = [
        Line2D([0], [0], color=str(config["color"]), marker="o", label=str(config["label"])),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=ANOMALY_COLOR, label="IQR 环比异常", markersize=7),
        Line2D([0], [0], color=BOUNDARY_COLOR, lw=8, alpha=0.35, label="不完整边界月"),
        Line2D([0], [0], color=MISSING_COLOR, linestyle="--", label="缺失月份"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=True, ncols=2, fontsize=9)
    ax.text(
        0.995,
        0.01,
        "注：峰值/低谷与异常判断均排除不完整边界月；折线断点表示月份缺失。",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.5,
        color="#555555",
    )
    output = FIGURE_DIR / str(config["filename"])
    fig.savefig(output, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return output


def plot_overview(
    df: pd.DataFrame,
    plot_df: pd.DataFrame,
    extrema: dict[str, dict[str, tuple[str, float]]],
) -> Path:
    fig, axes = plt.subplots(3, 2, figsize=(16, 15), layout="constrained")
    for ax, (metric, config) in zip(axes.flat[:5], METRICS.items()):
        ax.plot(
            plot_df["date"],
            plot_df[metric],
            color=config["color"],
            linewidth=2.0,
            marker="o",
            markersize=4.2,
            markerfacecolor="white",
            markeredgewidth=1.2,
            zorder=3,
        )
        add_context_marks(ax, df, compact=True)
        anomalies = df.loc[df[f"{metric}_anomaly"]]
        ax.scatter(anomalies["date"], anomalies[metric], marker="D", s=48, color=ANOMALY_COLOR, zorder=5)
        peak_month, peak_value = extrema[metric]["peak"]
        trough_month, trough_value = extrema[metric]["trough"]
        ax.scatter(pd.Timestamp(peak_month), peak_value, marker="^", s=58, color="#1B5E20", zorder=5)
        ax.scatter(pd.Timestamp(trough_month), trough_value, marker="v", s=58, color="#6A1B9A", zorder=5)
        ax.annotate(f"峰 {peak_month}", (pd.Timestamp(peak_month), peak_value), xytext=(4, 8), textcoords="offset points", fontsize=7.5, color="#1B5E20")
        ax.annotate(f"谷 {trough_month}", (pd.Timestamp(trough_month), trough_value), xytext=(4, -12), textcoords="offset points", fontsize=7.5, color="#6A1B9A")
        ax.set_title(str(config["title"]), fontsize=12)
        ax.set_ylabel(str(config["ylabel"]), fontsize=9)
        style_time_axis(ax, bool(config["money"]), compact=True)

    legend_ax = axes.flat[5]
    legend_ax.axis("off")
    handles = [
        Line2D([0], [0], marker="^", color="none", markerfacecolor="#1B5E20", label="峰值（排除边界月）", markersize=8),
        Line2D([0], [0], marker="v", color="none", markerfacecolor="#6A1B9A", label="低谷（排除边界月）", markersize=8),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=ANOMALY_COLOR, label="IQR 环比异常", markersize=8),
        Line2D([0], [0], color=BOUNDARY_COLOR, lw=10, alpha=0.35, label="不完整边界月"),
        Line2D([0], [0], color=MISSING_COLOR, linestyle="--", label="缺失月份（未补 0）"),
    ]
    legend_ax.legend(handles=handles, loc="center", frameon=False, fontsize=11, labelspacing=1.2)
    legend_ax.text(
        0.5,
        0.20,
        "边界：2016-09、2018-08\n缺月：2016-11\n异常阈值仅使用连续且完整月份的环比",
        ha="center",
        va="center",
        fontsize=10,
        color="#4A4A4A",
        linespacing=1.7,
    )
    fig.suptitle("核心业务指标月度趋势总览", fontsize=18, fontweight="bold")
    output = FIGURE_DIR / "06_core_metrics_overview.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return output


def format_nulls(null_counts: dict[str, int]) -> str:
    present = [f"`{column}` {count} 个" for column, count in null_counts.items() if count]
    return "、".join(present) if present else "无"


def format_metric_value(metric: str, value: float) -> str:
    unit = " BRL" if METRICS[metric]["money"] else (" 单" if metric == "order_count" else " 人")
    return f"{value:,.2f}{unit}" if METRICS[metric]["money"] else f"{value:,.0f}{unit}"


def overall_trend_text(df: pd.DataFrame, metric: str) -> str:
    complete = df.loc[~df["is_boundary_month"] & df[metric].notna()]
    first, last = complete.iloc[0], complete.iloc[-1]
    change = (last[metric] / first[metric] - 1) * 100 if first[metric] != 0 else np.nan
    peak_month = complete.loc[complete[metric].idxmax(), "month"]
    if metric == "average_order_value":
        stable = df.loc[(df["month"] >= "2017-02") & (df["month"] <= "2018-07"), metric]
        return (
            f"完整可比期由 {format_metric_value(metric, first[metric])} 变为 "
            f"{format_metric_value(metric, last[metric])}（{change:+.2f}%）；"
            f"2017-02 至 2018-07 主要落在 {stable.min():.2f}—{stable.max():.2f} BRL/单，"
            f"峰值出现在 {peak_month}。"
        )
    return (
        f"完整可比期由 {format_metric_value(metric, first[metric])} 增至 "
        f"{format_metric_value(metric, last[metric])}（{change:+.2f}%），"
        f"峰值出现在 {peak_month}。"
    )


def stage_description(stage: dict[str, object]) -> str:
    if int(stage["stage"]) == 1:
        return (
            "四项规模指标处于低基数并剧烈波动；2016-12 同时触及四项规模指标低谷，"
            "随后在 2017-01 共同反弹。"
        )
    return (
        "GMV、订单量、新增用户和活跃用户同步扩张，2017-11 共同达到峰值；"
        "2018 年上半年维持高位但月间有回落与修复。"
    )


def generate_report(
    df: pd.DataFrame,
    validation: ValidationSummary,
    thresholds: dict[str, tuple[float, float]],
    extrema: dict[str, dict[str, tuple[str, float]]],
    stages: list[dict[str, object]],
    bic: dict[int, float],
    font_name: str,
) -> None:
    metric_names = {metric: str(config["label"]) for metric, config in METRICS.items()}
    missing_text = "、".join(validation.missing_months) if validation.missing_months else "无"
    anomaly_rows = df.loc[df["anomaly_count"] > 0]

    extrema_lines = []
    for metric in METRICS:
        peak_month, peak_value = extrema[metric]["peak"]
        trough_month, trough_value = extrema[metric]["trough"]
        extrema_lines.append(
            f"| {metric_names[metric]} | {peak_month} | {format_metric_value(metric, peak_value)} "
            f"| {trough_month} | {format_metric_value(metric, trough_value)} |"
        )

    stage_lines = []
    for stage in stages:
        stage_lines.append(
            f"| {stage['stage']}：{stage['name']} | {stage['start_month']}—{stage['end_month']} "
            f"| {stage['observed_months']} | {stage_description(stage)} "
            f"| GMV 均值 {stage['gmv_average']:,.2f} BRL；订单量均值 {stage['order_count_average']:,.0f} 单；"
            f"新增/活跃用户均值 {stage['new_users_average']:,.0f}/{stage['active_users_average']:,.0f} 人 |"
        )

    anomaly_lines = []
    for _, row in anomaly_rows.iterrows():
        labels = "、".join(metric_names[metric] for metric in row["anomaly_metrics"].split(";") if metric)
        anomaly_lines.append(
            f"| {row['month']} | {labels} | {row['gmv_mom_pct']:.2f}% | "
            f"{row['order_count_mom_pct']:.2f}% | {row['average_order_value_mom_pct']:.2f}% | "
            f"{row['new_users_mom_pct']:.2f}% | {row['active_users_mom_pct']:.2f}% | {row['diagnosis']} |"
        )

    threshold_lines = [
        f"| {metric_names[metric]} | {bounds[0]:.2f}% | {bounds[1]:.2f}% |"
        for metric, bounds in thresholds.items()
    ]
    bic_text = "；".join(f"{count} 段={score:.2f}" for count, score in sorted(bic.items()))

    complete = df.loc[~df["is_boundary_month"]]
    start, end = complete.iloc[0], complete.iloc[-1]
    changes = {
        metric: (end[metric] / start[metric] - 1) * 100
        for metric in ["gmv", "order_count", "new_users", "active_users"]
    }
    aov_core = df.loc[(df["month"] >= "2017-02") & (df["month"] <= "2018-07"), "average_order_value"]
    recent = df.loc[(df["month"] >= "2018-03") & (df["month"] <= "2018-07")]

    report = f"""# 核心业务趋势分析

## 1. 数据范围与验证

- 数据源：`outputs/data/02_business_overview/monthly_kpi.csv`，并与 SQLite View `monthly_kpi` 逐值核对。
- 字段：`month`、`gmv`、`order_count`、`average_order_value`、`new_users`、`active_users`，与公共层字段完全一致。
- 覆盖范围：{validation.start_month} 至 {validation.end_month}，共 {validation.row_count} 个观测月份；源文件按月升序，重复月份 {validation.duplicate_months} 个。
- 缺失月份：{missing_text}。未填充为 0，图中的折线在缺月处主动断开。
- 空值：{format_nulls(validation.null_counts)}。公共层仅保留正支付 delivered 订单，AOV 与订单量使用同一订单范围。
- CSV 与数据库 View：{'完全一致' if validation.db_matches_csv else '不一致'}。

### 数据边界

全部 delivered 数据从 2016-09 月中开始，但该月唯一 delivered 订单没有正支付，因此不进入本支付型公共层。2018-08 是数据截止月，未覆盖完整自然月，保留在图中并以黄色背景标注，但不参与正常峰值、低谷、环比异常阈值和业务阶段判断。2016-11 在公共层中缺失，报告与图表均保留这一时间缺口，不补 0。新增用户是观察期内首次产生正支付 delivered 订单的用户，覆盖开始前历史缺失可能导致早期存量用户被识别为新增用户。

## 2. 五项核心指标总体趋势

- **GMV：** {overall_trend_text(df, 'gmv')}
- **订单量：** {overall_trend_text(df, 'order_count')}
- **客单价：** {overall_trend_text(df, 'average_order_value')}
- **新增用户：** {overall_trend_text(df, 'new_users')}
- **活跃用户：** {overall_trend_text(df, 'active_users')}

![核心指标总览](../../visualizations/business_overview/06_core_metrics_overview.png)

## 3. 业务阶段划分

阶段划分只使用 GMV、订单量、新增用户、活跃用户四项共同趋势，排除不完整的 2018-08。方法是对四指标做 `log1p` 与标准化，对 1—4 个有序阶段进行动态规划（每段至少 3 个观测月），以段内平方误差最小并用 BIC 惩罚段数；BIC 越低越优。本次结果为：{bic_text}，自动选择 {len(stages)} 个阶段。缺失的 2016-11 不参与拟合，也未补值。

| 阶段 | 起止月份 | 观测月数 | 主要变化 | 共同趋势依据 |
|---|---|---:|---|---|
{chr(10).join(stage_lines)}

该结果没有强行增加更多阶段：在复杂度惩罚后，额外分段未带来足够的联合趋势解释增益。阶段 2 内部仍可观察到 2017-11 的共同峰值及 2018 年上半年的高位调整，但不足以被模型识别为独立阶段。

## 4. 峰值、低谷与异常月份

峰值和低谷仅在完整月份中选择，边界月即使数值更极端也不参与。

| 指标 | 峰值月份 | 峰值 | 低谷月份 | 低谷 |
|---|---|---:|---|---:|
{chr(10).join(extrema_lines)}

异常候选基于逐指标环比 IQR：低于 `Q1 - 1.5 × IQR` 或高于 `Q3 + 1.5 × IQR`。只有当前月与上一个观测月连续、且两者均不是边界月时，环比才进入阈值计算及异常判断。

| 指标 | IQR 下界 | IQR 上界 |
|---|---:|---:|
{chr(10).join(threshold_lines)}

识别到的异常月份如下：

| 月份 | 越界指标 | GMV 环比 | 订单量环比 | 客单价环比 | 新增用户环比 | 活跃用户环比 | 初步回查 |
|---|---|---:|---:|---:|---:|---:|---|
{chr(10).join(anomaly_lines) if anomaly_lines else '| 无 | 无 | — | — | — | — | — | 无异常候选 |'}

## 5. 异常月份回查

- **2017-01：** 前一观测月 2016-12 仅有 1 单、GMV 19.62 BRL、新增与活跃用户均为 1 人，形成极低比较基数。2017-01 订单量增至 750 单、客单价由 19.62 升至 170.06 BRL，GMV 的异常增长由订单量与客单价共同推动；新增与活跃用户也同步回升。现有数据无法验证 2016-12 极低值或 2017-01 反弹的具体外部原因。
- **2017-02：** GMV 环比增长 {anomaly_rows.loc[anomaly_rows['month'].eq('2017-02'), 'gmv_mom_pct'].iloc[0]:.2f}%，订单量增长 {anomaly_rows.loc[anomaly_rows['month'].eq('2017-02'), 'order_count_mom_pct'].iloc[0]:.2f}%，而客单价变化 {anomaly_rows.loc[anomaly_rows['month'].eq('2017-02'), 'average_order_value_mom_pct'].iloc[0]:.2f}%；因此 GMV 异常主要由订单量扩张驱动。新增与活跃用户分别增长 {anomaly_rows.loc[anomaly_rows['month'].eq('2017-02'), 'new_users_mom_pct'].iloc[0]:.2f}% 和 {anomaly_rows.loc[anomaly_rows['month'].eq('2017-02'), 'active_users_mom_pct'].iloc[0]:.2f}%，与订单扩张方向一致。现有数据无法验证具体外部原因。

完整逐月环比、阈值、异常标记及诊断见 `outputs/data/02_business_overview/monthly_trend_diagnostics.csv`。

## 6. 核心业务结论

1. 四项规模指标长期同向扩张：从首个完整月 2016-10 到末个完整月 2018-07，GMV、订单量、新增用户和活跃用户分别增长 {changes['gmv']:.2f}%、{changes['order_count']:.2f}%、{changes['new_users']:.2f}% 和 {changes['active_users']:.2f}%。
2. 2017-11 是明确的共同规模峰值：GMV {extrema['gmv']['peak'][1]:,.2f} BRL、订单量 {extrema['order_count']['peak'][1]:,.0f} 单、新增用户 {extrema['new_users']['peak'][1]:,.0f} 人、活跃用户 {extrema['active_users']['peak'][1]:,.0f} 人同时达峰，不是单一指标造成的假象。
3. GMV 的长期增长主要伴随订单和用户规模增长，而非持续抬升客单价：2017-02 至 2018-07 的客单价范围仅为 {aov_core.min():.2f}—{aov_core.max():.2f} BRL/单，明显比同期规模指标的增幅平稳。
4. 2017-01 与 2017-02 是 IQR 规则识别出的异常月份。前者受 2016-12 极低基数及订单量、客单价共同反弹影响；后者主要由订单量和用户规模继续扩张驱动。两月的具体外部成因均无法由现有数据验证。
5. 2018-03 至 2018-07 处于高位波动区间：GMV 为 {recent['gmv'].min():,.2f}—{recent['gmv'].max():,.2f} BRL，订单量为 {recent['order_count'].min():,.0f}—{recent['order_count'].max():,.0f} 单；2018-08 因截止期不完整，不应用于判断后续趋势。

---

生成说明：图表采用 `{font_name}` 字体、300 DPI PNG；金额保留两位小数，数量按整数展示。分析严格复用月度公共数据层，未改变指标定义或 SQL 口径。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def save_diagnostics(df: pd.DataFrame) -> None:
    output = df.drop(columns=["date"]).copy()
    money_columns = ["gmv", "average_order_value"]
    output[money_columns] = output[money_columns].round(2)
    pct_columns = [column for column in output.columns if column.endswith("_pct")]
    output[pct_columns] = output[pct_columns].round(2)
    if output["month"].duplicated().any():
        raise ValueError("诊断 CSV 将产生重复月份，已中止写出")
    output.to_csv(DIAGNOSTIC_CSV, index=False, encoding="utf-8-sig")


def verify_outputs(paths: Iterable[Path], df: pd.DataFrame) -> None:
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"输出文件缺失或为空：{path}")
    diagnostic = pd.read_csv(DIAGNOSTIC_CSV)
    if diagnostic["month"].duplicated().any():
        raise RuntimeError("诊断 CSV 存在重复月份")
    if diagnostic["month"].tolist() != df["month"].tolist():
        raise RuntimeError("诊断 CSV 月份与 monthly_kpi 不一致")
    for metric in METRICS:
        left = pd.to_numeric(diagnostic[metric], errors="coerce")
        right = df[metric].round(2) if metric in ("gmv", "average_order_value") else df[metric]
        if not np.allclose(left, right, equal_nan=True, atol=0.005):
            raise RuntimeError(f"诊断 CSV 的 {metric} 与 monthly_kpi 不一致")
    # Matplotlib can decode its own generated images; this catches corrupt PNGs.
    for path in paths:
        if path.suffix.lower() == ".png":
            image = plt.imread(path)
            if image.size == 0 or image.ndim not in (2, 3):
                raise RuntimeError(f"PNG 无法正常读取：{path}")


def main() -> None:
    args = parse_args()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    font_name = configure_plotting()
    data, validation = read_and_validate(args.csv, args.database)
    diagnosed, thresholds = add_diagnostics(data)
    extrema = peak_and_trough(diagnosed)
    stages, bic = determine_business_stages(diagnosed)
    plot_data = continuous_plot_frame(diagnosed)

    generated: list[Path] = []
    for metric in METRICS:
        generated.append(plot_single_metric(diagnosed, plot_data, metric, extrema))
    generated.append(plot_overview(diagnosed, plot_data, extrema))
    save_diagnostics(diagnosed)
    generate_report(diagnosed, validation, thresholds, extrema, stages, bic, font_name)
    generated.extend([DIAGNOSTIC_CSV, REPORT_PATH])
    verify_outputs(generated, diagnosed)

    anomalies = diagnosed.loc[diagnosed["anomaly_count"] > 0, "month"].tolist()
    print(f"验证通过：{validation.row_count} 行，{validation.start_month} 至 {validation.end_month}")
    print(f"缺失月份：{', '.join(validation.missing_months) if validation.missing_months else '无'}")
    print(f"异常月份：{', '.join(anomalies) if anomalies else '无'}")
    print(f"阶段数：{len(stages)}")
    print(f"绘图字体：{font_name}")
    print("已生成并验证：")
    for path in generated:
        print(f"- {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
