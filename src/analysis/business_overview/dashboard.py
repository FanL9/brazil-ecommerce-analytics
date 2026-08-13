"""
Interactive workbook dashboard — Stage 1 18 core metrics + Stage 2 business analysis.

Stage 2 current scope
---------------------
1. Global filters:
   - Date range
   - Customer state
   - Payment method
   - Order value band
2. Five KPI cards:
   - GMV
   - Paid Delivered Orders
   - Average Order Value
   - New Users
   - Active Users
3. Five interactive monthly trend charts.
4. Interactive business structure analysis:
   - Payment method structure
   - Order value band structure
   - Customer-state ranking
   - Top 5 / Top 10 state concentration
5. Explainable structural risk and opportunity signals.
6. Platform-wide growth quality analysis from Member 2 outputs.
7. Holiday and seasonality comparison with coverage-aware validation.

Data grain
----------
One row per order_id + payment_type.

Metric behavior under payment filters
-------------------------------------
- Payment-method filters select paid delivered orders that used at least one
  selected method; all payment-method rows for those selected orders are retained.
- GMV: full order-level positive payment amount for the selected orders.
- Paid Delivered Orders: distinct selected order_id values.
- AOV: GMV divided by Paid Delivered Orders.
- New users: users whose exact first paid purchase is present in the
  filtered order cohort.
- Active users: distinct users with at least one selected paid delivered order.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "02_business_overview"
    / "dashboard_order_payment_detail.csv"
)

GROWTH_DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "02_business_overview"
    / "monthly_growth_rates.csv"
)

MONTHLY_KPI_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "02_business_overview"
    / "monthly_kpi.csv"
)

HOLIDAY_DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "02_business_overview"
    / "holiday_comparison.csv"
)

STAGE1_ORDER_DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "01_core_metrics"
    / "stage1_order_metric_base.csv"
)

STAGE1_COHORT_DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "01_core_metrics"
    / "stage1_cohort_retention.csv"
)

STAGE1_CATEGORY_DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "01_core_metrics"
    / "stage1_category_item_base.csv"
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "order_id",
    "customer_unique_id",
    "customer_state",
    "order_purchase_timestamp",
    "purchase_date",
    "purchase_month",
    "order_payment_amount",
    "order_value_band",
    "payment_type",
    "payment_gmv",
    "primary_payment_type",
    "is_mixed_payment",
    "first_paid_purchase_timestamp",
}

STAGE1_ORDER_REQUIRED_COLUMNS = {
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp",
    "purchase_date",
    "purchase_month",
    "is_valid_order",
    "order_payment_amount",
    "is_paid_delivered_order",
    "first_delivered_purchase_timestamp",
    "delivery_days",
    "is_delivery_evaluable",
    "is_late_delivery",
    "review_score",
    "has_valid_review",
    "is_positive_review",
}


STAGE1_COHORT_REQUIRED_COLUMNS = {
    "cohort_month",
    "retention_month_number",
    "cohort_customer_count",
    "retained_customer_count",
    "customer_retention_rate",
}

STAGE1_CATEGORY_REQUIRED_COLUMNS = {
    "order_id",
    "order_item_id",
    "order_purchase_timestamp",
    "purchase_date",
    "purchase_month",
    "product_category",
    "price",
}


ORDER_VALUE_BAND_ORDER = [
    "0-50",
    "50-100",
    "100-200",
    "200-500",
    "500+",
]

GROWTH_REQUIRED_COLUMNS = {
    "month",
    "gmv_mom",
    "gmv_yoy",
    "order_count_mom",
    "order_count_yoy",
    "aov_mom",
    "aov_yoy",
    "new_users_mom",
    "new_users_yoy",
    "active_users_mom",
    "active_users_yoy",
}

MONTHLY_KPI_REQUIRED_COLUMNS = {
    "month",
    "gmv",
    "order_count",
    "average_order_value",
    "new_users",
    "active_users",
}

GROWTH_METRIC_CONFIG = {
    "GMV": {
        "mom_column": "gmv_mom",
        "yoy_column": "gmv_yoy",
        "base_column": "gmv",
    },
    "Paid Delivered Orders": {
        "mom_column": "order_count_mom",
        "yoy_column": "order_count_yoy",
        "base_column": "order_count",
    },
    "Average Order Value": {
        "mom_column": "aov_mom",
        "yoy_column": "aov_yoy",
        "base_column": "average_order_value",
    },
    "New Users": {
        "mom_column": "new_users_mom",
        "yoy_column": "new_users_yoy",
        "base_column": "new_users",
    },
    "Active Users": {
        "mom_column": "active_users_mom",
        "yoy_column": "active_users_yoy",
        "base_column": "active_users",
    },
}


HOLIDAY_REQUIRED_COLUMNS = {
    "holiday_name",
    "year",
    "period_type",
    "start_date",
    "end_date",
    "expected_day_count",
    "observed_day_count",
    "coverage_rate",
    "gmv_observed",
    "order_count_observed",
    "average_order_value_observed",
    "daily_average_gmv_observed",
    "daily_average_orders_observed",
    "gmv_change_vs_pre",
    "order_change_vs_pre",
    "aov_change_vs_pre",
    "daily_gmv_change_vs_pre",
    "daily_orders_change_vs_pre",
    "comparison_status",
    "data_completeness_note",
    "window_definition",
}

HOLIDAY_PERIOD_ORDER = [
    "PRE",
    "DURING",
    "POST",
]

HOLIDAY_METRIC_CONFIG = {
    "Daily Average GMV": {
        "value_column": "daily_average_gmv_observed",
        "formal_change_column": "daily_gmv_change_vs_pre",
        "axis_title": "Daily average GMV (BRL)",
        "value_format": "money",
    },
    "Daily Average Orders": {
        "value_column": "daily_average_orders_observed",
        "formal_change_column": "daily_orders_change_vs_pre",
        "axis_title": "Daily average orders",
        "value_format": "number",
    },
    "Average Order Value": {
        "value_column": "average_order_value_observed",
        "formal_change_column": "aov_change_vs_pre",
        "axis_title": "Average order value (BRL)",
        "value_format": "money",
    },
}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_currency(value: float) -> str:
    """Format a value as Brazilian real."""
    return f"R$ {value:,.2f}"


def format_integer(value: int) -> str:
    """Format an integer with thousands separators."""
    return f"{value:,}"


def format_percentage(value: float) -> str:
    """Format a decimal as a percentage."""
    return f"{value * 100:.1f}%"


# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_stage1_order_data(
    data_path: str,
) -> pd.DataFrame:
    """Load and validate the one-row-per-order Stage 1 metric base."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Stage 1 order metric data file was not found:\n"
            f"{path}\n\n"
            "Run src/analysis/core_metrics/"
            "prepare_stage1_dashboard_data.py first."
        )

    data = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        STAGE1_ORDER_REQUIRED_COLUMNS
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "stage1_order_metric_base.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    data["order_purchase_timestamp"] = pd.to_datetime(
        data["order_purchase_timestamp"],
        errors="coerce",
    )

    data["first_delivered_purchase_timestamp"] = pd.to_datetime(
        data["first_delivered_purchase_timestamp"],
        errors="coerce",
    )

    data["purchase_date"] = pd.to_datetime(
        data["purchase_date"],
        errors="coerce",
    ).dt.date

    data["purchase_month_start"] = (
        data["order_purchase_timestamp"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    numeric_columns = [
        "order_payment_amount",
        "is_valid_order",
        "is_paid_delivered_order",
        "delivery_days",
        "is_delivery_evaluable",
        "is_late_delivery",
        "review_score",
        "has_valid_review",
        "is_positive_review",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    critical_columns = [
        "order_id",
        "order_status",
        "order_purchase_timestamp",
        "purchase_date",
        "purchase_month_start",
        "is_valid_order",
        "is_paid_delivered_order",
    ]

    null_counts = (
        data[critical_columns]
        .isna()
        .sum()
    )

    invalid_nulls = null_counts[
        null_counts > 0
    ]

    if not invalid_nulls.empty:
        raise ValueError(
            "Unexpected null values were found in the Stage 1 order base:\n"
            + invalid_nulls.to_string()
        )

    duplicate_orders = int(
        data["order_id"].duplicated().sum()
    )

    if duplicate_orders:
        raise ValueError(
            "stage1_order_metric_base.csv must contain one row per order_id. "
            f"Duplicate rows found: {duplicate_orders}"
        )

    paid_rows = data.loc[
        data["is_paid_delivered_order"] == 1
    ]

    if (
        paid_rows["order_payment_amount"].isna().any()
        or (
            paid_rows["order_payment_amount"] <= 0
        ).any()
    ):
        raise ValueError(
            "Paid delivered orders must have positive order-level payment amounts."
        )

    return data.sort_values(
        [
            "order_purchase_timestamp",
            "order_id",
        ]
    ).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_stage1_cohort_data(
    data_path: str,
) -> pd.DataFrame:
    """Load and validate the formal Stage 1 M09 cohort-retention output."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Stage 1 cohort-retention data file was not found:\n"
            f"{path}\n\n"
            "Run src/analysis/core_metrics/"
            "prepare_stage1_supporting_data.py first."
        )

    data = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        STAGE1_COHORT_REQUIRED_COLUMNS
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "stage1_cohort_retention.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    data["cohort_month"] = pd.to_datetime(
        data["cohort_month"],
        format="%Y-%m",
        errors="coerce",
    )

    numeric_columns = [
        "retention_month_number",
        "cohort_customer_count",
        "retained_customer_count",
        "customer_retention_rate",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    if data[
        [
            "cohort_month",
            *numeric_columns,
        ]
    ].isna().any().any():
        raise ValueError(
            "stage1_cohort_retention.csv contains invalid or missing values."
        )

    duplicate_keys = int(
        data.duplicated(
            subset=[
                "cohort_month",
                "retention_month_number",
            ]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate cohort_month + retention_month_number rows found: "
            f"{duplicate_keys}"
        )

    invalid_rates = data.loc[
        (data["customer_retention_rate"] < 0)
        | (data["customer_retention_rate"] > 1)
    ]

    if not invalid_rates.empty:
        raise ValueError(
            "Stage 1 retention rates must remain between 0 and 1."
        )

    return data.sort_values(
        [
            "cohort_month",
            "retention_month_number",
        ]
    ).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_stage1_category_data(
    data_path: str,
) -> pd.DataFrame:
    """Load and validate the one-row-per-order-item Stage 1 M18 base."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Stage 1 category-item data file was not found:\n"
            f"{path}\n\n"
            "Run src/analysis/core_metrics/"
            "prepare_stage1_supporting_data.py first."
        )

    data = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        STAGE1_CATEGORY_REQUIRED_COLUMNS
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "stage1_category_item_base.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    data["order_purchase_timestamp"] = pd.to_datetime(
        data["order_purchase_timestamp"],
        errors="coerce",
    )

    data["purchase_date"] = pd.to_datetime(
        data["purchase_date"],
        errors="coerce",
    ).dt.date

    data["price"] = pd.to_numeric(
        data["price"],
        errors="coerce",
    )

    critical_columns = [
        "order_id",
        "order_item_id",
        "order_purchase_timestamp",
        "purchase_date",
        "purchase_month",
        "product_category",
        "price",
    ]

    if data[
        critical_columns
    ].isna().any().any():
        raise ValueError(
            "stage1_category_item_base.csv contains invalid or missing values."
        )

    duplicate_keys = int(
        data.duplicated(
            subset=[
                "order_id",
                "order_item_id",
            ]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate order_id + order_item_id rows found: "
            f"{duplicate_keys}"
        )

    if (data["price"] < 0).any():
        raise ValueError(
            "Stage 1 category-item data contains negative prices."
        )

    return data.sort_values(
        [
            "order_purchase_timestamp",
            "order_id",
            "order_item_id",
        ]
    ).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dashboard_data(
    data_path: str,
) -> pd.DataFrame:
    """Load, type-cast, and validate the dashboard detail dataset."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Dashboard data file was not found:\n"
            f"{path}\n\n"
            "Run prepare_dashboard_data.py first."
        )

    data = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = REQUIRED_COLUMNS - set(data.columns)

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )
        raise ValueError(
            "The dashboard data file is missing required columns: "
            f"{missing_text}"
        )

    data["order_purchase_timestamp"] = pd.to_datetime(
        data["order_purchase_timestamp"],
        errors="coerce",
    )

    data["first_paid_purchase_timestamp"] = pd.to_datetime(
        data["first_paid_purchase_timestamp"],
        errors="coerce",
    )

    data["purchase_date"] = pd.to_datetime(
        data["purchase_date"],
        errors="coerce",
    ).dt.date

    data["purchase_month_start"] = (
        data["order_purchase_timestamp"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    numeric_columns = [
        "order_payment_amount",
        "payment_gmv",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    critical_columns = [
        "order_id",
        "customer_unique_id",
        "customer_state",
        "order_purchase_timestamp",
        "first_paid_purchase_timestamp",
        "purchase_date",
        "purchase_month_start",
        "order_value_band",
        "payment_type",
        "payment_gmv",
    ]

    null_counts = (
        data[critical_columns]
        .isna()
        .sum()
    )

    invalid_nulls = null_counts[
        null_counts > 0
    ]

    if not invalid_nulls.empty:
        raise ValueError(
            "Unexpected null values were found:\n"
            + invalid_nulls.to_string()
        )

    duplicate_keys = int(
        data.duplicated(
            subset=["order_id", "payment_type"]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate order_id + payment_type rows were found: "
            f"{duplicate_keys}"
        )

    if (data["payment_gmv"] <= 0).any():
        raise ValueError(
            "payment_gmv contains non-positive values."
        )

    unknown_bands = (
        set(data["order_value_band"].unique())
        - set(ORDER_VALUE_BAND_ORDER)
    )

    if unknown_bands:
        raise ValueError(
            "Unexpected order value bands were found: "
            + ", ".join(sorted(unknown_bands))
        )

    return data



@st.cache_data(show_spinner=False)
def load_growth_data(
    data_path: str,
) -> pd.DataFrame:
    """Load and validate Member 2's monthly growth-rate output."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Growth-rate data file was not found:\n"
            f"{path}"
        )

    growth = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        GROWTH_REQUIRED_COLUMNS
        - set(growth.columns)
    )

    if missing_columns:
        raise ValueError(
            "monthly_growth_rates.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    growth["month"] = pd.to_datetime(
        growth["month"],
        format="%Y-%m",
        errors="coerce",
    )

    if growth["month"].isna().any():
        raise ValueError(
            "monthly_growth_rates.csv contains invalid month values."
        )

    duplicate_months = int(
        growth["month"].duplicated().sum()
    )

    if duplicate_months:
        raise ValueError(
            "monthly_growth_rates.csv contains duplicate months: "
            f"{duplicate_months}"
        )

    numeric_columns = sorted(
        GROWTH_REQUIRED_COLUMNS
        - {"month"}
    )

    for column in numeric_columns:
        growth[column] = pd.to_numeric(
            growth[column],
            errors="coerce",
        )

    return growth.sort_values(
        "month"
    ).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_monthly_kpi_data(
    data_path: str,
) -> pd.DataFrame:
    """Load the public monthly KPI layer used as the growth base."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Monthly KPI data file was not found:\n"
            f"{path}"
        )

    monthly_kpi = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        MONTHLY_KPI_REQUIRED_COLUMNS
        - set(monthly_kpi.columns)
    )

    if missing_columns:
        raise ValueError(
            "monthly_kpi.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    monthly_kpi["month"] = pd.to_datetime(
        monthly_kpi["month"],
        format="%Y-%m",
        errors="coerce",
    )

    if monthly_kpi["month"].isna().any():
        raise ValueError(
            "monthly_kpi.csv contains invalid month values."
        )

    duplicate_months = int(
        monthly_kpi["month"].duplicated().sum()
    )

    if duplicate_months:
        raise ValueError(
            "monthly_kpi.csv contains duplicate months: "
            f"{duplicate_months}"
        )

    numeric_columns = sorted(
        MONTHLY_KPI_REQUIRED_COLUMNS
        - {"month"}
    )

    for column in numeric_columns:
        monthly_kpi[column] = pd.to_numeric(
            monthly_kpi[column],
            errors="coerce",
        )

    return monthly_kpi.sort_values(
        "month"
    ).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_holiday_data(
    data_path: str,
) -> pd.DataFrame:
    """Load and validate the coverage-aware holiday comparison table."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            "Holiday comparison data file was not found:\n"
            f"{path}"
        )

    holiday = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    missing_columns = (
        HOLIDAY_REQUIRED_COLUMNS
        - set(holiday.columns)
    )

    if missing_columns:
        raise ValueError(
            "holiday_comparison.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    holiday["holiday_name"] = (
        holiday["holiday_name"]
        .astype(str)
        .str.strip()
    )

    holiday["period_type"] = (
        holiday["period_type"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid_periods = sorted(
        set(
            holiday["period_type"]
        )
        - set(
            HOLIDAY_PERIOD_ORDER
        )
    )

    if invalid_periods:
        raise ValueError(
            "holiday_comparison.csv contains invalid period types: "
            + ", ".join(
                invalid_periods
            )
        )

    holiday["year"] = pd.to_numeric(
        holiday["year"],
        errors="coerce",
    ).astype("Int64")

    if holiday["year"].isna().any():
        raise ValueError(
            "holiday_comparison.csv contains invalid year values."
        )

    for column in [
        "start_date",
        "end_date",
    ]:
        holiday[column] = pd.to_datetime(
            holiday[column],
            errors="coerce",
        )

        if holiday[column].isna().any():
            raise ValueError(
                "holiday_comparison.csv contains invalid "
                f"{column} values."
            )

    numeric_columns = [
        "expected_day_count",
        "observed_day_count",
        "coverage_rate",
        "gmv_observed",
        "order_count_observed",
        "average_order_value_observed",
        "daily_average_gmv_observed",
        "daily_average_orders_observed",
        "gmv_change_vs_pre",
        "order_change_vs_pre",
        "aov_change_vs_pre",
        "daily_gmv_change_vs_pre",
        "daily_orders_change_vs_pre",
    ]

    optional_numeric_columns = [
        "observed_daily_gmv_change_vs_pre",
        "observed_daily_orders_change_vs_pre",
    ]

    for column in (
        numeric_columns
        + [
            value
            for value in optional_numeric_columns
            if value in holiday.columns
        ]
    ):
        holiday[column] = pd.to_numeric(
            holiday[column],
            errors="coerce",
        )

    duplicate_grain = int(
        holiday.duplicated(
            subset=[
                "holiday_name",
                "year",
                "period_type",
            ]
        ).sum()
    )

    if duplicate_grain:
        raise ValueError(
            "holiday_comparison.csv contains duplicate "
            "holiday-year-period rows: "
            f"{duplicate_grain}"
        )

    invalid_day_counts = holiday.loc[
        (
            holiday[
                "expected_day_count"
            ] <= 0
        )
        | (
            holiday[
                "observed_day_count"
            ] < 0
        )
        | (
            holiday[
                "observed_day_count"
            ]
            > holiday[
                "expected_day_count"
            ]
        )
    ]

    if not invalid_day_counts.empty:
        raise ValueError(
            "holiday_comparison.csv contains invalid expected or "
            "observed day counts."
        )

    invalid_coverage = holiday.loc[
        (
            holiday[
                "coverage_rate"
            ] < 0
        )
        | (
            holiday[
                "coverage_rate"
            ] > 1
        )
    ]

    if not invalid_coverage.empty:
        raise ValueError(
            "holiday_comparison.csv contains coverage rates "
            "outside the range 0 to 1."
        )

    holiday["period_type"] = pd.Categorical(
        holiday["period_type"],
        categories=HOLIDAY_PERIOD_ORDER,
        ordered=True,
    )

    return holiday.sort_values(
        [
            "holiday_name",
            "year",
            "period_type",
        ]
    ).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Filter state
# ---------------------------------------------------------------------------

def reset_filters(
    minimum_date: date,
    maximum_date: date,
) -> None:
    """Restore all filters to the full-data defaults."""
    st.session_state["date_range"] = (
        minimum_date,
        maximum_date,
    )
    st.session_state["state_filter"] = []
    st.session_state["payment_filter"] = []
    st.session_state["band_filter"] = []


def render_filters(
    data: pd.DataFrame,
) -> dict[str, object]:
    """Render global filters and return their selected values."""
    minimum_date = data["purchase_date"].min()
    maximum_date = data["purchase_date"].max()

    states = sorted(
        data["customer_state"]
        .dropna()
        .unique()
        .tolist()
    )

    payment_types = sorted(
        data["payment_type"]
        .dropna()
        .unique()
        .tolist()
    )

    available_bands = set(
        data["order_value_band"]
        .dropna()
        .unique()
        .tolist()
    )

    value_bands = [
        band
        for band in ORDER_VALUE_BAND_ORDER
        if band in available_bands
    ]

    with st.sidebar:
        st.header("Global Filters")

        if st.button(
            "Reset filters",
            use_container_width=True,
        ):
            reset_filters(
                minimum_date,
                maximum_date,
            )
            st.rerun()

        selected_dates = st.date_input(
            "Date range",
            value=(
                minimum_date,
                maximum_date,
            ),
            min_value=minimum_date,
            max_value=maximum_date,
            key="date_range",
        )

        selected_states = st.multiselect(
            "Customer state",
            options=states,
            default=[],
            placeholder="All states",
            key="state_filter",
        )

        selected_payments = st.multiselect(
            "Payment method",
            options=payment_types,
            default=[],
            placeholder="All payment methods",
            key="payment_filter",
        )

        selected_bands = st.multiselect(
            "Order value band",
            options=value_bands,
            default=[],
            placeholder="All value bands",
            key="band_filter",
        )

        st.caption(
            "Leaving a category filter empty means all values."
        )

    if isinstance(selected_dates, (tuple, list)):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
        elif len(selected_dates) == 1:
            start_date = selected_dates[0]
            end_date = selected_dates[0]
        else:
            start_date = minimum_date
            end_date = maximum_date
    else:
        start_date = selected_dates
        end_date = selected_dates

    return {
        "start_date": start_date,
        "end_date": end_date,
        "states": selected_states,
        "payments": selected_payments,
        "bands": selected_bands,
    }


def apply_filters(
    data: pd.DataFrame,
    filters: dict[str, object],
) -> pd.DataFrame:
    """Apply the global filters to the payment-detail dataset."""
    start_date = filters["start_date"]
    end_date = filters["end_date"]

    filtered = data.loc[
        data["purchase_date"].between(
            start_date,
            end_date,
        )
    ].copy()

    selected_states = filters["states"]
    selected_payments = filters["payments"]
    selected_bands = filters["bands"]

    if selected_states:
        filtered = filtered.loc[
            filtered["customer_state"].isin(
                selected_states
            )
        ]

    if selected_payments:
        matching_order_ids = filtered.loc[
            filtered["payment_type"].isin(
                selected_payments
            ),
            "order_id",
        ].unique()

        filtered = filtered.loc[
            filtered["order_id"].isin(
                matching_order_ids
            )
        ]

    if selected_bands:
        filtered = filtered.loc[
            filtered["order_value_band"].isin(
                selected_bands
            )
        ]

    return filtered


# ---------------------------------------------------------------------------
# KPI calculation
# ---------------------------------------------------------------------------

def build_order_level_view(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row per selected paid delivered order."""
    return (
        filtered.sort_values(
            [
                "order_purchase_timestamp",
                "order_id",
                "payment_type",
            ]
        )
        .drop_duplicates(
            subset=["order_id"],
            keep="first",
        )
        .copy()
    )


def calculate_kpis(
    filtered: pd.DataFrame,
) -> dict[str, float | int]:
    """Calculate the five paid-delivered KPIs from the filtered order cohort."""
    order_level = build_order_level_view(
        filtered
    )

    gmv = float(
        order_level["order_payment_amount"].sum()
    )

    order_count = int(
        order_level["order_id"].nunique()
    )

    average_order_value = (
        gmv / order_count
        if order_count > 0
        else 0.0
    )

    active_users = int(
        order_level["customer_unique_id"].nunique()
    )

    exact_first_purchase_rows = order_level.loc[
        order_level["order_purchase_timestamp"]
        == order_level["first_paid_purchase_timestamp"]
    ]

    new_users = int(
        exact_first_purchase_rows[
            "customer_unique_id"
        ].nunique()
    )

    return {
        "gmv": gmv,
        "order_count": order_count,
        "average_order_value": average_order_value,
        "new_users": new_users,
        "active_users": active_users,
    }


def render_kpi_cards(
    kpis: dict[str, float | int],
) -> None:
    """Display the five core KPI cards."""
    columns = st.columns(5)

    columns[0].metric(
        "GMV",
        format_currency(
            float(kpis["gmv"])
        ),
    )

    columns[1].metric(
        "Paid Delivered Orders",
        format_integer(
            int(kpis["order_count"])
        ),
    )

    columns[2].metric(
        "Average Order Value",
        format_currency(
            float(
                kpis["average_order_value"]
            )
        ),
    )

    columns[3].metric(
        "New Users",
        format_integer(
            int(kpis["new_users"])
        ),
    )

    columns[4].metric(
        "Active Users",
        format_integer(
            int(kpis["active_users"])
        ),
    )


# ---------------------------------------------------------------------------
# Monthly trend calculation
# ---------------------------------------------------------------------------

def build_monthly_trends(
    filtered: pd.DataFrame,
    source_data: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Build a complete monthly KPI series for the selected date range."""
    month_start = pd.Timestamp(start_date).to_period("M").to_timestamp()
    month_end = pd.Timestamp(end_date).to_period("M").to_timestamp()

    complete_months = pd.DataFrame(
        {
            "month": pd.date_range(
                month_start,
                month_end,
                freq="MS",
            )
        }
    )

    source_months = set(
        source_data[
            "purchase_month_start"
        ].dropna()
    )

    complete_months[
        "source_month_observed"
    ] = complete_months["month"].isin(
        source_months
    )

    order_level = build_order_level_view(
        filtered
    )

    monthly_gmv = (
        order_level.groupby(
            "purchase_month_start",
            as_index=False,
        )["order_payment_amount"]
        .sum()
        .rename(
            columns={
                "purchase_month_start": "month",
                "order_payment_amount": "gmv",
            }
        )
    )

    monthly_orders = (
        order_level.groupby(
            "purchase_month_start",
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "order_id": "order_count",
            }
        )
    )

    monthly_active_users = (
        order_level.groupby(
            "purchase_month_start",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "customer_unique_id": "active_users",
            }
        )
    )

    first_purchase_rows = order_level.loc[
        order_level["order_purchase_timestamp"]
        == order_level["first_paid_purchase_timestamp"]
    ].copy()

    monthly_new_users = (
        first_purchase_rows.groupby(
            "purchase_month_start",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "customer_unique_id": "new_users",
            }
        )
    )

    trends = (
        complete_months
        .merge(
            monthly_gmv,
            on="month",
            how="left",
        )
        .merge(
            monthly_orders,
            on="month",
            how="left",
        )
        .merge(
            monthly_new_users,
            on="month",
            how="left",
        )
        .merge(
            monthly_active_users,
            on="month",
            how="left",
        )
    )

    fill_zero_columns = [
        "gmv",
        "order_count",
        "new_users",
        "active_users",
    ]

    observed_mask = trends[
        "source_month_observed"
    ]

    for column in fill_zero_columns:
        trends.loc[
            observed_mask
            & trends[column].isna(),
            column,
        ] = 0

        trends.loc[
            ~observed_mask,
            column,
        ] = pd.NA

    trends["order_count"] = (
        pd.to_numeric(
            trends["order_count"],
            errors="coerce",
        )
        .astype("Int64")
    )

    trends["new_users"] = (
        pd.to_numeric(
            trends["new_users"],
            errors="coerce",
        )
        .astype("Int64")
    )

    trends["active_users"] = (
        pd.to_numeric(
            trends["active_users"],
            errors="coerce",
        )
        .astype("Int64")
    )

    trends["average_order_value"] = (
        trends["gmv"]
        / trends["order_count"].replace(
            0,
            pd.NA,
        )
    )

    return trends.drop(
        columns=["source_month_observed"]
    )


