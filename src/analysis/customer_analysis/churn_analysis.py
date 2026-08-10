from pathlib import Path
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Configuration
# ============================================================

DB_PATH = Path("database/brazil_ecommerce.db")

SQL_CHURN_PATH = Path(
    "sql/05_customer_analysis/03_churn_analysis.sql"
)

SQL_FEATURE_PATH = Path(
    "sql/05_customer_analysis/04_churn_related_features.sql"
)

DATA_DIR = Path(
    "outputs/data/03_customer_analysis"
)

FIGURE_DIR = Path(
    "visualizations/customer"
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Helpers
# ============================================================

def split_sql_statements(sql_text: str):
    return [
        statement.strip()
        for statement in sql_text.split(";")
        if statement.strip()
    ]


def execute_query(conn, sql):
    return pd.read_sql_query(sql, conn)


def save_csv(df, filename):
    path = DATA_DIR / filename
    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig"
    )
    print(
        f"[CSV] {path} | rows={len(df)}"
    )


def save_figure(fig, filename):
    path = FIGURE_DIR / filename

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"[FIG] {path}")


# ============================================================
# Read SQL
# ============================================================

churn_sql = SQL_CHURN_PATH.read_text(
    encoding="utf-8"
)

feature_sql = SQL_FEATURE_PATH.read_text(
    encoding="utf-8"
)

feature_statements = split_sql_statements(
    feature_sql
)

if len(feature_statements) != 5:
    raise ValueError(
        "04_churn_related_features.sql "
        "must contain exactly 5 executable queries."
    )


# ============================================================
# Run analysis
# ============================================================

conn = sqlite3.connect(DB_PATH)

