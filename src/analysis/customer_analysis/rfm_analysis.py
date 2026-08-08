r"""Run the fixed-date Stage 3 Member 1 RFM customer value analysis.

Run from the project root:
    .venv\Scripts\python.exe src\analysis\customer_analysis\rfm_analysis.py

The script executes the RFM SQL, exports final UTF-8 BOM CSV files, performs
strict reconciliations, reloads final summary CSV data for plotting, and writes
the scoring rules and analysis report. All project paths are derived from this
file; no machine-specific path is embedded.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from dataclasses import asdict, dataclass
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
import numpy as np
import pandas as pd


OBSERVATION_DATE = "2018-07-31"
DEFAULT_DATABASE = PROJECT_ROOT / "database" / "brazil_ecommerce.db"
RFM_SQL = PROJECT_ROOT / "sql" / "05_customer_analysis" / "02_rfm_analysis.sql"
DATA_DIR = PROJECT_ROOT / "outputs" / "data" / "03_customer_analysis"
FIGURE_DIR = PROJECT_ROOT / "visualizations" / "customer" / "rfm"
RULES_PATH = PROJECT_ROOT / "docs" / "rfm_scoring_rules.md"
REPORT_PATH = PROJECT_ROOT / "reports" / "customer" / "rfm_customer_value_report.md"

CSV_PATHS = {
    "detail": DATA_DIR / "rfm_customer_detail.csv",
    "summary": DATA_DIR / "rfm_segment_summary.csv",
    "boundaries": DATA_DIR / "rfm_scoring_boundaries.csv",
    "frequency_mapping": DATA_DIR / "rfm_frequency_score_mapping.csv",
    "score_distribution": DATA_DIR / "rfm_score_distribution.csv",
    "validation": DATA_DIR / "rfm_validation.csv",
}

FIGURE_PATHS = {
    "users": FIGURE_DIR / "rfm_segment_user_distribution.png",
    "gmv": FIGURE_DIR / "rfm_segment_gmv_contribution.png",
    "share": FIGURE_DIR / "rfm_user_vs_gmv_share.png",
    "spend": FIGURE_DIR / "rfm_spend_per_user.png",
    "repeat": FIGURE_DIR / "rfm_repeat_purchase_rate.png",
}

SEGMENT_ORDER = [
    "重要价值用户",
    "重要发展用户",
    "重要保持用户",
    "重要挽留用户",
    "一般用户",
]

SEGMENT_COLORS = {
    "重要价值用户": "#2E8B57",
    "重要发展用户": "#2A7FB8",
    "重要保持用户": "#7567A8",
    "重要挽留用户": "#D77A32",
    "一般用户": "#8A8F98",
}

QUERY_MAP = {
    "detail": """
        SELECT * FROM rfm_customer_detail
        ORDER BY customer_unique_id
    """,
    "summary": """
        SELECT * FROM rfm_segment_summary
        ORDER BY rfm_segment_order
    """,
    "boundaries": """
        SELECT * FROM rfm_scoring_boundaries
        ORDER BY CASE metric WHEN 'recency_days' THEN 1 ELSE 2 END,
                 percentile_value
    """,
    "frequency_mapping": """
        SELECT * FROM rfm_frequency_score_mapping
        ORDER BY frequency
    """,
    "score_distribution": """
        SELECT * FROM rfm_score_distribution
        ORDER BY metric_order, score
    """,
}


@dataclass
class ValidationRecord:
    check_id: str
    check_name: str
    expected_value: str
    actual_value: str
    difference: str
    tolerance: str
    status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="SQLite database path; relative paths resolve from project root.",
    )
    return parser.parse_args()


def resolve_database(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def configure_plotting() -> str:
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
            "axes.grid": True,
            "grid.color": "#D9D9D9",
            "grid.alpha": 0.55,
            "grid.linewidth": 0.7,
            "axes.titleweight": "bold",
            "savefig.dpi": 300,
        }
    )
    return font_name


def prepare_database(database_path: Path) -> None:
    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: {database_path}. Run the database builder first."
        )
    if not RFM_SQL.exists():
        raise FileNotFoundError(f"RFM SQL not found: {RFM_SQL}")

    with sqlite3.connect(database_path) as connection:
        objects = {
            row[0]: row[1]
            for row in connection.execute(
                """
                SELECT name, type FROM sqlite_master
                WHERE name IN ('customer_order_base', 'customer_profile')
                """
            )
        }
        if objects.get("customer_order_base") != "table":
            raise RuntimeError(
                "customer_order_base is missing. Run customer_profile_analysis.py first."
            )
        if objects.get("customer_profile") != "table":
            raise RuntimeError(
                "customer_profile is missing. Run customer_profile_analysis.py first."
            )
        connection.executescript(RFM_SQL.read_text(encoding="utf-8-sig"))


def load_data(database_path: Path) -> dict[str, pd.DataFrame]:
    with sqlite3.connect(database_path) as connection:
        return {
            name: pd.read_sql_query(query, connection)
            for name, query in QUERY_MAP.items()
        }


def rounded_copy(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    money_columns = {
        "monetary",
        "gmv",
        "spend_per_user",
        "average_order_value",
        "gmv_per_valid_order",
        "average_monetary",
    }
    average_columns = {
        "average_purchase_frequency",
        "average_recency",
        "average_frequency",
        "average_r_score",
        "average_f_score",
        "average_m_score",
    }
    share_columns = {
        "user_share",
        "order_share",
        "gmv_share",
        "repeat_purchase_rate",
    }

    for column in result.columns:
        if column in money_columns:
            numeric = pd.to_numeric(result[column], errors="coerce").round(2)
            result[column] = numeric.map(
                lambda value: "" if pd.isna(value) else f"{value:.2f}"
            )
        elif column in average_columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(6)
        elif column in share_columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(10)
        elif name == "boundaries" and column == "boundary_value":
            numeric = pd.to_numeric(result[column], errors="coerce").round(2)
            result[column] = numeric.map(
                lambda value: "" if pd.isna(value) else f"{value:.2f}"
            )
    return result


def export_data(data: dict[str, pd.DataFrame]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in data.items():
        rounded_copy(name, frame).to_csv(
            CSV_PATHS[name],
            index=False,
            encoding="utf-8-sig",
        )


def add_validation(
    records: list[ValidationRecord],
    check_id: str,
    check_name: str,
    passed: bool,
    expected: object,
    actual: object,
    difference: object = "",
    tolerance: object = "exact",
    detail: str = "",
) -> None:
    records.append(
        ValidationRecord(
            check_id=check_id,
            check_name=check_name,
            expected_value=str(expected),
            actual_value=str(actual),
            difference=str(difference),
            tolerance=str(tolerance),
            status="PASS" if passed else "FAIL",
            detail=detail,
        )
    )


def validate_all(
    data: dict[str, pd.DataFrame], database_path: Path
) -> list[ValidationRecord]:
    detail = data["detail"]
    summary = data["summary"]
    boundaries = data["boundaries"]
    frequency_mapping = data["frequency_mapping"]
    records: list[ValidationRecord] = []
    money_tolerance = 0.01
    share_tolerance = 1e-8

    with sqlite3.connect(database_path) as connection:
        source = connection.execute(
            """
            SELECT
                COUNT(*) AS order_count,
                COUNT(DISTINCT customer_unique_id) AS user_count,
                SUM(is_paid_order) AS paid_order_count,
                SUM(order_gmv) AS gmv
            FROM customer_order_base
            WHERE DATE(order_purchase_timestamp) <= DATE(?)
            """,
            (OBSERVATION_DATE,),
        ).fetchone()
        source_frequency_values = {
            int(row[0])
            for row in connection.execute(
                """
                SELECT DISTINCT frequency FROM rfm_customer_base
                ORDER BY frequency
                """
            )
        }

    source_orders, source_users, source_paid_orders, source_gmv = source
    total_users = len(detail)
    total_orders = int(detail["frequency"].sum())
    total_gmv = float(detail["monetary"].sum())

    add_validation(
        records, "V01", "RFM 明细行数等于截止日唯一用户数",
        total_users == source_users, source_users, total_users,
        total_users - source_users,
    )
    blank_ids = int(
        detail["customer_unique_id"].isna().sum()
        + detail["customer_unique_id"].fillna("").astype(str).str.strip().eq("").sum()
    )
    add_validation(
        records, "V02", "customer_unique_id 无空值",
        blank_ids == 0, 0, blank_ids, blank_ids,
    )
    duplicate_ids = int(detail["customer_unique_id"].duplicated().sum())
    add_validation(
        records, "V03", "customer_unique_id 无重复",
        duplicate_ids == 0, 0, duplicate_ids, duplicate_ids,
    )

    raw_nulls = int(detail[["recency_days", "frequency", "monetary"]].isna().sum().sum())
    add_validation(
        records, "V04", "R、F、M 原始指标无空值",
        raw_nulls == 0, 0, raw_nulls, raw_nulls,
    )
    score_nulls = int(detail[["r_score", "f_score", "m_score"]].isna().sum().sum())
    add_validation(
        records, "V05", "R、F、M 评分无空值",
        score_nulls == 0, 0, score_nulls, score_nulls,
    )
    score_range_ok = all(
        detail[column].between(1, 5).all()
        for column in ["r_score", "f_score", "m_score"]
    )
    add_validation(
        records, "V06", "R、F、M 评分均在 1—5",
        score_range_ok, "all scores in [1,5]",
        f"R={detail.r_score.min()}..{detail.r_score.max()}; "
        f"F={detail.f_score.min()}..{detail.f_score.max()}; "
        f"M={detail.m_score.min()}..{detail.m_score.max()}",
    )

    for check_id, raw_column, score_column, label in [
        ("V07", "recency_days", "r_score", "相同 Recency 获得相同 R 评分"),
        ("V08", "frequency", "f_score", "相同 Frequency 获得相同 F 评分"),
        ("V09", "monetary", "m_score", "相同 Monetary 获得相同 M 评分"),
    ]:
        max_scores = int(detail.groupby(raw_column)[score_column].nunique().max())
        add_validation(
            records, check_id, label,
            max_scores == 1, 1, max_scores, max_scores - 1,
        )

    segment_per_user = int(detail.groupby("customer_unique_id")["rfm_segment"].nunique().max())
    add_validation(
        records, "V10", "每名用户只有一个 RFM 层级",
        segment_per_user == 1, 1, segment_per_user, segment_per_user - 1,
    )
    invalid_segments = int((~detail["rfm_segment"].isin(SEGMENT_ORDER)).sum())
    add_validation(
        records, "V11", "不存在未分类或额外类别用户",
        invalid_segments == 0, 0, invalid_segments, invalid_segments,
    )

    summary_users = int(summary["user_count"].sum())
    summary_orders = int(summary["valid_order_count"].sum())
    summary_gmv = float(summary["gmv"].sum())
    add_validation(
        records, "V12", "五类用户数之和等于整体用户数",
        summary_users == total_users, total_users, summary_users,
        summary_users - total_users,
    )
    add_validation(
        records, "V13", "五类订单数之和等于整体有效订单数",
        summary_orders == source_orders, source_orders, summary_orders,
        summary_orders - source_orders,
    )
    gmv_difference = summary_gmv - float(source_gmv)
    add_validation(
        records, "V14", "五类 GMV 之和与公共表一致",
        abs(gmv_difference) <= money_tolerance,
        f"{source_gmv:.2f}", f"{summary_gmv:.2f}", f"{gmv_difference:.8f}",
        money_tolerance,
    )

    for check_id, column, label in [
        ("V15", "user_share", "用户占比之和约等于 100%"),
        ("V16", "order_share", "订单占比之和约等于 100%"),
        ("V17", "gmv_share", "GMV 占比之和约等于 100%"),
    ]:
        share_sum = float(summary[column].sum())
        add_validation(
            records, check_id, label,
            abs(share_sum - 1.0) <= share_tolerance,
            1.0, f"{share_sum:.10f}", f"{share_sum - 1.0:.10f}",
            share_tolerance,
        )

    add_validation(
        records, "V18", "frequency 汇总等于订单级公共表有效订单数",
        total_orders == source_orders, source_orders, total_orders,
        total_orders - source_orders,
    )
    monetary_difference = total_gmv - float(source_gmv)
    add_validation(
        records, "V19", "monetary 汇总等于订单级公共表 GMV",
        abs(monetary_difference) <= money_tolerance,
        f"{source_gmv:.2f}", f"{total_gmv:.2f}", f"{monetary_difference:.8f}",
        money_tolerance,
    )

    repeat_count = int(detail["is_repeat_customer"].sum())
    expected_repeat_count = int((detail["frequency"] >= 2).sum())
    repeat_rate = repeat_count / total_users
    expected_repeat_rate = expected_repeat_count / total_users
    add_validation(
        records, "V20", "复购率符合 frequency >= 2 统一口径",
        repeat_count == expected_repeat_count and abs(repeat_rate - expected_repeat_rate) <= share_tolerance,
        f"count={expected_repeat_count}; rate={expected_repeat_rate:.10f}",
        f"count={repeat_count}; rate={repeat_rate:.10f}",
        f"{repeat_rate - expected_repeat_rate:.10f}", share_tolerance,
    )

    observation_values = set(detail["observation_date"].astype(str))
    add_validation(
        records, "V21", "观察截止日全部为 2018-07-31",
        observation_values == {OBSERVATION_DATE}, OBSERVATION_DATE,
        ",".join(sorted(observation_values)),
    )
    future_users = int(
        (pd.to_datetime(detail["last_purchase_date"])
         > pd.Timestamp(OBSERVATION_DATE)).sum()
    )
    add_validation(
        records, "V22", "不存在最近购买日期晚于观察截止日的用户",
        future_users == 0, 0, future_users, future_users,
    )
    negative_values = int(
        (detail[["recency_days", "frequency", "monetary"]] < 0).sum().sum()
    )
    add_validation(
        records, "V23", "Recency、Frequency、Monetary 均非负",
        negative_values == 0, 0, negative_values, negative_values,
    )

    mapped_frequency_values = set(frequency_mapping["frequency"].astype(int))
    add_validation(
        records, "V24", "F 映射完整覆盖全部不同 Frequency",
        mapped_frequency_values == source_frequency_values,
        sorted(source_frequency_values), sorted(mapped_frequency_values),
    )
    boundary_ok = (
        len(boundaries) == 8
        and all(
            group["boundary_value"].is_monotonic_increasing
            for _, group in boundaries.sort_values("percentile_value").groupby("metric")
        )
    )
    add_validation(
        records, "V25", "R/M 各有四个单调分位边界",
        boundary_ok, "8 monotonic boundary rows", len(boundaries),
    )

    expected_segments = np.select(
        [
            (detail.r_score >= 4) & (detail.f_score >= 4) & (detail.m_score >= 4),
            (detail.r_score >= 4) & (detail.f_score <= 3) & (detail.m_score >= 4),
            (detail.r_score <= 3) & (detail.f_score >= 4) & (detail.m_score >= 4),
            (detail.r_score <= 3) & (detail.f_score <= 3) & (detail.m_score >= 4),
        ],
        SEGMENT_ORDER[:4],
        default=SEGMENT_ORDER[4],
    )
    segment_mismatches = int((detail["rfm_segment"].to_numpy() != expected_segments).sum())
    add_validation(
        records, "V26", "五类互斥分类严格符合顺序规则",
        segment_mismatches == 0, 0, segment_mismatches, segment_mismatches,
    )

    expected_score = detail.r_score + detail.f_score + detail.m_score
    expected_code = (
        detail.r_score.astype(str)
        + detail.f_score.astype(str)
        + detail.m_score.astype(str)
    )
    score_mismatches = int((detail.rfm_score != expected_score).sum())
    code_mismatches = int((detail.rfm_code.astype(str) != expected_code).sum())
    add_validation(
        records, "V27", "rfm_score 与 rfm_code 计算正确",
        score_mismatches == 0 and code_mismatches == 0,
        "score/code mismatches=0",
        f"score={score_mismatches}; code={code_mismatches}",
    )

    frequency_difference = (
        summary["average_purchase_frequency"] - summary["average_frequency"]
    ).abs().max()
    add_validation(
        records, "V28", "平均购买频次与 AVG(frequency) 一致",
        float(frequency_difference) <= 1e-12,
        0, f"{frequency_difference:.12f}", f"{frequency_difference:.12f}", 1e-12,
    )

    expected_aov = summary["gmv"] / summary["paid_order_count"].replace(0, np.nan)
    aov_difference = (summary["average_order_value"] - expected_aov).abs().max()
    add_validation(
        records, "V29", "客单价沿用正式口径 GMV / 支付订单数",
        float(aov_difference) <= 1e-9,
        0, f"{aov_difference:.12f}", f"{aov_difference:.12f}", 1e-9,
        f"截止日支付订单 {int(source_paid_orders):,}；另输出 gmv_per_valid_order 满足附件公式。",
    )

    failures = [record for record in records if record.status != "PASS"]
    if failures:
        failure_text = "; ".join(
            f"{record.check_id} {record.check_name}" for record in failures
        )
        raise AssertionError(f"RFM validation failed: {failure_text}")
    return records


def save_validation(records: list[ValidationRecord]) -> None:
    pd.DataFrame([asdict(record) for record in records]).to_csv(
        CSV_PATHS["validation"],
        index=False,
        encoding="utf-8-sig",
    )


def finish_axis(ax: plt.Axes, grid_axis: str = "x") -> None:
    ax.grid(False)
    ax.grid(True, axis=grid_axis, color="#D9D9D9", alpha=0.55, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)


def ordered_summary() -> pd.DataFrame:
    frame = pd.read_csv(CSV_PATHS["summary"], encoding="utf-8-sig")
    frame["rfm_segment"] = pd.Categorical(
        frame["rfm_segment"], categories=SEGMENT_ORDER, ordered=True
    )
    return frame.sort_values("rfm_segment").reset_index(drop=True)


def label_horizontal_bars(
    ax: plt.Axes,
    values: pd.Series,
    labels: list[str],
) -> None:
    maximum = max(float(values.max()), 1.0)
    for index, (value, label) in enumerate(zip(values, labels)):
        ax.text(
            max(float(value), maximum * 0.004) + maximum * 0.008,
            index,
            label,
            va="center",
            fontsize=9,
        )
    ax.set_xlim(left=0, right=maximum * 1.23)


def plot_user_distribution(frame: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    colors = [SEGMENT_COLORS[str(segment)] for segment in frame.rfm_segment]
    ax.barh(frame.rfm_segment, frame.user_count, color=colors)
    label_horizontal_bars(
        ax,
        frame.user_count,
        [f"{int(v):,}（{s:.2%}）" for v, s in zip(frame.user_count, frame.user_share)],
    )
    ax.invert_yaxis()
    ax.set_title("RFM 五类用户数量及占比", fontsize=17)
    ax.set_xlabel("用户数（人）")
    ax.set_ylabel("RFM 用户层级")
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    finish_axis(ax)
    fig.savefig(FIGURE_PATHS["users"], bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def plot_gmv_contribution(frame: pd.DataFrame) -> None:
    values = frame.gmv / 1_000_000
    labels = [
        (f"{gmv:,.2f} BRL（{share:.2%}）" if value < 0.01 else f"{value:,.2f}M（{share:.2%}）")
        for gmv, value, share in zip(frame.gmv, values, frame.gmv_share)
    ]
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    colors = [SEGMENT_COLORS[str(segment)] for segment in frame.rfm_segment]
    ax.barh(frame.rfm_segment, values, color=colors)
    label_horizontal_bars(
        ax,
        values,
        labels,
    )
    ax.invert_yaxis()
    ax.set_title("RFM 各层级 GMV 及贡献占比", fontsize=17)
    ax.set_xlabel("GMV（百万 BRL）")
    ax.set_ylabel("RFM 用户层级")
    finish_axis(ax)
    fig.savefig(FIGURE_PATHS["gmv"], bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def plot_share_comparison(frame: pd.DataFrame) -> None:
    y = np.arange(len(frame))
    height = 0.34
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    ax.barh(y - height / 2, frame.user_share, height, color="#2A7FB8", label="用户占比")
    ax.barh(y + height / 2, frame.gmv_share, height, color="#3A8F75", label="GMV 占比")
    for index, row in frame.iterrows():
        ax.text(row.user_share + 0.005, index - height / 2, f"{row.user_share:.2%}", va="center", fontsize=8)
        ax.text(row.gmv_share + 0.005, index + height / 2, f"{row.gmv_share:.2%}", va="center", fontsize=8)
    ax.set_yticks(y, frame.rfm_segment)
    ax.invert_yaxis()
    ax.set_xlim(0, max(frame.user_share.max(), frame.gmv_share.max()) * 1.22)
    ax.set_title("RFM 用户占比与 GMV 占比对比", fontsize=17)
    ax.set_xlabel("占比")
    ax.set_ylabel("RFM 用户层级")
    ax.xaxis.set_major_formatter(ticker.PercentFormatter(1.0))
    ax.legend(loc="lower right", frameon=False)
    finish_axis(ax)
    fig.savefig(FIGURE_PATHS["share"], bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def plot_spend_per_user(frame: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    colors = [SEGMENT_COLORS[str(segment)] for segment in frame.rfm_segment]
    ax.barh(frame.rfm_segment, frame.spend_per_user, color=colors)
    label_horizontal_bars(
        ax,
        frame.spend_per_user,
        [f"{value:,.2f}" for value in frame.spend_per_user],
    )
    ax.invert_yaxis()
    ax.set_title("RFM 各层级人均消费", fontsize=17)
    ax.set_xlabel("人均消费（BRL/人）")
    ax.set_ylabel("RFM 用户层级")
    finish_axis(ax)
    fig.savefig(FIGURE_PATHS["spend"], bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def plot_repeat_rate(frame: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    colors = [SEGMENT_COLORS[str(segment)] for segment in frame.rfm_segment]
    ax.barh(frame.rfm_segment, frame.repeat_purchase_rate, color=colors)
    label_horizontal_bars(
        ax,
        frame.repeat_purchase_rate,
        [f"{value:.2%}" for value in frame.repeat_purchase_rate],
    )
    ax.set_xlim(0, 1.12)
    ax.invert_yaxis()
    ax.set_title("RFM 各层级复购率", fontsize=17)
    ax.set_xlabel("复购率（frequency ≥ 2）")
    ax.set_ylabel("RFM 用户层级")
    ax.xaxis.set_major_formatter(ticker.PercentFormatter(1.0))
    finish_axis(ax)
    fig.savefig(FIGURE_PATHS["repeat"], bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def create_figures() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    frame = ordered_summary()
    plot_user_distribution(frame)
    plot_gmv_contribution(frame)
    plot_share_comparison(frame)
    plot_spend_per_user(frame)
    plot_repeat_rate(frame)


def boundary_lookup(boundaries: pd.DataFrame, metric: str) -> dict[str, float]:
    subset = boundaries.loc[boundaries.metric.eq(metric)]
    return {
        str(row.percentile_label): float(row.boundary_value)
        for row in subset.itertuples()
    }


def frequency_mapping_text(mapping: pd.DataFrame) -> str:
    return "\n".join(
        f"| {int(row.frequency)} | {int(row.f_score)} |"
        for row in mapping.itertuples()
    )


def generate_rules(data: dict[str, pd.DataFrame]) -> None:
    r = boundary_lookup(data["boundaries"], "recency_days")
    m = boundary_lookup(data["boundaries"], "monetary")
    mapping_rows = frequency_mapping_text(data["frequency_mapping"])
    distribution_rows = "\n".join(
        f"| {row.metric} | {int(row.score)} | {int(row.user_count):,} | {row.user_share:.2%} |"
        for row in data["score_distribution"].itertuples()
    )

    content = f"""# RFM 评分与分类规则说明