# ---------------------------------------------------------------------------
# Trend chart helpers
# ---------------------------------------------------------------------------

def create_trend_chart(
    data: pd.DataFrame,
    metric: str,
    title: str,
    y_title: str,
    tooltip_format: str,
) -> alt.Chart:
    """Create an interactive monthly line chart."""
    chart_data = data[
        ["month", metric]
    ].copy()

    line = (
        alt.Chart(chart_data)
        .mark_line(
            point=True,
            strokeWidth=2,
        )
        .encode(
            x=alt.X(
                "month:T",
                title="Month",
                axis=alt.Axis(
                    format="%Y-%m",
                    labelAngle=-45,
                ),
            ),
            y=alt.Y(
                f"{metric}:Q",
                title=y_title,
                scale=alt.Scale(
                    zero=False,
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "month:T",
                    title="Month",
                    format="%Y-%m",
                ),
                alt.Tooltip(
                    f"{metric}:Q",
                    title=title,
                    format=tooltip_format,
                ),
            ],
        )
        .properties(
            title=title,
            height=390,
        )
        .interactive(
            bind_y=False,
        )
    )

    return line


def render_monthly_trends(
    trends: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> None:
    """Display five monthly KPI trend charts in tabs."""
    st.subheader("Monthly KPI Trends")

    st.caption(
        "Calendar months absent from the paid-delivered source are retained "
        "as gaps (NULL), not filled with zero. In source-observed months, "
        "a filtered cohort with no matching orders displays zero; AOV remains "
        "blank when the monthly paid-order count is zero."
    )

    start_timestamp = pd.Timestamp(start_date)
    end_timestamp = pd.Timestamp(end_date)

    start_is_partial = start_timestamp.day != 1
    end_is_partial = (
        end_timestamp
        != end_timestamp.to_period("M").end_time.normalize()
    )

    if start_is_partial or end_is_partial:
        st.info(
            "The selected range starts or ends within a calendar month. "
            "The first and/or last monthly points therefore represent "
            "partial-month results."
        )

    tabs = st.tabs(
        [
            "GMV",
            "Paid Delivered Orders",
            "Average Order Value",
            "New Users",
            "Active Users",
        ]
    )

    with tabs[0]:
        st.altair_chart(
            create_trend_chart(
                trends,
                metric="gmv",
                title="Monthly GMV Trend",
                y_title="GMV (BRL)",
                tooltip_format=",.2f",
            ),
            use_container_width=True,
        )

    with tabs[1]:
        st.altair_chart(
            create_trend_chart(
                trends,
                metric="order_count",
                title="Monthly Paid Delivered Order Trend",
                y_title="Paid delivered orders",
                tooltip_format=",d",
            ),
            use_container_width=True,
        )

    with tabs[2]:
        st.altair_chart(
            create_trend_chart(
                trends,
                metric="average_order_value",
                title="Monthly Average Order Value Trend",
                y_title="Average order value (BRL)",
                tooltip_format=",.2f",
            ),
            use_container_width=True,
        )

    with tabs[3]:
        st.altair_chart(
            create_trend_chart(
                trends,
                metric="new_users",
                title="Monthly New User Trend",
                y_title="Distinct new users",
                tooltip_format=",d",
            ),
            use_container_width=True,
        )

    with tabs[4]:
        st.altair_chart(
            create_trend_chart(
                trends,
                metric="active_users",
                title="Monthly Active User Trend",
                y_title="Distinct active users",
                tooltip_format=",d",
            ),
            use_container_width=True,
        )




# ---------------------------------------------------------------------------
# Growth quality analysis
# ---------------------------------------------------------------------------

def prepare_growth_series(
    growth: pd.DataFrame,
    monthly_kpi: pd.DataFrame,
    metric_label: str,
    comparison_label: str,
) -> pd.DataFrame:
    """
    Prepare one growth series and add explainable interpretation flags.

    Low-base flags use the bottom decile of positive historical comparison
    bases for the selected metric. This is a distribution-based diagnostic,
    not a fixed business warning threshold.
    """
    config = GROWTH_METRIC_CONFIG[
        metric_label
    ]

    growth_column = (
        config["mom_column"]
        if comparison_label == "Month over Month"
        else config["yoy_column"]
    )

    base_column = config[
        "base_column"
    ]

    month_offset = (
        1
        if comparison_label == "Month over Month"
        else 12
    )

    series = growth[
        [
            "month",
            growth_column,
        ]
    ].copy()

    series = series.rename(
        columns={
            growth_column: "growth_rate",
        }
    )

    series["comparison_base_month"] = (
        series["month"]
        - pd.DateOffset(
            months=month_offset
        )
    )

    base_lookup = monthly_kpi[
        [
            "month",
            base_column,
        ]
    ].rename(
        columns={
            "month": "comparison_base_month",
            base_column: "comparison_base_value",
        }
    )

    series = series.merge(
        base_lookup,
        on="comparison_base_month",
        how="left",
    )

    positive_bases = monthly_kpi.loc[
        monthly_kpi[base_column] > 0,
        base_column,
    ].dropna()

    low_base_cutoff = (
        float(
            positive_bases.quantile(
                0.10
            )
        )
        if not positive_bases.empty
        else float("nan")
    )

    minimum_month = growth[
        "month"
    ].min()

    maximum_month = growth[
        "month"
    ].max()

    series["is_low_base"] = (
        series["growth_rate"].notna()
        & (
            series[
                "comparison_base_value"
            ].isna()
            | (
                series[
                    "comparison_base_value"
                ] <= 0
            )
            | (
                series[
                    "comparison_base_value"
                ] <= low_base_cutoff
            )
        )
    )

    series["is_coverage_boundary"] = (
        series["month"].isin(
            [
                minimum_month,
                maximum_month,
            ]
        )
    )

    series["is_interpretation_flag"] = (
        series["is_low_base"]
        | series[
            "is_coverage_boundary"
        ]
    )

    def build_status(
        row: pd.Series,
    ) -> str:
        if pd.isna(
            row["growth_rate"]
        ):
            return "No comparable period"

        reasons: list[str] = []

        if row["is_low_base"]:
            reasons.append(
                "Low comparison base"
            )

        if row[
            "is_coverage_boundary"
        ]:
            reasons.append(
                "Coverage-boundary month"
            )

        if not reasons:
            return "Comparable"

        return " + ".join(
            reasons
        )

    series["status"] = series.apply(
        build_status,
        axis=1,
    )

    series["growth_pct"] = (
        series["growth_rate"] * 100
    )

    series.attrs[
        "low_base_cutoff"
    ] = low_base_cutoff

    series.attrs[
        "base_column"
    ] = base_column

    return series


def filter_growth_by_date(
    series: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Filter monthly growth points using the selected calendar months."""
    start_month = (
        pd.Timestamp(start_date)
        .to_period("M")
        .to_timestamp()
    )

    end_month = (
        pd.Timestamp(end_date)
        .to_period("M")
        .to_timestamp()
    )

    return series.loc[
        series["month"].between(
            start_month,
            end_month,
        )
    ].copy()


def create_growth_rate_chart(
    series: pd.DataFrame,
    metric_label: str,
    comparison_label: str,
    exclude_flagged: bool,
) -> alt.Chart:
    """Create an interactive growth-rate trend chart."""
    chart_data = series.loc[
        series["growth_rate"].notna()
    ].copy()

    if exclude_flagged:
        chart_data = chart_data.loc[
            ~chart_data[
                "is_interpretation_flag"
            ]
        ]

    zero_rule = (
        alt.Chart(
            pd.DataFrame(
                {
                    "zero": [0.0],
                }
            )
        )
        .mark_rule(
            strokeDash=[5, 4],
        )
        .encode(
            y=alt.Y(
                "zero:Q",
            )
        )
    )

    line = (
        alt.Chart(chart_data)
        .mark_line(
            point=True,
            strokeWidth=2,
        )
        .encode(
            x=alt.X(
                "month:T",
                title="Month",
                axis=alt.Axis(
                    format="%Y-%m",
                    labelAngle=-45,
                ),
            ),
            y=alt.Y(
                "growth_pct:Q",
                title="Growth rate (%)",
                scale=alt.Scale(
                    zero=False,
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "month:T",
                    title="Month",
                    format="%Y-%m",
                ),
                alt.Tooltip(
                    "growth_pct:Q",
                    title="Growth rate (%)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "comparison_base_month:T",
                    title="Comparison base month",
                    format="%Y-%m",
                ),
                alt.Tooltip(
                    "comparison_base_value:Q",
                    title="Comparison base value",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "status:N",
                    title="Interpretation status",
                ),
            ],
        )
        .properties(
            title=(
                f"{metric_label} · "
                f"{comparison_label} Growth"
            ),
            height=390,
        )
        .interactive(
            bind_y=False,
        )
    )

    return alt.layer(
        zero_rule,
        line,
    )


def format_optional_growth(
    value: float | None,
) -> str:
    """Format a nullable decimal growth value."""
    if value is None or pd.isna(
        value
    ):
        return "N/A"

    return f"{value * 100:,.2f}%"


def render_growth_summary(
    series: pd.DataFrame,
) -> None:
    """Render non-flagged growth summary cards."""
    comparable = series.loc[
        series["growth_rate"].notna()
        & ~series[
            "is_interpretation_flag"
        ]
    ].copy()

    flagged_count = int(
        (
            series["growth_rate"].notna()
            & series[
                "is_interpretation_flag"
            ]
        ).sum()
    )

    columns = st.columns(4)

    if comparable.empty:
        columns[0].metric(
            "Latest Comparable Growth",
            "N/A",
        )
        columns[1].metric(
            "Largest Comparable Increase",
            "N/A",
        )
        columns[2].metric(
            "Largest Comparable Decline",
            "N/A",
        )
    else:
        latest = comparable.sort_values(
            "month"
        ).iloc[-1]

        highest_growth = comparable.sort_values(
            "growth_rate",
            ascending=False,
        ).iloc[0]

        lowest_growth = comparable.sort_values(
            "growth_rate",
            ascending=True,
        ).iloc[0]

        columns[0].metric(
            (
                "Latest Comparable Growth · "
                f"{latest['month']:%Y-%m}"
            ),
            format_optional_growth(
                float(
                    latest[
                        "growth_rate"
                    ]
                )
            ),
        )

        columns[1].metric(
            (
                "Highest Comparable Growth · "
                f"{highest_growth['month']:%Y-%m}"
            ),
            format_optional_growth(
                float(
                    highest_growth[
                        "growth_rate"
                    ]
                )
            ),
        )

        columns[2].metric(
            (
                "Lowest Comparable Growth · "
                f"{lowest_growth['month']:%Y-%m}"
            ),
            format_optional_growth(
                float(
                    lowest_growth[
                        "growth_rate"
                    ]
                )
            ),
        )

    columns[3].metric(
        "Flagged Observations",
        format_integer(
            flagged_count
        ),
    )


def build_growth_decomposition(
    growth: pd.DataFrame,
    comparison_label: str,
) -> pd.DataFrame:
    """Build algebraic GMV growth components for each comparable month."""
    suffix = (
        "mom"
        if comparison_label == "Month over Month"
        else "yoy"
    )

    decomposition = growth[
        [
            "month",
            f"gmv_{suffix}",
            f"order_count_{suffix}",
            f"aov_{suffix}",
        ]
    ].copy()

    decomposition = decomposition.rename(
        columns={
            f"gmv_{suffix}": "reported_gmv_growth",
            f"order_count_{suffix}": "order_effect",
            f"aov_{suffix}": "aov_effect",
        }
    )

    decomposition[
        "interaction_effect"
    ] = (
        decomposition[
            "order_effect"
        ]
        * decomposition[
            "aov_effect"
        ]
    )

    decomposition[
        "reconstructed_gmv_growth"
    ] = (
        decomposition[
            "order_effect"
        ]
        + decomposition[
            "aov_effect"
        ]
        + decomposition[
            "interaction_effect"
        ]
    )

    decomposition[
        "reconstruction_difference"
    ] = (
        decomposition[
            "reported_gmv_growth"
        ]
        - decomposition[
            "reconstructed_gmv_growth"
        ]
    )

    return decomposition


def create_decomposition_chart(
    selected_row: pd.Series,
) -> alt.Chart:
    """Create the order, AOV, and interaction contribution chart."""
    chart_data = pd.DataFrame(
        {
            "component": [
                "Order-count effect",
                "AOV effect",
                "Interaction effect",
            ],
            "contribution_pct": [
                float(
                    selected_row[
                        "order_effect"
                    ]
                ) * 100,
                float(
                    selected_row[
                        "aov_effect"
                    ]
                ) * 100,
                float(
                    selected_row[
                        "interaction_effect"
                    ]
                ) * 100,
            ],
        }
    )

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "component:N",
                title="Growth component",
                sort=[
                    "Order-count effect",
                    "AOV effect",
                    "Interaction effect",
                ],
            ),
            y=alt.Y(
                "contribution_pct:Q",
                title="Contribution (percentage points)",
            ),
            tooltip=[
                alt.Tooltip(
                    "component:N",
                    title="Component",
                ),
                alt.Tooltip(
                    "contribution_pct:Q",
                    title="Contribution (pp)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="GMV Growth Decomposition",
            height=360,
        )
    )


def render_growth_decomposition(
    growth: pd.DataFrame,
    gmv_series: pd.DataFrame,
    comparison_label: str,
    start_date: date,
    end_date: date,
) -> None:
    """Render one selected-month GMV growth decomposition."""
    decomposition = build_growth_decomposition(
        growth,
        comparison_label,
    )

    start_month = (
        pd.Timestamp(start_date)
        .to_period("M")
        .to_timestamp()
    )

    end_month = (
        pd.Timestamp(end_date)
        .to_period("M")
        .to_timestamp()
    )

    decomposition = decomposition.loc[
        decomposition["month"].between(
            start_month,
            end_month,
        )
    ]

    decomposition = decomposition.dropna(
        subset=[
            "reported_gmv_growth",
            "order_effect",
            "aov_effect",
        ]
    )

    if decomposition.empty:
        st.info(
            "No complete GMV decomposition is available for the "
            "selected date range and comparison mode."
        )
        return

    available_months = (
        decomposition["month"]
        .sort_values()
        .tolist()
    )

    comparable_months = (
        gmv_series.loc[
            gmv_series["status"]
            == "Comparable",
            "month",
        ]
        .loc[
            lambda values: values.isin(
                available_months
            )
        ]
        .sort_values()
        .tolist()
    )

    default_month = (
        comparable_months[-1]
        if comparable_months
        else available_months[-1]
    )

    default_index = available_months.index(
        default_month
    )

    selected_month = st.selectbox(
        "Decomposition month",
        options=available_months,
        index=default_index,
        format_func=lambda value: (
            value.strftime(
                "%Y-%m"
            )
        ),
        key=(
            "growth_decomposition_month_"
            + comparison_label
        ),
    )

    selected_row = decomposition.loc[
        decomposition["month"]
        == selected_month
    ].iloc[0]

    chart_column, explanation_column = st.columns(
        [
            1.4,
            1,
        ]
    )

    with chart_column:
        st.altair_chart(
            create_decomposition_chart(
                selected_row
            ),
            use_container_width=True,
        )

    with explanation_column:
        reported_growth = float(
            selected_row[
                "reported_gmv_growth"
            ]
        )

        reconstructed_growth = float(
            selected_row[
                "reconstructed_gmv_growth"
            ]
        )

        order_effect = float(
            selected_row[
                "order_effect"
            ]
        )

        aov_effect = float(
            selected_row[
                "aov_effect"
            ]
        )

        interaction_effect = float(
            selected_row[
                "interaction_effect"
            ]
        )

        dominant_driver = (
            "order count"
            if abs(order_effect)
            >= abs(aov_effect)
            else "average order value"
        )

        st.markdown(
            f"#### {selected_month:%Y-%m}"
        )

        st.markdown(
            "**Reported GMV growth:** "
            f"{format_optional_growth(reported_growth)}"
        )

        st.markdown(
            "**Reconstructed growth:** "
            f"{format_optional_growth(reconstructed_growth)}"
        )

        st.markdown(
            "**Order-count effect:** "
            f"{order_effect * 100:,.2f} percentage points"
        )

        st.markdown(
            "**AOV effect:** "
            f"{aov_effect * 100:,.2f} percentage points"
        )

        st.markdown(
            "**Interaction effect:** "
            f"{interaction_effect * 100:,.2f} percentage points"
        )

        st.info(
            "The larger direct component is "
            f"**{dominant_driver}** for this comparison."
        )

        selected_flag = gmv_series.loc[
            gmv_series["month"]
            == selected_month,
            "status",
        ]

        if (
            not selected_flag.empty
            and selected_flag.iloc[0]
            != "Comparable"
        ):
            st.warning(
                "Interpret with caution: "
                f"{selected_flag.iloc[0]}."
            )

    st.caption(
        "Decomposition identity: GMV growth is represented by the "
        "order-count effect, the AOV effect, and their interaction. "
        "This is an algebraic decomposition, not causal attribution."
    )


def render_growth_data_table(
    series: pd.DataFrame,
    metric_label: str,
    comparison_label: str,
) -> None:
    """Render the selected growth series and interpretation status."""
    table = series[
        [
            "month",
            "growth_rate",
            "comparison_base_month",
            "comparison_base_value",
            "status",
        ]
    ].copy()

    table.columns = [
        "Month",
        f"{metric_label} Growth",
        "Comparison Base Month",
        "Comparison Base Value",
        "Interpretation Status",
    ]

    table["Month"] = table[
        "Month"
    ].dt.strftime(
        "%Y-%m"
    )

    table[
        "Comparison Base Month"
    ] = table[
        "Comparison Base Month"
    ].dt.strftime(
        "%Y-%m"
    )

    st.dataframe(
        table.style.format(
            {
                f"{metric_label} Growth": (
                    lambda value: (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:.2%}"
                    )
                ),
                "Comparison Base Value": (
                    lambda value: (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:,.2f}"
                    )
                ),
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_growth_quality(
    start_date: date,
    end_date: date,
    category_filters_active: bool,
) -> None:
    """Render Member 2's platform-wide growth quality module."""
    st.subheader(
        "Growth Quality Analysis"
    )

    st.caption(
        "Source: monthly_growth_rates.csv produced from the public "
        "monthly KPI layer. Date range applies to this module."
    )

    if category_filters_active:
        st.warning(
            "Customer-state, payment-method, and order-value-band filters "
            "do not alter this module because the Member 2 file contains "
            "platform-wide monthly aggregates only. The date range still "
            "applies."
        )
    else:
        st.info(
            "This is a platform-wide module. Customer-state, payment-method, "
            "and order-value-band filters are not applicable to the source "
            "file."
        )

    try:
        growth = load_growth_data(
            str(
                GROWTH_DATA_PATH
            )
        )

        monthly_kpi = load_monthly_kpi_data(
            str(
                MONTHLY_KPI_PATH
            )
        )
    except (
        FileNotFoundError,
        ValueError,
        pd.errors.ParserError,
    ) as error:
        st.warning(
            "Growth quality data is not ready for display."
        )
        st.code(
            str(error)
        )
        return

    control_columns = st.columns(2)

    with control_columns[0]:
        metric_label = st.selectbox(
            "Growth metric",
            options=list(
                GROWTH_METRIC_CONFIG.keys()
            ),
            index=0,
            key="growth_metric",
        )

    with control_columns[1]:
        comparison_label = st.radio(
            "Comparison",
            options=[
                "Month over Month",
                "Year over Year",
            ],
            horizontal=True,
            key="growth_comparison",
        )

    series = prepare_growth_series(
        growth,
        monthly_kpi,
        metric_label,
        comparison_label,
    )

    series = filter_growth_by_date(
        series,
        start_date,
        end_date,
    )

    if series.empty:
        st.info(
            "No growth observations fall within the selected date range."
        )
        return

    render_growth_summary(
        series
    )

    exclude_flagged = st.checkbox(
        (
            "Exclude low-base and coverage-boundary observations "
            "from the chart scale"
        ),
        value=True,
        key="exclude_flagged_growth",
    )

    chartable_rows = series.loc[
        series["growth_rate"].notna()
    ]

    if exclude_flagged:
        chartable_rows = chartable_rows.loc[
            ~chartable_rows[
                "is_interpretation_flag"
            ]
        ]

    if chartable_rows.empty:
        st.info(
            "No comparable non-flagged observations remain for the chart. "
            "Clear the exclusion option or broaden the date range."
        )
    else:
        st.altair_chart(
            create_growth_rate_chart(
                series,
                metric_label,
                comparison_label,
                exclude_flagged,
            ),
            use_container_width=True,
        )

    cutoff = series.attrs.get(
        "low_base_cutoff"
    )

    base_column = series.attrs.get(
        "base_column"
    )

    if cutoff is not None and not pd.isna(
        cutoff
    ):
        st.caption(
            "Low-base diagnostic: the comparison base is in the bottom "
            "10% of positive historical values for "
            f"`{base_column}`. Current cutoff: {cutoff:,.2f}. "
            "Coverage-boundary months are also flagged because the dataset "
            "starts in 2016 and ends in 2018."
        )

    with st.expander(
        "View growth-rate data and interpretation flags"
    ):
        render_growth_data_table(
            series,
            metric_label,
            comparison_label,
        )

    st.markdown(
        "### GMV Growth Decomposition"
    )

    gmv_series = prepare_growth_series(
        growth,
        monthly_kpi,
        "GMV",
        comparison_label,
    )

    render_growth_decomposition(
        growth,
        gmv_series,
        comparison_label,
        start_date,
        end_date,
    )



# ---------------------------------------------------------------------------
# Holiday and seasonality analysis
# ---------------------------------------------------------------------------

def format_holiday_value(
    value: float | None,
    value_format: str,
) -> str:
    """Format a nullable holiday metric for cards and explanations."""
    if value is None or pd.isna(
        value
    ):
        return "N/A"

    if value_format == "money":
        return f"R$ {value:,.2f}"

    return f"{value:,.2f}"


def format_signed_percent(
    value: float | None,
    observed_only: bool = False,
) -> str:
    """Format a nullable signed decimal change."""
    if value is None or pd.isna(
        value
    ):
        return "N/A"

    suffix = "*" if observed_only else ""

    return f"{value:+.2%}{suffix}"


def holiday_groups_in_date_range(
    holiday: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Return holiday-year groups whose complete PRE/DURING/POST window
    overlaps the selected global date range.
    """
    start_timestamp = pd.Timestamp(
        start_date
    )

    end_timestamp = pd.Timestamp(
        end_date
    )

    groups = (
        holiday.groupby(
            [
                "holiday_name",
                "year",
            ],
            observed=True,
            as_index=False,
        )
        .agg(
            window_start=(
                "start_date",
                "min",
            ),
            window_end=(
                "end_date",
                "max",
            ),
        )
    )

    return groups.loc[
        (
            groups[
                "window_end"
            ] >= start_timestamp
        )
        & (
            groups[
                "window_start"
            ] <= end_timestamp
        )
    ].copy()


def create_holiday_period_chart(
    selected: pd.DataFrame,
    metric_label: str,
) -> alt.Chart:
    """Create the PRE/DURING/POST metric comparison chart."""
    config = HOLIDAY_METRIC_CONFIG[
        metric_label
    ]

    value_column = config[
        "value_column"
    ]

    chart_data = selected.loc[
        selected[
            value_column
        ].notna()
    ].copy()

    chart_data[
        "metric_value"
    ] = chart_data[
        value_column
    ]

    tooltip_format = (
        ",.2f"
    )

    bars = (
        alt.Chart(chart_data)
        .mark_bar(
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "period_type:N",
                title="Holiday period",
                sort=HOLIDAY_PERIOD_ORDER,
            ),
            y=alt.Y(
                "metric_value:Q",
                title=config[
                    "axis_title"
                ],
            ),
            color=alt.Color(
                "period_type:N",
                title="Period",
                sort=HOLIDAY_PERIOD_ORDER,
            ),
            opacity=alt.condition(
                "datum.coverage_rate >= 0.999999",
                alt.value(1.0),
                alt.value(0.45),
            ),
            tooltip=[
                alt.Tooltip(
                    "period_type:N",
                    title="Period",
                ),
                alt.Tooltip(
                    "start_date:T",
                    title="Start date",
                    format="%Y-%m-%d",
                ),
                alt.Tooltip(
                    "end_date:T",
                    title="End date",
                    format="%Y-%m-%d",
                ),
                alt.Tooltip(
                    "metric_value:Q",
                    title=metric_label,
                    format=tooltip_format,
                ),
                alt.Tooltip(
                    "coverage_rate:Q",
                    title="Coverage",
                    format=".1%",
                ),
                alt.Tooltip(
                    "comparison_status:N",
                    title="Comparison status",
                ),
            ],
        )
        .properties(
            title=(
                f"{metric_label} · "
                f"{selected['holiday_name'].iloc[0]} "
                f"{int(selected['year'].iloc[0])}"
            ),
            height=380,
        )
    )

    labels = (
        alt.Chart(chart_data)
        .mark_text(
            dy=-10,
        )
        .encode(
            x=alt.X(
                "period_type:N",
                sort=HOLIDAY_PERIOD_ORDER,
            ),
            y=alt.Y(
                "metric_value:Q",
            ),
            text=alt.Text(
                "metric_value:Q",
                format=",.2f",
            ),
        )
    )

    return alt.layer(
        bars,
        labels,
    )


def create_holiday_cross_year_chart(
    holiday_data: pd.DataFrame,
    metric_label: str,
    holiday_name: str,
) -> alt.Chart:
    """Create a cross-year comparison for one holiday."""
    config = HOLIDAY_METRIC_CONFIG[
        metric_label
    ]

    value_column = config[
        "value_column"
    ]

    chart_data = holiday_data.loc[
        (
            holiday_data[
                "holiday_name"
            ] == holiday_name
        )
        & holiday_data[
            value_column
        ].notna()
    ].copy()

    chart_data[
        "metric_value"
    ] = chart_data[
        value_column
    ]

    chart_data[
        "year_label"
    ] = chart_data[
        "year"
    ].astype(str)

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "year_label:N",
                title="Holiday year",
            ),
            xOffset=alt.XOffset(
                "period_type:N",
                sort=HOLIDAY_PERIOD_ORDER,
            ),
            y=alt.Y(
                "metric_value:Q",
                title=config[
                    "axis_title"
                ],
            ),
            color=alt.Color(
                "period_type:N",
                title="Period",
                sort=HOLIDAY_PERIOD_ORDER,
            ),
            opacity=alt.condition(
                "datum.coverage_rate >= 0.999999",
                alt.value(1.0),
                alt.value(0.45),
            ),
            tooltip=[
                alt.Tooltip(
                    "year_label:N",
                    title="Year",
                ),
                alt.Tooltip(
                    "period_type:N",
                    title="Period",
                ),
                alt.Tooltip(
                    "metric_value:Q",
                    title=metric_label,
                    format=",.2f",
                ),
                alt.Tooltip(
                    "coverage_rate:Q",
                    title="Coverage",
                    format=".1%",
                ),
                alt.Tooltip(
                    "comparison_status:N",
                    title="Status",
                ),
            ],
        )
        .properties(
            title=(
                f"{holiday_name} · "
                f"Cross-year {metric_label}"
            ),
            height=360,
        )
    )


def calculate_observed_change(
    selected: pd.DataFrame,
    period_type: str,
    value_column: str,
) -> float | None:
    """Calculate an observed-only period change relative to PRE."""
    pre_rows = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == "PRE"
    ]

    comparison_rows = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == period_type
    ]

    if (
        pre_rows.empty
        or comparison_rows.empty
    ):
        return None

    pre_value = pre_rows.iloc[0][
        value_column
    ]

    comparison_value = comparison_rows.iloc[0][
        value_column
    ]

    if (
        pd.isna(pre_value)
        or pd.isna(comparison_value)
        or float(pre_value) == 0
    ):
        return None

    return (
        float(
            comparison_value
        )
        / float(
            pre_value
        )
        - 1
    )


def comparison_value_and_status(
    selected: pd.DataFrame,
    period_type: str,
    metric_label: str,
) -> tuple[
    float | None,
    bool,
]:
    """
    Return a formal validated change when available; otherwise return an
    observed-only reference change and flag it as observed-only.
    """
    config = HOLIDAY_METRIC_CONFIG[
        metric_label
    ]

    target = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == period_type
    ]

    if target.empty:
        return None, False

    row = target.iloc[0]

    formal_change = row[
        config[
            "formal_change_column"
        ]
    ]

    if (
        row[
            "comparison_status"
        ] == "Validated"
        and pd.notna(
            formal_change
        )
    ):
        return (
            float(
                formal_change
            ),
            False,
        )

    observed_change = calculate_observed_change(
        selected,
        period_type,
        config[
            "value_column"
        ],
    )

    return (
        observed_change,
        observed_change is not None,
    )


def direction_phrase(
    value: float,
) -> str:
    """Create a readable increase/decrease phrase."""
    if value > 0:
        return f"increased by {value:.1%}"

    if value < 0:
        return f"decreased by {abs(value):.1%}"

    return "was unchanged"


def build_holiday_interpretation(
    selected: pd.DataFrame,
) -> str:
    """Build one non-causal interpretation from validated comparisons."""
    during = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == "DURING"
    ]

    post = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == "POST"
    ]

    messages: list[str] = []

    if (
        not during.empty
        and during.iloc[0][
            "comparison_status"
        ] == "Validated"
    ):
        row = during.iloc[0]

        daily_gmv = row[
            "daily_gmv_change_vs_pre"
        ]

        daily_orders = row[
            "daily_orders_change_vs_pre"
        ]

        aov = row[
            "aov_change_vs_pre"
        ]

        if all(
            pd.notna(value)
            for value in [
                daily_gmv,
                daily_orders,
                aov,
            ]
        ):
            message = (
                "During the holiday, daily GMV "
                f"{direction_phrase(float(daily_gmv))}, "
                "daily orders "
                f"{direction_phrase(float(daily_orders))}, "
                "and AOV "
                f"{direction_phrase(float(aov))} "
                "relative to PRE."
            )

            if (
                daily_gmv > 0
                and daily_orders > 0
                and aov < 0
            ):
                message += (
                    " The uplift was volume-led rather than "
                    "basket-size-led."
                )
            elif (
                daily_gmv > 0
                and daily_orders > 0
                and aov > 0
            ):
                message += (
                    " Both transaction volume and basket size "
                    "supported the uplift."
                )
            elif (
                daily_gmv < 0
                and daily_orders < 0
            ):
                message += (
                    " Lower order activity was the main observed "
                    "pressure on GMV."
                )

            messages.append(
                message
            )

    if (
        not post.empty
        and post.iloc[0][
            "comparison_status"
        ] == "Validated"
    ):
        row = post.iloc[0]

        daily_gmv = row[
            "daily_gmv_change_vs_pre"
        ]

        daily_orders = row[
            "daily_orders_change_vs_pre"
        ]

        if (
            pd.notna(
                daily_gmv
            )
            and pd.notna(
                daily_orders
            )
        ):
            messages.append(
                "After the holiday, daily GMV "
                f"{direction_phrase(float(daily_gmv))} "
                "and daily orders "
                f"{direction_phrase(float(daily_orders))} "
                "relative to PRE."
            )

    if not messages:
        return (
            "No formal interpretation is produced because the PRE or "
            "comparison window is incomplete. Observed-only values remain "
            "available for reference."
        )

    return " ".join(
        messages
    )


def render_holiday_detail_table(
    selected: pd.DataFrame,
) -> None:
    """Render coverage, metrics, and formal comparison status."""
    display = selected[
        [
            "period_type",
            "start_date",
            "end_date",
            "expected_day_count",
            "observed_day_count",
            "coverage_rate",
            "gmv_observed",
            "order_count_observed",
            "average_order_value_observed",
            "daily_average_gmv_observed",
            "daily_average_orders_observed",
            "daily_gmv_change_vs_pre",
            "daily_orders_change_vs_pre",
            "aov_change_vs_pre",
            "comparison_status",
            "data_completeness_note",
        ]
    ].copy()

    display[
        "period_type"
    ] = display[
        "period_type"
    ].astype(str)

    display.columns = [
        "Period",
        "Start Date",
        "End Date",
        "Expected Days",
        "Observed Days",
        "Coverage",
        "Observed GMV",
        "Observed Orders",
        "Observed AOV",
        "Observed Daily GMV",
        "Observed Daily Orders",
        "Validated Daily GMV vs PRE",
        "Validated Daily Orders vs PRE",
        "Validated AOV vs PRE",
        "Comparison Status",
        "Completeness Note",
    ]

    st.dataframe(
        display.style.format(
            {
                "Start Date": (
                    lambda value: value.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "End Date": (
                    lambda value: value.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "Coverage": "{:.1%}",
                "Observed GMV": "R$ {:,.2f}",
                "Observed Orders": "{:,.0f}",
                "Observed AOV": "R$ {:,.2f}",
                "Observed Daily GMV": "R$ {:,.2f}",
                "Observed Daily Orders": "{:,.2f}",
                "Validated Daily GMV vs PRE": (
                    lambda value: (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:+.2%}"
                    )
                ),
                "Validated Daily Orders vs PRE": (
                    lambda value: (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:+.2%}"
                    )
                ),
                "Validated AOV vs PRE": (
                    lambda value: (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:+.2%}"
                    )
                ),
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_holiday_analysis(
    start_date: date,
    end_date: date,
    category_filters_active: bool,
) -> None:
    """Render coverage-aware holiday and seasonality comparisons."""
    st.subheader(
        "Holiday and Seasonality Analysis"
    )

    st.caption(
        "Source: holiday_comparison.csv. The date range controls which "
        "holiday windows are available; selected windows remain whole so "
        "PRE/DURING/POST comparisons are not truncated."
    )

    if category_filters_active:
        st.warning(
            "Customer-state, payment-method, and order-value-band filters "
            "do not alter this module because the holiday file contains "
            "platform-wide aggregates only. The date range still controls "
            "eligible holiday windows."
        )
    else:
        st.info(
            "This is a platform-wide module. Category filters are not "
            "applicable to the source file."
        )

    try:
        holiday = load_holiday_data(
            str(
                HOLIDAY_DATA_PATH
            )
        )
    except (
        FileNotFoundError,
        ValueError,
        pd.errors.ParserError,
    ) as error:
        st.warning(
            "Holiday comparison data is not ready for display."
        )
        st.code(
            str(error)
        )
        return

    available_groups = holiday_groups_in_date_range(
        holiday,
        start_date,
        end_date,
    )

    if available_groups.empty:
        st.info(
            "No holiday comparison window overlaps the selected date range."
        )
        return

    holiday_options = sorted(
        available_groups[
            "holiday_name"
        ].unique()
    )

    control_columns = st.columns(3)

    with control_columns[0]:
        selected_holiday = st.selectbox(
            "Holiday",
            options=holiday_options,
            index=0,
            key="holiday_name",
        )

    available_years = sorted(
        available_groups.loc[
            available_groups[
                "holiday_name"
            ] == selected_holiday,
            "year",
        ].astype(int)
    )

    with control_columns[1]:
        selected_year = st.selectbox(
            "Holiday year",
            options=available_years,
            index=len(
                available_years
            ) - 1,
            key="holiday_year",
        )

    with control_columns[2]:
        metric_label = st.selectbox(
            "Comparison metric",
            options=list(
                HOLIDAY_METRIC_CONFIG.keys()
            ),
            index=0,
            key="holiday_metric",
        )

    selected = holiday.loc[
        (
            holiday[
                "holiday_name"
            ] == selected_holiday
        )
        & (
            holiday[
                "year"
            ].astype(int)
            == int(
                selected_year
            )
        )
    ].copy()

    selected = selected.sort_values(
        "period_type"
    )

    config = HOLIDAY_METRIC_CONFIG[
        metric_label
    ]

    value_column = config[
        "value_column"
    ]

    pre = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == "PRE"
    ]

    during = selected.loc[
        selected[
            "period_type"
        ].astype(str)
        == "DURING"
    ]

    pre_value = (
        float(
            pre.iloc[0][
                value_column
            ]
        )
        if (
            not pre.empty
            and pd.notna(
                pre.iloc[0][
                    value_column
                ]
            )
        )
        else None
    )

    during_value = (
        float(
            during.iloc[0][
                value_column
            ]
        )
        if (
            not during.empty
            and pd.notna(
                during.iloc[0][
                    value_column
                ]
            )
        )
        else None
    )

    during_change, during_observed_only = (
        comparison_value_and_status(
            selected,
            "DURING",
            metric_label,
        )
    )

    post_change, post_observed_only = (
        comparison_value_and_status(
            selected,
            "POST",
            metric_label,
        )
    )

    cards = st.columns(4)

    cards[0].metric(
        f"PRE · {metric_label}",
        format_holiday_value(
            pre_value,
            config[
                "value_format"
            ],
        ),
    )

    cards[1].metric(
        f"DURING · {metric_label}",
        format_holiday_value(
            during_value,
            config[
                "value_format"
            ],
        ),
    )

    cards[2].metric(
        "DURING vs PRE",
        format_signed_percent(
            during_change,
            during_observed_only,
        ),
    )

    cards[3].metric(
        "POST vs PRE",
        format_signed_percent(
            post_change,
            post_observed_only,
        ),
    )

    if (
        during_observed_only
        or post_observed_only
    ):
        st.warning(
            "* Asterisked changes are observed-only references because "
            "at least one comparison window has incomplete coverage. "
            "They are not treated as validated holiday effects."
        )

    chart_column, coverage_column = st.columns(
        [
            1.65,
            1,
        ]
    )

    with chart_column:
        chartable = selected.loc[
            selected[
                value_column
            ].notna()
        ]

        if chartable.empty:
            st.info(
                "No observed values are available for this holiday-year "
                "and metric."
            )
        else:
            st.altair_chart(
                create_holiday_period_chart(
                    selected,
                    metric_label,
                ),
                use_container_width=True,
            )

    with coverage_column:
        st.markdown(
            "#### Data Coverage"
        )

        for period in HOLIDAY_PERIOD_ORDER:
            row = selected.loc[
                selected[
                    "period_type"
                ].astype(str)
                == period
            ]

            if row.empty:
                continue

            current = row.iloc[0]

            st.metric(
                (
                    f"{period} Coverage · "
                    f"{int(current['observed_day_count'])}/"
                    f"{int(current['expected_day_count'])} days"
                ),
                f"{float(current['coverage_rate']):.1%}",
            )

        st.caption(
            "Full-opacity bars have 100% coverage. Faded bars are based "
            "on partial observation."
        )

    st.markdown(
        "### Interpretable Holiday Pattern"
    )

    st.info(
        build_holiday_interpretation(
            selected
        )
    )

    st.caption(
        "The interpretation describes observed associations within the "
        "configured windows. It is not causal evidence that the holiday "
        "alone produced the change."
    )

    with st.expander(
        "View holiday period metrics and validation status"
    ):
        render_holiday_detail_table(
            selected
        )

    st.markdown(
        "### Cross-year Holiday View"
    )

    cross_year = holiday.loc[
        holiday[
            "holiday_name"
        ] == selected_holiday
    ].copy()

    if cross_year[
        value_column
    ].notna().sum() == 0:
        st.info(
            "No observed values are available for the selected holiday."
        )
    else:
        st.altair_chart(
            create_holiday_cross_year_chart(
                cross_year,
                metric_label,
                selected_holiday,
            ),
            use_container_width=True,
        )

    selected_window = selected[
        "window_definition"
    ].dropna()

    if not selected_window.empty:
        st.caption(
            "Window definition: "
            f"{selected_window.iloc[0]}. "
            "PRE is the seven calendar days immediately before DURING; "
            "POST is the seven calendar days immediately after DURING."
        )

    st.caption(
        "Data-quality note: this module uses the supplied daily aggregate "
        "and its coverage-aware summary. Window-level unique active or new "
        "users are not displayed because they cannot be recovered reliably "
        "by summing daily unique-user counts."
    )


# ---------------------------------------------------------------------------
# Business structure calculation
# ---------------------------------------------------------------------------

def build_payment_structure(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce the formal payment attribution rules for current filters."""
    split_payment = (
        filtered.groupby(
            "payment_type",
            as_index=False,
        )
        .agg(
            split_gmv=(
                "payment_gmv",
                "sum",
            ),
        )
    )

    order_level = build_order_level_view(
        filtered
    )

    primary_payment = (
        order_level.groupby(
            "primary_payment_type",
            as_index=False,
        )
        .agg(
            attributed_order_gmv=(
                "order_payment_amount",
                "sum",
            ),
            primary_order_count=(
                "order_id",
                "nunique",
            ),
            mixed_payment_orders=(
                "is_mixed_payment",
                "sum",
            ),
        )
        .rename(
            columns={
                "primary_payment_type": "payment_type",
            }
        )
    )

    payment = split_payment.merge(
        primary_payment,
        on="payment_type",
        how="outer",
    )

    numeric_columns = [
        "split_gmv",
        "attributed_order_gmv",
        "primary_order_count",
        "mixed_payment_orders",
    ]

    payment[numeric_columns] = (
        payment[numeric_columns]
        .fillna(0)
    )

    payment["primary_order_count"] = (
        payment["primary_order_count"]
        .astype(int)
    )

    payment["mixed_payment_orders"] = (
        payment["mixed_payment_orders"]
        .astype(int)
    )

    total_gmv = float(
        order_level[
            "order_payment_amount"
        ].sum()
    )

    total_paid_orders = int(
        order_level[
            "order_id"
        ].nunique()
    )

    payment["average_order_value"] = (
        payment["attributed_order_gmv"]
        / payment[
            "primary_order_count"
        ].replace(0, pd.NA)
    )

    payment["gmv_share"] = (
        payment["split_gmv"] / total_gmv
        if total_gmv > 0
        else 0.0
    )

    payment["order_share"] = (
        payment["primary_order_count"]
        / total_paid_orders
        if total_paid_orders > 0
        else 0.0
    )

    payment["mixed_payment_order_share"] = (
        payment["mixed_payment_orders"]
        / payment[
            "primary_order_count"
        ].replace(0, pd.NA)
    ).fillna(0.0)

    payment["gmv_share_pct"] = (
        payment["gmv_share"] * 100
    )

    payment["order_share_pct"] = (
        payment["order_share"] * 100
    )

    return payment.sort_values(
        [
            "split_gmv",
            "payment_type",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)


def build_order_value_structure(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate order-value-band GMV, orders, AOV, and shares."""
    structure = (
        filtered.groupby(
            "order_value_band",
            as_index=False,
        )
        .agg(
            gmv=(
                "payment_gmv",
                "sum",
            ),
            order_count=(
                "order_id",
                "nunique",
            ),
        )
    )

    structure["order_value_band"] = pd.Categorical(
        structure["order_value_band"],
        categories=ORDER_VALUE_BAND_ORDER,
        ordered=True,
    )

    structure = structure.sort_values(
        "order_value_band"
    ).reset_index(drop=True)

    total_gmv = float(
        structure["gmv"].sum()
    )

    total_orders = int(
        filtered["order_id"].nunique()
    )

    structure["average_order_value"] = (
        structure["gmv"]
        / structure["order_count"].replace(0, pd.NA)
    )

    structure["gmv_share"] = (
        structure["gmv"] / total_gmv
        if total_gmv > 0
        else 0.0
    )

    structure["order_share"] = (
        structure["order_count"] / total_orders
        if total_orders > 0
        else 0.0
    )

    structure["gmv_share_pct"] = (
        structure["gmv_share"] * 100
    )

    structure["order_share_pct"] = (
        structure["order_share"] * 100
    )

    return structure


def build_state_structure(
    filtered: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Calculate state rankings and Top 5 / Top 10 concentration."""
    state = (
        filtered.groupby(
            "customer_state",
            as_index=False,
        )
        .agg(
            gmv=(
                "payment_gmv",
                "sum",
            ),
            order_count=(
                "order_id",
                "nunique",
            ),
            customer_count=(
                "customer_unique_id",
                "nunique",
            ),
        )
    )

    state["average_order_value"] = (
        state["gmv"]
        / state["order_count"].replace(0, pd.NA)
    )

    total_gmv = float(
        state["gmv"].sum()
    )

    total_orders = int(
        filtered["order_id"].nunique()
    )

    state["gmv_share"] = (
        state["gmv"] / total_gmv
        if total_gmv > 0
        else 0.0
    )

    state["order_share"] = (
        state["order_count"] / total_orders
        if total_orders > 0
        else 0.0
    )

    state["gmv_share_pct"] = (
        state["gmv_share"] * 100
    )

    state["order_share_pct"] = (
        state["order_share"] * 100
    )

    state = state.sort_values(
        ["gmv", "customer_state"],
        ascending=[False, True],
    ).reset_index(drop=True)

    state["gmv_rank"] = (
        state.index + 1
    )

    concentration = {
        "top_5_gmv_share": float(
            state.head(5)["gmv_share"].sum()
        ),
        "top_10_gmv_share": float(
            state.head(10)["gmv_share"].sum()
        ),
        "top_5_order_share": float(
            state.sort_values(
                "order_count",
                ascending=False,
            )
            .head(5)["order_share"]
            .sum()
        ),
        "top_10_order_share": float(
            state.sort_values(
                "order_count",
                ascending=False,
            )
            .head(10)["order_share"]
            .sum()
        ),
    }

    return state, concentration


# ---------------------------------------------------------------------------
# Business structure charts
# ---------------------------------------------------------------------------

def create_payment_gmv_chart(
    payment: pd.DataFrame,
) -> alt.Chart:
    """Create the payment-method split-GMV share chart."""
    chart_data = payment.copy()

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "gmv_share_pct:Q",
                title="GMV share (%)",
            ),
            y=alt.Y(
                "payment_type:N",
                title="Payment method",
                sort="-x",
            ),
            tooltip=[
                alt.Tooltip(
                    "payment_type:N",
                    title="Payment method",
                ),
                alt.Tooltip(
                    "split_gmv:Q",
                    title="Split GMV (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "gmv_share_pct:Q",
                    title="GMV share",
                    format=".1f",
                ),
                alt.Tooltip(
                    "primary_order_count:Q",
                    title="Primary paid orders",
                    format=",d",
                ),
                alt.Tooltip(
                    "average_order_value:Q",
                    title="AOV (BRL)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="Payment Method GMV Structure",
            height=320,
        )
    )


def create_payment_order_chart(
    payment: pd.DataFrame,
) -> alt.Chart:
    """Create the primary-payment paid-order chart."""
    chart_data = payment.copy()

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "primary_order_count:Q",
                title="Primary paid delivered orders",
            ),
            y=alt.Y(
                "payment_type:N",
                title="Payment method",
                sort="-x",
            ),
            tooltip=[
                alt.Tooltip(
                    "payment_type:N",
                    title="Payment method",
                ),
                alt.Tooltip(
                    "primary_order_count:Q",
                    title="Primary paid orders",
                    format=",d",
                ),
                alt.Tooltip(
                    "order_share_pct:Q",
                    title="Primary order share",
                    format=".1f",
                ),
                alt.Tooltip(
                    "attributed_order_gmv:Q",
                    title="Attributed order GMV (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "average_order_value:Q",
                    title="AOV (BRL)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="Paid Orders by Primary Payment Method",
            height=320,
        )
    )


def create_order_value_share_chart(
    structure: pd.DataFrame,
) -> alt.Chart:
    """Create the order and GMV share chart by order-value band."""
    chart_data = (
        structure[
            [
                "order_value_band",
                "order_share_pct",
                "gmv_share_pct",
            ]
        ]
        .melt(
            id_vars="order_value_band",
            value_vars=[
                "order_share_pct",
                "gmv_share_pct",
            ],
            var_name="metric",
            value_name="share_pct",
        )
    )

    chart_data["metric"] = chart_data["metric"].map(
        {
            "order_share_pct": "Order share",
            "gmv_share_pct": "GMV share",
        }
    )

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "order_value_band:N",
                title="Order value band (BRL)",
                sort=ORDER_VALUE_BAND_ORDER,
            ),
            y=alt.Y(
                "share_pct:Q",
                title="Share (%)",
            ),
            xOffset=alt.XOffset(
                "metric:N",
                sort=[
                    "Order share",
                    "GMV share",
                ],
            ),
            color=alt.Color(
                "metric:N",
                title="Metric",
                sort=[
                    "Order share",
                    "GMV share",
                ],
            ),
            tooltip=[
                alt.Tooltip(
                    "order_value_band:N",
                    title="Order value band",
                ),
                alt.Tooltip(
                    "metric:N",
                    title="Metric",
                ),
                alt.Tooltip(
                    "share_pct:Q",
                    title="Share",
                    format=".1f",
                ),
            ],
        )
        .properties(
            title="Order and GMV Share by Order Value Band",
            height=360,
        )
    )


