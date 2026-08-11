from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user analysis
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


def check_required_columns(df, required_columns, dataset_name):
    """Check whether all required columns exist."""
    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} missing required columns: "
            f"{missing_columns}"
        )


def main():
    # --------------------------------------------------------
    # 1. Check input files
    # --------------------------------------------------------
    if not RFM_PATH.exists():
        raise FileNotFoundError(
            f"RFM file not found: {RFM_PATH}"
        )

    if not CHURN_PATH.exists():
        raise FileNotFoundError(
            f"Churn file not found: {CHURN_PATH}"
        )

    # --------------------------------------------------------
    # 2. Load data
    # --------------------------------------------------------
    rfm_df = pd.read_csv(RFM_PATH)
    churn_df = pd.read_csv(CHURN_PATH)

    # --------------------------------------------------------
    # 3. Required fields based on unified standards
    # --------------------------------------------------------
    required_rfm_columns = [
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

    required_churn_columns = [
        "customer_unique_id",
        "recency_days",
        "churn_flag",
        "observation_date",
    ]

    check_required_columns(
        rfm_df,
        required_rfm_columns,
        "RFM"
    )

    check_required_columns(
        churn_df,
        required_churn_columns,
        "CHURN"
    )

    # --------------------------------------------------------
    # 4. Parse observation date
    # --------------------------------------------------------
    rfm_df["observation_date"] = pd.to_datetime(
        rfm_df["observation_date"],
        errors="coerce"
    )

    churn_df["observation_date"] = pd.to_datetime(
        churn_df["observation_date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # 5. Basic integrity checks
    # --------------------------------------------------------
    print("=" * 70)
    print("UNIFIED STANDARD VALIDATION")
    print("=" * 70)

    print("\n[1] RFM DATA")
    print(f"Rows: {len(rfm_df):,}")
    print(
        "Unique customers:",
        f"{rfm_df['customer_unique_id'].nunique():,}"
    )
    print(
        "Missing customer_unique_id:",
        f"{rfm_df['customer_unique_id'].isna().sum():,}"
    )
    print(
        "Duplicated customer_unique_id:",
        f"{rfm_df['customer_unique_id'].duplicated().sum():,}"
    )

    print("\n[2] CHURN DATA")
    print(f"Rows: {len(churn_df):,}")
    print(
        "Unique customers:",
        f"{churn_df['customer_unique_id'].nunique():,}"
    )
    print(
        "Missing customer_unique_id:",
        f"{churn_df['customer_unique_id'].isna().sum():,}"
    )
    print(
        "Duplicated customer_unique_id:",
        f"{churn_df['customer_unique_id'].duplicated().sum():,}"
    )

    # --------------------------------------------------------
    # 6. Observation-date validation
    # --------------------------------------------------------
    rfm_date_ok = (
        rfm_df["observation_date"]
        .eq(OBSERVATION_DATE)
        .all()
    )

    churn_date_ok = (
        churn_df["observation_date"]
        .eq(OBSERVATION_DATE)
        .all()
    )

    print("\n[3] OBSERVATION DATE")
    print(
        "RFM observation date = 2018-07-31:",
        "PASS" if rfm_date_ok else "FAIL"
    )
    print(
        "Churn observation date = 2018-07-31:",
        "PASS" if churn_date_ok else "FAIL"
    )

    # --------------------------------------------------------
    # 7. Churn-rule validation
    #
    # Unified standard:
    # churn     -> recency_days > 90
    # non-churn -> recency_days <= 90
    # --------------------------------------------------------
    expected_churn_flag = (
        churn_df["recency_days"] > 90
    ).astype(int)

    churn_rule_ok = (
        expected_churn_flag
        .eq(churn_df["churn_flag"])
        .all()
    )

    print("\n[4] CHURN RULE")
    print(
        "churn_flag == (recency_days > 90):",
        "PASS" if churn_rule_ok else "FAIL"
    )

    print(
        "Churn users:",
        f"{(churn_df['churn_flag'] == 1).sum():,}"
    )

    print(
        "Non-churn users:",
        f"{(churn_df['churn_flag'] == 0).sum():,}"
    )

    # --------------------------------------------------------
    # 8. RFM high-value rule validation
    #
    # Unified standard:
    # high R/F/M -> score >= 4
    # Important Value User = high R + high F + high M
    # --------------------------------------------------------
    calculated_high_value = (
        (rfm_df["r_score"] >= 4)
        & (rfm_df["f_score"] >= 4)
        & (rfm_df["m_score"] >= 4)
    )

    segment_high_value = (
        rfm_df["rfm_segment"]
        .astype(str)
        .eq("重要价值用户")
    )

    high_value_rule_ok = (
        calculated_high_value
        .eq(segment_high_value)
        .all()
    )

    print("\n[5] HIGH-VALUE USER RULE")
    print(
        "Important Value User == high R/F/M:",
        "PASS" if high_value_rule_ok else "FAIL"
    )

    print(
        "Important Value Users:",
        f"{segment_high_value.sum():,}"
    )

    # --------------------------------------------------------
    # 9. Cross-file customer coverage
    # --------------------------------------------------------
    rfm_ids = set(
        rfm_df["customer_unique_id"].dropna()
    )

    churn_ids = set(
        churn_df["customer_unique_id"].dropna()
    )

    print("\n[6] CROSS-FILE USER COVERAGE")
    print(
        "Customers in both files:",
        f"{len(rfm_ids & churn_ids):,}"
    )
    print(
        "Only in RFM:",
        f"{len(rfm_ids - churn_ids):,}"
    )
    print(
        "Only in churn:",
        f"{len(churn_ids - rfm_ids):,}"
    )

    # --------------------------------------------------------
    # 10. Final validation result
    # --------------------------------------------------------
    all_checks_pass = all([
        rfm_df["customer_unique_id"].isna().sum() == 0,
        churn_df["customer_unique_id"].isna().sum() == 0,
        rfm_df["customer_unique_id"].duplicated().sum() == 0,
        churn_df["customer_unique_id"].duplicated().sum() == 0,
        rfm_date_ok,
        churn_date_ok,
        churn_rule_ok,
        high_value_rule_ok,
        rfm_ids == churn_ids,
    ])

    print("\n" + "=" * 70)

    if all_checks_pass:
        print("FINAL RESULT: PASS")
        print(
            "RFM and churn data can proceed to cross-member analysis."
        )
    else:
        print("FINAL RESULT: FAIL")
        print(
            "Do not continue analysis until failed checks are resolved."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