## 1. 数据来源与观察窗口

- 数据源：SQLite 派生表 `customer_order_base`，该表已满足一行一个 delivered 订单，`order_gmv` 已先聚合到订单级。
- 观察截止日：固定为 `{OBSERVATION_DATE}`，不使用程序运行日期。
- 纳入范围：`purchase_date <= {OBSERVATION_DATE}` 的 delivered 订单。
- 用户标识：`customer_unique_id`。
- Monetary：用户截止观察日的 `SUM(order_gmv)`，未连接支付、商品或评论明细。
- 地域：使用截止日前最近一笔 delivered 订单地址；若时间相同，依次按 `order_id DESC`、`customer_id DESC` 稳定选择。

现有 `customer_profile` 包含 2018-08 交易，因此不能直接作为本次固定截止日的 RFM 汇总值；本分析仅复用订单级公共表，并在截止日内重新汇总。字段映射为：`purchase_date → 首/末购买日期`、`order_gmv → Monetary`、`customer_state/customer_city → 最近订单代表地域`。

## 2. RFM 指标

| 指标 | 定义 | 方向 |
|---|---|---|
| Recency | `2018-07-31 - 最近购买日期`，单位天 | 越小越好 |
| Frequency | 截止日内 delivered 订单数 | 越大越好 |
| Monetary | 截止日内订单级支付金额之和，BRL | 越大越好 |

