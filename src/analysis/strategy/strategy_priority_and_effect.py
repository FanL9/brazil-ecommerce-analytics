from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 6 - Member 3
# Strategy priority ranking and effect estimation
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# This script treats all scenario uplift rates as business
# assumptions, not causal estimates or guaranteed forecasts.
# ============================================================


ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "database/brazil_ecommerce.db"

INPUT_PATHS = {
    "core_problem_summary": ROOT / "outputs/data/strategy/core_problem_summary.csv",

    "monthly_kpi": (
        ROOT / "outputs/data/02_business_overview/monthly_kpi.csv"
    ),

    "customer_order_base": (
        ROOT / "outputs/data/03_customer_analysis/customer_order_base.csv"
    ),
    "rfm_customer_detail": (
        ROOT / "outputs/data/03_customer_analysis/rfm_customer_detail.csv"
    ),
    "rfm_segment_summary": (
        ROOT / "outputs/data/03_customer_analysis/rfm_segment_summary.csv"
    ),

    "category_association": (
        ROOT
        / "outputs/data/06_product_analysis/category_association_top20.csv"
    ),
    "category_satisfaction": (
        ROOT / "outputs/data/06_product_analysis/category_satisfaction.csv"
    ),
    "category_sales": (
        ROOT / "outputs/data/06_product_analysis/category_sales_base.csv"
    ),
    "category_negative_keywords": (
        ROOT
        / "outputs/data/06_product_analysis/category_negative_keywords.csv"
    ),

    "state_structure": (
        ROOT / "outputs/data/02_business_overview/state_structure.csv"
    ),
    "potential_regional_markets": (
        ROOT
        / "outputs/data/03_customer_analysis/potential_regional_markets.csv"
    ),
    "payment_structure": (
        ROOT / "outputs/data/02_business_overview/payment_structure.csv"
    ),
}


EXPECTED_PROBLEM_IDS = {
    "CBP-01",
    "CBP-02",
    "CBP-03",
    "CBP-04",
    "CBP-05",
    "CBP-06",
    "CBP-07",
}


def load_inputs() -> dict[str, pd.DataFrame]:
    """Load all formal Stage 6 Member 3 input CSV files."""

    missing = [
        str(path.relative_to(ROOT))
        for path in INPUT_PATHS.values()
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required input files:\n- " + "\n- ".join(missing)
        )

    return {
        name: pd.read_csv(path, low_memory=False)
        for name, path in INPUT_PATHS.items()
    }


def run_input_qa(data: dict[str, pd.DataFrame]) -> None:
    """Run concise input-layer QA before any scenario calculation."""

    print("=== STAGE 6 MEMBER 3 INPUT QA ===")

    for name, df in data.items():
        print(
            f"{name:<28} "
            f"rows={len(df):>7,}  cols={len(df.columns):>2}"
        )

    problems = data["core_problem_summary"]

    if "problem_id" not in problems.columns:
        raise ValueError(
            "core_problem_summary.csv missing column: problem_id"
        )

    actual_problem_ids = set(
        problems["problem_id"].dropna().astype(str)
    )

    if actual_problem_ids != EXPECTED_PROBLEM_IDS:
        raise ValueError(
            "CBP problem IDs mismatch. "
            f"Actual={sorted(actual_problem_ids)}"
        )

    if len(problems) != 7:
        raise ValueError(
            f"Expected 7 core problems, found {len(problems)}"
        )

    print()
    print("core_problem_summary: CBP-01 through CBP-07 confirmed")
    print("INPUT QA PASSED")



CBP01_UPLIFT_RATES = {
    "conservative": 0.10,
    "neutral": 0.20,
    "optimistic": 0.30,
}


