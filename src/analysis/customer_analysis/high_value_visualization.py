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
import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user final visualizations
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# All chart text is in English.
# High-value population = 4 users.
# Results are descriptive only.
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

CONSUMPTION_PATH = (
    DATA_DIR
    / "high_value_user_consumption_behavior.csv"
)

FIGURE_PATH = (
    FIGURE_DIR
    / "high_value_consumption_comparison.png"
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


def main():

    print("=" * 72)
    print("HIGH-VALUE CONSUMPTION COMPARISON FIGURE")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load final validated CSV
    # --------------------------------------------------------
    df = pd.read_csv(
        CONSUMPTION_PATH,
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
            "Consumption CSV must contain exactly "
            "all_users and high_value_users."
        )

    print("Input validation: PASS")

    # --------------------------------------------------------
    # 2. Prepare metrics
    # --------------------------------------------------------
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

    metrics = pd.DataFrame(
        {
            "Metric": [
                "Spend per User",
                "Average Order Value",
                "Purchase Frequency",
            ],
            "All Users": [
                all_row["spend_per_user"],
                all_row["average_order_value"],
                all_row["average_purchase_frequency"],
            ],
            "High-Value Users": [
                hv_row["spend_per_user"],
                hv_row["average_order_value"],
                hv_row["average_purchase_frequency"],
            ],
        }
    )

    print("\n[2] CHART DATA")
    print(metrics.to_string(index=False))

    # --------------------------------------------------------
    # 3. Normalize each metric to All Users = 100
    #
    # Different metrics have different units, so using an
    # index avoids putting BRL and frequency on one raw axis.
    # --------------------------------------------------------
    metrics["All Users Index"] = 100.0

    metrics["High-Value Users Index"] = (
        metrics["High-Value Users"]
        / metrics["All Users"]
        * 100
    )

    print("\n[3] INDEXED COMPARISON")
    print(
        metrics[
            [
                "Metric",
                "All Users Index",
                "High-Value Users Index",
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # 4. Plot
    # --------------------------------------------------------
    configure_plotting()

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    x = range(len(metrics))
    width = 0.36

    fig, ax = plt.subplots(
        figsize=(11, 7),
        layout="constrained",
    )

    bars_all = ax.bar(
        [i - width / 2 for i in x],
        metrics["All Users Index"],
        width=width,
        label="All Users",
    )

    bars_hv = ax.bar(
        [i + width / 2 for i in x],
        metrics["High-Value Users Index"],
        width=width,
        label="High-Value Users",
    )

    ax.set_title(
        "High-Value User Consumption Comparison\n"
        "All Users = 100 | High-Value Users: n = 4",
        fontsize=16,
    )

    ax.set_ylabel(
        "Index (All Users = 100)"
    )

    ax.set_xlabel(
        "Consumption Metric"
    )

    ax.set_xticks(
        list(x),
        metrics["Metric"],
    )

    ax.legend(
        frameon=False
    )

    ax.spines[
        ["top", "right"]
    ].set_visible(False)

    ax.bar_label(
        bars_all,
        labels=[
            "100"
            for _ in bars_all
        ],
        padding=3,
        fontsize=9,
    )

    ax.bar_label(
        bars_hv,
        labels=[
            f"{value:.0f}"
            for value in metrics[
                "High-Value Users Index"
            ]
        ],
        padding=3,
        fontsize=9,
    )

    ax.text(
        0.99,
        0.02,
        "Descriptive comparison only; high-value population = 4 users.",
        transform=ax.transAxes,
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
    # 5. Verify
    # --------------------------------------------------------
    if (
        not FIGURE_PATH.exists()
        or FIGURE_PATH.stat().st_size == 0
    ):
        raise RuntimeError(
            "Figure was not created."
        )

    image = plt.imread(
        FIGURE_PATH
    )

    if image.size == 0:
        raise RuntimeError(
            "Generated PNG cannot be read."
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

    print("\n" + "=" * 72)
    print("FINAL RESULT: PASS")
    print(
        "Consumption comparison figure "
        "successfully created."
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
