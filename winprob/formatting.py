"""Consistent metric labels and number formatting across the app."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

# Display labels (use these in UI copy and column headers)
LABEL_WINNING_PROBABILITY = "Winning Probability"
LABEL_SIGNIFICANCE = "Significance"
LABEL_ABSOLUTE_CVR_LIFT = "Absolute CVR Lift"
LABEL_RELATIVE_CVR_LIFT = "Relative CVR Lift"
LABEL_INCREMENTAL_CONVERSIONS = "Incremental Conversions"
LABEL_CPIS = "CPiS"
LABEL_CPS = "CPS"
LABEL_BUDGET = "Budget"
LABEL_TEST_CONVERSIONS = "Test Conversions"
LABEL_ELIGIBLE_TO_WIN = "Eligible to Win"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return not np.isfinite(float(value))
    except (TypeError, ValueError):
        return True


def fmt_winning_probability(value: Any, na: str = "N/A") -> str:
    """Winning Probability as percent with 1 decimal place."""
    if _is_missing(value):
        return na
    return f"{float(value) * 100:.1f}%"


def fmt_significance(value: Any, na: str = "N/A") -> str:
    """Significance as percent with 2 decimal places."""
    if _is_missing(value):
        return na
    return f"{float(value) * 100:.2f}%"


def fmt_cvr_lift(value: Any, na: str = "N/A") -> str:
    """Absolute CVR lift as percent with 4 decimal places."""
    if _is_missing(value):
        return na
    return f"{float(value) * 100:.4f}%"


def fmt_relative_cvr_lift(value: Any, na: str = "N/A") -> str:
    """Relative CVR lift as percent with 2 decimal places."""
    return fmt_significance(value, na=na)


def fmt_cpis(value: Any, na: str = "N/A") -> str:
    if _is_missing(value):
        return na
    return f"${float(value):,.2f}"


fmt_cps = fmt_cpis


def fmt_currency(value: Any, na: str = "N/A") -> str:
    """Budget / spend as whole dollars."""
    if _is_missing(value):
        return na
    return f"${float(value):,.0f}"


def fmt_count(value: Any, na: str = "N/A") -> str:
    """Conversions, population, reach as whole numbers."""
    if _is_missing(value):
        return na
    return f"{float(value):,.0f}"


def fmt_threshold(value: Any, na: str = "N/A") -> str:
    return fmt_significance(value, na=na)


def format_per_cell_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if LABEL_RELATIVE_CVR_LIFT in out.columns:
        out[LABEL_RELATIVE_CVR_LIFT] = out[LABEL_RELATIVE_CVR_LIFT].apply(fmt_relative_cvr_lift)
    if LABEL_ABSOLUTE_CVR_LIFT in out.columns:
        out[LABEL_ABSOLUTE_CVR_LIFT] = out[LABEL_ABSOLUTE_CVR_LIFT].apply(fmt_cvr_lift)
    if LABEL_BUDGET in out.columns:
        out[LABEL_BUDGET] = out[LABEL_BUDGET].apply(fmt_currency)
    if LABEL_TEST_CONVERSIONS in out.columns:
        out[LABEL_TEST_CONVERSIONS] = out[LABEL_TEST_CONVERSIONS].apply(fmt_count)
    if LABEL_INCREMENTAL_CONVERSIONS in out.columns:
        out[LABEL_INCREMENTAL_CONVERSIONS] = out[LABEL_INCREMENTAL_CONVERSIONS].apply(fmt_count)
    if LABEL_CPIS in out.columns:
        out[LABEL_CPIS] = out[LABEL_CPIS].apply(fmt_cpis)
    if LABEL_SIGNIFICANCE in out.columns:
        out[LABEL_SIGNIFICANCE] = out[LABEL_SIGNIFICANCE].apply(fmt_significance)
    if LABEL_ELIGIBLE_TO_WIN in out.columns:
        out[LABEL_ELIGIBLE_TO_WIN] = out[LABEL_ELIGIBLE_TO_WIN].map({True: "Yes", False: "No"})
    return out


def format_winning_probability_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if LABEL_WINNING_PROBABILITY in out.columns:
        out[LABEL_WINNING_PROBABILITY] = out[LABEL_WINNING_PROBABILITY].apply(fmt_winning_probability)
    if LABEL_RELATIVE_CVR_LIFT in out.columns:
        out[LABEL_RELATIVE_CVR_LIFT] = out[LABEL_RELATIVE_CVR_LIFT].apply(fmt_relative_cvr_lift)
    if LABEL_ABSOLUTE_CVR_LIFT in out.columns:
        out[LABEL_ABSOLUTE_CVR_LIFT] = out[LABEL_ABSOLUTE_CVR_LIFT].apply(fmt_cvr_lift)
    if LABEL_INCREMENTAL_CONVERSIONS in out.columns:
        out[LABEL_INCREMENTAL_CONVERSIONS] = out[LABEL_INCREMENTAL_CONVERSIONS].apply(fmt_count)
    if LABEL_CPIS in out.columns:
        out[LABEL_CPIS] = out[LABEL_CPIS].apply(fmt_cpis)
    if LABEL_SIGNIFICANCE in out.columns:
        out[LABEL_SIGNIFICANCE] = out[LABEL_SIGNIFICANCE].apply(fmt_significance)
    if LABEL_ELIGIBLE_TO_WIN in out.columns:
        out[LABEL_ELIGIBLE_TO_WIN] = out[LABEL_ELIGIBLE_TO_WIN].map({True: "Yes", False: "No"})
    return out


def format_stakeholder_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if LABEL_WINNING_PROBABILITY in out.columns:
        out[LABEL_WINNING_PROBABILITY] = out[LABEL_WINNING_PROBABILITY].apply(fmt_winning_probability)
    elif "Win Prob" in out.columns:
        out = out.rename(columns={"Win Prob": LABEL_WINNING_PROBABILITY})
        out[LABEL_WINNING_PROBABILITY] = out[LABEL_WINNING_PROBABILITY].apply(fmt_winning_probability)
    if LABEL_CPIS in out.columns:
        out[LABEL_CPIS] = out[LABEL_CPIS].apply(fmt_cpis)
    return out


def format_rankings_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in (
        LABEL_WINNING_PROBABILITY,
        LABEL_SIGNIFICANCE,
        LABEL_RELATIVE_CVR_LIFT,
    ):
        if col in out.columns:
            if col == LABEL_RELATIVE_CVR_LIFT:
                out[col] = out[col].apply(fmt_relative_cvr_lift)
            elif col == LABEL_SIGNIFICANCE:
                out[col] = out[col].apply(fmt_significance)
            elif col == LABEL_WINNING_PROBABILITY:
                out[col] = out[col].apply(fmt_winning_probability)
    if LABEL_CPIS in out.columns:
        out[LABEL_CPIS] = out[LABEL_CPIS].apply(fmt_cpis)
    if LABEL_INCREMENTAL_CONVERSIONS in out.columns:
        out[LABEL_INCREMENTAL_CONVERSIONS] = out[LABEL_INCREMENTAL_CONVERSIONS].apply(fmt_count)
    return out


def format_budget_optimizer(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    currency_cols = [
        "Current Spend",
        "Current CPiS",
    ]
    count_cols = [
        "Current Incremental Conversions",
        "Projected Incremental from Added Budget",
        "Projected Total Incremental Conversions",
    ]
    for col in currency_cols:
        if col in out.columns:
            out[col] = out[col].apply(
                fmt_cpis if col == "Current CPiS" else fmt_currency
            )
    for col in count_cols:
        if col in out.columns:
            out[col] = out[col].apply(fmt_count)
    return out


BUDGET_OPTIMIZER_PROJECTED_COLS = (
    "Projected Incremental from Added Budget",
    "Projected Total Incremental Conversions",
)


def style_budget_optimizer_table(df: pd.DataFrame):
    """Highlight projected columns so current vs. simulated values are easy to scan."""
    display = format_budget_optimizer(df)
    projected = set(BUDGET_OPTIMIZER_PROJECTED_COLS)

    def _highlight_projected_columns(col):
        if col.name in projected:
            return [
                "background-color: rgba(126, 217, 87, 0.22); font-weight: 600"
                for _ in col
            ]
        return [""] * len(col)

    styler = display.style.apply(_highlight_projected_columns, axis=0)
    styler.set_table_styles([
        {
            "selector": "thead th",
            "props": [
                ("background-color", "#12263A"),
                ("color", "#E6F2F0"),
            ],
        },
    ])
    return styler


def format_overlap_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prob_cols = [c for c in out.columns if c.startswith("p_a_beats_b")]
    for col in prob_cols:
        out[col] = out[col].apply(fmt_winning_probability)
    return out
