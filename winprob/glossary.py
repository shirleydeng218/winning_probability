"""Sidebar glossary and in-page section navigation."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

GlossaryTerm = Dict[str, str]
NavSection = Dict[str, str]


def slugify(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[\s_]+", "-", normalized).strip("-")


def section_anchor(
    anchor: str,
    title: str,
    *,
    level: str = "subheader",
    caption: Optional[str] = None,
    glossary_term: Optional[str] = None,
) -> str:
    """Render a stable anchor target plus a Streamlit heading."""
    from winprob.ui_styles import render_section_header

    render_section_header(
        title,
        caption=caption,
        anchor=anchor,
        level=level,
        glossary_term=glossary_term,
    )
    return anchor


def _normalize_term_key(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


# Display labels and column headers mapped to canonical glossary keys.
TERM_ALIASES: Dict[str, str] = {
    "significance": "Significance / Confidence",
    "confidence": "Confidence",
    "cpis": "CPiS",
    "incremental conversions": "Incremental conversions",
    "absolute cvr lift": "Absolute CVR lift",
    "relative cvr lift": "Relative CVR lift",
    "winning probability": "Winning Probability",
    "simulations": "Simulations",
    "conversion metrics": "Conversion metrics",
    "conversion metrics to analyze": "Conversion metrics",
    "winning rule": "Winning rule",
    "n_control": "n_control / n_test",
    "n_test": "n_control / n_test",
    "test_conversions": "test_conversions / control_conversions",
    "control_conversions": "test_conversions / control_conversions",
    "absolute_lift": "Absolute_lift",
    "event_type": "event_type",
}


@lru_cache(maxsize=1)
def get_term_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for terms in GLOSSARY.values():
        for entry in terms:
            lookup[_normalize_term_key(entry["term"])] = entry["definition"]
    for alias, target in TERM_ALIASES.items():
        target_key = _normalize_term_key(target)
        if target_key in lookup:
            lookup[_normalize_term_key(alias)] = lookup[target_key]
    return lookup


def lookup_term_definition(term: str) -> Optional[str]:
    if not term:
        return None
    lookup = get_term_lookup()
    return lookup.get(_normalize_term_key(term))


def render_main_glossary_cards(context: str) -> None:
    """Render glossary terms on the main page with hover definitions."""
    from winprob.ui_styles import _safe_html, term_tip_icon_html

    terms = GLOSSARY.get(context, [])
    if not terms:
        return

    cards = []
    for entry in terms:
        term = _safe_html(entry["term"])
        cards.append(
            f'<div class="winprob-glossary-card">'
            f'<code class="winprob-glossary-card-term">{term}</code>'
            f"{term_tip_icon_html(entry['definition'])}"
            f"</div>"
        )
    st.markdown(
        f'<div class="winprob-glossary-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def render_glossary_dataframe(df: pd.DataFrame, **kwargs: Any) -> None:
    """Render a dataframe with glossary help tooltips on recognized column headers."""
    column_config = dict(kwargs.pop("column_config", {}) or {})
    for col in df.columns:
        if col in column_config:
            continue
        definition = lookup_term_definition(str(col))
        if definition:
            column_config[col] = st.column_config.Column(help=definition)
    st.dataframe(df, column_config=column_config or None, **kwargs)


GLOSSARY: Dict[str, List[GlossaryTerm]] = {
    "home": [
        {
            "term": "WinProb",
            "definition": "Bayesian media test evaluator that estimates winning probability across cells using CPiS, CVR lift, and significance.",
        },
        {
            "term": "Incrementality test",
            "definition": "Treatment vs. control design that measures incremental conversions and lift attributable to media.",
        },
        {
            "term": "Split test",
            "definition": "A/B/C-style test without a control holdout; cells are compared directly on conversion rate or reach.",
        },
    ],
    "upload": [
        {
            "term": "spend_usd",
            "definition": "Total media spend for the cell in USD. Required on every row.",
        },
        {
            "term": "n_control / n_test",
            "definition": "Audience sizes for control and treatment. Required for rate and lift calculations.",
        },
        {
            "term": "test_conversions / control_conversions",
            "definition": "Observed conversion counts in treatment and control. Required for posterior modeling.",
        },
        {
            "term": "Absolute_lift",
            "definition": "Incremental conversions attributed to treatment. Derived from conv rates × n_test when blank.",
        },
        {
            "term": "CPIS",
            "definition": "Cost per incremental sign-up (or conversion): spend_usd divided by Absolute_lift.",
        },
        {
            "term": "confidence_level",
            "definition": "Statistical significance for absolute lift. Null values become 0 (shown as no significance).",
        },
        {
            "term": "event_type",
            "definition": "Conversion metric label (e.g., subscription, trial). One row per cell per metric.",
        },
    ],
    "configure": [
        {
            "term": "Winning rule",
            "definition": "How the recommended winner is chosen: lowest CPiS, highest incremental conversions, or highest relative CVR lift.",
        },
        {
            "term": "Confidence",
            "definition": "Stakeholder read from significance: Confident (≥90%), Directional (>0% but <90%), or No significance (0%). Does not gate winning probability.",
        },
        {
            "term": "Simulations",
            "definition": "Monte Carlo draws from posterior distributions used to estimate winning probability and overlap.",
        },
        {
            "term": "Conversion metrics",
            "definition": "Subset of event_type values included in the analysis run.",
        },
    ],
    "results": [
        {
            "term": "Winning Probability",
            "definition": "Share of simulations where a cell wins under the selected winning rule.",
        },
        {
            "term": "CPiS",
            "definition": "Cost per incremental conversion for a cell. Lower is more efficient when lift is positive.",
        },
        {
            "term": "Absolute CVR lift",
            "definition": "Treatment conversion rate minus control conversion rate (percentage-point change).",
        },
        {
            "term": "Relative CVR lift",
            "definition": "Percent change in conversion rate relative to control: (test − control) / control.",
        },
        {
            "term": "Incremental conversions",
            "definition": "Estimated additional conversions from treatment vs. control at test scale.",
        },
        {
            "term": "Significance / Confidence",
            "definition": "Significance is the statistical confidence level; Confidence is the plain-language read (Confident, Directional, or No significance).",
        },
    ],
    "split_test": [
        {
            "term": "ROPE",
            "definition": "Region of practical equivalence: cells within a small CVR margin are treated as ties.",
        },
        {
            "term": "Winning Probability",
            "definition": "Share of simulations where a cell wins after ROPE-aware tie-breaking.",
        },
        {
            "term": "Compare on",
            "definition": "Metric used to rank cells: conversion rate, conversions, reach, or impressions.",
        },
    ],
}

UPLOAD_NAV: List[NavSection] = [
    {"label": "Upload & validate", "anchor": "upload-validate"},
    {"label": "Input validation", "anchor": "input-validation"},
    {"label": "Column reference", "anchor": "column-reference"},
]

CONFIGURE_NAV: List[NavSection] = [
    {"label": "Configure analysis", "anchor": "configure-analysis"},
    {"label": "Test overview", "anchor": "test-overview"},
]

RESULTS_FULL_ANALYSIS_NAV: List[NavSection] = [
    {"label": "Full results table", "anchor": "winning-probability-summary"},
    {"label": "AI summary", "anchor": "ai-summary"},
    {"label": "Export readout", "anchor": "export-readout-pack"},
]

METRIC_SECTIONS: List[NavSection] = [
    {"label": "Executive summary", "anchor_suffix": "executive-summary"},
    {"label": "Per-cell metrics", "anchor_suffix": "per-cell-metrics"},
    {"label": "Rankings", "anchor_suffix": "multi-metric-rankings"},
    {"label": "Cell comparison", "anchor_suffix": "cell-comparison"},
    {"label": "Distribution & uncertainty", "anchor_suffix": "distribution-uncertainty"},
    {"label": "Advanced analysis", "anchor_suffix": "advanced-analysis"},
]

METRIC_ADVANCED_SUBSECTIONS: List[NavSection] = [
    {"label": "Pairwise win matrix", "anchor_suffix": "pairwise-win-matrix"},
    {"label": "Posterior overlap", "anchor_suffix": "posterior-overlap"},
    {"label": "Budget optimizer", "anchor_suffix": "budget-optimizer"},
]


def metric_anchor(metric: str, section_suffix: str) -> str:
    return f"{slugify(metric)}-{section_suffix}"


def _truncate_nav_label(text: str, max_len: int = 40) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1].rstrip()}…"


def _render_nav_links(
    sections: List[NavSection],
    *,
    sub: bool = False,
    nested: bool = False,
) -> str:
    from winprob.ui_styles import _safe_html

    if nested:
        css_class = "winprob-nav-link winprob-nav-sublink winprob-nav-nested-sublink"
    elif sub:
        css_class = "winprob-nav-link winprob-nav-sublink"
    else:
        css_class = "winprob-nav-link"

    links = []
    for section in sections:
        label = _safe_html(section["label"])
        anchor = _safe_html(section["anchor"])
        links.append(f'<a class="{css_class}" href="#{anchor}">{label}</a>')
    return "\n".join(links)


def _render_nav_group(label: str, sections: List[NavSection], *, sub: bool = False) -> None:
    from winprob.ui_styles import _safe_html

    if not sections:
        return
    body = _render_nav_links(sections, sub=sub)
    st.markdown(
        f'<div class="winprob-nav-group">'
        f'<div class="winprob-nav-group-label">{_safe_html(label)}</div>'
        f"{body}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_metric_nav_links(*, selected_metric: str) -> None:
    """Render flat metric-scoped section links with advanced sub-items."""
    metric_sections = [{
        "label": section["label"],
        "anchor": metric_anchor(selected_metric, section["anchor_suffix"]),
    } for section in METRIC_SECTIONS]

    _render_nav_group(
        f"Selected metric · {_truncate_nav_label(selected_metric)}",
        metric_sections,
        sub=True,
    )

    advanced_sections = [{
        "label": section["label"],
        "anchor": metric_anchor(selected_metric, section["anchor_suffix"]),
    } for section in METRIC_ADVANCED_SUBSECTIONS]
    if advanced_sections:
        st.markdown(
            f'<div class="winprob-nav-group">{_render_nav_links(advanced_sections, sub=True, nested=True)}</div>',
            unsafe_allow_html=True,
        )


def render_sidebar_nav(
    *,
    nav_sections: Optional[List[NavSection]] = None,
    metrics: Optional[List[str]] = None,
    selected_metric: Optional[str] = None,
    full_analysis_nav: Optional[List[NavSection]] = None,
) -> None:
    """Render compact jump links in the sidebar."""
    with st.sidebar:
        has_metric_nav = bool(metrics and selected_metric)
        has_full_analysis_nav = bool(full_analysis_nav)
        has_page_nav = bool(nav_sections) and not has_metric_nav
        if not (has_metric_nav or has_full_analysis_nav or has_page_nav):
            return

        st.markdown("---")
        st.subheader("On this page")

        if has_metric_nav:
            _render_metric_nav_links(selected_metric=selected_metric)

        if full_analysis_nav:
            _render_nav_group("Full Test Summary · all metrics", full_analysis_nav)

        elif nav_sections and not has_metric_nav:
            _render_nav_group("Sections", nav_sections)


def inject_navigation_styles() -> None:
    """Apply global WinProb styles (includes navigation link styling)."""
    from winprob.ui_styles import inject_app_styles, inject_glossary_tooltip_styles

    inject_app_styles()
    inject_glossary_tooltip_styles()
