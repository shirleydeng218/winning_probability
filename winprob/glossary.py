"""Sidebar glossary and in-page section navigation."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import streamlit as st

GlossaryTerm = Dict[str, str]
NavSection = Dict[str, str]


def slugify(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[\s_]+", "-", normalized).strip("-")


def section_anchor(anchor: str, title: str, *, level: str = "subheader", caption: Optional[str] = None) -> str:
    """Render a stable anchor target plus a Streamlit heading."""
    from winprob.ui_styles import render_section_header

    render_section_header(title, caption=caption, anchor=anchor, level=level)
    return anchor


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
            "definition": "Statistical significance for absolute lift. Null values become 0 (ineligible to win).",
        },
        {
            "term": "event_type",
            "definition": "Conversion metric label (e.g., subscription, trial). One row per cell per metric.",
        },
    ],
    "configure": [
        {
            "term": "Winning rule",
            "definition": "How the recommended winner is chosen among eligible cells: lowest CPiS, highest incremental conversions, or highest CVR lift.",
        },
        {
            "term": "Minimum significance",
            "definition": "Cells below this confidence level are ineligible to win, even if they lead on efficiency or lift.",
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
            "definition": "Share of simulations where a cell wins under the selected rule among significance-eligible cells.",
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
            "term": "Significance / eligibility",
            "definition": "Whether a cell meets the minimum confidence threshold to be considered for winning.",
        },
        {
            "term": "Executive summary",
            "definition": "Stakeholder readout: recommendation, winner metrics, and a per-cell status table with one-line takeaways.",
        },
        {
            "term": "Multi-metric rankings",
            "definition": "Rank order of cells across Winning Probability, CPiS, lift, and Significance on normalized scores.",
        },
        {
            "term": "Cell comparison (radar)",
            "definition": "Normalized spider chart comparing cells across key performance dimensions.",
        },
        {
            "term": "Pairwise win matrix",
            "definition": "Heatmap of head-to-head winning probability between every pair of cells.",
        },
        {
            "term": "Posterior overlap",
            "definition": "How often two cells' simulated outcomes are statistically indistinguishable.",
        },
        {
            "term": "Sensitivity analysis",
            "definition": "How the recommended winner changes as the significance threshold varies.",
        },
        {
            "term": "Budget optimizer",
            "definition": "Projects incremental conversions if additional budget were allocated by CPiS efficiency.",
        },
        {
            "term": "Confidence intervals",
            "definition": "Uncertainty bands around absolute lift estimates by cell and metric.",
        },
        {
            "term": "Density plots",
            "definition": "Posterior distributions for CVR lift and incremental conversions from simulation.",
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
    {"label": "Upload & Validate", "anchor": "upload-validate"},
    {"label": "Input validation", "anchor": "input-validation"},
    {"label": "Column reference", "anchor": "column-reference"},
]

CONFIGURE_NAV: List[NavSection] = [
    {"label": "Configure analysis", "anchor": "configure-analysis"},
    {"label": "Test overview", "anchor": "test-overview"},
]

RESULTS_GLOBAL_NAV: List[NavSection] = [
    {"label": "Per-cell metrics", "anchor": "per-cell-performance-metrics"},
    {"label": "Winning probability summary", "anchor": "winning-probability-summary"},
    {"label": "Confidence intervals", "anchor": "confidence-intervals"},
    {"label": "Interactive density plots", "anchor": "interactive-density-plots"},
    {"label": "Static density plots", "anchor": "static-density-plots"},
    {"label": "Export readout pack", "anchor": "export-readout-pack"},
    {"label": "AI summary", "anchor": "ai-summary"},
]

METRIC_SECTIONS: List[NavSection] = [
    {"label": "Executive summary", "anchor_suffix": "executive-summary"},
    {"label": "Multi-metric rankings", "anchor_suffix": "multi-metric-rankings"},
    {"label": "Cell comparison", "anchor_suffix": "cell-comparison"},
    {"label": "Pairwise win matrix", "anchor_suffix": "pairwise-win-matrix"},
    {"label": "Posterior overlap", "anchor_suffix": "posterior-overlap"},
    {"label": "Sensitivity", "anchor_suffix": "sensitivity"},
    {"label": "Budget optimizer", "anchor_suffix": "budget-optimizer"},
]


def metric_anchor(metric: str, section_suffix: str) -> str:
    return f"{slugify(metric)}-{section_suffix}"


def _render_nav_links(sections: List[NavSection]) -> None:
    for section in sections:
        st.markdown(
            f'<a class="winprob-nav-link" href="#{section["anchor"]}">{section["label"]}</a>',
            unsafe_allow_html=True,
        )


def render_sidebar_glossary(
    *,
    context: str,
    nav_sections: Optional[List[NavSection]] = None,
    metrics: Optional[List[str]] = None,
) -> None:
    """Render searchable glossary and optional jump links in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.header("Glossary & Navigation")

        if nav_sections:
            st.markdown("**On this page**")
            _render_nav_links(nav_sections)
            st.markdown("")

        if metrics:
            st.markdown("**By conversion metric**")
            selected_metric = st.selectbox(
                "Metric sections",
                options=metrics,
                key=f"glossary_metric_nav_{context}",
                label_visibility="collapsed",
            )
            metric_links = [
                {
                    "label": section["label"],
                    "anchor": metric_anchor(selected_metric, section["anchor_suffix"]),
                }
                for section in METRIC_SECTIONS
            ]
            _render_nav_links(metric_links)
            st.markdown("")

        terms = GLOSSARY.get(context, [])
        if not terms:
            return

        query = st.text_input(
            "Search glossary",
            placeholder="Filter terms…",
            key=f"glossary_search_{context}",
        ).strip().lower()

        filtered = [
            term
            for term in terms
            if not query
            or query in term["term"].lower()
            or query in term["definition"].lower()
        ]

        if not filtered:
            st.caption("No glossary terms match your search.")
            return

        st.markdown(f"**Terms ({len(filtered)})**")
        for term in filtered:
            with st.expander(term["term"], expanded=bool(query)):
                st.caption(term["definition"])


def inject_navigation_styles() -> None:
    """Apply global WinProb styles (includes navigation link styling)."""
    from winprob.ui_styles import inject_app_styles

    inject_app_styles()
