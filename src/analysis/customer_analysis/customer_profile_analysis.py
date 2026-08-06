"""Build, export, visualize, and validate Stage 3 customer analysis outputs.

Run from the project root:
    python src/analysis/customer_analysis/customer_profile_analysis.py

All paths are derived from this file's location. The script recreates the
Stage 3 SQLite common tables/views, exports UTF-8 BOM CSV files, reloads those
final CSV files for charting, writes the customer report, and fails fast if any
reconciliation check does not pass.
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


DEFAULT_DATABASE = PROJECT_ROOT / "database" / "brazil_ecommerce.db"
COMMON_SQL = PROJECT_ROOT / "sql" / "05_customer_analysis" / "00_customer_common_views.sql"
ANALYSIS_SQL = PROJECT_ROOT / "sql" / "05_customer_analysis" / "01_customer_profile_analysis.sql"
DATA_DIR = PROJECT_ROOT / "outputs" / "data" / "03_customer_analysis"
FIGURE_DIR = PROJECT_ROOT / "visualizations" / "customer"
REPORT_PATH = PROJECT_ROOT / "reports" / "customer" / "customer_analysis_report.md"

CSV_PATHS = {
    "orders": DATA_DIR / "customer_order_base.csv",
    "customers": DATA_DIR / "customer_profile.csv",
    "states": DATA_DIR / "state_customer_profile.csv",
    "cities": DATA_DIR / "city_customer_profile.csv",
    "hours": DATA_DIR / "hourly_customer_behavior.csv",
    "weekdays": DATA_DIR / "weekday_customer_behavior.csv",
    "day_types": DATA_DIR / "day_type_customer_behavior.csv",
    "growth_periods": DATA_DIR / "growth_periods.csv",
    "potential": DATA_DIR / "potential_regional_markets.csv",
    "validation": DATA_DIR / "customer_analysis_validation.csv",
}

FIGURE_PATHS = {
    "states": FIGURE_DIR / "state_users_gmv_contribution.png",
    "cities": FIGURE_DIR / "top10_city_users.png",
    "hours": FIGURE_DIR / "hourly_consumption_distribution.png",
    "weekdays": FIGURE_DIR / "weekday_consumption_distribution.png",
    "potential": FIGURE_DIR / "regional_market_potential.png",
}

BLUE = "#2A7FB8"
GREEN = "#3A8F75"
ORANGE = "#D77A32"
PURPLE = "#7567A8"
RED = "#C94C4C"
GRID = "#D9D9D9"


QUERY_MAP = {
    "orders": """
        SELECT * FROM customer_order_base
        ORDER BY order_purchase_timestamp, order_id
    """,
    "customers": """
        SELECT * FROM customer_profile
        ORDER BY customer_unique_id
    """,
    "states": """
        SELECT * FROM customer_state_profile
        ORDER BY user_rank, customer_state
    """,
    "cities": """
        SELECT * FROM customer_city_profile
        ORDER BY user_rank, customer_state, customer_city
    """,
    "hours": """
        SELECT * FROM customer_hourly_behavior
        ORDER BY hour
    """,
    "weekdays": """
        SELECT * FROM customer_weekday_behavior
        ORDER BY weekday_number
    """,
    "day_types": """
        SELECT * FROM customer_day_type_behavior
        ORDER BY day_type_order
    """,
    "growth_periods": "SELECT * FROM customer_growth_periods",
    "potential": """
        SELECT * FROM potential_regional_market_base
        ORDER BY recent_unique_users DESC, customer_state
    """,
}


@dataclass
class ValidationRecord:
    check_id: str
    check_name: str
    status: str
    actual: str
    expected: str
    tolerance: str
    details: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="SQLite database path; relative paths are resolved from project root.",
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
            "grid.color": GRID,
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
            f"Database not found: {database_path}. Run "
            "`python src/data_processing/build_sqlite_database.py` first."
        )
    for path in (COMMON_SQL, ANALYSIS_SQL):
        if not path.exists():
            raise FileNotFoundError(f"Required SQL file not found: {path}")

    with sqlite3.connect(database_path) as connection:
        required_clean_views = {
            "vw_orders_clean",
            "vw_order_payments_clean",
        }
        existing = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'view'"
            )
        }
        missing = required_clean_views - existing
        if missing:
            raise RuntimeError(
                "Cleaning views are missing: "
                + ", ".join(sorted(missing))
                + ". Run sql/02_data_cleaning/data_cleaning_rules.sql first."
            )
        connection.executescript(COMMON_SQL.read_text(encoding="utf-8-sig"))
        connection.executescript(ANALYSIS_SQL.read_text(encoding="utf-8-sig"))


def load_data(database_path: Path) -> dict[str, pd.DataFrame]:
    with sqlite3.connect(database_path) as connection:
        return {
            name: pd.read_sql_query(query, connection)
            for name, query in QUERY_MAP.items()
        }


def classify_potential_markets(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    positive_prior = result.loc[result["prior_unique_users"] > 0, "prior_unique_users"]
    positive_recent = result.loc[result["recent_unique_users"] > 0, "recent_unique_users"]
    prior_sample_threshold = int(np.ceil(positive_prior.quantile(0.25)))
    recent_sample_threshold = int(np.ceil(positive_recent.quantile(0.25)))

    result["sample_prior_user_threshold"] = prior_sample_threshold
    result["sample_recent_user_threshold"] = recent_sample_threshold
    result["is_sample_eligible"] = (
        (result["prior_unique_users"] >= prior_sample_threshold)
        & (result["recent_unique_users"] >= recent_sample_threshold)
    )

    eligible = result.loc[result["is_sample_eligible"]].copy()
    scale_q25 = float(eligible["recent_unique_users"].quantile(0.25))
    scale_median = float(eligible["recent_unique_users"].median())
    scale_q75 = float(eligible["recent_unique_users"].quantile(0.75))
    spend_median = float(eligible["recent_spend_per_user"].median())
    spend_q75 = float(eligible["recent_spend_per_user"].quantile(0.75))
    share_median = float(eligible["recent_user_share"].median())
    user_growth_median = float(eligible["user_growth_rate"].median())
    gmv_growth_median = float(eligible["gmv_growth_rate"].median())

    result["eligible_recent_users_q25"] = scale_q25
    result["eligible_recent_users_median"] = scale_median
    result["eligible_recent_users_q75"] = scale_q75
    result["eligible_spend_per_user_median"] = spend_median
    result["eligible_spend_per_user_q75"] = spend_q75
    result["eligible_user_share_median"] = share_median
    result["eligible_user_growth_median"] = user_growth_median
    result["eligible_gmv_growth_median"] = gmv_growth_median
    result["growth_strength"] = (
        result["user_growth_rate"] + result["gmv_growth_rate"]
    ) / 2.0

    eligible_mask = result["is_sample_eligible"]
    result["is_large_scale_low_spend"] = (
        eligible_mask
        & (result["recent_unique_users"] >= scale_median)
        & (result["recent_spend_per_user"] < spend_median)
    )
    result["is_medium_scale_fast_growth"] = (
        eligible_mask
        & (result["recent_unique_users"] >= scale_q25)
        & (result["recent_unique_users"] < scale_q75)
        & (result["user_growth_rate"] >= user_growth_median)
        & (result["gmv_growth_rate"] >= gmv_growth_median)
    )
    result["is_high_spend_low_penetration"] = (
        eligible_mask
        & (result["recent_spend_per_user"] >= spend_q75)
        & (result["recent_user_share"] < share_median)
    )

    def labels(row: pd.Series) -> str:
        if not row["is_sample_eligible"]:
            return "样本不足（不做潜力判断）"
        categories = []
        if row["is_large_scale_low_spend"]:
            categories.append("规模较大但人均消费较低")
        if row["is_medium_scale_fast_growth"]:
            categories.append("当前规模中等但增长较快")
        if row["is_high_spend_low_penetration"]:
            categories.append("人均消费较高但渗透规模较小")
        return "；".join(categories) if categories else "未命中重点类型"

    result["potential_market_type"] = result.apply(labels, axis=1)
    result["recent_user_rank"] = result["recent_unique_users"].rank(
        method="min", ascending=False
    ).astype(int)
    result["recent_gmv_rank"] = result["recent_gmv"].rank(
        method="min", ascending=False
    ).astype(int)
    result["user_growth_rank"] = result["user_growth_rate"].rank(
        method="min", ascending=False, na_option="bottom"
    ).astype(int)
    result["gmv_growth_rank"] = result["gmv_growth_rate"].rank(
        method="min", ascending=False, na_option="bottom"
    ).astype(int)
    return result.sort_values(
        ["is_sample_eligible", "recent_unique_users", "customer_state"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def rounded_copy(name: str, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    money_columns = [
        column
        for column in result.columns
        if column in {
            "order_gmv",
            "lifetime_gmv",
            "gmv",
            "prior_gmv",
            "recent_gmv",
        }
    ]
    for column in money_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").round(2)

    metric_columns = [
        column
        for column in result.columns
        if column in {
            "average_order_value",
            "spend_per_user",
            "recent_spend_per_user",
            "customer_lifecycle_days",
            "average_daily_orders",
            "eligible_recent_users_q25",
            "eligible_recent_users_median",
            "eligible_recent_users_q75",
            "eligible_spend_per_user_median",
            "eligible_spend_per_user_q75",
        }
    ]
    for column in metric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").round(6)

    rate_columns = [
        column
        for column in result.columns
        if column.endswith("_share")
        or column.endswith("_rate")
        or column in {
            "growth_strength",
            "eligible_user_share_median",
            "eligible_user_growth_median",
            "eligible_gmv_growth_median",
        }
    ]
    for column in rate_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").round(8)

    bool_columns = result.select_dtypes(include="bool").columns
    for column in bool_columns:
        result[column] = result[column].astype(int)
    return result


def export_data(data: dict[str, pd.DataFrame]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in CSV_PATHS.items():
        if name == "validation":
            continue
        rounded_copy(name, data[name]).to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )


def add_check(
    records: list[ValidationRecord],
    check_id: str,
    name: str,
    passed: bool,
    actual: object,
    expected: object,
    tolerance: object = "exact",
    details: str = "",
) -> None:
    records.append(
        ValidationRecord(
            check_id=check_id,
            check_name=name,
            status="PASS" if passed else "FAIL",
            actual=str(actual),
            expected=str(expected),
            tolerance=str(tolerance),
            details=details,
        )
    )


def month_sequence(start: str, end: str) -> list[str]:
    start_period = pd.Period(start, freq="M")
    end_period = pd.Period(end, freq="M")
    return [str(period) for period in pd.period_range(start_period, end_period, freq="M")]


def validate_all(
    data: dict[str, pd.DataFrame], database_path: Path
) -> list[ValidationRecord]:
    orders = data["orders"]
    customers = data["customers"]
    states = data["states"]
    cities = data["cities"]
    hours = data["hours"]
    weekdays = data["weekdays"]
    day_types = data["day_types"]
    periods = data["growth_periods"].iloc[0]

    total_orders = len(orders)
    total_users = len(customers)
    total_gmv = float(orders["order_gmv"].sum())
    tolerance = 0.01
    records: list[ValidationRecord] = []

    add_check(
        records,
        "V01",
        "customer_profile 的 customer_unique_id 唯一",
        customers["customer_unique_id"].nunique(dropna=False) == total_users,
        customers["customer_unique_id"].nunique(dropna=False),
        total_users,
    )
    blank_users = int(
        customers["customer_unique_id"].isna().sum()
        + customers["customer_unique_id"].fillna("").astype(str).str.strip().eq("").sum()
    )
    add_check(
        records,
        "V02",
        "customer_profile 无空 customer_unique_id",
        blank_users == 0,
        blank_users,
        0,
    )
    add_check(
        records,
        "V03",
        "customer_order_base 的 order_id 唯一",
        orders["order_id"].nunique(dropna=False) == total_orders,
        orders["order_id"].nunique(dropna=False),
        total_orders,
    )
    customer_gmv = float(customers["lifetime_gmv"].sum())
    add_check(
        records,
        "V04",
        "用户累计 GMV 与订单级 GMV 一致",
        abs(customer_gmv - total_gmv) <= tolerance,
        f"{customer_gmv:.2f}",
        f"{total_gmv:.2f}",
        tolerance,
    )
    add_check(
        records,
        "V05",
        "州级用户数合计与用户公共表一致",
        int(states["unique_user_count"].sum()) == total_users,
        int(states["unique_user_count"].sum()),
        total_users,
    )
    add_check(
        records,
        "V06",
        "州级 GMV 合计与总 GMV 一致",
        abs(float(states["gmv"].sum()) - total_gmv) <= tolerance,
        f"{states['gmv'].sum():.2f}",
        f"{total_gmv:.2f}",
        tolerance,
    )
    city_ok = (
        int(cities["unique_user_count"].sum()) == total_users
        and abs(float(cities["gmv"].sum()) - total_gmv) <= tolerance
    )
    add_check(
        records,
        "V07",
        "城市级用户数和 GMV 与总体对账",
        city_ok,
        f"users={int(cities['unique_user_count'].sum())}; gmv={cities['gmv'].sum():.2f}",
        f"users={total_users}; gmv={total_gmv:.2f}",
        tolerance,
    )

    for check_id, name, frame in [
        ("V08", "24 小时订单数和 GMV 与总体对账", hours),
        ("V09", "星期分布订单数和 GMV 与总体对账", weekdays),
        ("V10", "工作日/周末订单数和 GMV 与总体对账", day_types),
    ]:
        passed = (
            int(frame["valid_order_count"].sum()) == total_orders
            and abs(float(frame["gmv"].sum()) - total_gmv) <= tolerance
        )
        add_check(
            records,
            check_id,
            name,
            passed,
            f"orders={int(frame['valid_order_count'].sum())}; gmv={frame['gmv'].sum():.2f}",
            f"orders={total_orders}; gmv={total_gmv:.2f}",
            tolerance,
        )

    share_checks = []
    for frame_name, frame in [
        ("state", states),
        ("city", cities),
        ("hour", hours),
        ("weekday", weekdays),
        ("day_type", day_types),
    ]:
        user_or_order_share = "user_share" if "user_share" in frame.columns else "order_share"
        share_checks.append(
            f"{frame_name}:{user_or_order_share}={frame[user_or_order_share].sum():.8f},"
            f"gmv_share={frame['gmv_share'].sum():.8f}"
        )
    shares_ok = all(
        abs(float(frame[column].sum()) - 1.0) <= 1e-8
        for frame in (states, cities, hours, weekdays, day_types)
        for column in (["user_share", "gmv_share"] if "user_share" in frame else ["order_share", "gmv_share"])
    )
    add_check(
        records,
        "V11",
        "州/城市/时段占比合计为 1",
        shares_ok,
        " | ".join(share_checks),
        "each share sum = 1",
        "1e-8",
    )

    with sqlite3.connect(database_path) as connection:
        payment_audit = connection.execute(
            """
            WITH payment_by_order AS (
                SELECT order_id, COUNT(*) AS payment_rows, SUM(payment_value) AS amount
                FROM vw_order_payments_clean
                WHERE payment_value > 0
                GROUP BY order_id
                HAVING SUM(payment_value) > 0
            )
            SELECT
                COUNT(*) AS paid_delivered_orders,
                SUM(payment_rows > 1) AS multi_payment_orders,
                SUM(amount) AS official_gmv
            FROM payment_by_order AS p
            INNER JOIN vw_orders_clean AS o ON o.order_id = p.order_id
            WHERE o.order_status = 'delivered'
            """
        ).fetchone()
        raw_bounds = connection.execute(
            """
            SELECT
                STRFTIME('%Y-%m', MIN(order_purchase_timestamp)),
                STRFTIME('%Y-%m', MAX(order_purchase_timestamp))
            FROM customer_order_base
            """
        ).fetchone()

    paid_orders = int(orders["is_paid_order"].sum())
    payment_ok = (
        paid_orders == int(payment_audit[0])
        and abs(total_gmv - float(payment_audit[2])) <= tolerance
    )
    add_check(
        records,
        "V12",
        "支付先聚合到订单级且无 GMV 重复",
        payment_ok,
        f"paid_orders={paid_orders}; gmv={total_gmv:.2f}",
        f"paid_orders={payment_audit[0]}; gmv={payment_audit[2]:.2f}",
        tolerance,
        f"检测到 {int(payment_audit[1]):,} 个多支付记录订单，均先聚合后连接。",
    )

    prior_months = month_sequence(periods["prior_start_month"], periods["prior_end_month"])
    recent_months = month_sequence(periods["recent_start_month"], periods["recent_end_month"])
    selected_months = prior_months + recent_months
    period_ok = (
        int(periods["prior_month_count"]) == 6
        and int(periods["recent_month_count"]) == 6
        and len(selected_months) == 12
        and len(set(selected_months)) == 12
        and raw_bounds[0] not in selected_months
        and raw_bounds[1] not in selected_months
        and selected_months == month_sequence(selected_months[0], selected_months[-1])
    )
    add_check(
        records,
        "V13",
        "增长周期为连续、可比的 6+6 个完整月份",
        period_ok,
        f"prior={periods['prior_start_month']}..{periods['prior_end_month']}; "
        f"recent={periods['recent_start_month']}..{periods['recent_end_month']}",
        "6 consecutive prior + 6 consecutive recent; global boundary months excluded",
        "exact",
        f"全局边界月 {raw_bounds[0]}、{raw_bounds[1]} 未纳入。",
    )

    structure_ok = all(path.exists() for path in (COMMON_SQL, ANALYSIS_SQL, database_path))
    add_check(
        records,
        "V14",
        "根目录运行所需 SQL、数据库与相对路径完整",
        structure_ok,
        structure_ok,
        True,
        "exact",
        "脚本路径由 __file__ 定位项目根目录，不依赖本机绝对路径。",
    )

    failures = [record for record in records if record.status != "PASS"]
    if failures:
        messages = "; ".join(f"{item.check_id} {item.check_name}" for item in failures)
        raise AssertionError(f"Customer analysis validation failed: {messages}")
    return records


def save_validation(records: list[ValidationRecord]) -> None:
    frame = pd.DataFrame([asdict(record) for record in records])
    frame.to_csv(CSV_PATHS["validation"], index=False, encoding="utf-8-sig")


def read_chart_data() -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(path, encoding="utf-8-sig")
        for name, path in CSV_PATHS.items()
        if name not in {"orders", "customers", "validation"}
    }


def finish_axis(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.grid(False)
    ax.grid(True, axis=grid_axis, color=GRID, alpha=0.55, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)


def plot_state_contribution(data: pd.DataFrame) -> None:
    ordered = data.sort_values(["unique_user_count", "customer_state"], ascending=[True, True])
    fig, axes = plt.subplots(1, 2, figsize=(15, 11), layout="constrained")

    axes[0].barh(ordered["customer_state"], ordered["unique_user_count"], color=BLUE)
    axes[0].set_title("各州唯一用户数")
    axes[0].set_xlabel("唯一用户数（人）")
    axes[0].set_ylabel("州代码")
    axes[0].xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    finish_axis(axes[0], "x")

    axes[1].barh(ordered["customer_state"], ordered["gmv"] / 1_000_000, color=GREEN)
    axes[1].set_title("各州 GMV 贡献")
    axes[1].set_xlabel("GMV（百万 BRL）")
    axes[1].set_ylabel("")
    finish_axis(axes[1], "x")

    for ax, column, divisor in [
        (axes[0], "user_share", 1),
        (axes[1], "gmv_share", 1),
    ]:
        for index, (_, row) in enumerate(ordered.iterrows()):
            if row[column] >= 0.02:
                value = row["unique_user_count"] if ax is axes[0] else row["gmv"] / 1_000_000
                ax.text(value, index, f"  {row[column]:.1%}", va="center", fontsize=8)

    fig.suptitle("巴西电商各州用户与 GMV 贡献", fontsize=18, fontweight="bold")
    fig.text(
        0.5,
        -0.01,
        "用户与其完整历史订单按最近一次 delivered 订单地址归属；金额单位：BRL。",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    fig.savefig(FIGURE_PATHS["states"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def plot_top_cities(data: pd.DataFrame) -> None:
    top = data.sort_values(
        ["unique_user_count", "customer_state", "customer_city"],
        ascending=[False, True, True],
    ).head(10).sort_values("unique_user_count")
    labels = top["customer_city"].str.title() + " / " + top["customer_state"]
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    bars = ax.barh(labels, top["unique_user_count"], color=BLUE)
    ax.bar_label(
        bars,
        labels=[f"{int(v):,} ({s:.1%})" for v, s in zip(top["unique_user_count"], top["user_share"])],
        padding=5,
        fontsize=9,
    )
    ax.set_title("Top 10 城市唯一用户分布（城市 + 州联合识别）", fontsize=16)
    ax.set_xlabel("唯一用户数（人）")
    ax.set_ylabel("城市 / 州")
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    finish_axis(ax, "x")
    fig.savefig(FIGURE_PATHS["cities"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def plot_hours(data: pd.DataFrame) -> None:
    data = data.sort_values("hour")
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True, layout="constrained")
    axes[0].plot(data["hour"], data["valid_order_count"], color=BLUE, marker="o", linewidth=2)
    axes[0].fill_between(data["hour"], data["valid_order_count"], color=BLUE, alpha=0.12)
    axes[0].set_title("24 小时有效订单分布")
    axes[0].set_ylabel("有效订单数（单）")
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    finish_axis(axes[0], "y")

    axes[1].plot(data["hour"], data["gmv"] / 1_000, color=GREEN, marker="o", linewidth=2)
    axes[1].fill_between(data["hour"], data["gmv"] / 1_000, color=GREEN, alpha=0.12)
    axes[1].set_title("24 小时 GMV 分布")
    axes[1].set_ylabel("GMV（千 BRL）")
    axes[1].set_xlabel("购买小时（0—23 时）")
    axes[1].set_xticks(range(24))
    finish_axis(axes[1], "y")
    fig.suptitle("用户消费时段分布", fontsize=18, fontweight="bold")
    fig.savefig(FIGURE_PATHS["hours"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def plot_weekdays(data: pd.DataFrame) -> None:
    data = data.sort_values("weekday_number")
    labels = data["weekday_name"].str[:3]
    x = np.arange(len(data))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), layout="constrained")
    bars_orders = axes[0].bar(x, data["valid_order_count"], color=BLUE)
    axes[0].bar_label(bars_orders, labels=[f"{v:,.0f}" for v in data["valid_order_count"]], padding=3, fontsize=8)
    axes[0].set_title("星期有效订单分布")
    axes[0].set_ylabel("有效订单数（单）")
    axes[0].set_xticks(x, labels)
    finish_axis(axes[0], "y")

    bars_gmv = axes[1].bar(x, data["gmv"] / 1_000_000, color=GREEN)
    axes[1].bar_label(bars_gmv, labels=[f"{v:.2f}" for v in data["gmv"] / 1_000_000], padding=3, fontsize=8)
    axes[1].set_title("星期 GMV 分布")
    axes[1].set_ylabel("GMV（百万 BRL）")
    axes[1].set_xticks(x, labels)
    finish_axis(axes[1], "y")
    fig.suptitle("Monday—Sunday 消费分布", fontsize=18, fontweight="bold")
    fig.savefig(FIGURE_PATHS["weekdays"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def plot_potential(data: pd.DataFrame) -> None:
    eligible = data.loc[data["is_sample_eligible"].eq(1)].copy()
    sizes = 70 + 930 * np.sqrt(eligible["recent_gmv"] / eligible["recent_gmv"].max())
    fig, ax = plt.subplots(figsize=(13, 8), layout="constrained")
    scatter = ax.scatter(
        eligible["recent_unique_users"],
        eligible["recent_spend_per_user"],
        s=sizes,
        c=eligible["growth_strength"],
        cmap="RdYlGn",
        alpha=0.78,
        edgecolor="white",
        linewidth=0.9,
    )
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlabel("最近 6 个完整月份唯一用户数（对数刻度）")
    ax.set_ylabel("最近 6 个完整月份人均消费（BRL/人）")
    ax.set_title("潜力区域市场：规模—消费—增长矩阵", fontsize=17)
    finish_axis(ax, "both")
    colorbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    colorbar.set_label("用户增长率与 GMV 增长率均值")
    colorbar.ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))

    label_mask = (
        eligible["customer_state"].isin(["SP", "RJ", "MG"])
        | eligible["is_medium_scale_fast_growth"].eq(1)
        | eligible["is_high_spend_low_penetration"].eq(1)
    )
    label_offsets = {
        "SP": (8, 5),
        "RJ": (8, 14),
        "MG": (-18, -18),
        "DF": (8, -14),
        "ES": (-20, -16),
        "BA": (8, 8),
        "MS": (8, 8),
    }
    for _, row in eligible.loc[label_mask].iterrows():
        ax.annotate(
            row["customer_state"],
            (row["recent_unique_users"], row["recent_spend_per_user"]),
            xytext=label_offsets.get(row["customer_state"], (6, 6)),
            textcoords="offset points",
            fontsize=9,
        )
    ax.text(
        0.01,
        0.01,
        "横轴=用户规模；纵轴=人均消费；点大小=最近期 GMV；颜色=两项增长率均值。\n"
        "仅展示前后期用户数均达到分布 P25 门槛的州；增长为相关性描述，不代表因果。",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    fig.savefig(FIGURE_PATHS["potential"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def create_figures() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    chart_data = read_chart_data()
    plot_state_contribution(chart_data["states"])
    plot_top_cities(chart_data["cities"])
    plot_hours(chart_data["hours"])
    plot_weekdays(chart_data["weekdays"])
    plot_potential(chart_data["potential"])


def join_states(frame: pd.DataFrame, flag: str) -> str:
    selected = frame.loc[frame[flag].eq(True)].sort_values(
        ["recent_unique_users", "customer_state"], ascending=[False, True]
    )
    if selected.empty:
        return "无"
    return "、".join(
        f"{row.customer_state}（{int(row.recent_unique_users):,} 人，"
        f"人均 {row.recent_spend_per_user:.2f} BRL，"
        f"用户/GMV 增长 {row.user_growth_rate:.1%}/{row.gmv_growth_rate:.1%}）"
        for row in selected.itertuples()
    )


def generate_report(data: dict[str, pd.DataFrame], font_name: str) -> None:
    orders = data["orders"]
    customers = data["customers"]
    states = data["states"].sort_values("user_rank")
    cities = data["cities"].sort_values("user_rank")
    hours = data["hours"].sort_values("hour")
    weekdays = data["weekdays"].sort_values("weekday_number")
    day_types = data["day_types"].sort_values("day_type_order")
    potential = data["potential"]
    periods = data["growth_periods"].iloc[0]

    top_states = states.head(5)
    sp = states.loc[states["customer_state"].eq("SP")].iloc[0]
    rj = states.loc[states["customer_state"].eq("RJ")].iloc[0]
    mg = states.loc[states["customer_state"].eq("MG")].iloc[0]
    sao_paulo = cities.loc[
        cities["customer_state"].eq("SP") & cities["customer_city"].eq("sao paulo")
    ].iloc[0]
    rio = cities.loc[
        cities["customer_state"].eq("RJ") & cities["customer_city"].eq("rio de janeiro")
    ].iloc[0]
    peak_hour_orders = hours.loc[hours["valid_order_count"].idxmax()]
    peak_hour_gmv = hours.loc[hours["gmv"].idxmax()]
    peak_weekday_orders = weekdays.loc[weekdays["valid_order_count"].idxmax()]
    weekday_row = day_types.loc[day_types["day_type"].eq("Weekday")].iloc[0]
    weekend_row = day_types.loc[day_types["day_type"].eq("Weekend")].iloc[0]
    daily_ratio = weekend_row["average_daily_orders"] / weekday_row["average_daily_orders"]
    eligible = potential.loc[potential["is_sample_eligible"]]
    ineligible = potential.loc[~potential["is_sample_eligible"]]

    state_rows = "\n".join(
        f"| {row.customer_state} | {int(row.unique_user_count):,} | {row.user_share:.2%} | "
        f"{row.gmv:,.2f} | {row.gmv_share:.2%} | {row.spend_per_user:.2f} |"
        for row in top_states.itertuples()
    )
    city_rows = "\n".join(
        f"| {row.customer_city.title()} / {row.customer_state} | {int(row.unique_user_count):,} | "
        f"{row.user_share:.2%} | {row.gmv:,.2f} | {row.gmv_share:.2%} |"
        for row in cities.head(10).itertuples()
    )

    report = f"""# 用户画像与行为分析报告（阶段三 Member 1）