## 3. R 评分

采用完整用户 Recency 分布的经验最近秩分位点。同一 `recency_days` 始终同分，不对用户行使用 `NTILE`。

| R 分数 | Recency 范围 |
|---:|---|
| 5 | `recency_days <= {r['P20']:.0f}` |
| 4 | `{r['P20']:.0f} < recency_days <= {r['P40']:.0f}` |
| 3 | `{r['P40']:.0f} < recency_days <= {r['P60']:.0f}` |
| 2 | `{r['P60']:.0f} < recency_days <= {r['P80']:.0f}` |
| 1 | `recency_days > {r['P80']:.0f}` |

## 4. M 评分

采用完整用户 Monetary 分布的经验最近秩分位点。同一 Monetary 始终同分，不为强制均分而拆分相同金额。

| M 分数 | Monetary 范围（BRL） |
|---:|---|
| 1 | `monetary <= {m['P20']:.2f}` |
| 2 | `{m['P20']:.2f} < monetary <= {m['P40']:.2f}` |
| 3 | `{m['P40']:.2f} < monetary <= {m['P60']:.2f}` |
| 4 | `{m['P60']:.2f} < monetary <= {m['P80']:.2f}` |
| 5 | `monetary > {m['P80']:.2f}` |

## 5. F 评分映射

