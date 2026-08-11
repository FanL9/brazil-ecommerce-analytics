from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(PROJECT_ROOT / "outputs" / ".matplotlib-cache"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import ticker
import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user experience comparison visualization
#
# Source:
# high_value_user_experience_profile.csv
#
# High-value population = 4 users
# High-value orders = 35
# Descriptive comparison only.
# ============================================================


DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "visualizations"
    / "customer"
    / "high_value"
)

INPUT_PATH = (
    DATA_DIR
    / "high_value_user_experience_profile.csv"
)

FIGURE_PATH = (
    FIGURE_DIR
    / "high_value_experience_comparison.png"
)


def configure_plotting():

    plt.rcParams.update(
        {
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


def add_labels(ax, bars, formatter):

    labels = [
        formatter(bar.get_height())
        for bar in bars
    ]

    ax.bar_label(
        bars,
        labels=labels,
        padding=4,
        fontsize=9,
    )


def main():

    print("=" * 76)
    print("HIGH-VALUE EXPERIENCE COMPARISON FIGURE")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load validated final CSV
    # --------------------------------------------------------
    df = pd.read_csv(
        INPUT_PATH,
        encoding="utf-8-sig",
    )

    print("\n[1] INPUT")
    print(df.to_string(index=False))

    required_groups = {
        "all_users",
        "high_value_users",
    }

    if set(df["group"]) != required_groups:
        raise ValueError(
            "Experience profile must contain exactly "
            "all_users and high_value_users."
        )

    all_row = (
        df.loc[
            df["group"] == "all_users"
        ]
        .iloc[0]
    )

    hv_row = (
        df.loc[
            df["group"] == "high_value_users"
        ]
        .iloc[0]
    )

    # --------------------------------------------------------
    # 2. Validation
    # --------------------------------------------------------
    print("\n[2] SAMPLE VALIDATION")

    print(
        f"All-user reviewed orders: "
        f"{int(all_row['reviewed_orders']):,}"
    )

    print(
        f"High-value reviewed orders: "
        f"{int(hv_row['reviewed_orders']):,}"
    )

    print(
        f"All-user delivery orders: "
        f"{int(all_row['delivery_orders']):,}"
    )

    print(
        f"High-value delivery orders: "
        f"{int(hv_row['delivery_orders']):,}"
    )

    if int(hv_row["users"]) != 4:
        raise ValueError(
            "Expected 4 high-value users."
        )

    if int(hv_row["orders"]) != 35:
        raise ValueError(
            "Expected 35 high-value orders."
        )

    if int(hv_row["reviewed_orders"]) != 35:
        raise ValueError(
            "Expected 35 reviewed high-value orders."
        )

    if int(hv_row["delivery_orders"]) != 35:
        raise ValueError(
            "Expected 35 delivery high-value orders."
        )

    print("Sample validation: PASS")

    # --------------------------------------------------------
    # 3. Chart values
    # --------------------------------------------------------
    comparison = pd.DataFrame(
        {
            "metric": [
                "Average Review Score",
                "1-Star Order Share",
                "Average Delivery Days",
                "Delay Rate",
            ],
            "all_users": [
                all_row["average_review_score"],
                all_row["low_score_order_share"],
                all_row["average_delivery_days"],
                all_row["delay_rate"],
            ],
            "high_value_users": [
                hv_row["average_review_score"],
                hv_row["low_score_order_share"],
                hv_row["average_delivery_days"],
                hv_row["delay_rate"],
            ],
        }
    )

    print("\n[3] CHART DATA")
    print(comparison.to_string(index=False))

    # --------------------------------------------------------
    # 4. Plot
    # --------------------------------------------------------
    configure_plotting()

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(13, 9),
        layout="constrained",
    )

    axes = axes.flatten()

    groups = [
        "All Users",
        "High-Value Users",
    ]

    # --------------------------------------------------------
    # Panel 1 - Review score
    # --------------------------------------------------------
    values = [
        all_row["average_review_score"],
        hv_row["average_review_score"],
    ]

    bars = axes[0].bar(
        groups,
        values,
    )

    axes[0].set_title(
        "Average Review Score"
    )

    axes[0].set_ylabel(
        "Score (1–5)"
    )

    axes[0].set_ylim(
        0,
        5.5,
    )

    add_labels(
        axes[0],
        bars,
        lambda x: f"{x:.2f}",
    )

    # --------------------------------------------------------
    # Panel 2 - 1-star order share
    # --------------------------------------------------------
    values = [
        all_row["low_score_order_share"],
        hv_row["low_score_order_share"],
    ]

    bars = axes[1].bar(
        groups,
        values,
    )

    axes[1].set_title(
        "1-Star Order Share"
    )

    axes[1].set_ylabel(
        "Share of Reviewed Orders"
    )

    axes[1].yaxis.set_major_formatter(
        ticker.PercentFormatter(1.0)
    )

    axes[1].set_ylim(
        0,
        max(values) * 1.35
        if max(values) > 0
        else 1,
    )

    add_labels(
        axes[1],
        bars,
        lambda x: f"{x:.1%}",
    )

    # --------------------------------------------------------
    # Panel 3 - Delivery duration
    # --------------------------------------------------------
    values = [
        all_row["average_delivery_days"],
        hv_row["average_delivery_days"],
    ]

    bars = axes[2].bar(
        groups,
        values,
    )

    axes[2].set_title(
        "Average Delivery Time"
    )

    axes[2].set_ylabel(
        "Days"
    )

    axes[2].set_ylim(
        0,
        max(values) * 1.25,
    )

    add_labels(
        axes[2],
        bars,
        lambda x: f"{x:.2f}",
    )

    # --------------------------------------------------------
    # Panel 4 - Delay rate
    # --------------------------------------------------------
    values = [
        all_row["delay_rate"],
        hv_row["delay_rate"],
    ]

    bars = axes[3].bar(
        groups,
        values,
    )

    axes[3].set_title(
        "Late Delivery Rate"
    )

    axes[3].set_ylabel(
        "Share of Eligible Orders"
    )

    axes[3].yaxis.set_major_formatter(
        ticker.PercentFormatter(1.0)
    )

    axes[3].set_ylim(
        0,
        max(values) * 1.35
        if max(values) > 0
        else 1,
    )

    add_labels(
        axes[3],
        bars,
        lambda x: f"{x:.1%}",
    )

    # --------------------------------------------------------
    # Shared formatting
    # --------------------------------------------------------
    for ax in axes:

        ax.spines[
            ["top", "right"]
        ].set_visible(False)

        ax.tick_params(
            axis="x",
            rotation=0,
        )

    fig.suptitle(
        "High-Value User Review and Delivery Experience\n"
        "High-Value Users: n = 4 | Orders: n = 35",
        fontsize=17,
        fontweight="bold",
    )

    fig.text(
        0.99,
        0.005,
        "Descriptive comparison only. "
        "Review metrics use representative order-level reviews; "
        "delivery metrics use valid delivery denominators.",
        ha="right",
        va="bottom",
        fontsize=9,
    )

    fig.savefig(
        FIGURE_PATH,
        bbox_inches="tight",
        pad_inches=0.16,
    )

    plt.close(fig)

    # --------------------------------------------------------
    # 5. Verify PNG
    # --------------------------------------------------------
    if (
        not FIGURE_PATH.exists()
        or FIGURE_PATH.stat().st_size == 0
    ):
        raise RuntimeError(
            "Experience figure was not created."
        )

    image = plt.imread(
        FIGURE_PATH
    )

    if image.size == 0:
        raise RuntimeError(
            "Generated experience PNG cannot be read."
        )

    print("\n[4] OUTPUT")
    print(f"Saved: {FIGURE_PATH}")
    print(
        f"File size: "
        f"{FIGURE_PATH.stat().st_size:,} bytes"
    )
    print(
        f"Image shape: "
        f"{image.shape}"
    )

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "Experience comparison figure "
        "successfully created."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