try:

    # --------------------------------------------------------
    # 1. Core churn comparison
    # --------------------------------------------------------

    churn_comparison = execute_query(
        conn,
        churn_sql
    )

    # --------------------------------------------------------
    # 2. Related features
    # --------------------------------------------------------

    payment_structure = execute_query(
        conn,
        feature_statements[0]
    )

    state_structure = execute_query(
        conn,
        feature_statements[1]
    )

    city_structure = execute_query(
        conn,
        feature_statements[2]
    )

    weekday_weekend = execute_query(
        conn,
        feature_statements[3]
    )

    first_purchase_month = execute_query(
        conn,
        feature_statements[4]
    )


    # ========================================================
    # Validation
    # ========================================================

    print("\n=== Validation ===")

    # Core user reconciliation
    total_users = int(
        churn_comparison["user_count"].sum()
    )

    total_orders = int(
        churn_comparison[
            "total_valid_orders"
        ].sum()
    )

    total_paid_orders = int(
        churn_comparison[
            "total_paid_orders"
        ].sum()
    )

    total_gmv = round(
        churn_comparison[
            "total_gmv"
        ].sum(),
        2
    )

    print("Total users:", total_users)
    print("Total valid orders:", total_orders)
    print(
        "Total paid orders:",
        total_paid_orders
    )
    print("Total GMV:", total_gmv)

    assert total_users == 87214
    assert total_orders == 90127
    assert total_paid_orders == 90126
    assert abs(
        total_gmv - 14437047.49
    ) < 0.01

    # Payment reconciliation
    payment_check = (
        payment_structure
        .groupby("churn_status")[
            "order_count"
        ]
        .sum()
        .to_dict()
    )

    assert (
        payment_check.get(
            "Churned", 0
        ) == 70861
    )

    assert (
        payment_check.get(
            "Non-churned", 0
        ) == 19265
    )

    # State reconciliation
    assert (
        state_structure["user_count"].sum()
        == 87214
    )

    # Weekday / weekend reconciliation
    assert (
        weekday_weekend[
            "order_count"
        ].sum()
        == 90127
    )

    # First purchase month reconciliation
    assert (
        first_purchase_month[
            "cohort_users"
        ].sum()
        == 87214
    )

    print(
        "All reconciliation checks: PASS"
    )


    # ========================================================
    # Export CSV
    # ========================================================

    save_csv(
        churn_comparison,
        "churn_comparison.csv"
    )

    save_csv(
        payment_structure,
        "churn_payment_structure.csv"
    )

    save_csv(
        state_structure,
        "churn_state_structure.csv"
    )

    save_csv(
        city_structure,
        "churn_city_structure_top30.csv"
    )

    save_csv(
        weekday_weekend,
        "churn_weekday_weekend.csv"
    )

    save_csv(
        first_purchase_month,
        "churn_first_purchase_month.csv"
    )


    # ========================================================
    # Visualization 1
    # Core metrics comparison
    # ========================================================

    core = (
        churn_comparison
        .set_index("churn_status")
    )

    metrics = pd.DataFrame({
        "Spend per User": (
            core["spend_per_user"]
        ),
        "AOV": (
            core["average_order_value"]
        ),
        "Latest Order Amount": (
            core["avg_latest_order_amount"]
        )
    })

    ax = metrics.T.plot(
        kind="bar"
    )

    ax.set_title(
        "Churned vs Non-churned: "
        "Customer Value Metrics"
    )

    ax.set_xlabel("")
    ax.set_ylabel("BRL")

    ax.tick_params(
        axis="x",
        rotation=0
    )

    fig = ax.get_figure()

    save_figure(
        fig,
        "churn_core_metrics_comparison.png"
    )


    # ========================================================
    # Visualization 2
    # Experience comparison
    # ========================================================

    experience = pd.DataFrame({
        "Average Review Score": (
            core["avg_review_score"]
        ),
        "Average Delivery Days": (
            core["avg_delivery_days"]
        ),
        "Delay Rate (%)": (
            core["delay_rate_pct"]
        )
    })

    ax = experience.T.plot(
        kind="bar"
    )

    ax.set_title(
        "Churned vs Non-churned: "
        "Customer Experience"
    )

    ax.set_xlabel("")
    ax.set_ylabel("Value")

    ax.tick_params(
        axis="x",
        rotation=0
    )

    fig = ax.get_figure()

    save_figure(
        fig,
        "churn_experience_comparison.png"
    )


    # ========================================================
    # Visualization 3
    # Payment structure
    # ========================================================

    payment_pivot = (
        payment_structure
        .pivot(
            index="primary_payment_type",
            columns="churn_status",
            values="order_share_pct"
        )
        .fillna(0)
    )

    ax = payment_pivot.plot(
        kind="bar"
    )

    ax.set_title(
        "Primary Payment Type by Churn Status"
    )

    ax.set_xlabel(
        "Primary Payment Type"
    )

    ax.set_ylabel(
        "Order Share (%)"
    )

    ax.tick_params(
        axis="x",
        rotation=0
    )

    fig = ax.get_figure()

    save_figure(
        fig,
        "churn_payment_structure.png"
    )


    # ========================================================
    # Visualization 4
    # State comparison
    # ========================================================

    state_plot = (
        state_structure
        .head(10)
        .copy()
        .sort_values(
            "user_count",
            ascending=True
        )
    )

    fig, ax = plt.subplots()

    ax.barh(
        state_plot[
            "customer_state"
        ],
        state_plot[
            "churn_rate_pct"
        ]
    )

    ax.axvline(
        78.76,
        linestyle="--"
    )

    ax.set_title(
        "Churn Rate in Top 10 States by User Scale"
    )

    ax.set_xlabel(
        "Churn Rate (%)"
    )

    ax.set_ylabel(
        "Customer State"
    )

    save_figure(
        fig,
        "churn_state_comparison.png"
    )


    # ========================================================
    # Visualization 5
    # Weekday / weekend structure
    # ========================================================

    day_pivot = (
        weekday_weekend
        .pivot(
            index="day_type",
            columns="churn_status",
            values="order_share_pct"
        )
    )

    ax = day_pivot.plot(
        kind="bar"
    )

    ax.set_title(
        "Weekday vs Weekend Order Share "
        "by Churn Status"
    )

    ax.set_xlabel("")
    ax.set_ylabel(
        "Order Share (%)"
    )

    ax.tick_params(
        axis="x",
        rotation=0
    )

    fig = ax.get_figure()

    save_figure(
        fig,
        "churn_weekday_weekend_comparison.png"
    )


    print(
        "\nChurn analysis outputs "
        "generated successfully."
    )

finally:
    conn.close()
