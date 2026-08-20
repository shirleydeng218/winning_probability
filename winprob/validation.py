"""Input validation and cleaning for uploaded test files."""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

REQUIRED_INCREMENTALITY_COLUMNS = [
    "cell_name",
    "event_type",
    "spend_usd",
    "n_control",
    "n_test",
    "test_conversions",
    "control_conversions",
    "Absolute_lift",
    "CPIS",
    "confidence_level",
]

# Must be present and non-null for every row — simulation cannot run without these.
CORE_NUMERIC_COLUMNS = [
    "spend_usd",
    "n_control",
    "n_test",
    "test_conversions",
    "control_conversions",
]

# May be null in upload; cleaned/filled before analysis when possible.
DERIVABLE_NUMERIC_COLUMNS = [
    "Absolute_lift",
    "CPIS",
    "confidence_level",
]

OPTIONAL_NUMERIC_COLUMNS = [
    "relative_lift",
    "test_conv_rate",
    "control_conv_rate",
    "absolute_lift_CI",
    "absolute_lift_CI_max",
    "absolute_lift_CI_min",
]


def _null_row_labels(df: pd.DataFrame, col: str) -> str:
    mask = pd.to_numeric(df[col], errors="coerce").isna()
    if not mask.any():
        return ""
    rows = df.index[mask].tolist()
    labels = []
    for idx in rows[:5]:
        cell = df.loc[idx, "cell_name"] if "cell_name" in df.columns else f"row {idx + 2}"
        labels.append(str(cell))
    suffix = f" (+{len(rows) - 5} more)" if len(rows) > 5 else ""
    return ", ".join(labels) + suffix


def clean_incrementality_input(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    """
    Coerce numerics and fill derivable nulls.

    Policy:
    - Core metrics (spend, counts): must be provided; not auto-filled.
    - Absolute_lift: derive from conversion rates if missing.
    - CPIS: derive as spend / Absolute_lift when missing.
    - confidence_level: null → 0 (cell treated as not significant / ineligible).
    - Optional columns: left as-is.
    """
    cleaned = df.copy()
    actions: List[Dict[str, str]] = []

    for col in CORE_NUMERIC_COLUMNS + DERIVABLE_NUMERIC_COLUMNS + OPTIONAL_NUMERIC_COLUMNS:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    # Derive Absolute_lift from rates when missing
    if "Absolute_lift" in cleaned.columns:
        missing_lift = cleaned["Absolute_lift"].isna()
        if missing_lift.any() and {"test_conv_rate", "control_conv_rate", "n_test"}.issubset(cleaned.columns):
            derived = (
                (cleaned["test_conv_rate"] - cleaned["control_conv_rate"]) * cleaned["n_test"]
            )
            fill_mask = missing_lift & derived.notna()
            if fill_mask.any():
                cleaned.loc[fill_mask, "Absolute_lift"] = derived.loc[fill_mask]
                actions.append({
                    "check": "Absolute_lift",
                    "status": "warn",
                    "detail": f"Filled {fill_mask.sum()} null value(s) from CVR rates × n_test",
                })

    # Derive CPIS from spend / lift when missing
    if "CPIS" in cleaned.columns and "Absolute_lift" in cleaned.columns and "spend_usd" in cleaned.columns:
        missing_cpis = cleaned["CPIS"].isna()
        valid_lift = cleaned["Absolute_lift"].notna() & (cleaned["Absolute_lift"] > 0)
        fill_mask = missing_cpis & valid_lift
        if fill_mask.any():
            cleaned.loc[fill_mask, "CPIS"] = (
                cleaned.loc[fill_mask, "spend_usd"] / cleaned.loc[fill_mask, "Absolute_lift"]
            )
            actions.append({
                "check": "CPIS",
                "status": "warn",
                "detail": f"Filled {fill_mask.sum()} null value(s) as spend_usd / Absolute_lift",
            })

    # Null significance → 0 (explicitly not eligible to win)
    if "confidence_level" in cleaned.columns:
        missing_conf = cleaned["confidence_level"].isna()
        if missing_conf.any():
            cleaned.loc[missing_conf, "confidence_level"] = 0.0
            actions.append({
                "check": "confidence_level",
                "status": "warn",
                "detail": (
                    f"Filled {missing_conf.sum()} null value(s) with 0 "
                    "(cell will be ineligible unless threshold is lowered)"
                ),
            })

    return cleaned, actions


def validate_incrementality_input(df: pd.DataFrame) -> Dict[str, Any]:
    checks: List[Dict[str, str]] = []
    is_valid = True

    missing = [col for col in REQUIRED_INCREMENTALITY_COLUMNS if col not in df.columns]
    if missing:
        is_valid = False
        for col in missing:
            checks.append({"check": f"Column `{col}`", "status": "fail", "detail": "Missing required column"})
    else:
        for col in REQUIRED_INCREMENTALITY_COLUMNS:
            checks.append({"check": f"Column `{col}`", "status": "pass", "detail": "Present"})

    cleaned, clean_actions = clean_incrementality_input(df)
    checks.extend(clean_actions)

    if not missing:
        # Core columns must be non-null after coercion — cannot be derived
        for col in CORE_NUMERIC_COLUMNS:
            null_count = cleaned[col].isna().sum()
            if null_count:
                is_valid = False
                checks.append({
                    "check": f"Required numeric `{col}`",
                    "status": "fail",
                    "detail": f"{null_count} null value(s) in: {_null_row_labels(cleaned, col)}",
                })
            else:
                checks.append({
                    "check": f"Required numeric `{col}`",
                    "status": "pass",
                    "detail": "All rows populated",
                })

        # Derivables: fail only if still null after cleaning
        for col in DERIVABLE_NUMERIC_COLUMNS:
            if col not in cleaned.columns:
                continue
            null_count = cleaned[col].isna().sum()
            if null_count:
                is_valid = False
                checks.append({
                    "check": f"Derivable `{col}`",
                    "status": "fail",
                    "detail": (
                        f"{null_count} null value(s) could not be filled "
                        f"({ _null_row_labels(cleaned, col) }). "
                        f"Provide values or columns needed to derive them."
                    ),
                })
            elif not any(a["check"] == col for a in clean_actions):
                checks.append({
                    "check": f"Derivable `{col}`",
                    "status": "pass",
                    "detail": "All rows populated",
                })

        if "confidence_level" in cleaned.columns:
            conf = cleaned["confidence_level"]
            out_of_range = ((conf < 0) | (conf > 1)).sum()
            if out_of_range:
                is_valid = False
                checks.append({
                    "check": "Significance range",
                    "status": "fail",
                    "detail": f"{out_of_range} value(s) outside 0–1",
                })
            else:
                checks.append({
                    "check": "Significance range",
                    "status": "pass",
                    "detail": "All values between 0 and 1",
                })

        if {"test_conversions", "n_test"}.issubset(cleaned.columns):
            zero_conv = (cleaned["test_conversions"] <= 0).sum()
            if zero_conv:
                checks.append({
                    "check": "Test conversions",
                    "status": "warn",
                    "detail": f"{zero_conv} cell(s) with zero test conversions",
                })

    preview = cleaned.head(10).copy() if not cleaned.empty else cleaned
    return {
        "is_valid": is_valid,
        "checks": checks,
        "preview": preview,
        "row_count": len(cleaned),
        "cleaned_df": cleaned,
    }
