"""Sample datasets for demo mode."""

import pandas as pd

SAMPLE_INCREMENTALITY_ROWS = [
    {
        "cell_name": "Cell 1 - CLAL 15%",
        "event_type": "usergen:SVOD_Bundle: hulu_disney_ads_2p_bundle",
        "spend_usd": 374274.36,
        "n_control": 6218481,
        "n_test": 15299015,
        "test_conversions": 7073,
        "control_conversions": 1846,
        "relative_lift": 0.55737,
        "Absolute_lift": 2531,
        "CPIS": 147.85,
        "confidence_level": 0.05,
    },
    {
        "cell_name": "Cell 2 - CLAL 100%",
        "event_type": "usergen:SVOD_Bundle: hulu_disney_ads_2p_bundle",
        "spend_usd": 374245.14,
        "n_control": 10429924,
        "n_test": 24285376,
        "test_conversions": 8948,
        "control_conversions": 2241,
        "relative_lift": 0.71483,
        "Absolute_lift": 3730,
        "CPIS": 100.33,
        "confidence_level": 0.47,
    },
    {
        "cell_name": "Cell 3 - Target Everyone",
        "event_type": "usergen:SVOD_Bundle: hulu_disney_ads_2p_bundle",
        "spend_usd": 374324.11,
        "n_control": 15028309,
        "n_test": 33736778,
        "test_conversions": 10763,
        "control_conversions": 2766,
        "relative_lift": 0.73336,
        "Absolute_lift": 4554,
        "CPIS": 82.20,
        "confidence_level": 0.10,
    },
]

INPUT_TEMPLATE_COLUMNS = [
    "cell_name",
    "event_type",
    "spend_usd",
    "n_control",
    "n_test",
    "test_conversions",
    "control_conversions",
    "relative_lift",
    "Absolute_lift",
    "CPIS",
    "confidence_level",
]


SAMPLE_SPLIT_ROWS = [
    {
        "cell_name": "Cell A — Broad",
        "event_type": "subscription",
        "spend_usd": 420_000,
        "n_test": 8_500_000,
        "test_conversions": 18_700,
        "impressions": 42_000_000,
        "CPS": 22.46,
        "test_conv_rate": 0.0022,
    },
    {
        "cell_name": "Cell B — Targeted",
        "event_type": "subscription",
        "spend_usd": 395_000,
        "n_test": 6_200_000,
        "test_conversions": 16_120,
        "impressions": 31_500_000,
        "CPS": 24.50,
        "test_conv_rate": 0.0026,
    },
    {
        "cell_name": "Cell C — High Intent",
        "event_type": "subscription",
        "spend_usd": 410_000,
        "n_test": 4_800_000,
        "test_conversions": 14_880,
        "impressions": 22_000_000,
        "CPS": 27.55,
        "test_conv_rate": 0.0031,
    },
]

SPLIT_INPUT_TEMPLATE_COLUMNS = [
    "cell_name",
    "event_type",
    "spend_usd",
    "n_test",
    "test_conversions",
    "impressions",
    "CPS",
    "test_conv_rate",
]


def get_sample_incrementality_df() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_INCREMENTALITY_ROWS)


def get_sample_split_df() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_SPLIT_ROWS)


def get_input_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=INPUT_TEMPLATE_COLUMNS)


def get_split_input_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=SPLIT_INPUT_TEMPLATE_COLUMNS)