先提取 Frequency 的不同取值，只对不同取值执行 `NTILE(5)`，然后映射回用户。这样不会把相同购买次数拆入不同档位。

| Frequency | F 分数 |
|---:|---:|
{mapping_rows}

Frequency 高度离散且集中：F=1 分包含 frequency 1—2 的绝大多数用户；F>=4 只包含 frequency 7、9、12。由此产生的高 F 人群很小，是指定评分方法与真实分布的共同结果。

## 6. 各评分档分布

| 指标 | 分数 | 用户数 | 用户占比 |
|---|---:|---:|---:|
{distribution_rows}

## 7. 高低界定与五类互斥规则

- 高 R/F/M：对应评分 `>= 4`。
- 低 R/F/M：对应评分 `<= 3`。

| 判断顺序 | 用户类别 | 判断条件 |
|---:|---|---|
| 1 | 重要价值用户 | 高R、高F、高M |
| 2 | 重要发展用户 | 高R、低F、高M |
| 3 | 重要保持用户 | 低R、高F、高M |
| 4 | 重要挽留用户 | 低R、低F、高M |
| 5 | 一般用户 | 低M，不论R和F |

规则按表中顺序执行，五类互斥且完整。`rfm_score = r_score + f_score + m_score`；`rfm_code` 为三位评分组合。

