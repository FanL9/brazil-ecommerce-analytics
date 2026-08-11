from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


DB_PATH = Path("database/brazil_ecommerce.db")

PRODUCT_OUTPUT = Path(
    "outputs/data/06_product_analysis/product_association_top20.csv"
)

CATEGORY_OUTPUT = Path(
    "outputs/data/06_product_analysis/category_association_top20.csv"
)

MIN_COOCCURRENCE = 5
MIN_CONFIDENCE = 0.10
MIN_LIFT = 1.0
TOP_N = 20


def export_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_rules(
    baskets: dict[str, set[str]],
    total_orders: int,
) -> tuple[list[dict], Counter]:
    item_orders: Counter[str] = Counter()
    pair_orders: Counter[tuple[str, str]] = Counter()

    for items in baskets.values():
        sorted_items = sorted(items)

        for item in sorted_items:
            item_orders[item] += 1

        for item_a, item_b in combinations(sorted_items, 2):
            pair_orders[(item_a, item_b)] += 1

    rules: list[dict] = []

    for (item_a, item_b), pair_count in pair_orders.items():

        if pair_count < MIN_COOCCURRENCE:
            continue

        count_a = item_orders[item_a]
        count_b = item_orders[item_b]

        support = pair_count / total_orders

        # A -> B
        confidence_ab = pair_count / count_a
        lift_ab = confidence_ab / (count_b / total_orders)

        if (
            confidence_ab >= MIN_CONFIDENCE
            and lift_ab > MIN_LIFT
        ):
            rules.append(
                {
                    "item_a": item_a,
                    "item_b": item_b,
                    "antecedent_orders": count_a,
                    "consequent_orders": count_b,
                    "cooccurrence_orders": pair_count,
                    "support": support,
                    "confidence": confidence_ab,
                    "lift": lift_ab,
                }
            )

        # B -> A
        confidence_ba = pair_count / count_b
        lift_ba = confidence_ba / (count_a / total_orders)

        if (
            confidence_ba >= MIN_CONFIDENCE
            and lift_ba > MIN_LIFT
        ):
            rules.append(
                {
                    "item_a": item_b,
                    "item_b": item_a,
                    "antecedent_orders": count_b,
                    "consequent_orders": count_a,
                    "cooccurrence_orders": pair_count,
                    "support": support,
                    "confidence": confidence_ba,
                    "lift": lift_ba,
                }
            )

    rules.sort(
        key=lambda x: (
            -x["lift"],
            -x["cooccurrence_orders"],
            -x["confidence"],
            x["item_a"],
            x["item_b"],
        )
    )

    return rules, item_orders


def main() -> None:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    total_orders = cur.execute("""
        SELECT COUNT(DISTINCT order_id)
        FROM vw_orders_clean
        WHERE order_status = 'delivered'
    """).fetchone()[0]

    rows = cur.execute("""
        SELECT
            order_id,
            product_id,
            category_name
        FROM category_item_base
        ORDER BY order_id, product_id
    """).fetchall()

    db.close()

    product_baskets: dict[str, set[str]] = defaultdict(set)
    category_baskets: dict[str, set[str]] = defaultdict(set)

    product_category: dict[str, str] = {}

    for order_id, product_id, category_name in rows:

        if product_id is None:
            raise RuntimeError(
                f"NULL product_id detected in order {order_id}"
            )

        if category_name is None or category_name == "":
            raise RuntimeError(
                f"Invalid category_name detected for {product_id}"
            )

        product_baskets[order_id].add(product_id)
        category_baskets[order_id].add(category_name)

        existing = product_category.get(product_id)

        if existing is not None and existing != category_name:
            raise RuntimeError(
                "Product mapped to multiple categories: "
                f"{product_id}: {existing} vs {category_name}"
            )

        product_category[product_id] = category_name

    if len(product_baskets) != total_orders:
        raise RuntimeError(
            "Basket denominator mismatch: "
            f"{len(product_baskets)} != {total_orders}"
        )

    if len(category_baskets) != total_orders:
        raise RuntimeError(
            "Category basket denominator mismatch: "
            f"{len(category_baskets)} != {total_orders}"
        )

    print("=== ASSOCIATION INPUT QA ===")
    print(f"total delivered orders = {total_orders:,}")
    print(f"product baskets = {len(product_baskets):,}")
    print(f"category baskets = {len(category_baskets):,}")

    product_rules, product_support = build_rules(
        product_baskets,
        total_orders,
    )

    category_rules, category_support = build_rules(
        category_baskets,
        total_orders,
    )

    product_top = []

    for rank, rule in enumerate(
        product_rules[:TOP_N],
        start=1,
    ):
        product_top.append(
            {
                "rule_rank": rank,
                "product_a": rule["item_a"],
                "category_a": product_category[rule["item_a"]],
                "product_b": rule["item_b"],
                "category_b": product_category[rule["item_b"]],
                "antecedent_orders": rule["antecedent_orders"],
                "consequent_orders": rule["consequent_orders"],
                "cooccurrence_orders": rule["cooccurrence_orders"],
                "support": rule["support"],
                "confidence": rule["confidence"],
                "lift": rule["lift"],
            }
        )

    category_top = []

    for rank, rule in enumerate(
        category_rules[:TOP_N],
        start=1,
    ):
        category_top.append(
            {
                "rule_rank": rank,
                "category_a": rule["item_a"],
                "category_b": rule["item_b"],
                "antecedent_orders": rule["antecedent_orders"],
                "consequent_orders": rule["consequent_orders"],
                "cooccurrence_orders": rule["cooccurrence_orders"],
                "support": rule["support"],
                "confidence": rule["confidence"],
                "lift": rule["lift"],
            }
        )

    export_csv(
        PRODUCT_OUTPUT,
        product_top,
        [
            "rule_rank",
            "product_a",
            "category_a",
            "product_b",
            "category_b",
            "antecedent_orders",
            "consequent_orders",
            "cooccurrence_orders",
            "support",
            "confidence",
            "lift",
        ],
    )

    export_csv(
        CATEGORY_OUTPUT,
        category_top,
        [
            "rule_rank",
            "category_a",
            "category_b",
            "antecedent_orders",
            "consequent_orders",
            "cooccurrence_orders",
            "support",
            "confidence",
            "lift",
        ],
    )

    print()
    print("=== RULE COUNTS AFTER FORMAL FILTERS ===")
    print(f"product rules = {len(product_rules):,}")
    print(f"category rules = {len(category_rules):,}")

    print()
    print("=== EXPORTED ===")
    print(
        f"product top rules = {len(product_top)} -> "
        f"{PRODUCT_OUTPUT}"
    )
    print(
        f"category top rules = {len(category_top)} -> "
        f"{CATEGORY_OUTPUT}"
    )

    print()
    print("=== PRODUCT TOP 10 ===")

    for row in product_top[:10]:
        print(
            row["rule_rank"],
            f"{row['product_a']} -> {row['product_b']}",
            f"co={row['cooccurrence_orders']}",
            f"support={row['support']:.6f}",
            f"confidence={row['confidence']:.4f}",
            f"lift={row['lift']:.4f}",
        )

    print()
    print("=== CATEGORY TOP 10 ===")

    for row in category_top[:10]:
        print(
            row["rule_rank"],
            f"{row['category_a']} -> {row['category_b']}",
            f"co={row['cooccurrence_orders']}",
            f"support={row['support']:.6f}",
            f"confidence={row['confidence']:.4f}",
            f"lift={row['lift']:.4f}",
        )


if __name__ == "__main__":
    main()