def calculate_cbp01(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    CBP-01 repeat-purchase scenario.

    The formal observed repeat-purchase rate is used as a historical
    reference rate. Scenario uplifts are business assumptions only.

    Incremental repeat users:
        target single-purchase users
        x formal historical repeat rate
        x assumed relative uplift

    This is a historical scenario, not a causal forecast.
    """

    rfm = data["rfm_customer_detail"].copy()
    orders = data["customer_order_base"].copy()

    user_count = len(rfm)
    repeat_users = int(rfm["is_repeat_customer"].sum())
    single_purchase_users = user_count - repeat_users

    if user_count != 87214:
        raise ValueError(
            f"CBP-01 user baseline mismatch: {user_count}"
        )

    if repeat_users != 2621:
        raise ValueError(
            f"CBP-01 repeat-user baseline mismatch: {repeat_users}"
        )

    formal_repeat_rate = repeat_users / user_count

    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="coerce",
    )

    formal_orders = orders.loc[
        orders["order_purchase_timestamp"]
        < pd.Timestamp("2018-08-01")
    ].copy()

    formal_orders = formal_orders.sort_values(
        [
            "customer_unique_id",
            "order_purchase_timestamp",
            "order_id",
        ]
    )

    formal_orders["purchase_sequence"] = (
        formal_orders
        .groupby("customer_unique_id")
        .cumcount()
        + 1
    )

    second_orders = formal_orders.loc[
        formal_orders["purchase_sequence"] == 2
    ].copy()

    if len(second_orders) != repeat_users:
        raise ValueError(
            "CBP-01 second-order count does not reconcile "
            f"to repeat users: {len(second_orders)} != {repeat_users}"
        )

    second_order_avg_gmv = second_orders["order_gmv"].mean()

    baseline_expected_repeat_users = (
        single_purchase_users * formal_repeat_rate
    )

    rows = []

    for scenario, uplift_rate in CBP01_UPLIFT_RATES.items():
        incremental_repeat_users = (
            baseline_expected_repeat_users * uplift_rate
        )

        incremental_gmv = (
            incremental_repeat_users * second_order_avg_gmv
        )

        rows.append(
            {
                "problem_id": "CBP-01",
                "scenario": scenario,
                "target_users": single_purchase_users,
                "formal_repeat_rate": formal_repeat_rate,
                "assumed_relative_uplift": uplift_rate,
                "baseline_expected_repeat_users":
                    baseline_expected_repeat_users,
                "incremental_repeat_users":
                    incremental_repeat_users,
                "historical_second_order_avg_gmv":
                    second_order_avg_gmv,
                "simulated_incremental_gmv":
                    incremental_gmv,
                "estimate_type":
                    "historical_reference_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp01(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-01 REPEAT-PURCHASE SCENARIO ===")

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"uplift={row.assumed_relative_uplift:>5.0%}  "
            f"inc_users={row.incremental_repeat_users:>8.2f}  "
            f"inc_gmv={row.simulated_incremental_gmv:>11.2f} BRL"
        )

    print(
        "historical_second_order_avg_gmv="
        f"{result.iloc[0]['historical_second_order_avg_gmv']:.2f} BRL"
    )



CBP02_AOV_UPLIFT_RATES = {
    "conservative": 0.03,
    "neutral": 0.05,
    "optimistic": 0.08,
}


def calculate_cbp02(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    CBP-02 AOV uplift scenario.

    Formal comparison window:
        2018-01 through 2018-07

    Paid-order volume is held constant.
    AOV uplift rates are business assumptions only.
    """

    monthly = data["monthly_kpi"].copy()

    monthly["month"] = monthly["month"].astype(str)

    current = monthly.loc[
        monthly["month"].between("2018-01", "2018-07")
    ].copy()

    baseline_gmv = current["gmv"].sum()
    baseline_paid_orders = current["order_count"].sum()

    if baseline_paid_orders <= 0:
        raise ValueError("CBP-02 paid-order baseline is zero")

    baseline_aov = baseline_gmv / baseline_paid_orders

    if round(baseline_gmv, 2) != 7467560.92:
        raise ValueError(
            f"CBP-02 GMV baseline mismatch: {baseline_gmv}"
        )

    if int(baseline_paid_orders) != 46432:
        raise ValueError(
            "CBP-02 paid-order baseline mismatch: "
            f"{baseline_paid_orders}"
        )

    rows = []

    for scenario, uplift_rate in CBP02_AOV_UPLIFT_RATES.items():
        simulated_aov = baseline_aov * (1 + uplift_rate)

        simulated_gmv = (
            baseline_paid_orders * simulated_aov
        )

        incremental_gmv = simulated_gmv - baseline_gmv

        rows.append(
            {
                "problem_id": "CBP-02",
                "scenario": scenario,
                "baseline_gmv": baseline_gmv,
                "baseline_paid_orders": baseline_paid_orders,
                "baseline_aov": baseline_aov,
                "assumed_aov_uplift": uplift_rate,
                "simulated_aov": simulated_aov,
                "simulated_gmv": simulated_gmv,
                "simulated_incremental_gmv":
                    incremental_gmv,
                "order_volume_assumption":
                    "paid_orders_held_constant",
                "estimate_type":
                    "historical_reference_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp02(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-02 AOV SCENARIO ===")

    print(
        "baseline="
        f"{result.iloc[0]['baseline_gmv']:.2f} BRL | "
        f"{int(result.iloc[0]['baseline_paid_orders']):,} paid orders | "
        f"AOV={result.iloc[0]['baseline_aov']:.6f} BRL"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"uplift={row.assumed_aov_uplift:>5.0%}  "
            f"new_aov={row.simulated_aov:>9.2f}  "
            f"inc_gmv={row.simulated_incremental_gmv:>11.2f} BRL"
        )



CBP03_RECALL_COEFFICIENTS = {
    "conservative": 0.30,
    "neutral": 0.45,
    "optimistic": 0.60,
}


def calculate_cbp03(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    CBP-03 important-retention-user recall scenario.

    The within-segment historical repeat share is descriptive only.
    It is not interpreted as a future recall probability.

    Historical potential recall users:
        target users x historical within-segment repeat share

    Simulated reactivated users:
        historical potential recall users
        x assumed scenario coefficient
    """

    rfm = data["rfm_customer_detail"].copy()
    orders = data["customer_order_base"].copy()

    rfm["frequency"] = pd.to_numeric(
        rfm["frequency"],
        errors="coerce",
    )

    rfm["monetary"] = pd.to_numeric(
        rfm["monetary"],
        errors="coerce",
    )

    target = rfm.loc[
        rfm["rfm_segment"] == "重要挽留用户"
    ].copy()

    target_users = len(target)

    historical_repeat_users = int(
        (target["frequency"] >= 2).sum()
    )

    if target_users != 20391:
        raise ValueError(
            f"CBP-03 target-user baseline mismatch: {target_users}"
        )

    if historical_repeat_users != 1132:
        raise ValueError(
            "CBP-03 historical repeat-user mismatch: "
            f"{historical_repeat_users}"
        )

    target_historical_gmv = target["monetary"].sum()

    if round(target_historical_gmv, 2) != 6176160.10:
        raise ValueError(
            "CBP-03 historical GMV mismatch: "
            f"{target_historical_gmv}"
        )

    historical_repeat_share = (
        historical_repeat_users / target_users
    )

    historical_potential_recall_users = (
        target_users * historical_repeat_share
    )

    target_ids = set(target["customer_unique_id"])

    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="coerce",
    )

    formal_orders = orders.loc[
        orders["order_purchase_timestamp"]
        < pd.Timestamp("2018-08-01")
    ].copy()

    formal_orders = formal_orders.sort_values(
        [
            "customer_unique_id",
            "order_purchase_timestamp",
            "order_id",
        ]
    )

    formal_orders["purchase_sequence"] = (
        formal_orders
        .groupby("customer_unique_id")
        .cumcount()
        + 1
    )

    second_orders = formal_orders.loc[
        formal_orders["customer_unique_id"].isin(target_ids)
        & (formal_orders["purchase_sequence"] == 2)
    ].copy()

    if len(second_orders) != historical_repeat_users:
        raise ValueError(
            "CBP-03 second-order count mismatch: "
            f"{len(second_orders)} != {historical_repeat_users}"
        )

    historical_second_order_avg_gmv = pd.to_numeric(
        second_orders["order_gmv"],
        errors="coerce",
    ).mean()

    rows = []

    for scenario, coefficient in CBP03_RECALL_COEFFICIENTS.items():

        simulated_reactivated_users = (
            historical_potential_recall_users * coefficient
        )

        simulated_incremental_gmv = (
            simulated_reactivated_users
            * historical_second_order_avg_gmv
        )

        rows.append(
            {
                "problem_id": "CBP-03",
                "scenario": scenario,
                "target_users": target_users,
                "historical_repeat_users":
                    historical_repeat_users,
                "historical_repeat_share":
                    historical_repeat_share,
                "historical_potential_recall_users":
                    historical_potential_recall_users,
                "assumed_recall_coefficient":
                    coefficient,
                "simulated_reactivated_users":
                    simulated_reactivated_users,
                "historical_second_order_avg_gmv":
                    historical_second_order_avg_gmv,
                "simulated_incremental_gmv":
                    simulated_incremental_gmv,
                "estimate_type":
                    "historical_reference_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp03(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-03 RETENTION-USER RECALL SCENARIO ===")

    print(
        f"target_users={int(result.iloc[0]['target_users']):,} | "
        f"historical_repeat_users="
        f"{int(result.iloc[0]['historical_repeat_users']):,} | "
        f"repeat_share="
        f"{result.iloc[0]['historical_repeat_share']:.4%}"
    )

    print(
        "historical_second_order_avg_gmv="
        f"{result.iloc[0]['historical_second_order_avg_gmv']:.2f} BRL"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"coefficient={row.assumed_recall_coefficient:>4.0%}  "
            f"sim_users={row.simulated_reactivated_users:>8.2f}  "
            f"inc_gmv={row.simulated_incremental_gmv:>11.2f} BRL"
        )



CBP04_MULTI_ORDER_UPLIFT_RATES = {
    "conservative": 0.10,
    "neutral": 0.20,
    "optimistic": 0.30,
}


def calculate_cbp04() -> pd.DataFrame:
    """
    CBP-04 multi-product basket scenario.

    Historical basket type uses distinct product_id per delivered order.

    The difference between historical multi-product and single-product
    order GMV is used only as a structural reference, not as a causal
    recommendation effect.
    """

    db = sqlite3.connect(DB_PATH)

    sql = """
    WITH basket AS (
        SELECT
            order_id,
            COUNT(DISTINCT product_id) AS distinct_products
        FROM category_item_base
        GROUP BY order_id
    ),
    pay AS (
        SELECT
            order_id,
            SUM(payment_value) AS gmv
        FROM order_payments
        WHERE payment_value IS NOT NULL
          AND payment_value > 0
        GROUP BY order_id
    )
    SELECT
        CASE
            WHEN b.distinct_products = 1
                THEN 'single_product'
            ELSE 'multi_product'
        END AS basket_type,
        COUNT(*) AS delivered_orders,
        COUNT(p.gmv) AS paid_orders,
        AVG(p.gmv) AS avg_order_gmv,
        SUM(p.gmv) AS total_gmv
    FROM basket AS b
    LEFT JOIN pay AS p
        ON b.order_id = p.order_id
    GROUP BY basket_type
    """

    basket = pd.read_sql_query(sql, db)
    db.close()

    basket = basket.set_index("basket_type")

    single_orders = int(
        basket.loc["single_product", "delivered_orders"]
    )
    multi_orders = int(
        basket.loc["multi_product", "delivered_orders"]
    )

    single_avg_gmv = float(
        basket.loc["single_product", "avg_order_gmv"]
    )
    multi_avg_gmv = float(
        basket.loc["multi_product", "avg_order_gmv"]
    )

    if single_orders != 93281:
        raise ValueError(
            f"CBP-04 single-product baseline mismatch: {single_orders}"
        )

    if multi_orders != 3197:
        raise ValueError(
            f"CBP-04 multi-product baseline mismatch: {multi_orders}"
        )

    historical_value_gap = multi_avg_gmv - single_avg_gmv

    rows = []

    for scenario, uplift_rate in CBP04_MULTI_ORDER_UPLIFT_RATES.items():

        simulated_new_multi_orders = (
            multi_orders * uplift_rate
        )

        simulated_incremental_gmv = (
            simulated_new_multi_orders
            * historical_value_gap
        )

        rows.append(
            {
                "problem_id": "CBP-04",
                "scenario": scenario,
                "single_product_orders": single_orders,
                "multi_product_orders": multi_orders,
                "single_product_avg_gmv": single_avg_gmv,
                "multi_product_avg_gmv": multi_avg_gmv,
                "historical_value_gap": historical_value_gap,
                "assumed_multi_order_uplift": uplift_rate,
                "simulated_new_multi_orders":
                    simulated_new_multi_orders,
                "simulated_incremental_gmv":
                    simulated_incremental_gmv,
                "estimate_type":
                    "historical_structural_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp04(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-04 MULTI-PRODUCT BASKET SCENARIO ===")

    print(
        f"single_orders={int(result.iloc[0]['single_product_orders']):,} | "
        f"multi_orders={int(result.iloc[0]['multi_product_orders']):,}"
    )

    print(
        "historical_avg_gmv="
        f"{result.iloc[0]['single_product_avg_gmv']:.2f} single | "
        f"{result.iloc[0]['multi_product_avg_gmv']:.2f} multi | "
        f"gap={result.iloc[0]['historical_value_gap']:.2f} BRL"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"uplift={row.assumed_multi_order_uplift:>4.0%}  "
            f"new_multi={row.simulated_new_multi_orders:>8.2f}  "
            f"inc_gmv={row.simulated_incremental_gmv:>11.2f} BRL"
        )



CBP05_DELIVERY_REDUCTION_RATES = {
    "conservative": 0.05,
    "neutral": 0.10,
    "optimistic": 0.15,
}


def calculate_cbp05() -> pd.DataFrame:
    """
    CBP-05 office_furniture delivery-experience scenario.

    Historical delivery-time quartiles are used only as descriptive
    reference groups. Reduced delivery time does not imply that rating
    will causally improve to the historical mean of another group.

    Scenario outputs therefore describe:
        - orders crossing into a historically faster delivery group
        - historical score / one-star-rate reference space

    They are not causal score forecasts.
    """

    db = sqlite3.connect(DB_PATH)

    sql = """
    SELECT
        cob.order_id,
        JULIANDAY(o.order_delivered_customer_date)
            - JULIANDAY(o.order_purchase_timestamp)
            AS delivery_days,
        CAST(r.review_score AS REAL) AS review_score
    FROM category_order_base AS cob
    INNER JOIN vw_orders_clean AS o
        ON cob.order_id = o.order_id
    INNER JOIN vw_order_reviews_order_level AS r
        ON cob.order_id = r.order_id
    WHERE cob.category_name = 'office_furniture'
      AND o.order_status = 'delivered'
      AND r.review_score BETWEEN 1 AND 5
      AND DATETIME(o.order_purchase_timestamp) IS NOT NULL
      AND DATETIME(o.order_delivered_customer_date) IS NOT NULL
      AND JULIANDAY(o.order_delivered_customer_date)
          >= JULIANDAY(o.order_purchase_timestamp)
    """

    base = pd.read_sql_query(sql, db)
    db.close()

    if len(base) != 1244:
        raise ValueError(
            f"CBP-05 review-order baseline mismatch: {len(base)}"
        )

    base = base.sort_values(
        ["delivery_days", "order_id"]
    ).reset_index(drop=True)

    base["historical_quartile"] = pd.qcut(
        base.index,
        q=4,
        labels=[1, 2, 3, 4],
    ).astype(int)

    group_stats = (
        base.groupby("historical_quartile")
        .agg(
            min_days=("delivery_days", "min"),
            max_days=("delivery_days", "max"),
            avg_days=("delivery_days", "mean"),
            avg_score=("review_score", "mean"),
            one_star_rate=(
                "review_score",
                lambda s: (s == 1).mean(),
            ),
        )
    )

    q1_max = group_stats.loc[1, "max_days"]
    q2_max = group_stats.loc[2, "max_days"]
    q3_max = group_stats.loc[3, "max_days"]

    def assign_reference_group(days: float) -> int:
        if days <= q1_max:
            return 1
        if days <= q2_max:
            return 2
        if days <= q3_max:
            return 3
        return 4

    baseline_avg_score = base["review_score"].mean()
    baseline_one_star_rate = (base["review_score"] == 1).mean()

    rows = []

    for scenario, reduction_rate in CBP05_DELIVERY_REDUCTION_RATES.items():

        simulated = base.copy()

        simulated["simulated_delivery_days"] = (
            simulated["delivery_days"] * (1 - reduction_rate)
        )

        simulated["simulated_reference_group"] = (
            simulated["simulated_delivery_days"]
            .apply(assign_reference_group)
        )

        simulated["crossed_to_faster_group"] = (
            simulated["simulated_reference_group"]
            < simulated["historical_quartile"]
        )

        affected_orders = int(
            simulated["crossed_to_faster_group"].sum()
        )

        reference_scores = simulated[
            "simulated_reference_group"
        ].map(group_stats["avg_score"])

        reference_one_star_rates = simulated[
            "simulated_reference_group"
        ].map(group_stats["one_star_rate"])

        reference_avg_score = reference_scores.mean()
        reference_one_star_rate = reference_one_star_rates.mean()

        rows.append(
            {
                "problem_id": "CBP-05",
                "scenario": scenario,
                "review_orders": len(base),
                "baseline_avg_score": baseline_avg_score,
                "baseline_one_star_rate":
                    baseline_one_star_rate,
                "assumed_delivery_reduction":
                    reduction_rate,
                "affected_orders":
                    affected_orders,
                "affected_order_share":
                    affected_orders / len(base),
                "historical_reference_avg_score":
                    reference_avg_score,
                "historical_reference_score_gap":
                    reference_avg_score - baseline_avg_score,
                "historical_reference_one_star_rate":
                    reference_one_star_rate,
                "historical_reference_one_star_rate_gap":
                    reference_one_star_rate
                    - baseline_one_star_rate,
                "estimate_type":
                    "historical_experience_reference_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp05(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-05 DELIVERY-EXPERIENCE SCENARIO ===")

    print(
        f"review_orders={int(result.iloc[0]['review_orders']):,} | "
        f"baseline_score={result.iloc[0]['baseline_avg_score']:.4f} | "
        f"baseline_1star="
        f"{result.iloc[0]['baseline_one_star_rate']:.2%}"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"delivery_reduction={row.assumed_delivery_reduction:>4.0%}  "
            f"affected={row.affected_orders:>4} "
            f"({row.affected_order_share:>6.2%})  "
            f"ref_score_gap={row.historical_reference_score_gap:>7.4f}  "
            f"ref_1star_gap="
            f"{row.historical_reference_one_star_rate_gap:>7.2%}"
        )



CBP06_REGIONAL_GMV_UPLIFT_RATES = {
    "conservative": 0.05,
    "neutral": 0.10,
    "optimistic": 0.15,
}


def calculate_cbp06(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    CBP-06 regional pilot scenario.

    Candidate states reuse the formal Stage 3 historical screening labels:

        - exclude SP / RJ / MG
        - is_sample_eligible == 1
        - and either:
            is_large_scale_low_spend == 1
            or
            is_medium_scale_fast_growth == 1

    Formal scenario baseline:
        recent six-month window 2018-02 through 2018-07.

    Uplift rates are business assumptions, not causal forecasts.
    """

    regional = data["potential_regional_markets"].copy()

    numeric_columns = [
        "is_sample_eligible",
        "is_large_scale_low_spend",
        "is_medium_scale_fast_growth",
        "recent_gmv",
    ]

    for column in numeric_columns:
        regional[column] = pd.to_numeric(
            regional[column],
            errors="coerce",
        )

    expected_prior_start = {"2017-08"}
    expected_prior_end = {"2018-01"}
    expected_recent_start = {"2018-02"}
    expected_recent_end = {"2018-07"}

    if set(regional["prior_start_month"].dropna().astype(str)) != expected_prior_start:
        raise ValueError("CBP-06 prior start window mismatch")

    if set(regional["prior_end_month"].dropna().astype(str)) != expected_prior_end:
        raise ValueError("CBP-06 prior end window mismatch")

    if set(regional["recent_start_month"].dropna().astype(str)) != expected_recent_start:
        raise ValueError("CBP-06 recent start window mismatch")

    if set(regional["recent_end_month"].dropna().astype(str)) != expected_recent_end:
        raise ValueError("CBP-06 recent end window mismatch")

    candidates = regional.loc[
        (~regional["customer_state"].isin(["SP", "RJ", "MG"]))
        & (regional["is_sample_eligible"] == 1)
        & (
            (regional["is_large_scale_low_spend"] == 1)
            | (regional["is_medium_scale_fast_growth"] == 1)
        )
    ].copy()

    candidate_states = sorted(
        candidates["customer_state"].astype(str).tolist()
    )

    expected_states = [
        "BA",
        "DF",
        "ES",
        "GO",
        "MS",
        "PR",
        "RS",
        "SC",
    ]

    if candidate_states != expected_states:
        raise ValueError(
            "CBP-06 candidate-state mismatch: "
            f"{candidate_states}"
        )

    candidate_recent_gmv = candidates["recent_gmv"].sum()

    if round(candidate_recent_gmv, 2) != 1663859.03:
        raise ValueError(
            "CBP-06 recent-GMV baseline mismatch: "
            f"{candidate_recent_gmv}"
        )

    rows = []

    for scenario, uplift_rate in CBP06_REGIONAL_GMV_UPLIFT_RATES.items():

        simulated_incremental_gmv = (
            candidate_recent_gmv * uplift_rate
        )

        simulated_candidate_gmv = (
            candidate_recent_gmv
            + simulated_incremental_gmv
        )

        rows.append(
            {
                "problem_id": "CBP-06",
                "scenario": scenario,
                "candidate_state_count": len(candidates),
                "candidate_states": ",".join(candidate_states),
                "baseline_window":
                    "2018-02_to_2018-07",
                "candidate_recent_gmv":
                    candidate_recent_gmv,
                "assumed_gmv_uplift":
                    uplift_rate,
                "simulated_incremental_gmv":
                    simulated_incremental_gmv,
                "simulated_candidate_gmv":
                    simulated_candidate_gmv,
                "estimate_type":
                    "historical_regional_pilot_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp06(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-06 REGIONAL PILOT SCENARIO ===")

    print(
        f"candidate_states="
        f"{int(result.iloc[0]['candidate_state_count'])} | "
        f"{result.iloc[0]['candidate_states']}"
    )

    print(
        "recent_6m_gmv="
        f"{result.iloc[0]['candidate_recent_gmv']:.2f} BRL"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"uplift={row.assumed_gmv_uplift:>4.0%}  "
            f"inc_gmv={row.simulated_incremental_gmv:>11.2f} BRL  "
            f"sim_gmv={row.simulated_candidate_gmv:>12.2f} BRL"
        )



CBP07_CREDIT_CARD_SHARE_REDUCTION_PP = {
    "conservative": 0.02,
    "neutral": 0.05,
    "optimistic": 0.10,
}


def calculate_cbp07(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    CBP-07 payment-structure scenario.

    Scenario means credit-card GMV share decreases by a stated number
    of percentage points while total platform GMV is held constant.

    Therefore:
        shifted GMV = total platform GMV x share reduction

    Shifted GMV is NOT incremental GMV.
    """

    payment = data["payment_structure"].copy()

    payment["split_gmv"] = pd.to_numeric(
        payment["split_gmv"],
        errors="coerce",
    )

    payment["primary_order_count"] = pd.to_numeric(
        payment["primary_order_count"],
        errors="coerce",
    )

    payment["total_gmv"] = pd.to_numeric(
        payment["total_gmv"],
        errors="coerce",
    )

    payment["total_paid_orders"] = pd.to_numeric(
        payment["total_paid_orders"],
        errors="coerce",
    )

    all_data = payment.loc[
        payment["period"] == "ALL_DATA"
    ].copy()

    credit = all_data.loc[
        all_data["payment_type"] == "credit_card"
    ].iloc[0]

    total_gmv = float(credit["total_gmv"])
    total_paid_orders = int(credit["total_paid_orders"])

    credit_card_gmv = float(credit["split_gmv"])
    credit_card_primary_orders = int(
        credit["primary_order_count"]
    )

    if round(total_gmv, 2) != 15422461.77:
        raise ValueError(
            f"CBP-07 total-GMV baseline mismatch: {total_gmv}"
        )

    if total_paid_orders != 96477:
        raise ValueError(
            "CBP-07 paid-order baseline mismatch: "
            f"{total_paid_orders}"
        )

    if round(credit_card_gmv, 2) != 12101094.88:
        raise ValueError(
            "CBP-07 credit-card GMV mismatch: "
            f"{credit_card_gmv}"
        )

    if credit_card_primary_orders != 72785:
        raise ValueError(
            "CBP-07 credit-card order mismatch: "
            f"{credit_card_primary_orders}"
        )

    credit_card_gmv_share = (
        credit_card_gmv / total_gmv
    )

    credit_card_order_share = (
        credit_card_primary_orders / total_paid_orders
    )

    rows = []

    for scenario, reduction_pp in (
        CBP07_CREDIT_CARD_SHARE_REDUCTION_PP.items()
    ):

        shifted_gmv = total_gmv * reduction_pp

        simulated_credit_card_share = (
            credit_card_gmv_share - reduction_pp
        )

        rows.append(
            {
                "problem_id": "CBP-07",
                "scenario": scenario,
                "total_gmv": total_gmv,
                "total_paid_orders": total_paid_orders,
                "credit_card_gmv": credit_card_gmv,
                "credit_card_gmv_share":
                    credit_card_gmv_share,
                "credit_card_primary_orders":
                    credit_card_primary_orders,
                "credit_card_order_share":
                    credit_card_order_share,
                "assumed_share_reduction_pp":
                    reduction_pp,
                "simulated_shifted_gmv":
                    shifted_gmv,
                "simulated_credit_card_share":
                    simulated_credit_card_share,
                "simulated_incremental_gmv": 0.0,
                "estimate_type":
                    "payment_structure_shift_scenario",
            }
        )

    return pd.DataFrame(rows)


def print_cbp07(result: pd.DataFrame) -> None:
    print()
    print("=== CBP-07 PAYMENT-STRUCTURE SCENARIO ===")

    print(
        f"total_gmv={result.iloc[0]['total_gmv']:.2f} BRL | "
        f"credit_card_share="
        f"{result.iloc[0]['credit_card_gmv_share']:.4%} | "
        f"credit_card_order_share="
        f"{result.iloc[0]['credit_card_order_share']:.4%}"
    )

    for row in result.itertuples(index=False):
        print(
            f"{row.scenario:<12} "
            f"share_reduction="
            f"{row.assumed_share_reduction_pp * 100:>4.0f}pp  "
            f"shifted_gmv={row.simulated_shifted_gmv:>12.2f} BRL  "
            f"new_cc_share="
            f"{row.simulated_credit_card_share:>7.2%}"
        )



PRIORITY_WEIGHTS = {
    "effect": 0.50,
    "feasibility": 0.30,
    "cost_controllability": 0.20,
}


STRATEGY_SCORECARD = [
    {
        "problem_id": "CBP-01",
        "strategy_name": "单次购买用户分层二购提升",
        "effect_score": 5,
        "feasibility_score": 5,
        "cost_controllability_score": 4,
        "effect_rationale":
            "覆盖84,593名单次购买用户，直接关系复购基础和客户长期价值；"
            "已完成复购用户及增量GMV情景测算。",
        "feasibility_rationale":
            "用户级目标群、历史订单和第二笔订单基准均已具备，"
            "可通过分层触达和小规模对照实验实施。",
        "cost_rationale":
            "可先对高潜力用户定向触达，避免全量补贴，资源范围较易控制。",
    },
    {
        "problem_id": "CBP-02",
        "strategy_name": "AOV提升与加购组合试验",
        "effect_score": 5,
        "feasibility_score": 4,
        "cost_controllability_score": 3,
        "effect_rationale":
            "2018年1至7月支付订单规模较大，AOV提升情景对应的GMV空间明显。",
        "feasibility_rationale":
            "历史订单结构与AOV基准完整，可进行加购、组合或价格带小流量测试，"
            "但需要商品展示和运营配合。",
        "cost_rationale":
            "组合、满减或多件购可能涉及优惠成本和产品改造，"
            "需同时控制订单量与转化率。",
    },
    {
        "problem_id": "CBP-03",
        "strategy_name": "重要挽留用户分层召回",
        "effect_score": 4,
        "feasibility_score": 4,
        "cost_controllability_score": 4,
        "effect_rationale":
            "目标群20,391人且历史GMV贡献高，召回具有明确业务价值，"
            "但历史价值不能直接视为未来可恢复收入。",
        "feasibility_rationale":
            "RFM、历史复购及第二笔订单数据完整，可直接进行用户分层试验。",
        "cost_rationale":
            "可按历史价值和Recency定向触达，避免对全体用户统一投入。",
    },
    {
        "problem_id": "CBP-04",
        "strategy_name": "多商品购物篮小流量推荐试验",
        "effect_score": 3,
        "feasibility_score": 3,
        "cost_controllability_score": 4,
        "effect_rationale":
            "多商品订单历史价值更高，但正式跨品类规则仅1条，"
            "当前增量只属于历史结构参考情景。",
        "feasibility_rationale":
            "可以进行小流量推荐实验，但候选规则稀疏且缺少推荐曝光数据。",
        "cost_rationale":
            "可从少量高流量页面和购物车入口开始验证，试点范围较容易控制。",
    },
    {
        "problem_id": "CBP-05",
        "strategy_name": "office_furniture配送体验定向优化",
        "effect_score": 3,
        "feasibility_score": 3,
        "cost_controllability_score": 3,
        "effect_rationale":
            "配送时长与评分、1星率存在清晰历史梯度，但影响集中于特定品类，"
            "且不能直接解释为因果关系。",
        "feasibility_rationale":
            "需要进一步定位卖家、SKU或履约环节后才能实施定向整改。",
        "cost_rationale":
            "物流与履约优化可能涉及商家和运营协作，实际成本字段当前缺失。",
    },
    {
        "problem_id": "CBP-06",
        "strategy_name": "非核心州分层区域试点",
        "effect_score": 4,
        "feasibility_score": 2,
        "cost_controllability_score": 2,
        "effect_rationale":
            "8个候选州具有一定近期GMV规模，区域试点存在增长空间，"
            "且问题业务优先级为高。",
        "feasibility_rationale":
            "缺少人口、获客成本、物流成本和市场容量等关键外部数据，"
            "只能先做小范围试点。",
        "cost_rationale":
            "区域扩张可能需要营销、履约和供给资源，投入规模和单位经济性尚不明确。",
    },
    {
        "problem_id": "CBP-07",
        "strategy_name": "支付观测与备用渠道验证",
        "effect_score": 2,
        "feasibility_score": 2,
        "cost_controllability_score": 3,
        "effect_rationale":
            "信用卡集中度较高，但当前只能量化渠道结构迁移，"
            "未观察到可归因的新增GMV或实际支付损失。",
        "feasibility_rationale":
            "缺少支付成功率、失败率、费率、拒付和重试等关键链路数据，"
            "应先补充监控体系。",
        "cost_rationale":
            "支付监控本身可控，但备用路由或渠道系统改造的真实成本目前未知。",
    },
]


def build_priority_matrix(
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Build the formal Member 3 strategy priority matrix.

    Scores are analyst assessments under documented 1-5 rubrics.
    They are not historical measurements.
    """

    matrix = pd.DataFrame(STRATEGY_SCORECARD)

    if set(matrix["problem_id"]) != EXPECTED_PROBLEM_IDS:
        raise ValueError(
            "Priority scorecard does not cover CBP-01 through CBP-07"
        )

    if len(matrix) != 7:
        raise ValueError(
            f"Expected 7 strategies, found {len(matrix)}"
        )

    score_columns = [
        "effect_score",
        "feasibility_score",
        "cost_controllability_score",
    ]

    for column in score_columns:
        if not matrix[column].between(1, 5).all():
            raise ValueError(
                f"Invalid 1-5 score detected in {column}"
            )

    matrix["priority_score"] = (
        matrix["effect_score"] * PRIORITY_WEIGHTS["effect"]
        + matrix["feasibility_score"]
        * PRIORITY_WEIGHTS["feasibility"]
        + matrix["cost_controllability_score"]
        * PRIORITY_WEIGHTS["cost_controllability"]
    ).round(2)

    matrix["priority_level"] = pd.cut(
        matrix["priority_score"],
        bins=[0, 3.0, 4.0, 5.01],
        labels=["low", "medium", "high"],
        right=False,
    ).astype(str)

    problem_meta = data["core_problem_summary"][
        [
            "problem_id",
            "problem_title",
            "business_priority",
            "evidence_strength",
        ]
    ].copy()

    matrix = matrix.merge(
        problem_meta,
        on="problem_id",
        how="left",
        validate="one_to_one",
    )

    business_priority_order = {
        "高": 2,
        "中高": 1,
        "中": 0,
    }

    matrix["_business_priority_order"] = (
        matrix["business_priority"]
        .map(business_priority_order)
        .fillna(-1)
    )

    matrix = matrix.sort_values(
        [
            "priority_score",
            "_business_priority_order",
            "problem_id",
        ],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    matrix["priority_rank"] = (
        matrix.index + 1
    )

    matrix = matrix.drop(
        columns=["_business_priority_order"]
    )

    return matrix


def print_priority_matrix(matrix: pd.DataFrame) -> None:
    print()
    print("=== STRATEGY PRIORITY MATRIX ===")

    for row in matrix.itertuples(index=False):
        print(
            f"#{row.priority_rank} "
            f"{row.problem_id}  "
            f"effect={row.effect_score}  "
            f"feas={row.feasibility_score}  "
            f"cost={row.cost_controllability_score}  "
            f"score={row.priority_score:.2f}  "
            f"level={row.priority_level}"
        )



OUTPUT_DIR = ROOT / "outputs/data/strategy"
PRIORITY_OUTPUT = OUTPUT_DIR / "strategy_priority_matrix.csv"
EFFECT_OUTPUT = OUTPUT_DIR / "strategy_effect_estimation.csv"


def build_effect_estimation(
    cbp01: pd.DataFrame,
    cbp02: pd.DataFrame,
    cbp03: pd.DataFrame,
    cbp04: pd.DataFrame,
    cbp05: pd.DataFrame,
    cbp06: pd.DataFrame,
    cbp07: pd.DataFrame,
) -> pd.DataFrame:
    """
    Standardize seven heterogeneous scenario models into one formal
    effect-estimation table.

    The table explicitly separates:
        - growth / GMV scenarios
        - experience reference scenarios
        - payment structure shift scenarios

    Missing values mean the metric is not applicable, not zero.
    """

    rows = []

    for row in cbp01.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-01",
                "scenario": row.scenario,
                "effect_type": "repeat_purchase_growth",
                "assumption":
                    f"historical repeat rate relative uplift "
                    f"{row.assumed_relative_uplift:.0%}",
                "target_scope":
                    f"{int(row.target_users)} single-purchase users",
                "primary_metric":
                    "incremental_repeat_users",
                "primary_effect_value":
                    row.incremental_repeat_users,
                "primary_effect_unit":
                    "users",
                "simulated_incremental_gmv_brl":
                    row.simulated_incremental_gmv,
                "reference_value":
                    row.historical_second_order_avg_gmv,
                "reference_unit":
                    "BRL historical second-order average GMV",
                "interpretation_limit":
                    "Historical reference scenario; not causal forecast.",
            }
        )

    for row in cbp02.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-02",
                "scenario": row.scenario,
                "effect_type": "aov_growth",
                "assumption":
                    f"AOV uplift {row.assumed_aov_uplift:.0%}; "
                    "paid orders held constant",
                "target_scope":
                    f"{int(row.baseline_paid_orders)} paid orders "
                    "in 2018-01 to 2018-07",
                "primary_metric":
                    "simulated_aov",
                "primary_effect_value":
                    row.simulated_aov,
                "primary_effect_unit":
                    "BRL/order",
                "simulated_incremental_gmv_brl":
                    row.simulated_incremental_gmv,
                "reference_value":
                    row.baseline_aov,
                "reference_unit":
                    "BRL/order baseline AOV",
                "interpretation_limit":
                    "Mathematical scenario with order volume held constant.",
            }
        )

    for row in cbp03.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-03",
                "scenario": row.scenario,
                "effect_type": "retention_user_recall",
                "assumption":
                    f"historical potential recall users x "
                    f"{row.assumed_recall_coefficient:.0%}",
                "target_scope":
                    f"{int(row.target_users)} important retention users",
                "primary_metric":
                    "simulated_reactivated_users",
                "primary_effect_value":
                    row.simulated_reactivated_users,
                "primary_effect_unit":
                    "users",
                "simulated_incremental_gmv_brl":
                    row.simulated_incremental_gmv,
                "reference_value":
                    row.historical_second_order_avg_gmv,
                "reference_unit":
                    "BRL historical second-order average GMV",
                "interpretation_limit":
                    "Historical RFM reference; not future recall probability.",
            }
        )

    for row in cbp04.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-04",
                "scenario": row.scenario,
                "effect_type": "basket_structure",
                "assumption":
                    f"multi-product order count relative uplift "
                    f"{row.assumed_multi_order_uplift:.0%}",
                "target_scope":
                    f"{int(row.multi_product_orders)} historical "
                    "multi-product orders",
                "primary_metric":
                    "simulated_new_multi_orders",
                "primary_effect_value":
                    row.simulated_new_multi_orders,
                "primary_effect_unit":
                    "orders",
                "simulated_incremental_gmv_brl":
                    row.simulated_incremental_gmv,
                "reference_value":
                    row.historical_value_gap,
                "reference_unit":
                    "BRL historical multi-vs-single order GMV gap",
                "interpretation_limit":
                    "Structural reference only; association is not causal.",
            }
        )

    for row in cbp05.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-05",
                "scenario": row.scenario,
                "effect_type": "delivery_experience",
                "assumption":
                    f"delivery time reduction "
                    f"{row.assumed_delivery_reduction:.0%}",
                "target_scope":
                    f"{int(row.review_orders)} office_furniture "
                    "review orders",
                "primary_metric":
                    "orders_crossing_to_faster_reference_group",
                "primary_effect_value":
                    row.affected_orders,
                "primary_effect_unit":
                    "orders",
                "simulated_incremental_gmv_brl":
                    None,
                "reference_value":
                    row.historical_reference_score_gap,
                "reference_unit":
                    "historical rating reference gap",
                "interpretation_limit":
                    "Historical delivery-rating association; "
                    "not predicted rating uplift.",
            }
        )

    for row in cbp06.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-06",
                "scenario": row.scenario,
                "effect_type": "regional_pilot_growth",
                "assumption":
                    f"candidate-state GMV uplift "
                    f"{row.assumed_gmv_uplift:.0%}",
                "target_scope":
                    f"{int(row.candidate_state_count)} states: "
                    f"{row.candidate_states}",
                "primary_metric":
                    "simulated_candidate_gmv",
                "primary_effect_value":
                    row.simulated_candidate_gmv,
                "primary_effect_unit":
                    "BRL",
                "simulated_incremental_gmv_brl":
                    row.simulated_incremental_gmv,
                "reference_value":
                    row.candidate_recent_gmv,
                "reference_unit":
                    "BRL recent six-month candidate-state GMV",
                "interpretation_limit":
                    "Historical regional pilot scenario; "
                    "not forecast state growth.",
            }
        )

    for row in cbp07.itertuples(index=False):
        rows.append(
            {
                "problem_id": "CBP-07",
                "scenario": row.scenario,
                "effect_type": "payment_structure_shift",
                "assumption":
                    f"credit-card GMV share reduction "
                    f"{row.assumed_share_reduction_pp * 100:.0f}pp",
                "target_scope":
                    "all platform payment GMV",
                "primary_metric":
                    "simulated_shifted_gmv",
                "primary_effect_value":
                    row.simulated_shifted_gmv,
                "primary_effect_unit":
                    "BRL shifted between payment channels",
                "simulated_incremental_gmv_brl":
                    0.0,
                "reference_value":
                    row.credit_card_gmv_share,
                "reference_unit":
                    "historical credit-card GMV share",
                "interpretation_limit":
                    "Channel redistribution only; not incremental GMV.",
            }
        )

    result = pd.DataFrame(rows)

    if len(result) != 21:
        raise ValueError(
            f"Expected 21 effect scenario rows, found {len(result)}"
        )

    return result