## 8. 口径差异与方法限制

- 附件将“客单价”写为 GMV / 全部有效订单数，但项目正式指标定义要求 GMV / 正支付 delivered 订单数。本分析以正式定义为准，将其输出为 `average_order_value`；同时额外输出 `gmv_per_valid_order` 满足附件公式。截止日前仅有 1 个 delivered 订单无正支付，差异很小但不静默混用。
- 经验分位点可能因重复值导致档位人数不完全均匀；这是保持同值同分的必要结果。
- F 按不同 Frequency 取值而非用户数分档，因此高 F 样本极少，不能把小样本画像外推为稳定人群规律。
- 观察期开始前历史缺失会影响 Frequency 和首次购买日期；截止日后的购买被有意排除。
- RFM 是描述性价值分层，不包含成本、利润、营销触达或因果效果。
"""
    RULES_PATH.write_text(content, encoding="utf-8")


def generate_report(data: dict[str, pd.DataFrame], font_name: str) -> None:
    summary = data["summary"].sort_values("rfm_segment_order")
    boundaries = data["boundaries"]
    mapping = data["frequency_mapping"]
    detail = data["detail"]
    r = boundary_lookup(boundaries, "recency_days")
    m = boundary_lookup(boundaries, "monetary")
    overall_repeat_rate = detail.is_repeat_customer.sum() / len(detail)

    segment_rows = "\n".join(
        f"| {row.rfm_segment} | {int(row.user_count):,} | {row.user_share:.2%} | "
        f"{int(row.valid_order_count):,} | {row.gmv:,.2f} | {row.gmv_share:.2%} | "
        f"{row.spend_per_user:,.2f} | {row.average_order_value:,.2f} | "
        f"{row.repeat_purchase_rate:.2%} | {row.average_recency:.2f} |"
        for row in summary.itertuples()
    )
    frequency_rows = frequency_mapping_text(mapping)
    validation_count = len(pd.read_csv(CSV_PATHS["validation"], encoding="utf-8-sig"))

    value = summary.loc[summary.rfm_segment.eq("重要价值用户")].iloc[0]
    develop = summary.loc[summary.rfm_segment.eq("重要发展用户")].iloc[0]
    keep = summary.loc[summary.rfm_segment.eq("重要保持用户")].iloc[0]
    winback = summary.loc[summary.rfm_segment.eq("重要挽留用户")].iloc[0]
    general = summary.loc[summary.rfm_segment.eq("一般用户")].iloc[0]

    report = f"""# RFM 用户价值分析报告

