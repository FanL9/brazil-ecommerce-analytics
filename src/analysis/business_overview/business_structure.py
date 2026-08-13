"""
Business structure analysis.

Outputs
-------
CSV files:
    outputs/data/02_business_overview/payment_structure.csv
    outputs/data/02_business_overview/order_value_structure.csv
    outputs/data/02_business_overview/state_structure.csv

Figures:
    visualizations/business_overview/payment_structure.png
    visualizations/business_overview/order_value_structure.png
    visualizations/business_overview/state_gmv_ranking.png
    visualizations/business_overview/regional_structure_change.png

Metric scope
------------
- Paid delivered orders: delivered orders with a positive order-level payment amount.
- GMV: positive payment values aggregated to order_id.
- AOV: GMV divided by paid delivered order count.
- Time comparison: January-July 2017 versus January-July 2018.
- Geography: customer_state.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "brazil_ecommerce.db"
)

CSV_OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "02_business_overview"
)

FIGURE_OUTPUT_DIR = (
    PROJECT_ROOT
    / "visualizations"
    / "business_overview"
)


# ---------------------------------------------------------------------------
# Output filenames
# ---------------------------------------------------------------------------

PAYMENT_CSV_PATH = (
    CSV_OUTPUT_DIR
    / "payment_structure.csv"
)

ORDER_VALUE_CSV_PATH = (
    CSV_OUTPUT_DIR
    / "order_value_structure.csv"
)

STATE_CSV_PATH = (
    CSV_OUTPUT_DIR
    / "state_structure.csv"
)

PAYMENT_FIGURE_PATH = (
    FIGURE_OUTPUT_DIR
    / "payment_structure.png"
)

ORDER_VALUE_FIGURE_PATH = (
    FIGURE_OUTPUT_DIR
    / "order_value_structure.png"
)

STATE_RANKING_FIGURE_PATH = (
    FIGURE_OUTPUT_DIR
    / "state_gmv_ranking.png"
)

REGIONAL_CHANGE_FIGURE_PATH = (
    FIGURE_OUTPUT_DIR
    / "regional_structure_change.png"
)


def prepare_output_directories() -> None:
    """Create required output directories when they do not exist."""
    CSV_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FIGURE_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

PAYMENT_STRUCTURE_QUERY = """
SELECT
    period_order,
    period,
    payment_type,
    split_gmv,
    attributed_order_gmv,
    primary_order_count,
    average_order_value,
    gmv_share,
    order_share,
    mixed_payment_orders,
    mixed_payment_order_share,
    total_gmv,
    total_paid_orders
FROM business_structure_payment_summary
ORDER BY
    period_order,
    split_gmv DESC,
    payment_type;
"""


ORDER_VALUE_STRUCTURE_QUERY = """
SELECT
    period_order,
    period,
    band_order,
    order_value_band,
    paid_order_count,
    gmv,
    average_order_value,
    paid_order_share,
    gmv_share,
    total_paid_orders,
    total_gmv
FROM business_structure_order_value_summary
ORDER BY
    period_order,
    band_order;
"""


STATE_STRUCTURE_QUERY = """
SELECT
    s.period_order,
    s.period,
    s.customer_state,
    s.paid_order_count,
    s.customer_count,
    s.gmv,
    s.average_order_value,
    s.paid_order_share,
    s.gmv_share,
    s.gmv_rank,
    s.total_paid_orders,
    s.total_gmv,

    concentration.top_5_gmv_share,
    concentration.top_10_gmv_share,
    concentration.top_5_paid_order_share,
    concentration.top_10_paid_order_share,
    concentration.state_gmv_hhi,
    concentration.state_paid_order_hhi,

    change_data.paid_order_count_2017,
    change_data.paid_order_count_2018,
    change_data.customer_count_2017,
    change_data.customer_count_2018,
    change_data.gmv_2017,
    change_data.gmv_2018,
    change_data.average_order_value_2017,
    change_data.average_order_value_2018,
    change_data.paid_order_share_2017,
    change_data.paid_order_share_2018,
    change_data.gmv_share_2017,
    change_data.gmv_share_2018,
    change_data.gmv_rank_2017,
    change_data.gmv_rank_2018,
    change_data.gmv_growth_rate,
    change_data.paid_order_growth_rate,
    change_data.customer_growth_rate,
    change_data.average_order_value_growth_rate,
    change_data.gmv_share_change,
    change_data.paid_order_share_change,
    change_data.platform_gmv_growth_rate,
    change_data.growth_gap_vs_platform,
    change_data.equal_state_share_benchmark,
    change_data.state_structure_segment