def export_outputs(
    priority_matrix: pd.DataFrame,
    effect_estimation: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    priority_columns = [
        "priority_rank",
        "problem_id",
        "problem_title",
        "strategy_name",
        "business_priority",
        "evidence_strength",
        "effect_score",
        "feasibility_score",
        "cost_controllability_score",
        "priority_score",
        "priority_level",
        "effect_rationale",
        "feasibility_rationale",
        "cost_rationale",
    ]

    priority_matrix[
        priority_columns
    ].to_csv(
        PRIORITY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    effect_estimation.to_csv(
        EFFECT_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=== FORMAL OUTPUTS ===")
    print(f"priority matrix -> {PRIORITY_OUTPUT.relative_to(ROOT)}")
    print(f"effect estimation -> {EFFECT_OUTPUT.relative_to(ROOT)}")
    print(
        f"rows: priority={len(priority_matrix)}, "
        f"effect={len(effect_estimation)}"
    )

def main() -> None:
    data = load_inputs()
    run_input_qa(data)

    cbp01 = calculate_cbp01(data)
    print_cbp01(cbp01)

    cbp02 = calculate_cbp02(data)
    print_cbp02(cbp02)

    cbp03 = calculate_cbp03(data)
    print_cbp03(cbp03)

    cbp04 = calculate_cbp04()
    print_cbp04(cbp04)

    cbp05 = calculate_cbp05()
    print_cbp05(cbp05)

    cbp06 = calculate_cbp06(data)
    print_cbp06(cbp06)

    cbp07 = calculate_cbp07(data)
    print_cbp07(cbp07)

    priority_matrix = build_priority_matrix(data)
    print_priority_matrix(priority_matrix)

    effect_estimation = build_effect_estimation(
        cbp01, cbp02, cbp03, cbp04, cbp05, cbp06, cbp07
    )
    export_outputs(priority_matrix, effect_estimation)


if __name__ == "__main__":
    main()