## 1. 分析目标

建立可供 Member 2、Member 3 复用的订单级与用户级公共数据层，刻画用户地域、购买时段和区域市场差异，并用透明的规模—消费—增长规则识别“潜力区域市场”。本报告不使用“下沉市场”标签，因为数据没有城市等级、人口、收入或行政层级字段。

## 2. 数据范围与统一口径

- 数据库：`database/brazil_ecommerce.db`；购买时间覆盖 {orders['order_purchase_timestamp'].min()} 至 {orders['order_purchase_timestamp'].max()}。
- 有效订单：`order_status = 'delivered'`，共 {len(orders):,} 单；其中正支付订单 {int(orders['is_paid_order'].sum()):,} 单。
- 唯一用户：`customer_unique_id`，共 {len(customers):,} 人；不得用 `customer_id` 替代。
- GMV：正 `payment_value` 先按 `order_id` 聚合，再连接 delivered 订单，总计 {orders['order_gmv'].sum():,.2f} BRL。唯一无正支付的 delivered 订单保留在订单数中，`order_gmv` 记 0，但不进入客单价分母。
- 客单价：GMV / 正支付 delivered 订单数；与正式指标字典一致，不使用全部 delivered 订单数作分母。
- 数据边界：2016-09 与 2018-08 为不完整首尾月；增长分析排除这两个边界月。