def create_order_value_gmv_chart(
    structure: pd.DataFrame,
) -> alt.Chart:
    """Create the GMV chart by order-value band."""
    return (
        alt.Chart(structure)
        .mark_bar()
        .encode(
            x=alt.X(
                "order_value_band:N",
                title="Order value band (BRL)",
                sort=ORDER_VALUE_BAND_ORDER,
            ),
            y=alt.Y(
                "gmv:Q",
                title="GMV (BRL)",
            ),
            tooltip=[
                alt.Tooltip(
                    "order_value_band:N",
                    title="Order value band",
                ),
                alt.Tooltip(
                    "gmv:Q",
                    title="GMV (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "order_count:Q",
                    title="Distinct orders",
                    format=",d",
                ),
                alt.Tooltip(
                    "average_order_value:Q",
                    title="Payment GMV per order",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="GMV by Order Value Band",
            height=360,
        )
    )


def create_state_gmv_ranking_chart(
    state: pd.DataFrame,
) -> alt.Chart:
    """Create the Top 10 customer-state GMV ranking."""
    top_states = (
        state.head(10)
        .sort_values(
            "gmv",
            ascending=True,
        )
    )

    return (
        alt.Chart(top_states)
        .mark_bar()
        .encode(
            x=alt.X(
                "gmv:Q",
                title="GMV (BRL)",
            ),
            y=alt.Y(
                "customer_state:N",
                title="Customer state",
                sort=None,
            ),
            tooltip=[
                alt.Tooltip(
                    "customer_state:N",
                    title="State",
                ),
                alt.Tooltip(
                    "gmv:Q",
                    title="GMV (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "gmv_share_pct:Q",
                    title="GMV share",
                    format=".1f",
                ),
                alt.Tooltip(
                    "order_count:Q",
                    title="Distinct orders",
                    format=",d",
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=",d",
                ),
                alt.Tooltip(
                    "average_order_value:Q",
                    title="AOV (BRL)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="Top 10 Customer States by GMV",
            height=400,
        )
    )


def create_state_order_ranking_chart(
    state: pd.DataFrame,
) -> alt.Chart:
    """Create the Top 10 customer-state order ranking."""
    top_states = (
        state.sort_values(
            ["order_count", "customer_state"],
            ascending=[False, True],
        )
        .head(10)
        .sort_values(
            "order_count",
            ascending=True,
        )
    )

    return (
        alt.Chart(top_states)
        .mark_bar()
        .encode(
            x=alt.X(
                "order_count:Q",
                title="Distinct orders",
            ),
            y=alt.Y(
                "customer_state:N",
                title="Customer state",
                sort=None,
            ),
            tooltip=[
                alt.Tooltip(
                    "customer_state:N",
                    title="State",
                ),
                alt.Tooltip(
                    "order_count:Q",
                    title="Distinct orders",
                    format=",d",
                ),
                alt.Tooltip(
                    "order_share_pct:Q",
                    title="Order share",
                    format=".1f",
                ),
                alt.Tooltip(
                    "gmv:Q",
                    title="GMV (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=",d",
                ),
            ],
        )
        .properties(
            title="Top 10 Customer States by Orders",
            height=400,
        )
    )


def render_business_structure(
    filtered: pd.DataFrame,
) -> None:
    """Display payment, value-band, and state structure modules."""
    st.subheader("Business Structure Analysis")

    st.caption(
        "All structure charts use the same global filters as the KPI "
        "cards and monthly trends."
    )

    payment_tab, value_tab, state_tab = st.tabs(
        [
            "Payment Methods",
            "Order Value Bands",
            "Customer States",
        ]
    )

    with payment_tab:
        payment = build_payment_structure(
            filtered
        )

        payment_columns = st.columns(2)

        with payment_columns[0]:
            st.altair_chart(
                create_payment_gmv_chart(
                    payment
                ),
                use_container_width=True,
            )

        with payment_columns[1]:
            st.altair_chart(
                create_payment_order_chart(
                    payment
                ),
                use_container_width=True,
            )

        st.caption(
            "GMV is split by the actual amount paid with each method. "
            "Paid-order counts use one primary payment method per order: "
            "the method with the largest aggregated payment amount, with "
            "payment_type ascending as the deterministic tie-breaker. "
            "AOV uses full attributed order GMV divided by primary order count."
        )

        with st.expander(
            "View payment structure data"
        ):
            payment_table = payment[
                [
                    "payment_type",
                    "split_gmv",
                    "gmv_share",
                    "primary_order_count",
                    "order_share",
                    "attributed_order_gmv",
                    "average_order_value",
                    "mixed_payment_orders",
                    "mixed_payment_order_share",
                ]
            ].copy()

            payment_table.columns = [
                "Payment Method",
                "Split GMV (BRL)",
                "GMV Share",
                "Primary Order Count",
                "Primary Order Share",
                "Attributed Order GMV (BRL)",
                "Average Order Value (BRL)",
                "Mixed-Payment Orders",
                "Mixed-Payment Order Share",
            ]

            st.dataframe(
                payment_table.style.format(
                    {
                        "Split GMV (BRL)": "{:,.2f}",
                        "GMV Share": "{:.1%}",
                        "Primary Order Count": "{:,}",
                        "Primary Order Share": "{:.1%}",
                        "Attributed Order GMV (BRL)": "{:,.2f}",
                        "Average Order Value (BRL)": "{:,.2f}",
                        "Mixed-Payment Orders": "{:,}",
                        "Mixed-Payment Order Share": "{:.1%}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with value_tab:
        order_value = build_order_value_structure(
            filtered
        )

        value_columns = st.columns(2)

        with value_columns[0]:
            st.altair_chart(
                create_order_value_share_chart(
                    order_value
                ),
                use_container_width=True,
            )

        with value_columns[1]:
            st.altair_chart(
                create_order_value_gmv_chart(
                    order_value
                ),
                use_container_width=True,
            )

        st.caption(
            "Order value bands use the full positive payment amount at "
            "the order level. Under a payment-method filter, GMV reflects "
            "the selected method contribution within matching orders."
        )

        with st.expander(
            "View order value structure data"
        ):
            value_table = order_value[
                [
                    "order_value_band",
                    "order_count",
                    "order_share",
                    "gmv",
                    "gmv_share",
                    "average_order_value",
                ]
            ].copy()

            value_table.columns = [
                "Order Value Band",
                "Distinct Orders",
                "Order Share",
                "GMV (BRL)",
                "GMV Share",
                "Payment GMV per Order (BRL)",
            ]

            st.dataframe(
                value_table.style.format(
                    {
                        "Distinct Orders": "{:,}",
                        "Order Share": "{:.1%}",
                        "GMV (BRL)": "{:,.2f}",
                        "GMV Share": "{:.1%}",
                        "Payment GMV per Order (BRL)": "{:,.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with state_tab:
        state, concentration = build_state_structure(
            filtered
        )

        concentration_columns = st.columns(4)

        concentration_columns[0].metric(
            "Top 5 States · GMV",
            format_percentage(
                concentration[
                    "top_5_gmv_share"
                ]
            ),
        )

        concentration_columns[1].metric(
            "Top 10 States · GMV",
            format_percentage(
                concentration[
                    "top_10_gmv_share"
                ]
            ),
        )

        concentration_columns[2].metric(
            "Top 5 States · Orders",
            format_percentage(
                concentration[
                    "top_5_order_share"
                ]
            ),
        )

        concentration_columns[3].metric(
            "Top 10 States · Orders",
            format_percentage(
                concentration[
                    "top_10_order_share"
                ]
            ),
        )

        state_columns = st.columns(2)

        with state_columns[0]:
            st.altair_chart(
                create_state_gmv_ranking_chart(
                    state
                ),
                use_container_width=True,
            )

        with state_columns[1]:
            st.altair_chart(
                create_state_order_ranking_chart(
                    state
                ),
                use_container_width=True,
            )

        st.caption(
            "Geography is based on customer_state. Concentration shares "
            "are recalculated from the currently filtered data and are "
            "descriptive indicators, not fixed risk thresholds."
        )

        with st.expander(
            "View customer-state structure data"
        ):
            state_table = state[
                [
                    "gmv_rank",
                    "customer_state",
                    "gmv",
                    "gmv_share",
                    "order_count",
                    "order_share",
                    "customer_count",
                    "average_order_value",
                ]
            ].copy()

            state_table.columns = [
                "GMV Rank",
                "State",
                "GMV (BRL)",
                "GMV Share",
                "Distinct Orders",
                "Order Share",
                "Customers",
                "AOV (BRL)",
            ]

            st.dataframe(
                state_table.style.format(
                    {
                        "GMV Rank": "{:,}",
                        "GMV (BRL)": "{:,.2f}",
                        "GMV Share": "{:.1%}",
                        "Distinct Orders": "{:,}",
                        "Order Share": "{:.1%}",
                        "Customers": "{:,}",
                        "AOV (BRL)": "{:,.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------------------------
# Explainable structural signals
# ---------------------------------------------------------------------------

def build_structural_signals(
    filtered: pd.DataFrame,
) -> tuple[list[dict[str, str | float]], list[dict[str, str | float]]]:
    """
    Build data-based structural risks and opportunities.

    Risk selection uses concentration relative to an equal-share benchmark.
    Opportunity selection uses contribution efficiency and next-tier scale.
    No fixed warning threshold or causal claim is used.
    """
    payment = build_payment_structure(
        filtered
    )

    order_value = build_order_value_structure(
        filtered
    )

    state, concentration = build_state_structure(
        filtered
    )

    order_level = build_order_level_view(
        filtered
    )

    overall_gmv = float(
        order_level[
            "order_payment_amount"
        ].sum()
    )

    overall_orders = int(
        order_level[
            "order_id"
        ].nunique()
    )

    overall_aov = (
        overall_gmv / overall_orders
        if overall_orders > 0
        else 0.0
    )

    risk_candidates: list[
        dict[str, str | float]
    ] = []

    # Payment concentration risk.
    if len(payment) >= 2:
        top_payment = payment.iloc[0]
        equal_share = 1.0 / len(payment)
        concentration_multiple = (
            float(top_payment["gmv_share"])
            / equal_share
            if equal_share > 0
            else 0.0
        )

        risk_candidates.append(
            {
                "score": concentration_multiple,
                "title": (
                    "Payment mix is concentrated in "
                    f"{top_payment['payment_type']}"
                ),
                "evidence": (
                    f"{top_payment['payment_type']} contributes "
                    f"{format_percentage(float(top_payment['gmv_share']))} "
                    "of filtered GMV and is the primary payment method for "
                    f"{format_percentage(float(top_payment['order_share']))} "
                    f"of filtered paid delivered orders. With {len(payment)} available "
                    "payment methods, the equal-share GMV benchmark is "
                    f"{format_percentage(equal_share)}."
                ),
                "implication": (
                    "A disruption, conversion change, or policy change "
                    "affecting the leading payment method could influence "
                    "a large part of current GMV."
                ),
                "monitor": (
                    "Leading-method GMV share, primary-order share, "
                    "mixed-payment order share, and primary-attribution AOV."
                ),
                "basis": (
                    "Ranked by the leading method's GMV share divided by "
                    "the equal-share benchmark."
                ),
            }
        )

    # Geographic concentration risk.
    if len(state) >= 2:
        state_count = len(state)
        equal_top_5_share = (
            min(5, state_count)
            / state_count
        )

        geographic_multiple = (
            concentration[
                "top_5_gmv_share"
            ] / equal_top_5_share
            if equal_top_5_share > 0
            else 0.0
        )

        leading_state = state.iloc[0]

        risk_candidates.append(
            {
                "score": geographic_multiple,
                "title": (
                    "GMV is concentrated in a small group of states"
                ),
                "evidence": (
                    "The Top 5 customer states contribute "
                    f"{format_percentage(concentration['top_5_gmv_share'])} "
                    "of filtered GMV, while the equal-share Top 5 "
                    f"benchmark across {state_count} states is "
                    f"{format_percentage(equal_top_5_share)}. "
                    f"{leading_state['customer_state']} alone contributes "
                    f"{format_percentage(float(leading_state['gmv_share']))}."
                ),
                "implication": (
                    "Platform performance is more exposed to demand, "
                    "logistics, and competitive changes in the leading "
                    "customer states."
                ),
                "monitor": (
                    "Top 5 and Top 10 state GMV share, leading-state share, "
                    "state-level orders, and state-level AOV."
                ),
                "basis": (
                    "Ranked by Top 5 GMV share divided by the equal-share "
                    "Top 5 benchmark."
                ),
            }
        )

    # Order-value-band concentration risk.
    non_empty_bands = order_value.loc[
        order_value["order_count"] > 0
    ].copy()

    if len(non_empty_bands) >= 2:
        top_band = non_empty_bands.sort_values(
            "gmv",
            ascending=False,
        ).iloc[0]

        equal_share = 1.0 / len(
            non_empty_bands
        )

        band_multiple = (
            float(top_band["gmv_share"])
            / equal_share
            if equal_share > 0
            else 0.0
        )

        risk_candidates.append(
            {
                "score": band_multiple,
                "title": (
                    "GMV depends heavily on the "
                    f"{top_band['order_value_band']} order band"
                ),
                "evidence": (
                    f"The {top_band['order_value_band']} band contributes "
                    f"{format_percentage(float(top_band['gmv_share']))} "
                    "of filtered GMV and "
                    f"{format_percentage(float(top_band['order_share']))} "
                    f"of filtered orders. Across {len(non_empty_bands)} "
                    "active bands, the equal-share GMV benchmark is "
                    f"{format_percentage(equal_share)}."
                ),
                "implication": (
                    "A change in demand within the dominant spending band "
                    "could have an outsized effect on platform GMV."
                ),
                "monitor": (
                    "Leading-band GMV share, leading-band order share, "
                    "band-level AOV, and monthly band mix."
                ),
                "basis": (
                    "Ranked by the leading band's GMV share divided by "
                    "the equal-share benchmark."
                ),
            }
        )

    risks = sorted(
        risk_candidates,
        key=lambda item: float(item["score"]),
        reverse=True,
    )[:2]

    opportunities: list[
        dict[str, str | float]
    ] = []

    # Order-value contribution efficiency opportunity.
    efficiency_data = non_empty_bands.loc[
        non_empty_bands["order_share"] > 0
    ].copy()

    if not efficiency_data.empty:
        efficiency_data[
            "gmv_to_order_share_ratio"
        ] = (
            efficiency_data["gmv_share"]
            / efficiency_data["order_share"]
        )

        leverage_band = efficiency_data.sort_values(
            [
                "gmv_to_order_share_ratio",
                "gmv_share",
            ],
            ascending=[False, False],
        ).iloc[0]

        aov_ratio = (
            float(
                leverage_band[
                    "average_order_value"
                ]
            ) / overall_aov
            if overall_aov > 0
            else 0.0
        )

        opportunities.append(
            {
                "score": float(
                    leverage_band[
                        "gmv_to_order_share_ratio"
                    ]
                ),
                "title": (
                    "High-value leverage is strongest in the "
                    f"{leverage_band['order_value_band']} band"
                ),
                "evidence": (
                    f"The band produces "
                    f"{format_percentage(float(leverage_band['gmv_share']))} "
                    "of filtered GMV from "
                    f"{format_percentage(float(leverage_band['order_share']))} "
                    "of filtered orders. Its payment GMV per order is "
                    f"{format_currency(float(leverage_band['average_order_value']))}, "
                    f"or {aov_ratio:.1f}× the filtered overall AOV."
                ),
                "implication": (
                    "Retention, service, and merchandising efforts focused "
                    "on this band may protect a disproportionate share of "
                    "GMV. This is a prioritization signal, not a forecast."
                ),
                "monitor": (
                    "Band-level order share, GMV share, repeat purchase, "
                    "cancellation rate, and service quality."
                ),
                "basis": (
                    "Selected using the highest GMV-share-to-order-share "
                    "ratio among active value bands."
                ),
            }
        )

    # Regional diversification opportunity.
    if len(state) > 5:
        next_tier_state = state.iloc[5]

        next_tier_aov_ratio = (
            float(
                next_tier_state[
                    "average_order_value"
                ]
            ) / overall_aov
            if overall_aov > 0
            else 0.0
        )

        opportunities.append(
            {
                "score": (
                    float(next_tier_state["gmv_share"])
                    * max(next_tier_aov_ratio, 0.01)
                ),
                "title": (
                    "The next-tier regional diversification candidate is "
                    f"{next_tier_state['customer_state']}"
                ),
                "evidence": (
                    f"{next_tier_state['customer_state']} is the largest "
                    "state outside the current Top 5 by GMV, contributing "
                    f"{format_percentage(float(next_tier_state['gmv_share']))} "
                    "of filtered GMV from "
                    f"{format_integer(int(next_tier_state['order_count']))} "
                    "orders and "
                    f"{format_integer(int(next_tier_state['customer_count']))} "
                    "customers. Its AOV is "
                    f"{format_currency(float(next_tier_state['average_order_value']))} "
                    f"({next_tier_aov_ratio:.1f}× the filtered overall AOV)."
                ),
                "implication": (
                    "This state provides the clearest existing scale base "
                    "outside the Top 5 for diversification analysis. "
                    "Additional logistics, margin, and acquisition evidence "
                    "is required before investment."
                ),
                "monitor": (
                    "State GMV share, customer growth, AOV, delivery time, "
                    "freight cost, and repeat purchase."
                ),
                "basis": (
                    "Selected as the highest-GMV state outside the current "
                    "Top 5."
                ),
            }
        )

    # Fallback payment opportunity when the filtered scope has too few states.
    if len(opportunities) < 2 and len(payment) >= 2:
        non_leading_payment = (
            payment.iloc[1:]
            .sort_values(
                [
                    "average_order_value",
                    "split_gmv",
                ],
                ascending=[False, False],
            )
            .iloc[0]
        )

        payment_aov_ratio = (
            float(
                non_leading_payment[
                    "average_order_value"
                ]
            ) / overall_aov
            if overall_aov > 0
            else 0.0
        )

        opportunities.append(
            {
                "score": payment_aov_ratio,
                "title": (
                    "A higher-value payment segment appears in "
                    f"{non_leading_payment['payment_type']}"
                ),
                "evidence": (
                    f"{non_leading_payment['payment_type']} has a "
                    "primary-attribution AOV of "
                    f"{format_currency(float(non_leading_payment['average_order_value']))}, "
                    f"or {payment_aov_ratio:.1f}× the filtered overall AOV, "
                    "while contributing "
                    f"{format_percentage(float(non_leading_payment['gmv_share']))} "
                    "of GMV."
                ),
                "implication": (
                    "This segment may warrant checkout, financing, or "
                    "customer-profile analysis. The structure alone does "
                    "not show that expanding the method would cause growth."
                ),
                "monitor": (
                    "Primary-attribution AOV, conversion, payment failure "
                    "rate, refund rate, and customer profile."
                ),
                "basis": (
                    "Selected as the highest-AOV non-leading payment method."
                ),
            }
        )

    opportunities = sorted(
        opportunities,
        key=lambda item: float(item["score"]),
        reverse=True,
    )[:2]

    return risks, opportunities


def render_signal_card(
    signal: dict[str, str | float],
    label: str,
) -> None:
    """Render one explainable structural signal."""
    with st.container(
        border=True
    ):
        st.markdown(
            f"#### {label}: {signal['title']}"
        )

        st.markdown(
            f"**Evidence:** {signal['evidence']}"
        )

        st.markdown(
            f"**Business implication:** {signal['implication']}"
        )

        st.markdown(
            f"**Monitor:** {signal['monitor']}"
        )

        st.caption(
            f"Selection basis: {signal['basis']}"
        )


def render_structural_signals(
    filtered: pd.DataFrame,
) -> None:
    """Display two risks and two opportunities from the filtered data."""
    st.subheader(
        "Explainable Structural Signals"
    )

    st.caption(
        "Signals are recalculated from the current filters. Risk signals "
        "use relative concentration versus equal-share benchmarks; "
        "opportunities use observed contribution efficiency or next-tier "
        "scale. No fixed arbitrary warning threshold is applied."
    )

    risks, opportunities = build_structural_signals(
        filtered
    )

    risk_column, opportunity_column = st.columns(2)

    with risk_column:
        st.markdown(
            "### Structural Risks"
        )

        if risks:
            for index, risk in enumerate(
                risks,
                start=1,
            ):
                render_signal_card(
                    risk,
                    label=f"Risk {index}",
                )
        else:
            st.info(
                "The current filters leave too few independent categories "
                "to produce a concentration-based risk signal. Reset or "
                "broaden the filters for a fuller view."
            )

    with opportunity_column:
        st.markdown(
            "### Structural Opportunities"
        )

        if opportunities:
            for index, opportunity in enumerate(
                opportunities,
                start=1,
            ):
                render_signal_card(
                    opportunity,
                    label=f"Opportunity {index}",
                )
        else:
            st.info(
                "The current filters leave too few categories to produce "
                "a supported structural opportunity signal."
            )

    with st.expander(
        "How the signals are selected"
    ):
        st.markdown(
            """
- **Concentration risks:** compare the leading category share with an
  equal-share benchmark based on the number of categories visible under
  the current filters.
- **Value-band opportunity:** select the band with the highest ratio of
  GMV share to order share.
- **Regional opportunity:** select the highest-GMV state outside the
  current Top 5.
- **Interpretation boundary:** these are descriptive structural signals.
  They do not prove causality or predict the effect of an intervention.
            """
        )

# ---------------------------------------------------------------------------
# Stage 1 core-metrics worksheet
# ---------------------------------------------------------------------------

def reset_stage1_filters(
    minimum_date: date,
    maximum_date: date,
) -> None:
    """Restore the Stage 1 date filter to the full order observation."""
    st.session_state["stage1_date_range"] = (
        minimum_date,
        maximum_date,
    )


def render_stage1_filters(
    data: pd.DataFrame,
) -> dict[str, date]:
    """Render the metric-safe Stage 1 filter set."""
    minimum_date = data["purchase_date"].min()
    maximum_date = data["purchase_date"].max()

    with st.sidebar:
        st.header("Stage 1 Filters")

        if st.button(
            "Reset Stage 1 filters",
            use_container_width=True,
            key="stage1_reset_filters",
        ):
            reset_stage1_filters(
                minimum_date,
                maximum_date,
            )
            st.rerun()

        selected_dates = st.date_input(
            "Date range",
            value=(
                minimum_date,
                maximum_date,
            ),
            min_value=minimum_date,
            max_value=maximum_date,
            key="stage1_date_range",
        )

        st.caption(
            "Stage 1 uses purchase date as the default business time. "
            "Metric-specific cohorts keep their formal denominators."
        )

    if isinstance(
        selected_dates,
        (tuple, list),
    ):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
        elif len(selected_dates) == 1:
            start_date = selected_dates[0]
            end_date = selected_dates[0]
        else:
            start_date = minimum_date
            end_date = maximum_date
    else:
        start_date = selected_dates
        end_date = selected_dates

    return {
        "start_date": start_date,
        "end_date": end_date,
    }


def apply_stage1_date_filter(
    data: pd.DataFrame,
    filters: dict[str, date],
) -> pd.DataFrame:
    """Apply only the Stage 1 purchase-date filter."""
    return data.loc[
        data["purchase_date"].between(
            filters["start_date"],
            filters["end_date"],
        )
    ].copy()


def calculate_stage1_m01_m08(
    filtered: pd.DataFrame,
    source_data: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> dict[str, float | int | None]:
    """Calculate Stage 1 metrics M01-M08 using their formal cohorts."""
    valid_orders = filtered.loc[
        filtered["is_valid_order"] == 1
    ].copy()

    paid_orders = filtered.loc[
        filtered["is_paid_delivered_order"] == 1
    ].copy()

    gmv = float(
        paid_orders["order_payment_amount"].sum()
    )

    valid_order_count = int(
        valid_orders["order_id"].nunique()
    )

    paid_order_count = int(
        paid_orders["order_id"].nunique()
    )

    average_order_value = (
        gmv / paid_order_count
        if paid_order_count > 0
        else None
    )

    active_customer_count = int(
        valid_orders[
            "customer_unique_id"
        ].nunique()
    )

    first_purchase = (
        source_data[
            [
                "customer_unique_id",
                "first_delivered_purchase_timestamp",
            ]
        ]
        .dropna(
            subset=[
                "customer_unique_id",
                "first_delivered_purchase_timestamp",
            ]
        )
        .drop_duplicates(
            subset=["customer_unique_id"],
            keep="first",
        )
        .copy()
    )

    first_purchase["first_purchase_date"] = (
        first_purchase[
            "first_delivered_purchase_timestamp"
        ].dt.date
    )

    new_customer_count = int(
        first_purchase.loc[
            first_purchase[
                "first_purchase_date"
            ].between(
                start_date,
                end_date,
            ),
            "customer_unique_id",
        ].nunique()
    )

    user_order_counts = (
        valid_orders.dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            "customer_unique_id"
        )["order_id"]
        .nunique()
    )

    repeat_customer_count = int(
        (user_order_counts >= 2).sum()
    )

    repeat_purchase_rate = (
        repeat_customer_count
        / active_customer_count
        if active_customer_count > 0
        else None
    )

    return {
        "gmv": gmv,
        "valid_order_count": valid_order_count,
        "average_order_value": average_order_value,
        "paid_order_count": paid_order_count,
        "active_customer_count": active_customer_count,
        "new_customer_count": new_customer_count,
        "repeat_customer_count": repeat_customer_count,
        "repeat_purchase_rate": repeat_purchase_rate,
    }


def render_stage1_m01_m08_cards(
    metrics: dict[str, float | int | None],
) -> None:
    """Render the first eight formal Stage 1 metrics."""
    revenue_columns = st.columns([1.7, 1, 1, 1])

    revenue_columns[0].metric(
        "M01 · GMV",
        format_currency(
            float(metrics["gmv"])
        ),
    )

    revenue_columns[1].metric(
        "M02 · Valid Orders",
        format_integer(
            int(metrics["valid_order_count"])
        ),
    )

    aov = metrics["average_order_value"]

    revenue_columns[2].metric(
        "M03 · Average Order Value",
        (
            format_currency(float(aov))
            if aov is not None
            else "—"
        ),
    )

    revenue_columns[3].metric(
        "M04 · Paid Orders",
        format_integer(
            int(metrics["paid_order_count"])
        ),
    )

    customer_columns = st.columns(4)

    customer_columns[0].metric(
        "M05 · Active Customers",
        format_integer(
            int(metrics["active_customer_count"])
        ),
    )

    customer_columns[1].metric(
        "M06 · New Customers",
        format_integer(
            int(metrics["new_customer_count"])
        ),
    )

    customer_columns[2].metric(
        "M07 · Repeat Customers",
        format_integer(
            int(metrics["repeat_customer_count"])
        ),
    )

    repeat_rate = metrics[
        "repeat_purchase_rate"
    ]

    customer_columns[3].metric(
        "M08 · Repeat Purchase Rate",
        (
            format_percentage(
                float(repeat_rate)
            )
            if repeat_rate is not None
            else "—"
        ),
    )


def build_stage1_m01_m08_monthly_trends(
    filtered: pd.DataFrame,
    source_data: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Build monthly Stage 1 M01-M08 series without inventing missing months."""
    month_start = (
        pd.Timestamp(start_date)
        .to_period("M")
        .to_timestamp()
    )

    month_end = (
        pd.Timestamp(end_date)
        .to_period("M")
        .to_timestamp()
    )

    complete_months = pd.DataFrame(
        {
            "month": pd.date_range(
                month_start,
                month_end,
                freq="MS",
            )
        }
    )

    source_valid_months = set(
        source_data.loc[
            source_data["is_valid_order"] == 1,
            "purchase_month_start",
        ].dropna()
    )

    complete_months[
        "source_valid_month_observed"
    ] = complete_months["month"].isin(
        source_valid_months
    )

    valid_orders = filtered.loc[
        filtered["is_valid_order"] == 1
    ].copy()

    paid_orders = filtered.loc[
        filtered["is_paid_delivered_order"] == 1
    ].copy()

    monthly_gmv = (
        paid_orders.groupby(
            "purchase_month_start",
            as_index=False,
        )["order_payment_amount"]
        .sum()
        .rename(
            columns={
                "purchase_month_start": "month",
                "order_payment_amount": "gmv",
            }
        )
    )

    monthly_valid_orders = (
        valid_orders.groupby(
            "purchase_month_start",
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "order_id": "valid_order_count",
            }
        )
    )

    monthly_paid_orders = (
        paid_orders.groupby(
            "purchase_month_start",
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "order_id": "paid_order_count",
            }
        )
    )

    monthly_active_customers = (
        valid_orders.dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            "purchase_month_start",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "customer_unique_id": "active_customer_count",
            }
        )
    )

    customer_month_orders = (
        valid_orders.dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            [
                "purchase_month_start",
                "customer_unique_id",
            ],
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "order_id": "valid_order_count",
            }
        )
    )

    monthly_repeat_customers = (
        customer_month_orders.loc[
            customer_month_orders[
                "valid_order_count"
            ] >= 2
        ]
        .groupby(
            "purchase_month_start",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "purchase_month_start": "month",
                "customer_unique_id": "repeat_customer_count",
            }
        )
    )

    first_purchase = (
        source_data[
            [
                "customer_unique_id",
                "first_delivered_purchase_timestamp",
            ]
        ]
        .dropna(
            subset=[
                "customer_unique_id",
                "first_delivered_purchase_timestamp",
            ]
        )
        .drop_duplicates(
            subset=["customer_unique_id"],
            keep="first",
        )
        .copy()
    )

    first_purchase["first_purchase_date"] = (
        first_purchase[
            "first_delivered_purchase_timestamp"
        ].dt.date
    )

    first_purchase = first_purchase.loc[
        first_purchase[
            "first_purchase_date"
        ].between(
            start_date,
            end_date,
        )
    ].copy()

    first_purchase["month"] = (
        first_purchase[
            "first_delivered_purchase_timestamp"
        ]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly_new_customers = (
        first_purchase.groupby(
            "month",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "customer_unique_id": "new_customer_count",
            }
        )
    )

    trends = complete_months.copy()

    for monthly_data in [
        monthly_gmv,
        monthly_valid_orders,
        monthly_paid_orders,
        monthly_active_customers,
        monthly_new_customers,
        monthly_repeat_customers,
    ]:
        trends = trends.merge(
            monthly_data,
            on="month",
            how="left",
        )

    fill_zero_columns = [
        "gmv",
        "valid_order_count",
        "paid_order_count",
        "active_customer_count",
        "new_customer_count",
        "repeat_customer_count",
    ]

    observed_mask = trends[
        "source_valid_month_observed"
    ]

    for column in fill_zero_columns:
        trends.loc[
            observed_mask
            & trends[column].isna(),
            column,
        ] = 0

        trends.loc[
            ~observed_mask,
            column,
        ] = pd.NA

    trends["average_order_value"] = (
        trends["gmv"]
        / trends[
            "paid_order_count"
        ].replace(
            0,
            pd.NA,
        )
    )

    trends["repeat_purchase_rate"] = (
        trends["repeat_customer_count"]
        / trends[
            "active_customer_count"
        ].replace(
            0,
            pd.NA,
        )
    )

    for column in [
        "valid_order_count",
        "paid_order_count",
        "active_customer_count",
        "new_customer_count",
        "repeat_customer_count",
    ]:
        trends[column] = pd.to_numeric(
            trends[column],
            errors="coerce",
        ).astype("Int64")

    return trends.drop(
        columns=[
            "source_valid_month_observed",
        ]
    )


def render_stage1_partial_month_note(
    start_date: date,
    end_date: date,
) -> None:
    """Flag partial calendar months in Stage 1 trend views."""
    start_timestamp = pd.Timestamp(start_date)
    end_timestamp = pd.Timestamp(end_date)

    start_is_partial = (
        start_timestamp.day != 1
    )

    end_is_partial = (
        end_timestamp
        != end_timestamp
        .to_period("M")
        .end_time
        .normalize()
    )

    if start_is_partial or end_is_partial:
        st.info(
            "The selected range starts or ends within a calendar month. "
            "The first and/or last monthly points therefore represent "
            "partial-month results."
        )


def render_stage1_revenue_order_trends(
    trends: pd.DataFrame,
) -> None:
    """Render M01-M04 monthly trends."""
    tabs = st.tabs(
        [
            "M01 · GMV",
            "M02 · Valid Orders",
            "M03 · AOV",
            "M04 · Paid Orders",
        ]
    )

    chart_specs = [
        (
            "gmv",
            "Monthly GMV",
            "GMV (BRL)",
            ",.2f",
        ),
        (
            "valid_order_count",
            "Monthly Valid Orders",
            "Valid delivered orders",
            ",d",
        ),
        (
            "average_order_value",
            "Monthly Average Order Value",
            "Average order value (BRL)",
            ",.2f",
        ),
        (
            "paid_order_count",
            "Monthly Paid Orders",
            "Paid delivered orders",
            ",d",
        ),
    ]

    for tab, spec in zip(
        tabs,
        chart_specs,
    ):
        with tab:
            metric, title, y_title, tooltip_format = spec

            st.altair_chart(
                create_trend_chart(
                    trends,
                    metric=metric,
                    title=title,
                    y_title=y_title,
                    tooltip_format=tooltip_format,
                ),
                use_container_width=True,
            )


def render_stage1_customer_trends(
    trends: pd.DataFrame,
) -> None:
    """Render M05-M08 monthly customer trends."""
    tabs = st.tabs(
        [
            "M05 · Active",
            "M06 · New",
            "M07 · Repeat",
            "M08 · Repeat Rate",
        ]
    )

    chart_specs = [
        (
            "active_customer_count",
            "Monthly Active Customers",
            "Distinct active customers",
            ",d",
        ),
        (
            "new_customer_count",
            "Monthly New Customers",
            "Distinct new customers",
            ",d",
        ),
        (
            "repeat_customer_count",
            "Monthly Repeat Customers",
            "Distinct repeat customers",
            ",d",
        ),
        (
            "repeat_purchase_rate",
            "Monthly Repeat Purchase Rate",
            "Repeat purchase rate",
            ".1%",
        ),
    ]

    for tab, spec in zip(
        tabs,
        chart_specs,
    ):
        with tab:
            metric, title, y_title, tooltip_format = spec

            st.altair_chart(
                create_trend_chart(
                    trends,
                    metric=metric,
                    title=title,
                    y_title=y_title,
                    tooltip_format=tooltip_format,
                ),
                use_container_width=True,
            )


def render_stage1_filter_summary(
    filtered: pd.DataFrame,
    filters: dict[str, date],
) -> None:
    """Show Stage 1 period and cohort volumes."""
    valid_orders = int(
        filtered.loc[
            filtered["is_valid_order"] == 1,
            "order_id",
        ].nunique()
    )

    paid_orders = int(
        filtered.loc[
            filtered[
                "is_paid_delivered_order"
            ] == 1,
            "order_id",
        ].nunique()
    )

    st.caption(
        f"Selected period: {filters['start_date']} to {filters['end_date']} · "
        f"All order rows: {len(filtered):,} · "
        f"Valid delivered orders: {valid_orders:,} · "
        f"Paid delivered orders: {paid_orders:,}"
    )


def calculate_stage1_m10_m17(
    filtered: pd.DataFrame,
) -> dict[str, float | int | None]:
    """Calculate Stage 1 metrics M10-M17 with metric-specific denominators."""
    valid_orders = filtered.loc[
        filtered["is_valid_order"] == 1
    ].copy()

    paid_orders = filtered.loc[
        filtered["is_paid_delivered_order"] == 1
    ].copy()

    customer_revenue = (
        paid_orders.dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            "customer_unique_id",
            as_index=False,
        )["order_payment_amount"]
        .sum()
        .rename(
            columns={
                "order_payment_amount": "customer_revenue",
            }
        )
    )

    customer_lifetime_value = (
        float(
            customer_revenue[
                "customer_revenue"
            ].mean()
        )
        if not customer_revenue.empty
        else None
    )

    active_customer_count = int(
        valid_orders[
            "customer_unique_id"
        ].nunique()
    )

    valid_order_count = int(
        valid_orders["order_id"].nunique()
    )

    average_purchase_frequency = (
        valid_order_count
        / active_customer_count
        if active_customer_count > 0
        else None
    )

    sequenced = (
        valid_orders.dropna(
            subset=[
                "customer_unique_id",
                "order_purchase_timestamp",
            ]
        )
        .sort_values(
            [
                "customer_unique_id",
                "order_purchase_timestamp",
                "order_id",
            ]
        )
        .copy()
    )

    sequenced["previous_purchase_timestamp"] = (
        sequenced.groupby(
            "customer_unique_id"
        )["order_purchase_timestamp"]
        .shift(1)
    )

    sequenced["interval_days"] = (
        sequenced[
            "order_purchase_timestamp"
        ]
        - sequenced[
            "previous_purchase_timestamp"
        ]
    ).dt.total_seconds() / 86400.0

    valid_intervals = sequenced.loc[
        sequenced["interval_days"].notna()
        & (sequenced["interval_days"] >= 0)
    ].copy()

    average_repurchase_interval = (
        float(
            valid_intervals[
                "interval_days"
            ].mean()
        )
        if not valid_intervals.empty
        else None
    )

    delivery_orders = valid_orders.loc[
        valid_orders["delivery_days"].notna()
    ].copy()

    average_delivery_time = (
        float(
            delivery_orders[
                "delivery_days"
            ].mean()
        )
        if not delivery_orders.empty
        else None
    )

    evaluable_delivery = filtered.loc[
        filtered["is_delivery_evaluable"] == 1
    ].copy()

    late_delivery_rate = (
        float(
            evaluable_delivery[
                "is_late_delivery"
            ].sum()
        )
        / len(evaluable_delivery)
        if not evaluable_delivery.empty
        else None
    )

    reviewed_orders = filtered.loc[
        filtered["has_valid_review"] == 1
    ].copy()

    average_review_score = (
        float(
            reviewed_orders[
                "review_score"
            ].mean()
        )
        if not reviewed_orders.empty
        else None
    )

    positive_review_rate = (
        float(
            reviewed_orders[
                "is_positive_review"
            ].sum()
        )
        / len(reviewed_orders)
        if not reviewed_orders.empty
        else None
    )

    total_order_count = int(
        filtered["order_id"].nunique()
    )

    canceled_order_count = int(
        filtered.loc[
            filtered["order_status"] == "canceled",
            "order_id",
        ].nunique()
    )

    cancellation_rate = (
        canceled_order_count
        / total_order_count
        if total_order_count > 0
        else None
    )

    return {
        "customer_lifetime_value": customer_lifetime_value,
        "paying_customer_count": int(
            customer_revenue[
                "customer_unique_id"
            ].nunique()
        ),
        "average_purchase_frequency": average_purchase_frequency,
        "average_repurchase_interval_days": average_repurchase_interval,
        "valid_interval_count": int(
            len(valid_intervals)
        ),
        "average_delivery_days": average_delivery_time,
        "delivery_order_count": int(
            len(delivery_orders)
        ),
        "late_delivery_rate": late_delivery_rate,
        "evaluable_delivery_order_count": int(
            len(evaluable_delivery)
        ),
        "average_review_score": average_review_score,
        "reviewed_order_count": int(
            len(reviewed_orders)
        ),
        "positive_review_rate": positive_review_rate,
        "total_order_count": total_order_count,
        "canceled_order_count": canceled_order_count,
        "cancellation_rate": cancellation_rate,
    }


def render_stage1_m10_m17_cards(
    metrics: dict[str, float | int | None],
) -> None:
    """Render scalar Stage 1 metrics M10-M17."""
    customer_columns = st.columns(3)

    ltv = metrics["customer_lifetime_value"]
    customer_columns[0].metric(
        "M10 · Observed Revenue LTV",
        (
            format_currency(float(ltv))
            if ltv is not None
            else "—"
        ),
    )

    frequency = metrics[
        "average_purchase_frequency"
    ]
    customer_columns[1].metric(
        "M11 · Avg Purchase Frequency",
        (
            f"{float(frequency):,.3f}"
            if frequency is not None
            else "—"
        ),
    )

    interval = metrics[
        "average_repurchase_interval_days"
    ]
    customer_columns[2].metric(
        "M12 · Avg Repurchase Interval",
        (
            f"{float(interval):,.2f} days"
            if interval is not None
            else "—"
        ),
    )

    experience_columns = st.columns(4)

    delivery = metrics["average_delivery_days"]
    experience_columns[0].metric(
        "M13 · Avg Delivery Time",
        (
            f"{float(delivery):,.2f} days"
            if delivery is not None
            else "—"
        ),
    )

    late_rate = metrics["late_delivery_rate"]
    experience_columns[1].metric(
        "M14 · Late Delivery Rate",
        (
            format_percentage(
                float(late_rate)
            )
            if late_rate is not None
            else "—"
        ),
    )

    review_score = metrics[
        "average_review_score"
    ]
    experience_columns[2].metric(
        "M15 · Avg Review Score",
        (
            f"{float(review_score):,.2f} / 5"
            if review_score is not None
            else "—"
        ),
    )

    positive_rate = metrics[
        "positive_review_rate"
    ]
    experience_columns[3].metric(
        "M16 · Positive Review Rate",
        (
            format_percentage(
                float(positive_rate)
            )
            if positive_rate is not None
            else "—"
        ),
    )

    cancellation_rate = metrics[
        "cancellation_rate"
    ]
    st.metric(
        "M17 · Cancellation Rate",
        (
            format_percentage(
                float(cancellation_rate)
            )
            if cancellation_rate is not None
            else "—"
        ),
    )


def filter_stage1_cohort_months(
    cohort: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Filter M09 by cohort start month without truncating observed activity."""
    start_month = (
        pd.Timestamp(start_date)
        .to_period("M")
        .to_timestamp()
    )

    end_month = (
        pd.Timestamp(end_date)
        .to_period("M")
        .to_timestamp()
    )

    return cohort.loc[
        cohort["cohort_month"].between(
            start_month,
            end_month,
        )
    ].copy()


def create_stage1_retention_heatmap(
    cohort: pd.DataFrame,
) -> alt.Chart:
    """Create the M09 natural-month cohort retention heatmap."""
    chart_data = cohort.copy()

    chart_data["cohort_label"] = (
        chart_data["cohort_month"]
        .dt.strftime("%Y-%m")
    )

    chart_data["retention_pct"] = (
        chart_data[
            "customer_retention_rate"
        ] * 100
    )

    return (
        alt.Chart(chart_data)
        .mark_rect()
        .encode(
            x=alt.X(
                "retention_month_number:O",
                title="Retention month number",
            ),
            y=alt.Y(
                "cohort_label:O",
                title="Cohort month",
                sort=alt.SortField(
                    field="cohort_month",
                    order="ascending",
                ),
            ),
            color=alt.Color(
                "customer_retention_rate:Q",
                title="Retention rate",
                scale=alt.Scale(
                    domain=[0, 1],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "cohort_label:N",
                    title="Cohort month",
                ),
                alt.Tooltip(
                    "retention_month_number:O",
                    title="Retention month",
                ),
                alt.Tooltip(
                    "cohort_customer_count:Q",
                    title="Cohort customers",
                    format=",d",
                ),
                alt.Tooltip(
                    "retained_customer_count:Q",
                    title="Retained customers",
                    format=",d",
                ),
                alt.Tooltip(
                    "retention_pct:Q",
                    title="Retention rate (%)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="M09 · Natural-Month Customer Retention",
            height=480,
        )
    )


def build_stage1_customer_revenue(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Build per-customer positive delivered revenue for M10."""
    return (
        filtered.loc[
            filtered[
                "is_paid_delivered_order"
            ] == 1
        ]
        .dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            "customer_unique_id",
            as_index=False,
        )["order_payment_amount"]
        .sum()
        .rename(
            columns={
                "order_payment_amount": "customer_revenue",
            }
        )
    )


def create_stage1_ltv_distribution(
    customer_revenue: pd.DataFrame,
) -> alt.Chart:
    """Create a customer-revenue distribution supporting M10."""
    return (
        alt.Chart(customer_revenue)
        .mark_bar()
        .encode(
            x=alt.X(
                "customer_revenue:Q",
                bin=alt.Bin(maxbins=35),
                title="Observed customer revenue (BRL)",
            ),
            y=alt.Y(
                "count():Q",
                title="Paying customers",
            ),
            tooltip=[
                alt.Tooltip(
                    "count():Q",
                    title="Paying customers",
                    format=",d",
                ),
            ],
        )
        .properties(
            title="Customer Revenue Distribution",
            height=360,
        )
    )


def build_stage1_customer_frequency(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Build delivered-order counts per active customer for M11."""
    customer_frequency = (
        filtered.loc[
            filtered["is_valid_order"] == 1
        ]
        .dropna(
            subset=["customer_unique_id"]
        )
        .groupby(
            "customer_unique_id",
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "order_id": "purchase_frequency",
            }
        )
    )

    return (
        customer_frequency.groupby(
            "purchase_frequency",
            as_index=False,
        )["customer_unique_id"]
        .nunique()
        .rename(
            columns={
                "customer_unique_id": "customer_count",
            }
        )
        .sort_values(
            "purchase_frequency"
        )
    )


def create_stage1_frequency_chart(
    frequency: pd.DataFrame,
) -> alt.Chart:
    """Create the M11 customer purchase-frequency distribution."""
    return (
        alt.Chart(frequency)
        .mark_bar()
        .encode(
            x=alt.X(
                "purchase_frequency:O",
                title="Delivered orders per active customer",
            ),
            y=alt.Y(
                "customer_count:Q",
                title="Active customers",
            ),
            tooltip=[
                alt.Tooltip(
                    "purchase_frequency:O",
                    title="Delivered orders",
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Active customers",
                    format=",d",
                ),
            ],
        )
        .properties(
            title="Active Customers by Purchase Frequency",
            height=360,
        )
    )


def build_stage1_repurchase_intervals(
    filtered: pd.DataFrame,
) -> pd.DataFrame:
    """Build all legal adjacent delivered-order intervals for M12."""
    sequenced = (
        filtered.loc[
            filtered["is_valid_order"] == 1
        ]
        .dropna(
            subset=[
                "customer_unique_id",
                "order_purchase_timestamp",
            ]
        )
        .sort_values(
            [
                "customer_unique_id",
                "order_purchase_timestamp",
                "order_id",
            ]
        )
        .copy()
    )

    sequenced["previous_purchase_timestamp"] = (
        sequenced.groupby(
            "customer_unique_id"
        )["order_purchase_timestamp"]
        .shift(1)
    )

    sequenced["interval_days"] = (
        sequenced[
            "order_purchase_timestamp"
        ]
        - sequenced[
            "previous_purchase_timestamp"
        ]
    ).dt.total_seconds() / 86400.0

    return sequenced.loc[
        sequenced["interval_days"].notna()
        & (sequenced["interval_days"] >= 0),
        [
            "customer_unique_id",
            "interval_days",
        ],
    ].copy()


def create_stage1_interval_chart(
    intervals: pd.DataFrame,
) -> alt.Chart:
    """Create the M12 adjacent-order interval distribution."""
    return (
        alt.Chart(intervals)
        .mark_bar()
        .encode(
            x=alt.X(
                "interval_days:Q",
                bin=alt.Bin(maxbins=35),
                title="Adjacent delivered-order interval (days)",
            ),
            y=alt.Y(
                "count():Q",
                title="Valid adjacent order intervals",
            ),
            tooltip=[
                alt.Tooltip(
                    "count():Q",
                    title="Intervals",
                    format=",d",
                ),
            ],
        )
        .properties(
            title="Repurchase Interval Distribution",
            height=360,
        )
    )


def build_stage1_m13_m17_monthly_trends(
    filtered: pd.DataFrame,
    source_data: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Build monthly M13-M17 series with denominator-aware missing values."""
    month_start = (
        pd.Timestamp(start_date)
        .to_period("M")
        .to_timestamp()
    )

    month_end = (
        pd.Timestamp(end_date)
        .to_period("M")
        .to_timestamp()
    )

    trends = pd.DataFrame(
        {
            "month": pd.date_range(
                month_start,
                month_end,
                freq="MS",
            )
        }
    )

    valid_source_months = set(
        source_data.loc[
            source_data["is_valid_order"] == 1,
            "purchase_month_start",
        ].dropna()
    )

    all_source_months = set(
        source_data[
            "purchase_month_start"
        ].dropna()
    )

    trends[
        "valid_source_month_observed"
    ] = trends["month"].isin(
        valid_source_months
    )

    trends[
        "all_source_month_observed"
    ] = trends["month"].isin(
        all_source_months
    )

    delivery = filtered.loc[
        (filtered["is_valid_order"] == 1)
        & filtered["delivery_days"].notna()
    ].copy()

    monthly_delivery = (
        delivery.groupby(
            "purchase_month_start",
            as_index=False,
        )["delivery_days"]
        .mean()
        .rename(
            columns={
                "purchase_month_start": "month",
                "delivery_days": "average_delivery_days",
            }
        )
    )

    evaluable = filtered.loc[
        filtered["is_delivery_evaluable"] == 1
    ].copy()

    monthly_late = (
        evaluable.groupby(
            "purchase_month_start",
            as_index=False,
        )
        .agg(
            evaluable_delivery_orders=(
                "order_id",
                "nunique",
            ),
            late_delivery_orders=(
                "is_late_delivery",
                "sum",
            ),
        )
        .rename(
            columns={
                "purchase_month_start": "month",
            }
        )
    )

    monthly_late[
        "late_delivery_rate"
    ] = (
        monthly_late[
            "late_delivery_orders"
        ]
        / monthly_late[
            "evaluable_delivery_orders"
        ].replace(
            0,
            pd.NA,
        )
    )

    reviewed = filtered.loc[
        filtered["has_valid_review"] == 1
    ].copy()

    monthly_reviews = (
        reviewed.groupby(
            "purchase_month_start",
            as_index=False,
        )
        .agg(
            average_review_score=(
                "review_score",
                "mean",
            ),
            reviewed_orders=(
                "order_id",
                "nunique",
            ),
            positive_review_orders=(
                "is_positive_review",
                "sum",
            ),
        )
        .rename(
            columns={
                "purchase_month_start": "month",
            }
        )
    )

    monthly_reviews[
        "positive_review_rate"
    ] = (
        monthly_reviews[
            "positive_review_orders"
        ]
        / monthly_reviews[
            "reviewed_orders"
        ].replace(
            0,
            pd.NA,
        )
    )

    monthly_cancellation = (
        filtered.groupby(
            "purchase_month_start",
            as_index=False,
        )
        .agg(
            total_orders=(
                "order_id",
                "nunique",
            ),
            canceled_orders=(
                "order_status",
                lambda values: int(
                    (values == "canceled").sum()
                ),
            ),
        )
        .rename(
            columns={
                "purchase_month_start": "month",
            }
        )
    )

    monthly_cancellation[
        "cancellation_rate"
    ] = (
        monthly_cancellation[
            "canceled_orders"
        ]
        / monthly_cancellation[
            "total_orders"
        ].replace(
            0,
            pd.NA,
        )
    )

    for monthly_data in [
        monthly_delivery,
        monthly_late[
            [
                "month",
                "late_delivery_rate",
            ]
        ],
        monthly_reviews[
            [
                "month",
                "average_review_score",
                "positive_review_rate",
            ]
        ],
        monthly_cancellation[
            [
                "month",
                "total_orders",
                "canceled_orders",
                "cancellation_rate",
            ]
        ],
    ]:
        trends = trends.merge(
            monthly_data,
            on="month",
            how="left",
        )

    for column in [
        "average_delivery_days",
        "late_delivery_rate",
        "average_review_score",
        "positive_review_rate",
    ]:
        trends.loc[
            ~trends[
                "valid_source_month_observed"
            ],
            column,
        ] = pd.NA

    cancellation_columns = [
        "total_orders",
        "canceled_orders",
        "cancellation_rate",
    ]

    trends.loc[
        ~trends[
            "all_source_month_observed"
        ],
        cancellation_columns,
    ] = pd.NA

    observed_missing_cancellation = (
        trends[
            "all_source_month_observed"
        ]
        & trends[
            "total_orders"
        ].isna()
    )

    trends.loc[
        observed_missing_cancellation,
        [
            "total_orders",
            "canceled_orders",
        ],
    ] = 0

    trends.loc[
        observed_missing_cancellation,
        "cancellation_rate",
    ] = pd.NA

    return trends.drop(
        columns=[
            "valid_source_month_observed",
            "all_source_month_observed",
        ]
    )


def create_stage1_cancellation_chart(
    trends: pd.DataFrame,
) -> alt.Chart:
    """Create the M17 monthly cancellation chart with denominator context."""
    chart_data = trends[
        [
            "month",
            "total_orders",
            "canceled_orders",
            "cancellation_rate",
        ]
    ].copy()

    return (
        alt.Chart(chart_data)
        .mark_line(
            point=True,
            strokeWidth=2,
        )
        .encode(
            x=alt.X(
                "month:T",
                title="Month",
                axis=alt.Axis(
                    format="%Y-%m",
                    labelAngle=-45,
                ),
            ),
            y=alt.Y(
                "cancellation_rate:Q",
                title="Cancellation rate",
                scale=alt.Scale(
                    domain=[0, 1],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "month:T",
                    title="Month",
                    format="%Y-%m",
                ),
                alt.Tooltip(
                    "cancellation_rate:Q",
                    title="Cancellation rate",
                    format=".2%",
                ),
                alt.Tooltip(
                    "canceled_orders:Q",
                    title="Canceled orders",
                    format=",.0f",
                ),
                alt.Tooltip(
                    "total_orders:Q",
                    title="All orders",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            title="Monthly Cancellation Rate",
            height=390,
        )
        .interactive(
            bind_y=False,
        )
    )


def render_stage1_delivery_review_trends(
    trends: pd.DataFrame,
) -> None:
    """Render monthly M13-M16 delivery and review trends."""
    tabs = st.tabs(
        [
            "M13 · Delivery Time",
            "M14 · Late Rate",
            "M15 · Review Score",
            "M16 · Positive Rate",
        ]
    )

    chart_specs = [
        (
            "average_delivery_days",
            "Monthly Average Delivery Time",
            "Average delivery time (days)",
            ",.2f",
        ),
        (
            "late_delivery_rate",
            "Monthly Late Delivery Rate",
            "Late delivery rate",
            ".1%",
        ),
        (
            "average_review_score",
            "Monthly Average Review Score",
            "Average review score",
            ",.2f",
        ),
        (
            "positive_review_rate",
            "Monthly Positive Review Rate",
            "Positive review rate",
            ".1%",
        ),
    ]

    for tab, spec in zip(
        tabs,
        chart_specs,
    ):
        with tab:
            metric, title, y_title, tooltip_format = spec

            st.altair_chart(
                create_trend_chart(
                    trends,
                    metric=metric,
                    title=title,
                    y_title=y_title,
                    tooltip_format=tooltip_format,
                ),
                use_container_width=True,
            )


def filter_stage1_category_data(
    category_data: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Apply the Stage 1 purchase-date window to M18 item-grain data."""
    return category_data.loc[
        category_data[
            "purchase_date"
        ].between(
            start_date,
            end_date,
        )
    ].copy()


def build_stage1_category_share(
    category_data: pd.DataFrame,
) -> pd.DataFrame:
    """Build M18 category sales amount and share from cleaned item prices."""
    if category_data.empty:
        return pd.DataFrame(
            columns=[
                "product_category",
                "category_sales_amount",
                "category_sales_share",
            ]
        )

    summary = (
        category_data.groupby(
            "product_category",
            as_index=False,
            dropna=False,
        )["price"]
        .sum()
        .rename(
            columns={
                "price": "category_sales_amount",
            }
        )
    )

    total_sales = float(
        summary[
            "category_sales_amount"
        ].sum()
    )

    summary[
        "category_sales_share"
    ] = (
        summary[
            "category_sales_amount"
        ]
        / total_sales
        if total_sales > 0
        else pd.NA
    )

    return summary.sort_values(
        [
            "category_sales_amount",
            "product_category",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)


def create_stage1_category_share_chart(
    category_share: pd.DataFrame,
) -> alt.Chart:
    """Create the M18 ranked category-sales-share chart."""
    chart_data = category_share.copy()

    chart_data["category_sales_pct"] = (
        chart_data[
            "category_sales_share"
        ] * 100
    )

    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            y=alt.Y(
                "product_category:N",
                title="Product category",
                sort="-x",
            ),
            x=alt.X(
                "category_sales_pct:Q",
                title="Category sales share (%)",
            ),
            tooltip=[
                alt.Tooltip(
                    "product_category:N",
                    title="Product category",
                ),
                alt.Tooltip(
                    "category_sales_amount:Q",
                    title="Product sales (BRL)",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "category_sales_pct:Q",
                    title="Sales share (%)",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            title="M18 · Category Sales Share",
            height=430,
        )
    )


def render_stage1_dashboard() -> None:
    """Render the complete Stage 1 core-metrics workbook M01-M18."""
    st.header("Stage 1 · Core Metrics")

    st.write(
        "Interactive view of the formal Stage 1 18-metric system. "
        "Each metric preserves its own denominator, grain, and business scope."
    )

    try:
        data = load_stage1_order_data(
            str(STAGE1_ORDER_DATA_PATH)
        )
        cohort_data = load_stage1_cohort_data(
            str(STAGE1_COHORT_DATA_PATH)
        )
        category_data = load_stage1_category_data(
            str(STAGE1_CATEGORY_DATA_PATH)
        )
    except (
        FileNotFoundError,
        ValueError,
        pd.errors.ParserError,
    ) as error:
        st.error(str(error))
        st.stop()

    filters = render_stage1_filters(
        data
    )

    if (
        filters["start_date"]
        > filters["end_date"]
    ):
        st.error(
            "The start date cannot be later than the end date."
        )
        st.stop()

    filtered = apply_stage1_date_filter(
        data,
        filters,
    )

    render_stage1_filter_summary(
        filtered,
        filters,
    )

    if filtered.empty:
        st.warning(
            "No orders match the selected Stage 1 date range."
        )
        st.stop()

    metrics_m01_m08 = calculate_stage1_m01_m08(
        filtered,
        data,
        filters["start_date"],
        filters["end_date"],
    )

    metrics_m10_m17 = calculate_stage1_m10_m17(
        filtered
    )

    trends_m01_m08 = build_stage1_m01_m08_monthly_trends(
        filtered,
        data,
        filters["start_date"],
        filters["end_date"],
    )

    trends_m13_m17 = build_stage1_m13_m17_monthly_trends(
        filtered,
        data,
        filters["start_date"],
        filters["end_date"],
    )

    selected_cohort = filter_stage1_cohort_months(
        cohort_data,
        filters["start_date"],
        filters["end_date"],
    )

    selected_category_data = filter_stage1_category_data(
        category_data,
        filters["start_date"],
        filters["end_date"],
    )

    category_share = build_stage1_category_share(
        selected_category_data
    )

    worksheet_tabs = st.tabs(
        [
            "Overview",
            "Revenue & Orders",
            "Customers & Retention",
            "Delivery & Reviews",
            "Operations & Categories",
        ]
    )

    with worksheet_tabs[0]:
        st.subheader("Stage 1 Metric Overview")

        st.caption(
            "The cards preserve metric-specific formal cohorts. Valid orders "
            "include all delivered orders; GMV/AOV/Paid Orders use positive-"
            "payment delivered orders; cancellation uses all order statuses."
        )

        render_stage1_m01_m08_cards(
            metrics_m01_m08
        )

        st.divider()

        render_stage1_m10_m17_cards(
            metrics_m10_m17
        )

        st.info(
            "M09 Customer Retention and M18 Category Sales Share are "
            "distributional metrics rather than single scalar KPIs. "
            "Use their dedicated workbook tabs for the full interactive views."
        )

        overview_support = st.columns(2)

        overview_support[0].metric(
            "M09 · Cohort Start Months Shown",
            format_integer(
                int(
                    selected_cohort[
                        "cohort_month"
                    ].nunique()
                )
            ),
        )

        overview_support[1].metric(
            "M18 · Categories Shown",
            format_integer(
                int(
                    category_share[
                        "product_category"
                    ].nunique()
                )
            ),
        )

        st.caption(
            "M06 New Customers uses each customer's first delivered purchase "
            "from the complete observed history before the date filter. "
            "M07-M08 and M10-M12 are recalculated inside the selected "
            "analysis window."
        )

    with worksheet_tabs[1]:
        st.subheader(
            "Revenue & Orders · M01-M04"
        )

        st.caption(
            "Calendar months with no delivered source orders remain gaps "
            "(NULL), rather than being silently converted to zero."
        )

        render_stage1_partial_month_note(
            filters["start_date"],
            filters["end_date"],
        )

        render_stage1_revenue_order_trends(
            trends_m01_m08
        )

    with worksheet_tabs[2]:
        st.subheader(
            "Customers & Retention · M05-M12"
        )

        customer_tabs = st.tabs(
            [
                "M05-M08 · Customer Trends",
                "M09 · Retention",
                "M10 · LTV",
                "M11 · Frequency",
                "M12 · Repurchase Interval",
            ]
        )

        with customer_tabs[0]:
            st.caption(
                "Active and repeat customers use customer_unique_id. "
                "Monthly repeat customers have at least two distinct delivered "
                "orders within that calendar month."
            )

            render_stage1_partial_month_note(
                filters["start_date"],
                filters["end_date"],
            )

            render_stage1_customer_trends(
                trends_m01_m08
            )

        with customer_tabs[1]:
            st.caption(
                "The date selector filters cohort start months only. "
                "Already observed activity after each selected cohort's first "
                "month remains in the retention calculation, so the dashboard "
                "does not manufacture right-censored zeros."
            )

            if selected_cohort.empty:
                st.info(
                    "No Stage 1 cohort starts fall inside the selected date range."
                )
            else:
                st.altair_chart(
                    create_stage1_retention_heatmap(
                        selected_cohort
                    ),
                    use_container_width=True,
                )

                st.caption(
                    f"Cohort starts shown: "
                    f"{selected_cohort['cohort_month'].nunique():,} · "
                    f"Retention cells shown: {len(selected_cohort):,}"
                )

        with customer_tabs[2]:
            ltv = metrics_m10_m17[
                "customer_lifetime_value"
            ]

            ltv_columns = st.columns(2)

            ltv_columns[0].metric(
                "M10 · Observed Revenue LTV",
                (
                    format_currency(
                        float(ltv)
                    )
                    if ltv is not None
                    else "—"
                ),
            )

            ltv_columns[1].metric(
                "Paying Customers",
                format_integer(
                    int(
                        metrics_m10_m17[
                            "paying_customer_count"
                        ]
                    )
                ),
            )

            customer_revenue = build_stage1_customer_revenue(
                filtered
            )

            if not customer_revenue.empty:
                st.altair_chart(
                    create_stage1_ltv_distribution(
                        customer_revenue
                    ),
                    use_container_width=True,
                )

            st.caption(
                "M10 is observed-period revenue LTV: positive delivered "
                "order-level payments are summed per customer, then averaged. "
                "It is not profit LTV and does not subtract costs or CAC."
            )

        with customer_tabs[3]:
            frequency = metrics_m10_m17[
                "average_purchase_frequency"
            ]

            st.metric(
                "M11 · Average Purchase Frequency",
                (
                    f"{float(frequency):,.3f}"
                    if frequency is not None
                    else "—"
                ),
            )

            frequency_data = build_stage1_customer_frequency(
                filtered
            )

            if not frequency_data.empty:
                st.altair_chart(
                    create_stage1_frequency_chart(
                        frequency_data
                    ),
                    use_container_width=True,
                )

            st.caption(
                "M11 = distinct delivered orders / active "
                "customer_unique_id users inside the selected window."
            )

        with customer_tabs[4]:
            interval = metrics_m10_m17[
                "average_repurchase_interval_days"
            ]

            interval_columns = st.columns(2)

            interval_columns[0].metric(
                "M12 · Average Repurchase Interval",
                (
                    f"{float(interval):,.2f} days"
                    if interval is not None
                    else "—"
                ),
            )

            interval_columns[1].metric(
                "Valid Adjacent Intervals",
                format_integer(
                    int(
                        metrics_m10_m17[
                            "valid_interval_count"
                        ]
                    )
                ),
            )

            intervals = build_stage1_repurchase_intervals(
                filtered
            )

            if intervals.empty:
                st.info(
                    "The selected window contains no legal adjacent "
                    "delivered-order intervals."
                )
            else:
                st.altair_chart(
                    create_stage1_interval_chart(
                        intervals
                    ),
                    use_container_width=True,
                )

            st.caption(
                "M12 gives every legal adjacent delivered-order interval "
                "equal weight. It is not an equal-weight average of each "
                "customer's personal mean."
            )

    with worksheet_tabs[3]:
        st.subheader(
            "Delivery & Reviews · M13-M16"
        )

        delivery_review_columns = st.columns(4)

        delivery = metrics_m10_m17[
            "average_delivery_days"
        ]
        delivery_review_columns[0].metric(
            "M13 · Avg Delivery Time",
            (
                f"{float(delivery):,.2f} days"
                if delivery is not None
                else "—"
            ),
        )

        late_rate = metrics_m10_m17[
            "late_delivery_rate"
        ]
        delivery_review_columns[1].metric(
            "M14 · Late Delivery Rate",
            (
                format_percentage(
                    float(late_rate)
                )
                if late_rate is not None
                else "—"
            ),
        )

        review_score = metrics_m10_m17[
            "average_review_score"
        ]
        delivery_review_columns[2].metric(
            "M15 · Avg Review Score",
            (
                f"{float(review_score):,.2f} / 5"
                if review_score is not None
                else "—"
            ),
        )

        positive_rate = metrics_m10_m17[
            "positive_review_rate"
        ]
        delivery_review_columns[3].metric(
            "M16 · Positive Review Rate",
            (
                format_percentage(
                    float(positive_rate)
                )
                if positive_rate is not None
                else "—"
            ),
        )

        st.caption(
            "M13 uses purchase-to-customer-delivery days. M14 uses only "
            "evaluable delivered orders. M15-M16 use one deterministic "
            "representative valid review per delivered order."
        )

        render_stage1_partial_month_note(
            filters["start_date"],
            filters["end_date"],
        )

        render_stage1_delivery_review_trends(
            trends_m13_m17
        )

    with worksheet_tabs[4]:
        st.subheader(
            "Operations & Categories · M17-M18"
        )

        cancellation_rate = metrics_m10_m17[
            "cancellation_rate"
        ]

        cancellation_columns = st.columns(3)

        cancellation_columns[0].metric(
            "M17 · Cancellation Rate",
            (
                format_percentage(
                    float(cancellation_rate)
                )
                if cancellation_rate is not None
                else "—"
            ),
        )

        cancellation_columns[1].metric(
            "Canceled Orders",
            format_integer(
                int(
                    metrics_m10_m17[
                        "canceled_order_count"
                    ]
                )
            ),
        )

        cancellation_columns[2].metric(
            "All Orders",
            format_integer(
                int(
                    metrics_m10_m17[
                        "total_order_count"
                    ]
                )
            ),
        )

        st.altair_chart(
            create_stage1_cancellation_chart(
                trends_m13_m17
            ),
            use_container_width=True,
        )

        st.caption(
            "M17 is the exception to the delivered-order default: "
            "the numerator is canceled orders and the denominator is "
            "all order statuses in the selected purchase-date window. "
            "Boundary or low-volume months can produce extreme percentages; "
            "hover over each point to inspect canceled and total order counts "
            "before comparing it with a complete operating month."
        )

        st.divider()

        if category_share.empty:
            st.info(
                "No delivered category-item sales fall inside the selected "
                "date range."
            )
        else:
            category_total_sales = float(
                category_share[
                    "category_sales_amount"
                ].sum()
            )

            category_columns = st.columns(2)

            category_columns[0].metric(
                "M18 · Product Sales Total",
                format_currency(
                    category_total_sales
                ),
            )

            category_columns[1].metric(
                "Categories",
                format_integer(
                    int(
                        category_share[
                            "product_category"
                        ].nunique()
                    )
                ),
            )

            top_n_options: list[int | str] = [
                10,
                15,
                20,
                "All",
            ]

            selected_top_n = st.selectbox(
                "M18 categories shown",
                options=top_n_options,
                index=0,
                key="stage1_category_top_n",
            )

            chart_data = (
                category_share
                if selected_top_n == "All"
                else category_share.head(
                    int(selected_top_n)
                )
            )

            st.altair_chart(
                create_stage1_category_share_chart(
                    chart_data
                ),
                use_container_width=True,
            )

            st.caption(
                "M18 sales use SUM(order_items.price) for delivered orders, "
                "exclude freight, and are not GMV. Unknown categories remain "
                "in the full denominator even when only Top N bars are shown. "
                f"Selected-window category sales: "
                f"{format_currency(category_total_sales)}."
            )

    st.caption(
        "Stage 1 data sources: "
        "outputs/data/01_core_metrics/stage1_order_metric_base.csv · "
        "stage1_cohort_retention.csv · "
        "stage1_category_item_base.csv"
    )


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

def render_filter_summary(
    filtered: pd.DataFrame,
    filters: dict[str, object],
) -> None:
    """Show the active date range and filtered data volume."""
    start_date = filters["start_date"]
    end_date = filters["end_date"]

    st.caption(
        f"Selected period: {start_date} to {end_date} · "
        f"Payment-detail rows: {len(filtered):,} · "
        f"Paid delivered orders: "
        f"{filtered['order_id'].nunique():,}"
    )


def render_stage2_dashboard() -> None:
    """Render the existing Stage 2 business-analysis dashboard."""
    st.header("Stage 2 · Business Analysis")

    st.write(
        "Use the global filters to review paid delivered order KPIs "
        "and monthly trends."
    )

    try:
        data = load_dashboard_data(
            str(DATA_PATH)
        )
    except (
        FileNotFoundError,
        ValueError,
        pd.errors.ParserError,
    ) as error:
        st.error(str(error))
        st.stop()

    filters = render_filters(data)

    if (
        filters["start_date"]
        > filters["end_date"]
    ):
        st.error(
            "The start date cannot be later than the end date."
        )
        st.stop()

    filtered = apply_filters(
        data,
        filters,
    )

    render_filter_summary(
        filtered,
        filters,
    )

    if filtered.empty:
        st.warning(
            "No data matches the current filters. "
            "Adjust or reset the filters."
        )
        st.stop()

    kpis = calculate_kpis(filtered)

    render_kpi_cards(kpis)

    st.divider()

    trends = build_monthly_trends(
        filtered,
        data,
        filters["start_date"],
        filters["end_date"],
    )

    render_monthly_trends(
        trends,
        filters["start_date"],
        filters["end_date"],
    )

    st.divider()

    category_filters_active = bool(
        filters["states"]
        or filters["payments"]
        or filters["bands"]
    )

    render_growth_quality(
        filters["start_date"],
        filters["end_date"],
        category_filters_active,
    )

    st.divider()

    render_holiday_analysis(
        filters["start_date"],
        filters["end_date"],
        category_filters_active,
    )

    st.divider()

    render_business_structure(
        filtered
    )

    st.divider()

    render_structural_signals(
        filtered
    )

    st.divider()

    st.info(
        "Payment-filter interpretation: selecting a payment method defines "
        "an order cohort containing paid delivered orders that used that "
        "method. GMV and AOV use each selected order's full positive "
        "order-level payment amount; payment-method structure can still split "
        "GMV by the actual amount paid with each method."
    )

    st.caption(
        "Data source: "
        "outputs/data/02_business_overview/"
        "dashboard_order_payment_detail.csv"
    )


def main() -> None:
    """Run the workbook-style Stage 1 / Stage 2 dashboard."""
    st.set_page_config(
        page_title="Brazil / Olist E-commerce Analytics",
        page_icon="📊",
        layout="wide",
    )

    st.title(
        "Brazil / Olist E-commerce Analytics"
    )

    worksheet = st.radio(
        "Worksheet",
        options=[
            "Stage 1 · Core Metrics",
            "Stage 2 · Business Analysis",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="dashboard_worksheet",
    )

    st.caption(
        "Workbook view: Stage 1 contains the formal core-metric system; "
        "Stage 2 contains the existing business-analysis dashboard."
    )

    st.divider()

    if worksheet == "Stage 1 · Core Metrics":
        render_stage1_dashboard()
    else:
        render_stage2_dashboard()


if __name__ == "__main__":
    main()
