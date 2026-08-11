from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd


DB_PATH = Path("database/brazil_ecommerce.db")
OUTPUT_PATH = Path(
    "outputs/data/06_product_analysis/category_negative_keywords.csv"
)

# Portuguese stopwords.
# Kept locally to make the analysis reproducible without downloading
# external NLP resources at runtime.
PORTUGUESE_STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo",
    "as", "ate", "com", "como", "da", "das", "de", "dela", "delas", "dele",
    "deles", "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em",
    "entre", "era", "eram", "essa", "essas", "esse", "esses", "esta", "estao",
    "estas", "estava", "estavam", "este", "estes", "eu", "foi", "foram",
    "ha", "isso", "isto", "ja", "mais", "mas", "me", "mesmo", "meu", "meus",
    "minha", "minhas", "muito", "na", "nao", "nas", "nem", "no", "nos",
    "nossa", "nossas", "nosso", "nossos", "num", "numa", "o", "os", "ou",
    "para", "pela", "pelas", "pelo", "pelos", "por", "porque", "que", "quem",
    "se", "sem", "ser", "seu", "seus", "so", "sua", "suas", "tambem",
    "tem", "tendo", "tenho", "ter", "teve", "um", "uma", "umas", "uns",
    "voce", "voces"
}


def normalize_text(text: str) -> str:
    """Lowercase, remove accents, punctuation, digits and extra whitespace."""
    text = str(text).lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )

    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str) -> list[str]:
    """Tokenize normalized Portuguese review text."""
    tokens = normalize_text(text).split()

    return [
        token
        for token in tokens
        if len(token) >= 2
        and token not in PORTUGUESE_STOPWORDS
    ]


def build_keyword_rows(
    category_name: str,
    texts: list[str],
    one_star_rate: float,
    negative_text_review_orders: int,
) -> list[dict]:
    """Create unigram and bigram frequency rows for one category."""
    unigram_counter: Counter[str] = Counter()
    bigram_counter: Counter[str] = Counter()

    for text in texts:
        tokens = tokenize(text)

        unigram_counter.update(tokens)

        bigrams = [
            f"{tokens[i]} {tokens[i + 1]}"
            for i in range(len(tokens) - 1)
        ]
        bigram_counter.update(bigrams)

    rows: list[dict] = []

    for keyword, frequency in unigram_counter.most_common():
        rows.append(
            {
                "category_name": category_name,
                "keyword_type": "unigram",
                "keyword": keyword,
                "frequency": frequency,
                "one_star_rate": one_star_rate,
                "negative_text_review_orders": negative_text_review_orders,
            }
        )

    for keyword, frequency in bigram_counter.most_common():
        rows.append(
            {
                "category_name": category_name,
                "keyword_type": "bigram",
                "keyword": keyword,
                "frequency": frequency,
                "one_star_rate": one_star_rate,
                "negative_text_review_orders": negative_text_review_orders,
            }
        )

    return rows



def generate_wordclouds(result: pd.DataFrame) -> None:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt

    selected_categories = [
        "office_furniture",
        "audio",
        "bed_bath_table",
    ]

    output_dir = Path(
        "outputs/figures/06_product_analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    for category_name in selected_categories:
        subset = result[
            (result["category_name"] == category_name)
            & (result["keyword_type"] == "unigram")
        ]

        frequencies = dict(
            zip(
                subset["keyword"],
                subset["frequency"],
            )
        )

        if not frequencies:
            print(
                f"Skipped word cloud: {category_name} "
                "(no usable keywords)"
            )
            continue

        cloud = WordCloud(
            width=1400,
            height=800,
            background_color="white",
            collocations=False,
        ).generate_from_frequencies(frequencies)

        plt.figure(figsize=(14, 8))
        plt.imshow(cloud, interpolation="bilinear")
        plt.axis("off")
        plt.title(
            f"One-star Review Keywords: {category_name}"
        )
        plt.tight_layout()

        output_path = (
            output_dir
            / f"negative_keywords_{category_name}.png"
        )

        plt.savefig(
            output_path,
            dpi=180,
            bbox_inches="tight",
        )
        plt.close()

        print(f"word cloud -> {output_path}")

def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        cob.category_name,
        cob.order_id,
        r.review_comment_message,
        cs.one_star_rate,
        cs.negative_text_review_orders
    FROM category_order_base AS cob
    INNER JOIN vw_order_reviews_order_level AS r
        ON cob.order_id = r.order_id
    INNER JOIN category_satisfaction AS cs
        ON cob.category_name = cs.category_name
    WHERE
        cs.sample_status = 'eligible'
        AND r.review_score = 1
        AND r.review_comment_message IS NOT NULL
        AND TRIM(r.review_comment_message) <> ''
    ORDER BY
        cob.category_name,
        cob.order_id
    """

    source = pd.read_sql_query(query, conn)
    conn.close()

    if source.empty:
        raise RuntimeError(
            "No eligible one-star text reviews were found."
        )

    # Defensive uniqueness check at the intended order-category grain.
    duplicate_count = int(
        source.duplicated(
            subset=["category_name", "order_id"]
        ).sum()
    )

    if duplicate_count != 0:
        raise RuntimeError(
            "Duplicate order-category review rows detected: "
            f"{duplicate_count}"
        )

    output_rows: list[dict] = []

    for category_name, group in source.groupby(
        "category_name",
        sort=True,
    ):
        one_star_rate = float(group["one_star_rate"].iloc[0])
        negative_text_review_orders = int(
            group["negative_text_review_orders"].iloc[0]
        )

        rows = build_keyword_rows(
            category_name=category_name,
            texts=group["review_comment_message"].tolist(),
            one_star_rate=one_star_rate,
            negative_text_review_orders=negative_text_review_orders,
        )

        output_rows.extend(rows)

    result = pd.DataFrame(output_rows)

    if result.empty:
        raise RuntimeError(
            "Keyword extraction produced no usable tokens."
        )

    result = result.sort_values(
        by=[
            "category_name",
            "keyword_type",
            "frequency",
            "keyword",
        ],
        ascending=[True, True, False, True],
        kind="stable",
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("=== CATEGORY NEGATIVE KEYWORDS ===")
    print(f"source review rows = {len(source):,}")
    print(
        "categories with text reviews = "
        f"{source['category_name'].nunique():,}"
    )
    print(f"duplicate order-category rows = {duplicate_count}")
    print(f"keyword rows = {len(result):,}")
    print(f"exported -> {OUTPUT_PATH}")

    print()
    print("=== TOP CANDIDATES FOR WORD CLOUD ===")

    candidates = (
        source[
            [
                "category_name",
                "one_star_rate",
                "negative_text_review_orders",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by=[
                "one_star_rate",
                "negative_text_review_orders",
                "category_name",
            ],
            ascending=[False, False, True],
            kind="stable",
        )
        .head(15)
    )

    print(candidates.to_string(index=False))

    print()
    print("=== WORD CLOUDS ===")
    generate_wordclouds(result)


if __name__ == "__main__":
    main()