## 3. 公共表粒度与地域规则

- `customer_order_base`：一行一个 delivered `order_id`，保留订单发生时的用户州、市、购买时间、订单 GMV 和是否正支付。
- `customer_profile`：一行一个 `customer_unique_id`，包含首购、最近购买、有效/支付订单数、累计 GMV、客单价、生命周期天数、活跃购买月数、复购标记和代表地域。
- 代表地域：取用户最近一次 delivered 订单对应的客户地址；若购买时间相同，依次按 `order_id DESC`、`customer_id DESC` 确定，保证结果可重复。
- 州/城市画像把用户完整观察期订单与 GMV归属到该代表地域，因此每名用户只进入一个州和一个“城市 + 州”组合，汇总后可与用户公共表严格对账。增长分析则使用每笔订单当时的地址，以反映两个时期真实发生的区域交易。

## 4. 用户地域分布结果

### 4.1 州级 Top 5

| 州 | 唯一用户数 | 用户占比 | GMV（BRL） | GMV 占比 | 人均消费（BRL/人） |
|---|---:|---:|---:|---:|---:|
{state_rows}

**数据事实：** SP 用户与 GMV 均排名第 1，贡献 {int(sp.unique_user_count):,} 人（{sp.user_share:.2%}）和 {sp.gmv:,.2f} BRL（{sp.gmv_share:.2%}）。RJ、MG 分别位列第 2、3；前三州合计贡献 {(sp.user_share + rj.user_share + mg.user_share):.2%} 用户和 {(sp.gmv_share + rj.gmv_share + mg.gmv_share):.2%} GMV。

