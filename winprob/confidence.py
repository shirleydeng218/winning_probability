"""Confidence framing from statistical significance (not a user-facing threshold)."""

from __future__ import annotations

from typing import Any

import numpy as np

# Internal cutoff: Confident vs Directional read (not exposed as a sidebar control).
CONFIDENCE_THRESHOLD = 0.90

CONFIDENT = "Confident"
DIRECTIONAL = "Directional"
NO_SIGNIFICANCE = "No significance"


def confidence_read(conf_level: Any) -> str:
    """Map significance to a stakeholder confidence label."""
    try:
        value = float(conf_level)
    except (TypeError, ValueError):
        return NO_SIGNIFICANCE
    if not np.isfinite(value) or value <= 0:
        return NO_SIGNIFICANCE
    if value >= CONFIDENCE_THRESHOLD:
        return CONFIDENT
    return DIRECTIONAL


def confidence_callout_tone(read: str) -> str:
    if read == CONFIDENT:
        return "success"
    if read == DIRECTIONAL:
        return "warning"
    return "info"
