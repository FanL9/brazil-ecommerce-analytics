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
import numpy as np
import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value payment comparison visualization
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Order share:
# one main payment type per paid order
#
# GMV share:
# actual positive payment_value by payment_type
#
# High-value population = 4 users
# High-value paid orders = 35
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

ORDER_SHARE_PATH = (
    DATA_DIR
    / "high_value_user_payment_method_order_share.csv"
)

GMV_SHARE_PATH = (
    DATA_DIR
    / "high_value_user_payment_method_gmv_share.csv"
)

FIGURE_PATH = (
    FIGURE_DIR
    / "high_value_payment_comparison.png"
)


PAYMENT_ORDER = [
    "credit_card",
    "boleto",
    "voucher",
    "debit_card",
]

PAYMENT_LABELS = {
    "credit_card": "Credit Card",
    "boleto": "Boleto",
    "voucher": "Voucher",
    "debit_card": "Debit Card",
}


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


def prepare_share_table(
    df,
    value_col,
):

    pivot = (
        df.pivot(
            index=("payment_type" if "payment_type" in df.columns else "main_payment_type"),
            columns="group",
            values=value_col,
        )
        .reindex(PAYMENT_ORDER)
        .fillna(0)
    )

    required = {
        "all_users",
        "high_value_users",
    }

    if not required.issubset(
        pivot.columns
    ):
        raise ValueError(
            f"Missing required groups in {value_col}."
        )

    return pivot


def add_bar_labels(
    ax,
    bars,
):

    labels = []

    for bar in bars:
        value = bar.get_width()

        if value == 0:
            labels.append("0%")
        else:
            labels.append(
                f"{value:.1%}"
            )

    ax.bar_label(
        bars,
        labels=labels,
        padding=3,
        fontsize=8,
    )


def main():

    print("=" * 76)
    print("HIGH-VALUE PAYMENT COMPARISON FIGURE")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load final validated CSV outputs
    # --------------------------------------------------------
    order_share = pd.read_csv(
        ORDER_SHARE_PATH,
        encoding="utf-8-sig",
    )

    gmv_share = pd.read_csv(
        GMV_SHARE_PATH,
        encoding="utf-8-sig",
    )

    print("\n[1] ORDER SHARE INPUT")
    print(
        order_share.to_string(index=False)
    )

    print("\n[2] GMV SHARE INPUT")
    print(
        gmv_share.to_string(index=False)
    )

    required_groups = {
        "all_users",
        "high_value_users",
    }

    if set(order_share["group"]) != required_groups:
        raise ValueError(
            "Order-share CSV has unexpected groups."
        )

    if set(gmv_share["group"]) != required_groups:
        raise ValueError(
            "GMV-share CSV has unexpected groups."
        )

    # --------------------------------------------------------
    # 2. Share reconciliation
    # --------------------------------------------------------
    order_totals = (
        order_share.groupby(
            "group"
        )["order_share"]
        .sum()
    )

    gmv_totals = (
        gmv_share.groupby(
            "group"
        )["gmv_share"]
        .sum()
    )

    print("\n[3] SHARE RECONCILIATION")

    for group in [
        "all_users",
        "high_value_users",
    ]:

        print(
            f"{group} order share sum: "
            f"{order_totals[group]:.6f}"
        )

        print(
            f"{group} GMV share sum: "
            f"{gmv_totals[group]:.6f}"
        )

        if abs(
            order_totals[group] - 1
        ) > 1e-6:
            raise ValueError(
                f"{group} order shares do not sum to 1."
            )

        if abs(
            gmv_totals[group] - 1
        ) > 1e-6:
            raise ValueError(
                f"{group} GMV shares do not sum to 1."
            )

    print("Share reconciliation: PASS")

    # --------------------------------------------------------
    # 3. Prepare aligned chart data
    # --------------------------------------------------------
    order_pivot = prepare_share_table(
        order_share,
        "order_share",
    )

    gmv_pivot = prepare_share_table(
        gmv_share,
        "gmv_share",
    )

    print("\n[4] ALIGNED ORDER SHARE")
    print(order_pivot.to_string())

    print("\n[5] ALIGNED GMV SHARE")
    print(gmv_pivot.to_string())

    # --------------------------------------------------------
    # 4. Plot
    # --------------------------------------------------------
    configure_plotting()

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    y = np.arange(
        len(PAYMENT_ORDER)
    )

    height = 0.34

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(15, 7),
        layout="constrained",
    )

    # --------------------------------------------------------
    # Order-share panel
    # --------------------------------------------------------
    bars_all_order = axes[0].barh(
        y - height / 2,
        order_pivot["all_users"],
        height=height,
        label="All Users",
    )

    bars_hv_order = axes[0].barh(
        y + height / 2,
        order_pivot["high_value_users"],
        height=height,
        label="High-Value Users",
    )

    axes[0].set_title(
        "Main Payment Type Order Share"
    )

    axes[0].set_xlabel(
        "Share of Paid Orders"
    )

    axes[0].set_yticks(
        y,
        [
            PAYMENT_LABELS[x]
            for x in PAYMENT_ORDER
        ],
    )

    axes[0].xaxis.set_major_formatter(
        ticker.PercentFormatter(1.0)
    )

    axes[0].set_xlim(
        0,
        max(
            1.0,
            order_pivot.to_numpy().max()
            * 1.18,
        ),
    )

    axes[0].spines[
        ["top", "right"]
    ].set_visible(False)

    add_bar_labels(
        axes[0],
        bars_all_order,
    )

    add_bar_labels(
        axes[0],
        bars_hv_order,
    )

    # --------------------------------------------------------
    # GMV-share panel
    # --------------------------------------------------------
    bars_all_gmv = axes[1].barh(
        y - height / 2,
        gmv_pivot["all_users"],
        height=height,
        label="All Users",
    )

    bars_hv_gmv = axes[1].barh(
        y + height / 2,
        gmv_pivot["high_value_users"],
        height=height,
        label="High-Value Users",
    )

    axes[1].set_title(
        "Actual Payment-Type GMV Share"
    )

    axes[1].set_xlabel(
        "Share of Payment GMV"
    )

    axes[1].set_yticks(
        y,
        [
            PAYMENT_LABELS[x]
            for x in PAYMENT_ORDER
        ],
    )

    axes[1].xaxis.set_major_formatter(
        ticker.PercentFormatter(1.0)
    )

    axes[1].set_xlim(
        0,
        max(
            1.0,
            gmv_pivot.to_numpy().max()
            * 1.18,
        ),
    )

    axes[1].spines[
        ["top", "right"]
    ].set_visible(False)

    add_bar_labels(
        axes[1],
        bars_all_gmv,
    )

    add_bar_labels(
        axes[1],
        bars_hv_gmv,
    )

    axes[0].legend(
        frameon=False,
        loc="lower right",
    )

    fig.suptitle(
        "High-Value User Payment Structure Comparison\n"
        "High-Value Users: n = 4 | Paid Orders: n = 35",
        fontsize=17,
        fontweight="bold",
    )

    fig.text(
        0.99,
        0.005,
        "Descriptive comparison only. "
        "GMV shares use actual payment amounts for mixed-payment orders.",
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
            "Payment figure was not created."
        )

    image = plt.imread(
        FIGURE_PATH
    )

    if image.size == 0:
        raise RuntimeError(
            "Generated payment PNG cannot be read."
        )

    print("\n[6] OUTPUT")
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
        "Payment comparison figure "
        "successfully created."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