**基于数据的解释：** 用户和 GMV 均明显集中在 SP、RJ、MG，核心市场识别来自客观排名，而非事前指定。

![各州用户与 GMV](../../visualizations/customer/state_users_gmv_contribution.png)

### 4.2 城市级 Top 10（城市 + 州）

| 城市 / 州 | 唯一用户数 | 用户占比 | GMV（BRL） | GMV 占比 |
|---|---:|---:|---:|---:|
{city_rows}

São Paulo / SP 贡献 {int(sao_paulo.unique_user_count):,} 人（{sao_paulo.user_share:.2%}）与 {sao_paulo.gmv:,.2f} BRL（{sao_paulo.gmv_share:.2%}）；Rio de Janeiro / RJ 贡献 {int(rio.unique_user_count):,} 人（{rio.user_share:.2%}）与 {rio.gmv:,.2f} BRL（{rio.gmv_share:.2%}）。城市始终与州联合识别，避免跨州同名城市被错误合并。

![Top 10 城市](../../visualizations/customer/top10_city_users.png)

## 5. 消费时段结果

- **数据事实—小时：** 订单峰值为 {int(peak_hour_orders.hour)} 时，共 {int(peak_hour_orders.valid_order_count):,} 单（{peak_hour_orders.order_share:.2%}）；GMV 峰值为 {int(peak_hour_gmv.hour)} 时，共 {peak_hour_gmv.gmv:,.2f} BRL（{peak_hour_gmv.gmv_share:.2%}）。0—23 时均在输出中保留。
- **数据事实—星期：** {peak_weekday_orders.weekday_name} 订单最多，为 {int(peak_weekday_orders.valid_order_count):,} 单（{peak_weekday_orders.order_share:.2%}）。输出按 Monday 至 Sunday 排序，并保留星期序号。
- **数据事实—工作日/周末：** 工作日合计 {int(weekday_row.valid_order_count):,} 单（{weekday_row.order_share:.2%}），周末 {int(weekend_row.valid_order_count):,} 单（{weekend_row.order_share:.2%}）；按观察区间内自然日标准化后，工作日 {weekday_row.average_daily_orders:.2f} 单/日、周末 {weekend_row.average_daily_orders:.2f} 单/日，周末约为工作日的 {daily_ratio:.2%}。
- **基于数据的解释：** 工作日总量优势并非完全来自 5 天对 2 天的天数差异；日均指标仍显示工作日更高。
- **尚未验证的原因假设：** 工作日白天/晚间的使用场景、营销触达节奏或履约承诺可能影响下单时段，但数据没有访问、曝光、活动或用户职业字段，不能验证原因。

