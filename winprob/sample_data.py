"""Sample datasets for demo mode."""

import pandas as pd

# Hypothetical Meta paid-media incrementality test: three creative cells x two metrics.
# Frequentist incremental CIs overlap (no clear winner); WinProb resolves via simulation.
_META_TEST_NAME = "Meta Paid Media Creative Test"
_N_CONTROL = 19_490_250
_CTRL_CONV_DUO = 25_614
_CTRL_CONV_TOTAL = 65_738

SAMPLE_INCREMENTALITY_ROWS = [
    {
        "cell_name": "Text Only",
        "event_type": "Duo Bundle Signups",
        "spend_usd": 387_412,
        "n_control": _N_CONTROL,
        "n_test": 19_370_600,
        "test_conversions": 33_735,
        "control_conversions": _CTRL_CONV_DUO,
        "relative_lift": 0.32519,
        "Absolute_lift": 8_278,
        "absolute_lift_CI_min": 6_800,
        "absolute_lift_CI_max": 9_680,
        "CPIS": 46.80,
        "confidence_level": 0.42,
    },
    {
        "cell_name": "Single Title + Text",
        "event_type": "Duo Bundle Signups",
        "spend_usd": 392_847,
        "n_control": _N_CONTROL,
        "n_test": 19_642_350,
        "test_conversions": 35_349,
        "control_conversions": _CTRL_CONV_DUO,
        "relative_lift": 0.36938,
        "Absolute_lift": 9_535,
        "absolute_lift_CI_min": 7_400,
        "absolute_lift_CI_max": 15_800,
        "CPIS": 41.20,
        "confidence_level": 0.52,
    },
    {
        "cell_name": "Multi Title + Text",
        "event_type": "Duo Bundle Signups",
        "spend_usd": 389_156,
        "n_control": _N_CONTROL,
        "n_test": 19_457_800,
        "test_conversions": 34_316,
        "control_conversions": _CTRL_CONV_DUO,
        "relative_lift": 0.34197,
        "Absolute_lift": 8_745,
        "absolute_lift_CI_min": 8_100,
        "absolute_lift_CI_max": 11_400,
        "CPIS": 44.50,
        "confidence_level": 0.31,
    },
    {
        "cell_name": "Text Only",
        "event_type": "Total Signups",
        "spend_usd": 387_412,
        "n_control": _N_CONTROL,
        "n_test": 19_370_600,
        "test_conversions": 77_912,
        "control_conversions": _CTRL_CONV_TOTAL,
        "relative_lift": 0.19251,
        "Absolute_lift": 12_578,
        "absolute_lift_CI_min": 10_500,
        "absolute_lift_CI_max": 14_600,
        "CPIS": 30.80,
        "confidence_level": 0.38,
    },
    {
        "cell_name": "Single Title + Text",
        "event_type": "Total Signups",
        "spend_usd": 392_847,
        "n_control": _N_CONTROL,
        "n_test": 19_642_350,
        "test_conversions": 81_132,
        "control_conversions": _CTRL_CONV_TOTAL,
        "relative_lift": 0.22462,
        "Absolute_lift": 14_881,
        "absolute_lift_CI_min": 11_400,
        "absolute_lift_CI_max": 24_200,
        "CPIS": 26.40,
        "confidence_level": 0.48,
    },
    {
        "cell_name": "Multi Title + Text",
        "event_type": "Total Signups",
        "spend_usd": 389_156,
        "n_control": _N_CONTROL,
        "n_test": 19_457_800,
        "test_conversions": 79_236,
        "control_conversions": _CTRL_CONV_TOTAL,
        "relative_lift": 0.20734,
        "Absolute_lift": 13_607,
        "absolute_lift_CI_min": 13_200,
        "absolute_lift_CI_max": 15_800,
        "CPIS": 28.60,
        "confidence_level": 0.29,
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
    "absolute_lift_CI_min",
    "absolute_lift_CI_max",
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


def get_sample_incrementality_test_name() -> str:
    return _META_TEST_NAME


def get_sample_split_df() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_SPLIT_ROWS)


def get_input_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=INPUT_TEMPLATE_COLUMNS)


def get_split_input_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=SPLIT_INPUT_TEMPLATE_COLUMNS)
