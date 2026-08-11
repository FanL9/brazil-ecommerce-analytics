from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT_PATH = Path(
    "outputs/data/06_product_analysis/category_satisfaction.csv"
)

OUTPUT_DIR = Path(
    "outputs/figures/06_product_analysis"
)

OUTPUT_PATH = OUTPUT_DIR / "category_satisfaction_matrix.png"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_PATH)

    eligible = df[
        df["sample_status"] == "eligible"
    ].copy()

    if eligible.empty:
        raise RuntimeError(
            "No eligible categories available for plotting."
        )

    if (eligible["valid_review_orders"] < 30).any():
        raise RuntimeError(
            "Small-sample category entered formal matrix."
        )

    fig, ax = plt.subplots(figsize=(12, 8))

    bubble_sizes = (
        eligible["valid_review_orders"] ** 0.5
    ) * 12

    ax.scatter(
        eligible["avg_review_score"],
        eligible["one_star_rate"],
        s=bubble_sizes,
        alpha=0.65,
    )

    # Label categories requiring the most attention:
    # lowest average scores among formally comparable categories.
    label_df = (
        eligible
        .sort_values(
            by=[
                "avg_review_score",
                "one_star_rate",
                "valid_review_orders",
            ],
            ascending=[True, False, False],
        )
        .head(12)
    )

    for _, row in label_df.iterrows():
        ax.annotate(
            row["category_name"],
            (
                row["avg_review_score"],
                row["one_star_rate"],
            ),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title(
        "Category Satisfaction Matrix"
    )
    ax.set_xlabel(
        "Average Review Score"
    )
    ax.set_ylabel(
        "One-Star Review Rate"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_PATH,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("=== SATISFACTION MATRIX ===")
    print(f"eligible categories = {len(eligible)}")
    print(
        "minimum valid review orders =",
        int(eligible["valid_review_orders"].min()),
    )
    print(f"saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