![24 小时分布](../../visualizations/customer/hourly_consumption_distribution.png)

![星期分布](../../visualizations/customer/weekday_consumption_distribution.png)

## 6. 核心市场贡献

- SP + RJ 合计贡献 {(sp.user_share + rj.user_share):.2%} 用户、{(sp.gmv_share + rj.gmv_share):.2%} GMV；MG 是数据中实际排名第 3 的市场，贡献 {mg.user_share:.2%} 用户、{mg.gmv_share:.2%} GMV。
- SP 人均消费 {sp.spend_per_user:.2f} BRL/人，低于 RJ 的 {rj.spend_per_user:.2f} 和 MG 的 {mg.spend_per_user:.2f} BRL/人。该差异是观察期关联，不足以说明地区收入、价格或营销导致了差异。

## 7. 潜力区域市场识别方法与结果

增长窗口采用最近 6 个完整月份 {periods['recent_start_month']}—{periods['recent_end_month']}，对比此前 6 个完整月份 {periods['prior_start_month']}—{periods['prior_end_month']}。两期连续且等长，排除了不完整首尾月。

样本门槛完全由数据分布确定：分别取 27 州前期、近期正样本用户数的第 25 百分位并向上取整，即前后期均至少 {int(potential['sample_prior_user_threshold'].iloc[0])} 人与 {int(potential['sample_recent_user_threshold'].iloc[0])} 人；{len(eligible)} 州满足门槛，{len(ineligible)} 州只保留原始指标、不作潜力判断。分母为 0 的增长率保持 `NULL`。本分析不建立主观综合评分，而采用公开阈值的多标签筛选；同一州可以属于多个类型。

