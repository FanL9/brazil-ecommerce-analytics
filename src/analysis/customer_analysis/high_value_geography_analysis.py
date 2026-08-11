from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user geography analysis
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# User grain:
# one row per customer_unique_id
#
# Geography rule:
# representative geography already derived from the latest
# valid order before 2018-08-01.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

INPUT_PATH = DATA_DIR / "member3_user_value_base.csv"

STATE_OUTPUT_PATH = (
    DATA_DIR / "high_value_user_state_profile.csv"
)

CITY_OUTPUT_PATH = (
    DATA_DIR / "high_value_user_city_profile.csv"
)

DETAIL_OUTPUT_PATH = (
    DATA_DIR / "high_value_user_detail.csv"
)


def safe_divide(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def build_geography_profile(df, group_cols):
    """
    Build geography comparison table.

    All-user denominator and high-value numerator use:
    - same observation date
    - same customer_unique_id population
    - same representative geography rule
    """

    high_value = df[
        df["is_high_value_user"] == 1
    ].copy()

    total_users = df["customer_unique_id"].nunique()
    total_high_value_users = high_value[
        "customer_unique_id"
    ].nunique()

    total_gmv = df["monetary"].sum()
    total_high_value_gmv = high_value["monetary"].sum()

    # --------------------------------------------------------
    # Overall population by geography
    # --------------------------------------------------------
    all_profile = (
        df.groupby(
            group_cols,
            dropna=False,
            as_index=False,
        )
        .agg(
            all_users=(
                "customer_unique_id",
                "nunique",
            ),
            all_user_gmv=(
                "monetary",
                "sum",
            ),
        )
    )

    # --------------------------------------------------------
    # High-value users by geography
    # --------------------------------------------------------
    high_profile = (
        high_value.groupby(
            group_cols,
            dropna=False,
            as_index=False,
        )
        .agg(
            high_value_users=(
                "customer_unique_id",
                "nunique",
            ),
            high_value_gmv=(
                "monetary",
                "sum",
            ),
            high_value_churn_users=(
                "is_high_value_churn_user",
                "sum",
            ),
        )
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------
    result = all_profile.merge(
        high_profile,
        on=group_cols,
        how="left",
        validate="one_to_one",
    )

    fill_zero_cols = [
        "high_value_users",
        "high_value_gmv",
        "high_value_churn_users",
    ]

    result[fill_zero_cols] = (
        result[fill_zero_cols]
        .fillna(0)
    )

    result["high_value_users"] = (
        result["high_value_users"].astype(int)
    )

    result["high_value_churn_users"] = (
        result["high_value_churn_users"].astype(int)
    )

    # --------------------------------------------------------
    # Shares / penetration
    # --------------------------------------------------------
    result["all_user_share"] = (
        result["all_users"] / total_users
    )

    if total_high_value_users == 0:
        result["high_value_user_share"] = None
    else:
        result["high_value_user_share"] = (
            result["high_value_users"]
            / total_high_value_users
        )

    result["high_value_penetration"] = (
        result["high_value_users"]
        / result["all_users"]
    )

    if total_gmv == 0:
        result["all_gmv_share"] = None
    else:
        result["all_gmv_share"] = (
            result["all_user_gmv"]
            / total_gmv
        )

    if total_high_value_gmv == 0:
        result["high_value_gmv_share"] = None
    else:
        result["high_value_gmv_share"] = (
            result["high_value_gmv"]
            / total_high_value_gmv
        )

    # Difference between high-value user geographic share
    # and overall user geographic share.
    result["user_share_gap"] = (
        result["high_value_user_share"]
        - result["all_user_share"]
    )

    result = result.sort_values(
        by=[
            "high_value_users",
            "high_value_penetration",
            "all_users",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return result


def main():

    print("=" * 72)
    print("HIGH-VALUE USER GEOGRAPHY ANALYSIS")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load unified user base
    # --------------------------------------------------------
    df = pd.read_csv(INPUT_PATH)

    print("\n[1] INPUT")
    print(f"Rows: {len(df):,}")
    print(
        f"Unique customers: "
        f"{df['customer_unique_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # 2. Validate input grain
    # --------------------------------------------------------
    if len(df) != 87214:
        raise ValueError(
            f"Expected 87,214 rows, got {len(df):,}."
        )

    if df["customer_unique_id"].duplicated().any():
        raise ValueError(
            "Duplicate customer_unique_id found."
        )

    required = [
        "customer_unique_id",
        "profile_state",
        "profile_city",
        "monetary",
        "rfm_segment",
        "churn_flag",
        "is_high_value_user",
        "is_high_value_churn_user",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    print("Unified user base validation: PASS")

    # --------------------------------------------------------
    # 3. High-value population
    # --------------------------------------------------------
    high_value = df[
        df["is_high_value_user"] == 1
    ].copy()

    print("\n[2] HIGH-VALUE POPULATION")
    print(
        f"Important Value Users: "
        f"{len(high_value):,}"
    )
    print(
        f"High-value churn users: "
        f"{high_value['is_high_value_churn_user'].sum():,}"
    )

    if len(high_value) != 4:
        raise ValueError(
            f"Expected 4 high-value users, got {len(high_value)}."
        )

    # --------------------------------------------------------
    # 4. State profile
    # --------------------------------------------------------
    state_profile = build_geography_profile(
        df,
        ["profile_state"],
    )

    print("\n[3] STATE PROFILE")
    state_high_value_sum = (
        state_profile["high_value_users"].sum()
    )

    print(
        f"High-value users recovered by state: "
        f"{state_high_value_sum:,}"
    )

    if state_high_value_sum != 4:
        raise ValueError(
            "State profile does not recover all 4 high-value users."
        )

    print("\nStates containing high-value users:")

    state_display = state_profile[
        state_profile["high_value_users"] > 0
    ][
        [
            "profile_state",
            "all_users",
            "high_value_users",
            "high_value_penetration",
            "high_value_gmv",
            "high_value_gmv_share",
            "high_value_churn_users",
        ]
    ].copy()

    state_display["high_value_penetration"] = (
        state_display["high_value_penetration"]
        .map(lambda x: f"{x:.4%}")
    )

    state_display["high_value_gmv_share"] = (
        state_display["high_value_gmv_share"]
        .map(lambda x: f"{x:.2%}")
    )

    print(
        state_display.to_string(index=False)
    )

    # --------------------------------------------------------
    # 5. City + state profile
    # --------------------------------------------------------
    city_profile = build_geography_profile(
        df,
        [
            "profile_state",
            "profile_city",
        ],
    )

    print("\n[4] CITY + STATE PROFILE")

    city_high_value_sum = (
        city_profile["high_value_users"].sum()
    )

    print(
        f"High-value users recovered by city+state: "
        f"{city_high_value_sum:,}"
    )

    if city_high_value_sum != 4:
        raise ValueError(
            "City profile does not recover all 4 high-value users."
        )

    print("\nCities containing high-value users:")

    city_display = city_profile[
        city_profile["high_value_users"] > 0
    ][
        [
            "profile_state",
            "profile_city",
            "all_users",
            "high_value_users",
            "high_value_penetration",
            "high_value_gmv",
            "high_value_churn_users",
        ]
    ].copy()

    city_display["high_value_penetration"] = (
        city_display["high_value_penetration"]
        .map(lambda x: f"{x:.4%}")
    )

    print(
        city_display.to_string(index=False)
    )

    # --------------------------------------------------------
    # 6. High-value user detail
    # --------------------------------------------------------
    detail_columns = [
        "customer_unique_id",
        "profile_state",
        "profile_city",
        "recency_days",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_segment",
        "churn_flag",
        "is_high_value_churn_user",
    ]

    high_value_detail = (
        high_value[detail_columns]
        .sort_values(
            by="monetary",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print("\n[5] HIGH-VALUE USER DETAIL")
    print(
        high_value_detail.to_string(index=False)
    )

    # --------------------------------------------------------
    # 7. Save outputs
    # --------------------------------------------------------
    state_profile.to_csv(
        STATE_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    city_profile.to_csv(
        CITY_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    high_value_detail.to_csv(
        DETAIL_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[6] OUTPUTS")
    print(f"Saved: {STATE_OUTPUT_PATH}")
    print(f"Saved: {CITY_OUTPUT_PATH}")
    print(f"Saved: {DETAIL_OUTPUT_PATH}")

    print("\n" + "=" * 72)
    print("FINAL RESULT: PASS")
    print(
        "High-value geography outputs successfully created."
    )
    print(
        "IMPORTANT: high-value sample size = 4; "
        "interpret geographic patterns descriptively."
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