## 1. 分析目标

以固定观察截止日为基准，建立一行一个 `customer_unique_id` 的 RFM 明细，严格执行同值同分和五类互斥规则，量化各层级的用户、订单、GMV、消费和复购差异，并向 Member 3 提供可直接使用的用户分层文件。

## 2. 数据来源与统一口径

- 公共层：`customer_order_base`，一行一个 delivered 订单；`order_gmv` 已聚合到订单级。
- 观察截止日：`{OBSERVATION_DATE}`；最后一笔纳入订单时间不晚于该日期。
- RFM 范围：{len(detail):,} 名用户、{int(detail.frequency.sum()):,} 个有效订单、{detail.monetary.sum():,.2f} BRL。
- 用户标识：`customer_unique_id`；Monetary 为截止日内 `SUM(order_gmv)`。
- 复购：`frequency >= 2`；整体复购用户 {int(detail.is_repeat_customer.sum()):,} 人，复购率 {overall_repeat_rate:.2%}。
- 地域：截止日前最近 delivered 订单地址，时间相同按 `order_id DESC`、`customer_id DESC` 稳定选择。

`customer_profile` 的全期指标包含 2018-08，不能直接用于本次 2018-07-31 截止口径；本分析从订单级公共层按截止日重新汇总，没有重新连接原始支付或商品明细。