- **规模较大但人均消费较低：** {join_states(potential, 'is_large_scale_low_spend')}
- **当前规模中等但增长较快：** {join_states(potential, 'is_medium_scale_fast_growth')}
- **人均消费较高但渗透规模较小：** {join_states(potential, 'is_high_spend_low_penetration')}

其中“规模较大”=合格州近期用户数不低于中位数；“人均消费较低”=低于合格州中位数；“中等规模”=合格州近期用户数 P25—P75；“增长较快”=用户增长率和 GMV 增长率均不低于合格州各自中位数；“人均消费较高”=不低于合格州 P75，且用户占比低于合格州中位数。完整阈值已逐行写入 `potential_regional_markets.csv`。

**数据事实：** RR 的用户/GMV 增长率很高，但前期仅 {int(potential.loc[potential.customer_state.eq('RR'), 'prior_unique_users'].iloc[0])} 人、近期仅 {int(potential.loc[potential.customer_state.eq('RR'), 'recent_unique_users'].iloc[0])} 人，因此被样本门槛排除，避免把小基数波动误报为潜力。

**基于数据的解释：** 中等规模且两项增长均高于合格市场中位数的州适合进入下一轮验证；高人均、低渗透州可能存在扩量空间，但并不等于已证明可增长。

**尚未验证的原因假设：** 地区增长可能与品类偏好、物流改善、营销投放或支付结构有关。现有结果仅反映历史相关性，必须结合成本、利润、人口、触达和实验数据验证，不能作因果结论。

