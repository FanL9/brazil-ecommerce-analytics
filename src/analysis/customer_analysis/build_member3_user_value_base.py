from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Build unified user-value analysis base
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Grain:
# one row per customer_unique_id
# ============================================================

OBSERVATION_DATE = pd.Timestamp("2018-07-31")
CUTOFF_TIMESTAMP = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

ORDER_BASE_PATH = DATA_DIR / "customer_order_base.csv"
RFM_PATH = DATA_DIR / "rfm_customer_detail.csv"
CHURN_PATH = DATA_DIR / "churn_user_detail.csv"

OUTPUT_PATH = DATA_DIR / "member3_user_value_base.csv"


def main():

    print("=" * 72)
    print("BUILD MEMBER 3 UNIFIED USER VALUE BASE")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load source data
    # --------------------------------------------------------
    orders = pd.read_csv(
        ORDER_BASE_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    rfm = pd.read_csv(
        RFM_PATH,
        parse_dates=["observation_date"],
    )

    churn = pd.read_csv(
        CHURN_PATH,
        parse_dates=["observation_date"],
    )

    print("\n[1] SOURCE DATA")
    print(f"Order-base rows: {len(orders):,}")
    print(f"RFM users: {len(rfm):,}")
    print(f"Churn users: {len(churn):,}")

    # --------------------------------------------------------
    # 2. Fixed observation window
    # --------------------------------------------------------
    orders = orders[
        orders["order_purchase_timestamp"] < CUTOFF_TIMESTAMP
    ].copy()

    print("\n[2] FIXED OBSERVATION WINDOW")
    print(f"Orders before cutoff: {len(orders):,}")
    print(
        f"Customers before cutoff: "
        f"{orders['customer_unique_id'].nunique():,}"
    )

    if len(orders) != 90127:
        raise ValueError(
            f"Expected 90,127 orders before cutoff, got {len(orders):,}"
        )

    if orders["customer_unique_id"].nunique() != 87214:
        raise ValueError(
            "Fixed-cutoff customer population is not 87,214."
        )

    print("Fixed observation window: PASS")

    # --------------------------------------------------------
    # 3. Validate RFM / churn user grain
    # --------------------------------------------------------
    if rfm["customer_unique_id"].duplicated().any():
        raise ValueError(
            "RFM contains duplicated customer_unique_id."
        )

    if churn["customer_unique_id"].duplicated().any():
        raise ValueError(
            "Churn contains duplicated customer_unique_id."
        )

    if not rfm["observation_date"].eq(OBSERVATION_DATE).all():
        raise ValueError(
            "RFM observation date is not uniformly 2018-07-31."
        )

    if not churn["observation_date"].eq(OBSERVATION_DATE).all():
        raise ValueError(
            "Churn observation date is not uniformly 2018-07-31."
        )

    print("\n[3] CROSS-MEMBER INPUT VALIDATION")
    print("RFM one row per customer: PASS")
    print("Churn one row per customer: PASS")
    print("Observation date: PASS")

    # --------------------------------------------------------
    # 4. Derive representative user geography
    #
    # Unified rule:
    # latest valid order before cutoff
    # tie-break:
    # order_id DESC, customer_id DESC
    # --------------------------------------------------------
    geo_source = orders[
        [
            "customer_unique_id",
            "customer_id",
            "order_id",
            "order_purchase_timestamp",
            "customer_state",
            "customer_city",
        ]
    ].copy()

    geo_source = geo_source.sort_values(
        by=[
            "customer_unique_id",
            "order_purchase_timestamp",
            "order_id",
            "customer_id",
        ],
        ascending=[True, True, True, True],
    )

    latest_geo = (
        geo_source
        .drop_duplicates(
            subset=["customer_unique_id"],
            keep="last",
        )
        .rename(
            columns={
                "order_id": "latest_order_id",
                "order_purchase_timestamp":
                    "latest_order_purchase_timestamp",
                "customer_state": "profile_state",
                "customer_city": "profile_city",
            }
        )
    )

    latest_geo = latest_geo[
        [
            "customer_unique_id",
            "latest_order_id",
            "latest_order_purchase_timestamp",
            "profile_state",
            "profile_city",
        ]
    ]

    print("\n[4] REPRESENTATIVE GEOGRAPHY")
    print(f"User rows: {len(latest_geo):,}")
    print(
        f"Missing profile_state: "
        f"{latest_geo['profile_state'].isna().sum():,}"
    )
    print(
        f"Missing profile_city: "
        f"{latest_geo['profile_city'].isna().sum():,}"
    )

    if len(latest_geo) != 87214:
        raise ValueError(
            "Representative geography does not contain 87,214 users."
        )

    print("Representative geography: PASS")

    # --------------------------------------------------------
    # 5. Prepare RFM fields
    # --------------------------------------------------------
    rfm_fields = rfm[
        [
            "customer_unique_id",
            "recency_days",
            "frequency",
            "monetary",
            "r_score",
            "f_score",
            "m_score",
            "rfm_score",
            "rfm_code",
            "rfm_segment",
            "observation_date",
        ]
    ].rename(
        columns={
            "observation_date": "rfm_observation_date",
        }
    )

    # --------------------------------------------------------
    # 6. Prepare churn fields
    # --------------------------------------------------------
    churn_fields = churn[
        [
            "customer_unique_id",
            "churn_flag",
            "observation_date",
        ]
    ].rename(
        columns={
            "observation_date": "churn_observation_date",
        }
    )

    # --------------------------------------------------------
    # 7. Merge user-level data
    # --------------------------------------------------------
    base = latest_geo.merge(
        rfm_fields,
        on="customer_unique_id",
        how="inner",
        validate="one_to_one",
    )

    base = base.merge(
        churn_fields,
        on="customer_unique_id",
        how="inner",
        validate="one_to_one",
    )

    print("\n[5] FINAL USER-LEVEL MERGE")
    print(f"Rows: {len(base):,}")
    print(
        f"Unique customers: "
        f"{base['customer_unique_id'].nunique():,}"
    )

    if len(base) != 87214:
        raise ValueError(
            f"Expected 87,214 users, got {len(base):,}"
        )

    # --------------------------------------------------------
    # 8. Unified high-value / churn flags
    # --------------------------------------------------------
    base["is_high_value_user"] = (
        base["rfm_segment"] == "重要价值用户"
    ).astype(int)

    base["is_high_value_churn_user"] = (
        (base["is_high_value_user"] == 1)
        & (base["churn_flag"].astype(int) == 1)
    ).astype(int)

    high_value_count = (
        base["is_high_value_user"] == 1
    ).sum()

    high_value_churn_count = (
        base["is_high_value_churn_user"] == 1
    ).sum()

    print("\n[6] HIGH-VALUE CROSS-CHECK")
    print(
        f"Important Value Users: "
        f"{high_value_count:,}"
    )
    print(
        f"High-value churn users: "
        f"{high_value_churn_count:,}"
    )

    if high_value_count != 4:
        raise ValueError(
            f"Expected 4 Important Value Users, got {high_value_count}."
        )

    if high_value_churn_count != 1:
        raise ValueError(
            "Expected 1 high-value churn user."
        )

    print("High-value cross-check: PASS")

    # --------------------------------------------------------
    # 9. Final validation
    # --------------------------------------------------------
    churn_rule_ok = (
        base["churn_flag"].astype(int)
        == (base["recency_days"] > 90).astype(int)
    ).all()

    if not churn_rule_ok:
        raise ValueError(
            "churn_flag conflicts with recency_days > 90."
        )

    high_value_rule_ok = (
        base["is_high_value_user"].astype(bool)
        == (
            (base["r_score"] >= 4)
            & (base["f_score"] >= 4)
            & (base["m_score"] >= 4)
        )
    ).all()

    if not high_value_rule_ok:
        raise ValueError(
            "High-value classification conflicts with R/F/M >= 4."
        )

    print("\n[7] UNIFIED RULE VALIDATION")
    print("Churn = recency_days > 90: PASS")
    print("High-value = high R/F/M: PASS")

    # --------------------------------------------------------
    # 10. Save reproducible base
    # --------------------------------------------------------
    base.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[8] OUTPUT")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows written: {len(base):,}")

    print("\n" + "=" * 72)
    print("FINAL RESULT: PASS")
    print("Member 3 unified user-value base successfully created.")
    print("=" * 72)


if __name__ == "__main__":
    main()
