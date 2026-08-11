from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# RFM x Churn cross-member validation
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
# ============================================================

OBSERVATION_DATE = pd.Timestamp("2018-07-31")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

RFM_PATH = DATA_DIR / "rfm_customer_detail.csv"
CHURN_PATH = DATA_DIR / "churn_user_detail.csv"


def main():
    print("=" * 70)
    print("RFM x CHURN CROSS-MEMBER VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load data
    # --------------------------------------------------------
    rfm = pd.read_csv(RFM_PATH)
    churn = pd.read_csv(CHURN_PATH)

    print("\n[1] SOURCE DATA")
    print(f"RFM rows: {len(rfm):,}")
    print(f"Churn rows: {len(churn):,}")

    # --------------------------------------------------------
    # 2. Required columns
    # --------------------------------------------------------
    rfm_required = [
        "customer_unique_id",
        "recency_days",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_segment",
        "observation_date",
    ]

    churn_required = [
        "customer_unique_id",
        "recency_days",
        "churn_flag",
        "observation_date",
    ]

    missing_rfm = [c for c in rfm_required if c not in rfm.columns]
    missing_churn = [c for c in churn_required if c not in churn.columns]

    if missing_rfm:
        raise ValueError(
            f"RFM missing required columns: {missing_rfm}"
        )

    if missing_churn:
        raise ValueError(
            f"Churn missing required columns: {missing_churn}"
        )

    print("\n[2] REQUIRED COLUMNS")
    print("RFM required columns: PASS")
    print("Churn required columns: PASS")

    # --------------------------------------------------------
    # 3. User-grain validation
    # --------------------------------------------------------
    rfm_dup = rfm["customer_unique_id"].duplicated().sum()
    churn_dup = churn["customer_unique_id"].duplicated().sum()

    if rfm_dup != 0:
        raise ValueError(
            f"RFM has duplicated customer_unique_id: {rfm_dup}"
        )

    if churn_dup != 0:
        raise ValueError(
            f"Churn has duplicated customer_unique_id: {churn_dup}"
        )

    print("\n[3] USER GRAIN")
    print("RFM one row per customer_unique_id: PASS")
    print("Churn one row per customer_unique_id: PASS")

    # --------------------------------------------------------
    # 4. Observation-date validation
    # --------------------------------------------------------
    rfm["observation_date"] = pd.to_datetime(
        rfm["observation_date"]
    )

    churn["observation_date"] = pd.to_datetime(
        churn["observation_date"]
    )

    rfm_date_ok = rfm["observation_date"].eq(
        OBSERVATION_DATE
    ).all()

    churn_date_ok = churn["observation_date"].eq(
        OBSERVATION_DATE
    ).all()

    if not rfm_date_ok:
        raise ValueError(
            "RFM observation_date is not uniformly 2018-07-31"
        )

    if not churn_date_ok:
        raise ValueError(
            "Churn observation_date is not uniformly 2018-07-31"
        )

    print("\n[4] OBSERVATION DATE")
    print("RFM observation date: PASS")
    print("Churn observation date: PASS")

    # --------------------------------------------------------
    # 5. Unified-rule validation before merge
    # --------------------------------------------------------
    churn_rule_ok = (
        churn["churn_flag"].astype(int)
        == (churn["recency_days"] > 90).astype(int)
    ).all()

    if not churn_rule_ok:
        raise ValueError(
            "churn_flag conflicts with recency_days > 90"
        )

    high_value_rule = (
        (rfm["r_score"] >= 4)
        & (rfm["f_score"] >= 4)
        & (rfm["m_score"] >= 4)
    )

    segment_rule = (
        rfm["rfm_segment"] == "重要价值用户"
    )

    high_value_rule_ok = high_value_rule.eq(
        segment_rule
    ).all()

    if not high_value_rule_ok:
        raise ValueError(
            "Important Value User classification conflicts "
            "with high R/F/M >= 4 rule"
        )

    print("\n[5] UNIFIED BUSINESS RULES")
    print("Churn = recency_days > 90: PASS")
    print("Important Value User = high R/F/M: PASS")

    # --------------------------------------------------------
    # 6. Merge
    # --------------------------------------------------------
    churn_for_merge = churn[
        [
            "customer_unique_id",
            "recency_days",
            "churn_flag",
        ]
    ].rename(
        columns={
            "recency_days": "churn_recency_days"
        }
    )

    merged = rfm.merge(
        churn_for_merge,
        on="customer_unique_id",
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    both_count = (merged["_merge"] == "both").sum()
    only_rfm = (merged["_merge"] == "left_only").sum()
    only_churn = (merged["_merge"] == "right_only").sum()

    print("\n[6] MERGE COVERAGE")
    print(f"Matched users: {both_count:,}")
    print(f"Only in RFM: {only_rfm:,}")
    print(f"Only in churn: {only_churn:,}")

    if only_rfm != 0 or only_churn != 0:
        raise ValueError(
            "RFM and churn user sets are not identical."
        )

    merged = merged.drop(columns="_merge")

    # --------------------------------------------------------
    # 7. Cross-file recency consistency
    # --------------------------------------------------------
    recency_match = (
        merged["recency_days"]
        == merged["churn_recency_days"]
    ).all()

    if not recency_match:
        raise ValueError(
            "RFM recency_days and churn recency_days do not match."
        )

    print("\n[7] CROSS-FILE METRIC CONSISTENCY")
    print("recency_days: PASS")

    # --------------------------------------------------------
    # 8. High-value x churn analysis
    # --------------------------------------------------------
    high_value = merged[
        merged["rfm_segment"] == "重要价值用户"
    ].copy()

    high_value_count = len(high_value)

    high_value_churn_count = (
        high_value["churn_flag"].astype(int) == 1
    ).sum()

    high_value_non_churn_count = (
        high_value["churn_flag"].astype(int) == 0
    ).sum()

    if high_value_count == 0:
        high_value_churn_rate = None
    else:
        high_value_churn_rate = (
            high_value_churn_count / high_value_count
        )

    print("\n[8] IMPORTANT VALUE USER x CHURN")
    print(f"Important Value Users: {high_value_count:,}")
    print(
        f"High-value churn users: "
        f"{high_value_churn_count:,}"
    )
    print(
        f"High-value non-churn users: "
        f"{high_value_non_churn_count:,}"
    )

    if high_value_churn_rate is None:
        print("High-value churn rate: NULL")
    else:
        print(
            "High-value churn rate: "
            f"{high_value_churn_rate:.2%}"
        )

    # --------------------------------------------------------
    # 9. Show the four high-value users
    # --------------------------------------------------------
    display_columns = [
        "customer_unique_id",
        "recency_days",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_segment",
        "churn_flag",
    ]

    print("\n[9] IMPORTANT VALUE USER DETAIL")
    print(
        high_value[display_columns]
        .sort_values(
            by=["churn_flag", "monetary"],
            ascending=[False, False],
        )
        .to_string(index=False)
    )

    print("\n" + "=" * 70)
    print("FINAL RESULT: PASS")
    print(
        "RFM and churn data are ready for "
        "high-value user profiling."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