![潜力区域市场](../../visualizations/customer/regional_market_potential.png)

## 8. 业务问题与可验证假设

1. **事实：** 核心市场高度集中，且 SP 人均消费低于 RJ/MG。**假设：** SP 的订单结构或品类组合更偏低客单；可按州比较品类、订单金额带和复购率验证。
2. **事实：** 工作日日均订单高于周末。**假设：** 营销触达或使用场景造成差异；需接入曝光、访问、活动日历并做分时实验验证。
3. **事实：** 部分中等规模市场同时出现用户和 GMV 增长。**假设：** 这些市场具备增量投放效率；需结合 CAC、利润、物流时效和小范围增量实验验证。

## 9. 数据限制

- 数据只有交易成功后的订单、支付和客户地址，没有人口、收入、城市层级、流量、注册、营销成本或利润，因此不能定义“下沉市场”、渗透率或获客效率。
- `customer_unique_id` 的首次购买是观察期内首购，不代表平台注册或历史首次购买；生命周期受左右截尾影响。
- 代表地域采用最近订单地址，会把用户完整历史归到最新地址；适合一人一地画像，但不等同于订单发生时地域。订单级公共层保留原始订单地址供其他分析使用。
- 工作日/周末日均按首末订单日期之间的自然日计算；2016 年早期缺月可能压低整体日均，因此该指标适合相对比较，不宜解释为完整平台运营日均。
- 增长率不等于因果效果；样本门槛只能降低、不能消除小样本波动。