## 3. RFM 计算与评分方法

- Recency：截止日距离最近购买日期的天数，范围 {int(detail.recency_days.min())}—{int(detail.recency_days.max())} 天。
- Frequency：累计 delivered 订单数，范围 {int(detail.frequency.min())}—{int(detail.frequency.max())}。
- Monetary：累计订单级支付金额，范围 {detail.monetary.min():.2f}—{detail.monetary.max():,.2f} BRL。
- R 分位边界：P20={r['P20']:.0f}、P40={r['P40']:.0f}、P60={r['P60']:.0f}、P80={r['P80']:.0f} 天；越近分数越高。
- M 分位边界：P20={m['P20']:.2f}、P40={m['P40']:.2f}、P60={m['P60']:.2f}、P80={m['P80']:.2f} BRL；金额越高分数越高。
- R/M 使用经验最近秩分位点并保持同值同分。F 只对不同取值执行五档划分。

### Frequency 与 F 分数映射

| Frequency | F 分数 |
|---:|---:|
{frequency_rows}

## 4. 五类用户分类规则

| 顺序 | 类别 | 规则 |
|---:|---|---|
| 1 | 重要价值用户 | R>=4、F>=4、M>=4 |
| 2 | 重要发展用户 | R>=4、F<=3、M>=4 |
| 3 | 重要保持用户 | R<=3、F>=4、M>=4 |
| 4 | 重要挽留用户 | R<=3、F<=3、M>=4 |
| 5 | 一般用户 | M<=3，不论R/F |

规则依次判断，验证确认每名用户有且只有一个层级。

## 5. 各层级价值贡献

| 用户层级 | 用户数 | 用户占比 | 有效订单数 | GMV（BRL） | GMV占比 | 人均消费 | 客单价 | 复购率 | 平均Recency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{segment_rows}

![用户分布](../../visualizations/customer/rfm/rfm_segment_user_distribution.png)

![GMV贡献](../../visualizations/customer/rfm/rfm_segment_gmv_contribution.png)

![用户与GMV占比](../../visualizations/customer/rfm/rfm_user_vs_gmv_share.png)

![人均消费](../../visualizations/customer/rfm/rfm_spend_per_user.png)

![复购率](../../visualizations/customer/rfm/rfm_repeat_purchase_rate.png)

## 6. 关键业务发现

1. **数据事实：** 重要挽留用户占 {winback.user_share:.2%}，贡献 {winback.gmv_share:.2%} GMV，是五类中 GMV 贡献最高的层级；其平均 Recency 为 {winback.average_recency:.2f} 天、人均消费 {winback.spend_per_user:.2f} BRL。**基于数据的解释：** 该层级历史价值较高但最近购买较远，是优先验证召回策略的人群。
2. **数据事实：** 重要发展用户占 {develop.user_share:.2%}，贡献 {develop.gmv_share:.2%} GMV，人均消费 {develop.spend_per_user:.2f} BRL、复购率 {develop.repeat_purchase_rate:.2%}。**基于数据的解释：** 其近期性和金额较高但 F 较低，可作为第二次购买促进实验的候选人群。
3. **数据事实：** 一般用户占 {general.user_share:.2%}，GMV贡献 {general.gmv_share:.2%}，人均消费 {general.spend_per_user:.2f} BRL、复购率 {general.repeat_purchase_rate:.2%}。该层级规模大但单用户历史价值较低。
4. **数据事实：** 重要价值用户仅 {int(value.user_count)} 人，重要保持用户仅 {int(keep.user_count)} 人。原因是 F>=4 仅覆盖 frequency 7、9、12；不是数据缺失，也没有为了扩大高价值样本而改变评分规则。
5. **关联描述：** 高 M 层级的人均消费显著高于一般用户，但 RFM 本身不能证明营销、地区或品类导致了这些差异。