FROM business_structure_state_summary AS s

LEFT JOIN business_structure_state_concentration AS concentration
    ON concentration.period = s.period

LEFT JOIN business_structure_state_change AS change_data
    ON change_data.customer_state = s.customer_state

ORDER BY
    s.period_order,
    s.gmv_rank,
    s.customer_state;
"""


def load_analysis_data() -> dict[str, pd.DataFrame]:
    """Load the validated business structure result tables."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        payment_data = pd.read_sql_query(
            PAYMENT_STRUCTURE_QUERY,
            connection,
        )

        order_value_data = pd.read_sql_query(
            ORDER_VALUE_STRUCTURE_QUERY,
            connection,
        )

        state_data = pd.read_sql_query(
            STATE_STRUCTURE_QUERY,
            connection,
        )

    expected_rows = {
        "payment": 12,
        "order_value": 15,
        "state": 81,
    }

    actual_rows = {
        "payment": len(payment_data),
        "order_value": len(order_value_data),
        "state": len(state_data),
    }

    for dataset_name, expected_count in expected_rows.items():
        actual_count = actual_rows[dataset_name]

        if actual_count != expected_count:
            raise ValueError(
                f"{dataset_name} row count mismatch: "
                f"expected {expected_count}, got {actual_count}"
            )

    return {
        "payment": payment_data,
        "order_value": order_value_data,
        "state": state_data,
    }


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv_files(
    analysis_data: dict[str, pd.DataFrame],
) -> None:
    """Export the three required business structure CSV files."""
    payment_data = analysis_data["payment"]
    order_value_data = analysis_data["order_value"]
    state_data = analysis_data["state"]

    payment_data.to_csv(
        PAYMENT_CSV_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    order_value_data.to_csv(
        ORDER_VALUE_CSV_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    state_data.to_csv(
        STATE_CSV_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("CSV files exported:")
    print(f"  {PAYMENT_CSV_PATH}")
    print(f"  {ORDER_VALUE_CSV_PATH}")
    print(f"  {STATE_CSV_PATH}")

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_analysis_data(
    analysis_data: dict[str, pd.DataFrame],
) -> None:
    """Confirm that all three structures use the same order and GMV totals."""
    payment_data = analysis_data["payment"]
    order_value_data = analysis_data["order_value"]
    state_data = analysis_data["state"]

    payment_all = payment_data.loc[
        payment_data["period"] == "ALL_DATA"
    ]

    order_value_all = order_value_data.loc[
        order_value_data["period"] == "ALL_DATA"
    ]

    state_all = state_data.loc[
        state_data["period"] == "ALL_DATA"
    ]

    payment_orders = int(
        payment_all["primary_order_count"].sum()
    )
    payment_gmv = round(
        float(payment_all["split_gmv"].sum()),
        2,
    )

    order_value_orders = int(
        order_value_all["paid_order_count"].sum()
    )
    order_value_gmv = round(
        float(order_value_all["gmv"].sum()),
        2,
    )

    state_orders = int(
        state_all["paid_order_count"].sum()
    )
    state_gmv = round(
        float(state_all["gmv"].sum()),
        2,
    )

    expected_paid_orders = 96_477
    expected_gmv = 15_422_461.77

    order_totals = {
        payment_orders,
        order_value_orders,
        state_orders,
        expected_paid_orders,
    }

    if len(order_totals) != 1:
        raise ValueError(
            "Order totals do not match: "
            f"payment={payment_orders}, "
            f"order_value={order_value_orders}, "
            f"state={state_orders}, "
            f"expected={expected_paid_orders}"
        )

    gmv_totals = [
        payment_gmv,
        order_value_gmv,
        state_gmv,
    ]

    for dataset_gmv in gmv_totals:
        if abs(dataset_gmv - expected_gmv) > 0.01:
            raise ValueError(
                "GMV totals do not match: "
                f"payment={payment_gmv}, "
                f"order_value={order_value_gmv}, "
                f"state={state_gmv}, "
                f"expected={expected_gmv}"
            )

    print("Analysis data validated:")
    print(f"  Paid delivered orders: {expected_paid_orders:,}")
    print(f"  GMV: {expected_gmv:,.2f}")
    print(f"  Payment rows: {len(payment_data)}")
    print(f"  Order value rows: {len(order_value_data)}")
    print(f"  State rows: {len(state_data)}")


# ---------------------------------------------------------------------------
# Payment structure figure
# ---------------------------------------------------------------------------

def create_payment_structure_figure(
    payment_data: pd.DataFrame,
) -> None:
    """Create the comparable-period payment GMV share chart."""
    comparable_periods = [
        "2017-01_to_2017-07",
        "2018-01_to_2018-07",
    ]

    period_labels = {
        "2017-01_to_2017-07": "Jan-Jul 2017",
        "2018-01_to_2018-07": "Jan-Jul 2018",
    }

    payment_order = (
        payment_data.loc[
            payment_data["period"] == "ALL_DATA"
        ]
        .sort_values(
            "split_gmv",
            ascending=False,
        )["payment_type"]
        .tolist()
    )

    plot_data = (
        payment_data.loc[
            payment_data["period"].isin(
                comparable_periods
            )
        ]
        .pivot(
            index="payment_type",
            columns="period",
            values="gmv_share",
        )
        .reindex(payment_order)
        .rename(columns=period_labels)
        .fillna(0)
        * 100
    )

    axis = plot_data.plot(
        kind="bar",
        figsize=(10, 6),
        width=0.78,
    )

    axis.set_title(
        "Payment Method GMV Share: "
        "Jan-Jul 2017 vs Jan-Jul 2018"
    )
    axis.set_xlabel("Payment method")
    axis.set_ylabel("GMV share (%)")
    axis.tick_params(
        axis="x",
        rotation=0,
    )
    axis.legend(
        title="Comparable period",
    )

    maximum_share = float(
        plot_data.to_numpy().max()
    )

    axis.set_ylim(
        0,
        maximum_share * 1.15,
    )

    for container in axis.containers:
        labels = [
            f"{value:.1f}%"
            for value in container.datavalues
        ]

        axis.bar_label(
            container,
            labels=labels,
            padding=3,
            fontsize=9,
        )

    figure = axis.get_figure()
    figure.tight_layout()

    figure.savefig(
        PAYMENT_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    print("Payment structure figure exported:")
    print(f"  {PAYMENT_FIGURE_PATH}")


# ---------------------------------------------------------------------------
# Order value structure figure
# ---------------------------------------------------------------------------

def create_order_value_structure_figure(
    order_value_data: pd.DataFrame,
) -> None:
    """Create the overall order share and GMV share chart by value band."""
    band_order = [
        "0-50",
        "50-100",
        "100-200",
        "200-500",
        "500+",
    ]

    plot_data = (
        order_value_data.loc[
            order_value_data["period"] == "ALL_DATA",
            [
                "order_value_band",
                "paid_order_share",
                "gmv_share",
            ],
        ]
        .set_index("order_value_band")
        .reindex(band_order)
        .rename(
            columns={
                "paid_order_share": "Paid order share",
                "gmv_share": "GMV share",
            }
        )
        * 100
    )

    axis = plot_data.plot(
        kind="bar",
        figsize=(10, 6),
        width=0.78,
    )

    axis.set_title(
        "Paid Order and GMV Share by Order Value Band"
    )
    axis.set_xlabel("Order value band")
    axis.set_ylabel("Share (%)")
    axis.tick_params(
        axis="x",
        rotation=0,
    )
    axis.legend(
        title="Metric",
    )

    maximum_share = float(
        plot_data.to_numpy().max()
    )

    axis.set_ylim(
        0,
        maximum_share * 1.18,
    )

    for container in axis.containers:
        labels = [
            f"{value:.1f}%"
            for value in container.datavalues
        ]

        axis.bar_label(
            container,
            labels=labels,
            padding=3,
            fontsize=9,
        )

    figure = axis.get_figure()
    figure.tight_layout()

    figure.savefig(
        ORDER_VALUE_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    print("Order value structure figure exported:")
    print(f"  {ORDER_VALUE_FIGURE_PATH}")


# ---------------------------------------------------------------------------
# State GMV ranking figure
# ---------------------------------------------------------------------------

def create_state_gmv_ranking_figure(
    state_data: pd.DataFrame,
) -> None:
    """Create the overall top-10 customer-state GMV ranking chart."""
    plot_data = (
        state_data.loc[
            state_data["period"] == "ALL_DATA",
            [
                "customer_state",
                "gmv",
                "gmv_share",
                "gmv_rank",
            ],
        ]
        .sort_values(
            "gmv_rank",
            ascending=True,
        )
        .head(10)
        .sort_values(
            "gmv",
            ascending=True,
        )
        .copy()
    )

    plot_data["gmv_million"] = (
        plot_data["gmv"] / 1_000_000
    )

    figure, axis = plt.subplots(
        figsize=(10, 6),
    )

    bars = axis.barh(
        plot_data["customer_state"],
        plot_data["gmv_million"],
    )

    axis.set_title(
        "Top 10 Customer States by GMV"
    )
    axis.set_xlabel(
        "GMV (BRL millions)"
    )
    axis.set_ylabel(
        "Customer state"
    )

    maximum_gmv = float(
        plot_data["gmv_million"].max()
    )

    axis.set_xlim(
        0,
        maximum_gmv * 1.22,
    )

    for bar, (_, row) in zip(
        bars,
        plot_data.iterrows(),
    ):
        label = (
            f"{row['gmv_million']:.2f}M "
            f"({row['gmv_share'] * 100:.1f}%)"
        )

        axis.text(
            bar.get_width() + maximum_gmv * 0.015,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=9,
        )

    figure.tight_layout()

    figure.savefig(
        STATE_RANKING_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    print("State GMV ranking figure exported:")
    print(f"  {STATE_RANKING_FIGURE_PATH}")


# ---------------------------------------------------------------------------
# Regional structure change figure
# ---------------------------------------------------------------------------

def create_regional_structure_change_figure(
    state_data: pd.DataFrame,
) -> None:
    """Create overview and zoomed regional scale-growth charts."""
    plot_data = (
        state_data.loc[
            state_data["period"] == "ALL_DATA",
            [
                "customer_state",
                "gmv_share_2018",
                "growth_gap_vs_platform",
                "equal_state_share_benchmark",
                "state_structure_segment",
            ],
        ]
        .drop_duplicates(
            subset=["customer_state"]
        )
        .copy()
    )

    plot_data["gmv_share_2018_pct"] = (
        plot_data["gmv_share_2018"] * 100
    )

    plot_data["growth_gap_pct"] = (
        plot_data["growth_gap_vs_platform"] * 100
    )

    equal_share_benchmark = float(
        plot_data[
            "equal_state_share_benchmark"
        ].iloc[0]
        * 100
    )

    segment_labels = {
        "HIGH_SCALE_HIGH_GROWTH":
            "High scale, high growth",
        "HIGH_SCALE_LOW_GROWTH":
            "High scale, low growth",
        "LOW_SCALE_HIGH_GROWTH":
            "Low scale, high growth",
        "LOW_SCALE_LOW_GROWTH":
            "Low scale, low growth",
    }

    segment_order = [
        "HIGH_SCALE_HIGH_GROWTH",
        "HIGH_SCALE_LOW_GROWTH",
        "LOW_SCALE_HIGH_GROWTH",
        "LOW_SCALE_LOW_GROWTH",
    ]

    figure, axes = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(15, 7),
    )

    overview_axis = axes[0]
    detail_axis = axes[1]

    for axis in axes:
        for segment in segment_order:
            segment_data = plot_data.loc[
                plot_data["state_structure_segment"]
                == segment
            ]

            axis.scatter(
                segment_data["gmv_share_2018_pct"],
                segment_data["growth_gap_pct"],
                label=segment_labels[segment],
                s=65,
                alpha=0.8,
            )

        axis.axhline(
            0,
            linestyle="--",
            linewidth=1,
        )

        axis.axvline(
            equal_share_benchmark,
            linestyle="--",
            linewidth=1,
        )

        axis.set_xscale("log")

        axis.set_xlabel(
            "Jan-Jul 2018 GMV share (%) - log scale"
        )

        axis.grid(
            True,
            linestyle=":",
            alpha=0.4,
        )

    overview_axis.set_title(
        "All States"
    )

    overview_axis.set_ylabel(
        "GMV growth gap vs platform "
        "(percentage points)"
    )

    detail_axis.set_title(
        "Central Cluster — Zoomed View"
    )

    detail_axis.set_ylabel(
        "GMV growth gap vs platform "
        "(percentage points)"
    )

    detail_axis.set_ylim(
        -110,
        60,
    )

    overview_label_states = {
        "RR",
        "AC",
        "SP",
        "RJ",
        "MG",
        "SC",
    }

    detail_label_states = {
        "SP",
        "RJ",
        "MG",
        "RS",
        "PR",
        "SC",
        "BA",
        "DF",
        "ES",
        "GO",
        "PE",
        "RN",
        "PB",
    }

    label_offsets = {
        "SP": (6, 2),
        "RJ": (6, -10),
        "MG": (6, 7),
        "RS": (6, -10),
        "PR": (6, 7),
        "SC": (6, 7),
        "BA": (6, -10),
        "DF": (6, 10),
        "ES": (6, -10),
        "GO": (6, -10),
        "PE": (-20, 9),
        "RN": (6, 9),
        "PB": (6, 9),
        "RR": (6, 5),
        "AC": (6, -2),
    }

    for _, row in plot_data.loc[
        plot_data["customer_state"].isin(
            overview_label_states
        )
    ].iterrows():
        state = row["customer_state"]

        overview_axis.annotate(
            state,
            (
                row["gmv_share_2018_pct"],
                row["growth_gap_pct"],
            ),
            xytext=label_offsets.get(
                state,
                (5, 5),
            ),
            textcoords="offset points",
            fontsize=8,
        )

    detail_rows = plot_data.loc[
        plot_data["customer_state"].isin(
            detail_label_states
        )
        & plot_data["growth_gap_pct"].between(
            -110,
            60,
        )
    ]

    for _, row in detail_rows.iterrows():
        state = row["customer_state"]

        detail_axis.annotate(
            state,
            (
                row["gmv_share_2018_pct"],
                row["growth_gap_pct"],
            ),
            xytext=label_offsets.get(
                state,
                (5, 5),
            ),
            textcoords="offset points",
            fontsize=8,
        )

    handles, legend_labels = (
        overview_axis.get_legend_handles_labels()
    )

    figure.legend(
        handles,
        legend_labels,
        title="State segment",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=2,
    )

    figure.suptitle(
        "Regional Structure Change: "
        "Jan-Jul 2018 Scale vs Growth Gap",
        y=1.01,
    )

    figure.tight_layout(
        rect=(0, 0, 1, 0.88),
    )

    figure.savefig(
        REGIONAL_CHANGE_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    print("Regional structure change figure exported:")
    print(f"  {REGIONAL_CHANGE_FIGURE_PATH}")



# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main() -> None:
    """Run data loading, validation, and CSV export."""
    print("Starting business structure analysis...")

    prepare_output_directories()

    analysis_data = load_analysis_data()

    validate_analysis_data(
        analysis_data
    )

    export_csv_files(
        analysis_data
    )

    create_payment_structure_figure(
        analysis_data["payment"]
    )

    create_order_value_structure_figure(
        analysis_data["order_value"]
    )

    create_state_gmv_ranking_figure(
        analysis_data["state"]
    )

    create_regional_structure_change_figure(
        analysis_data["state"]
    )

    print("Business structure analysis completed.")




if __name__ == "__main__":
    main()