## 10. Member 2、Member 3 使用说明

- 生命周期、留存、RFM 和用户价值分析优先使用数据库表 `customer_profile` 或导出 `outputs/data/03_customer_analysis/customer_profile.csv`。主键为 `customer_unique_id`；关键字段为 `first_purchase_timestamp`、`last_purchase_timestamp`、`valid_order_count`、`paid_order_count`、`lifetime_gmv`、`average_order_value`、`customer_lifecycle_days`、`latest_purchase_month`、`customer_state`、`customer_city`。
- 需要订单序列、消费时段、复购间隔或按订单发生地分析时，使用数据库表 `customer_order_base` 或导出 `customer_order_base.csv`。主键为 `order_id`；`order_gmv` 已按订单聚合，禁止再次直接连接支付明细后求和。
- 若 Member 2/3 需要重新归属地域，应明确与本报告“最近一次有效订单地址”规则的差异，并重新做用户数与 GMV 对账。

---

生成说明：所有 CSV 使用 UTF-8 BOM；图表从最终 CSV 重新读取后生成，采用 `{font_name}` 字体和 300 DPI PNG。验证明细见 `outputs/data/03_customer_analysis/customer_analysis_validation.csv`。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def verify_output_files() -> None:
    expected = list(CSV_PATHS.values()) + list(FIGURE_PATHS.values()) + [REPORT_PATH]
    missing = [path for path in expected if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing or empty outputs: " + ", ".join(map(str, missing)))
    validation = pd.read_csv(CSV_PATHS["validation"], encoding="utf-8-sig")
    if not validation["status"].eq("PASS").all():
        raise RuntimeError("Saved validation CSV contains failed checks")
    for path in FIGURE_PATHS.values():
        image = plt.imread(path)
        if image.size == 0 or image.ndim not in (2, 3):
            raise RuntimeError(f"Generated PNG cannot be read: {path}")


def main() -> None:
    args = parse_args()
    database_path = resolve_database(args.database)
    prepare_database(database_path)
    data = load_data(database_path)
    data["potential"] = classify_potential_markets(data["potential"])
    records = validate_all(data, database_path)
    export_data(data)
    save_validation(records)
    font_name = configure_plotting()
    create_figures()
    generate_report(data, font_name)
    verify_output_files()

    print("Stage 3 Member 1 customer analysis completed and validated.")
    print(f"Unique customers: {len(data['customers']):,}")
    print(f"Delivered orders: {len(data['orders']):,}")
    print(f"Paid delivered orders: {int(data['orders']['is_paid_order'].sum()):,}")
    print(f"GMV: {data['orders']['order_gmv'].sum():,.2f} BRL")
    print(f"Validation checks passed: {len(records)}/{len(records)}")
    print(f"Growth comparison: {data['growth_periods'].iloc[0]['prior_start_month']}.."
          f"{data['growth_periods'].iloc[0]['prior_end_month']} vs "
          f"{data['growth_periods'].iloc[0]['recent_start_month']}.."
          f"{data['growth_periods'].iloc[0]['recent_end_month']}")
    print("Outputs:")
    for path in list(CSV_PATHS.values()) + list(FIGURE_PATHS.values()) + [REPORT_PATH]:
        print(f"- {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