## 7. 可执行运营建议

1. 对重要挽留用户设计分层召回试验，按最近品类和历史金额设置不同触达内容；以增量复购率、净 GMV 和毛利为评估指标，并保留对照组。
2. 对重要发展用户测试首购后限时二购提醒、关联品类推荐或服务提醒；当前分析只支持确定候选人群，不能预判促销必然有效。
3. 对一般用户先按首购金额、品类和物流体验继续拆分，避免对 60% 用户统一补贴；优先验证可识别的高意向子群。
4. 重要价值/保持用户样本仅 4/1 人，建议作为个案核查而非规模化策略依据；后续可对比其他 F 评分方案做敏感性分析，但必须保留本版规则作为基准。

## 8. 口径差异与限制

- 项目正式 AOV 口径为 GMV / 正支付 delivered 订单数，报告和 `average_order_value` 沿用正式口径；附件给出的 GMV / 全部有效订单数另存为 `gmv_per_valid_order`。截止日前仅 1 个有效订单无正支付。
- 观察期开始前历史不可见，Frequency 和首次购买日期可能被低估；截止日后交易被主动排除。
- F 的不同取值只有 9 个且极度集中，导致 F 高分样本很少；不应将 4—5 个用户外推为稳定群体画像。
- R/M 分位档保持同值同分，因此档位人数允许不完全均匀。
- 数据没有成本、利润、营销触达和实验结果，运营建议均需实验验证，不能作因果结论。
- 项目未找到附件提及的 `阶段三分工.md`；本次按附件中完整 Member 1 要求实施。

## 9. 验证结果与交付

- 严格验证共 {validation_count} 项，全部通过；包括唯一性、无空值、同值同分、互斥分类、订单/GMV/复购对账、固定截止日和未来订单排除。
- Member 3 应直接使用 `outputs/data/03_customer_analysis/rfm_customer_detail.csv`。
- 完整规则见 `docs/rfm_scoring_rules.md`，验证明细见 `outputs/data/03_customer_analysis/rfm_validation.csv`。

---

生成说明：CSV 使用 UTF-8 BOM；金额至少保留两位小数；图表从最终汇总 CSV 重新读取后生成，采用 `{font_name}` 字体与 300 DPI PNG。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def verify_outputs() -> None:
    expected = list(CSV_PATHS.values()) + list(FIGURE_PATHS.values()) + [RULES_PATH, REPORT_PATH]
    missing = [path for path in expected if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing or empty RFM outputs: " + ", ".join(map(str, missing)))

    validation = pd.read_csv(CSV_PATHS["validation"], encoding="utf-8-sig")
    if not validation["status"].eq("PASS").all():
        raise RuntimeError("Saved RFM validation CSV contains failures")

    saved_detail = pd.read_csv(CSV_PATHS["detail"], encoding="utf-8-sig")
    if not saved_detail.customer_unique_id.is_unique:
        raise RuntimeError("Saved RFM detail contains duplicate customers")
    if set(saved_detail.rfm_segment) - set(SEGMENT_ORDER):
        raise RuntimeError("Saved RFM detail contains invalid segment labels")

    for path in FIGURE_PATHS.values():
        image = plt.imread(path)
        if image.size == 0 or image.ndim not in (2, 3):
            raise RuntimeError(f"Generated RFM PNG cannot be read: {path}")


def main() -> None:
    args = parse_args()
    database_path = resolve_database(args.database)
    prepare_database(database_path)
    data = load_data(database_path)
    records = validate_all(data, database_path)
    export_data(data)
    save_validation(records)
    font_name = configure_plotting()
    create_figures()
    generate_rules(data)
    generate_report(data, font_name)
    verify_outputs()

    detail = data["detail"]
    summary = data["summary"].sort_values("rfm_segment_order")
    print("Stage 3 Member 1 RFM analysis completed and validated.")
    print(f"Observation date: {OBSERVATION_DATE}")
    print(f"Unique customers: {len(detail):,}")
    print(f"Delivered orders: {int(detail.frequency.sum()):,}")
    print(f"GMV: {detail.monetary.sum():,.2f} BRL")
    print(f"Repeat purchase rate: {detail.is_repeat_customer.sum() / len(detail):.4%}")
    print(f"Validation checks passed: {len(records)}/{len(records)}")
    print("Segments:")
    for row in summary.itertuples():
        print(
            f"- {row.rfm_segment}: {int(row.user_count):,} users "
            f"({row.user_share:.2%}), {row.gmv:,.2f} BRL ({row.gmv_share:.2%})"
        )
    print("Outputs:")
    for path in list(CSV_PATHS.values()) + list(FIGURE_PATHS.values()) + [RULES_PATH, REPORT_PATH]:
        print(f"- {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
