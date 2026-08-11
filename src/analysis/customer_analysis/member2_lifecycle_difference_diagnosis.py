from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

LIFECYCLE_PATH = DATA_DIR / "customer_lifecycle_segment.csv"
CHURN_PATH = DATA_DIR / "churn_user_detail.csv"


def official_stage(row):

    recency = row["recency_days_official"]
    orders = row["valid_order_count_official"]
    lifetime = row["customer_lifecycle_days_official"]

    if recency > 90:
        return "Dormant Customer"

    if orders == 1 and recency <= 30:
        return "New Customer"

    if orders == 1 and 30 < recency <= 90:
        return "Early Customer"

    if orders >= 2 and lifetime <= 180:
        return "Growing Customer"

    if orders >= 2 and lifetime > 180:
        return "Mature Customer"

    return "UNCLASSIFIED"


def main():

    lifecycle = pd.read_csv(LIFECYCLE_PATH)
    churn = pd.read_csv(CHURN_PATH)

    merged = churn[
        [
            "customer_unique_id",
            "valid_order_count",
            "customer_lifecycle_days",
            "recency_days",
        ]
    ].merge(
        lifecycle[
            [
                "customer_unique_id",
                "lifecycle_stage",
                "valid_order_count",
                "customer_lifecycle_days",
                "recency_days",
            ]
        ],
        on="customer_unique_id",
        how="left",
        suffixes=("_official", "_member2"),
        validate="one_to_one",
    )

    print("=" * 76)
    print("MEMBER 2 LIFECYCLE DIFFERENCE DIAGNOSIS")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Recency difference
    # --------------------------------------------------------
    merged["recency_diff"] = (
        merged["recency_days_member2"]
        - merged["recency_days_official"]
    )

    print("\n[1] RECENCY DIFFERENCE DISTRIBUTION")

    print(
        merged["recency_diff"]
        .value_counts(dropna=False)
        .sort_index()
        .head(20)
        .to_string()
    )

    print("\nRecency difference summary:")
    print(
        merged["recency_diff"]
        .describe()
        .to_string()
    )

    # --------------------------------------------------------
    # 2. Order-count differences
    # --------------------------------------------------------
    order_mismatch = merged[
        merged["valid_order_count_member2"]
        != merged["valid_order_count_official"]
    ].copy()

    print("\n[2] ORDER COUNT DIFFERENCES")
    print(f"Mismatched users: {len(order_mismatch):,}")

    if not order_mismatch.empty:
        order_mismatch["order_count_diff"] = (
            order_mismatch["valid_order_count_member2"]
            - order_mismatch["valid_order_count_official"]
        )

        print("\nDifference distribution:")
        print(
            order_mismatch["order_count_diff"]
            .value_counts()
            .sort_index()
            .to_string()
        )

        print("\nSample:")
        print(
            order_mismatch[
                [
                    "customer_unique_id",
                    "valid_order_count_official",
                    "valid_order_count_member2",
                    "order_count_diff",
                ]
            ]
            .head(20)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # 3. Lifecycle-day differences
    # --------------------------------------------------------
    lifetime_mismatch = merged[
        merged["customer_lifecycle_days_member2"]
        != merged["customer_lifecycle_days_official"]
    ].copy()

    print("\n[3] LIFECYCLE DAY DIFFERENCES")
    print(f"Mismatched users: {len(lifetime_mismatch):,}")

    if not lifetime_mismatch.empty:
        lifetime_mismatch["lifecycle_days_diff"] = (
            lifetime_mismatch["customer_lifecycle_days_member2"]
            - lifetime_mismatch["customer_lifecycle_days_official"]
        )

        print("\nDifference distribution:")
        print(
            lifetime_mismatch["lifecycle_days_diff"]
            .value_counts()
            .sort_index()
            .head(30)
            .to_string()
        )

    # --------------------------------------------------------
    # 4. Rebuild official lifecycle stage
    # --------------------------------------------------------
    merged["official_lifecycle_stage"] = merged.apply(
        official_stage,
        axis=1,
    )

    stage_match = (
        merged["official_lifecycle_stage"]
        == merged["lifecycle_stage"]
    )

    print("\n[4] LIFECYCLE STAGE AFTER LABEL ALIGNMENT")
    print(f"Matched: {stage_match.sum():,}")
    print(f"Mismatched: {(~stage_match).sum():,}")

    print("\nOfficial distribution:")
    print(
        merged["official_lifecycle_stage"]
        .value_counts()
        .to_string()
    )

    print("\nMember 2 distribution:")
    print(
        merged["lifecycle_stage"]
        .value_counts()
        .to_string()
    )

    if (~stage_match).any():
        print("\nStage mismatch cross-tab:")
        print(
            pd.crosstab(
                merged.loc[
                    ~stage_match,
                    "official_lifecycle_stage",
                ],
                merged.loc[
                    ~stage_match,
                    "lifecycle_stage",
                ],
            ).to_string()
        )

    print("\n" + "=" * 76)
    print("DIAGNOSIS COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
