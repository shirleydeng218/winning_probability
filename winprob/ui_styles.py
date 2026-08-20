"""Shared visual styling and layout helpers."""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

# Brand palette
NAVY = "#0B1C2D"
PANEL = "#12263A"
BORDER = "#2F5175"
MINT = "#B8F2E6"
GREEN = "#7ED957"
TEXT = "#E6F2F0"
MUTED = "#9FB3C8"
AMBER = "#FBBF24"
RED = "#F87171"

STATUS_ICONS = {
    "Recommended": "🏆",
    "Runner-up": "🥈",
    "Leads (not eligible)": "⚠️",
    "Not eligible": "⛔",
    "Alternative": "📊",
}


def inject_app_styles() -> None:
    st.markdown(
        f"""
        <style>
        html {{ scroll-behavior: smooth; }}

        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }}

        h1 {{
            color: {MINT};
            font-weight: 700;
            letter-spacing: -0.02em;
        }}

        h2, h3 {{
            color: {TEXT};
        }}

        [data-testid="stSidebar"] {{
            border-right: 1px solid {BORDER};
        }}

        [data-testid="stSidebar"] .block-container {{
            padding-top: 1rem;
        }}

        .winprob-nav-group {{
            display: flex;
            flex-direction: column;
            gap: 0.1rem;
            margin-bottom: 0.85rem;
        }}
        .winprob-nav-group-label {{
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {MUTED};
            margin: 0 0 0.35rem 0;
            line-height: 1.3;
        }}
        .winprob-nav-link {{
            display: block;
            color: {TEXT};
            text-decoration: none;
            padding: 0.32rem 0.55rem;
            font-size: 0.875rem;
            line-height: 1.35;
            border-radius: 6px;
            border-left: 2px solid transparent;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }}
        .winprob-nav-link:hover {{
            color: {MINT};
            background: {PANEL};
            border-left-color: {GREEN};
            text-decoration: none;
        }}
        .winprob-nav-sublink {{
            padding-left: 0.85rem;
            font-size: 0.84rem;
        }}
        .winprob-nav-nested-sublink {{
            padding-left: 1.25rem;
            font-size: 0.8rem;
            color: {MUTED};
        }}
        .winprob-nav-nested-sublink:hover {{
            color: {MINT};
        }}
        [data-testid="stSidebar"] h2 {{
            font-size: 0.95rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: {MUTED};
            margin-bottom: 0.5rem;
        }}

        .winprob-hero {{
            background: linear-gradient(135deg, {NAVY} 0%, {PANEL} 100%);
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }}
        .winprob-hero-title {{
            color: {MINT};
            font-size: 0.8rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }}
        .winprob-hero-body {{
            color: {TEXT};
            font-size: 1rem;
            line-height: 1.6;
            margin: 0;
        }}

        .winprob-steps {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.75rem;
            margin: 1rem 0 1.25rem 0;
        }}
        @media (max-width: 900px) {{
            .winprob-steps {{ grid-template-columns: 1fr; }}
        }}
        .winprob-step-card {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0.9rem 1rem;
        }}
        .winprob-step-card.active {{
            border-color: {GREEN};
            box-shadow: 0 0 0 1px {GREEN};
        }}
        .winprob-step-card.done {{
            opacity: 0.85;
        }}
        .winprob-step-num {{
            color: {GREEN};
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
        }}
        .winprob-step-label {{
            color: {TEXT};
            font-size: 0.95rem;
            font-weight: 600;
            margin-top: 0.15rem;
        }}
        .winprob-step-hint {{
            color: {MUTED};
            font-size: 0.82rem;
            margin-top: 0.25rem;
            line-height: 1.4;
        }}

        .winprob-callout {{
            border-radius: 12px;
            padding: 1rem 1.15rem;
            margin: 0.75rem 0 1rem 0;
            border: 1px solid {BORDER};
            line-height: 1.55;
        }}
        .winprob-callout-success {{
            background: rgba(126, 217, 87, 0.12);
            border-color: rgba(126, 217, 87, 0.45);
            color: {TEXT};
        }}
        .winprob-callout-warning {{
            background: rgba(251, 191, 36, 0.12);
            border-color: rgba(251, 191, 36, 0.45);
            color: {TEXT};
        }}
        .winprob-callout-info {{
            background: rgba(184, 242, 230, 0.08);
            border-color: rgba(184, 242, 230, 0.35);
            color: {TEXT};
        }}

        .winprob-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            margin: 0.5rem 0 1rem 0;
        }}
        @media (max-width: 900px) {{
            .winprob-kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        .winprob-kpi {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-top: 3px solid {GREEN};
            border-radius: 12px;
            padding: 0.85rem 1rem;
        }}
        .winprob-kpi-label {{
            color: {MUTED};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .winprob-kpi-value {{
            color: {TEXT};
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 0.25rem;
            line-height: 1.3;
        }}
        .winprob-kpi-sub {{
            color: {MINT};
            font-size: 0.82rem;
            margin-top: 0.15rem;
        }}

        .winprob-section-caption {{
            color: {MUTED};
            font-size: 0.92rem;
            margin: -0.35rem 0 0.85rem 0;
            line-height: 1.45;
        }}

        .winprob-metric-pill {{
            display: inline-block;
            background: {PANEL};
            border: 1px solid {BORDER};
            color: {MINT};
            border-radius: 999px;
            padding: 0.2rem 0.65rem;
            font-size: 0.82rem;
            margin-right: 0.35rem;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 12px;
            overflow: hidden;
        }}

        .winprob-app-header {{
            background: linear-gradient(135deg, {NAVY} 0%, {PANEL} 55%, #0f2840 100%);
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.22);
        }}
        .winprob-header-grid {{
            display: grid;
            grid-template-columns: minmax(100px, 1fr) minmax(220px, 2fr) minmax(100px, 1fr);
            align-items: center;
            gap: 1rem;
        }}
        .winprob-header-logo img {{
            max-height: 76px;
            width: auto;
            max-width: 132px;
            object-fit: contain;
            display: block;
            margin: 0 auto;
        }}
        .winprob-header-logo-right img {{
            max-width: 112px;
        }}
        .winprob-header-center {{
            text-align: center;
        }}
        .winprob-header-eyebrow {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            color: {GREEN};
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }}
        .winprob-header-main {{
            font-size: clamp(1.45rem, 2.8vw, 2rem);
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.15;
            background: linear-gradient(90deg, {MINT} 0%, {GREEN} 45%, {MINT} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .winprob-header-sub {{
            margin-top: 0.4rem;
            font-size: 0.86rem;
            color: {MUTED};
            letter-spacing: 0.05em;
        }}
        @media (max-width: 768px) {{
            .winprob-header-grid {{
                grid-template-columns: 1fr;
                text-align: center;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(text: str, *, label: str = "WinProb") -> None:
    st.markdown(
        f'<div class="winprob-hero">'
        f'<div class="winprob-hero-title">{_safe_html(label)}</div>'
        f'<p class="winprob-hero-body">{_inline_md(text)}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_quick_start() -> None:
    st.markdown(
        """
        <div class="winprob-steps">
            <div class="winprob-step-card">
                <div class="winprob-step-num">STEP 1</div>
                <div class="winprob-step-label">Upload &amp; validate</div>
                <div class="winprob-step-hint">Load your test results or try sample data.</div>
            </div>
            <div class="winprob-step-card">
                <div class="winprob-step-num">STEP 2</div>
                <div class="winprob-step-label">Configure scenario</div>
                <div class="winprob-step-hint">Pick metrics, winning rule, and significance in the sidebar.</div>
            </div>
            <div class="winprob-step-card">
                <div class="winprob-step-num">STEP 3</div>
                <div class="winprob-step-label">Review &amp; export</div>
                <div class="winprob-step-hint">Read the executive summary, then export or share.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_wizard_steps(steps: List[str], current: int) -> None:
    cards = []
    for i, label in enumerate(steps):
        state = "active" if i == current else ("done" if i < current else "")
        safe_label = html.escape(label)
        cards.append(
            f'<div class="winprob-step-card {state}">'
            f'<div class="winprob-step-num">STEP {i + 1}</div>'
            f'<div class="winprob-step-label">{safe_label}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="winprob-steps">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
    st.progress((current + 1) / len(steps), text=f"Step {current + 1} of {len(steps)}: {steps[current]}")


def _safe_html(text: str) -> str:
    return html.escape(str(text), quote=True)


def _inline_md(text: str) -> str:
    parts = re.split(r"\*\*(.+?)\*\*", text)
    out: List[str] = []
    for i, part in enumerate(parts):
        escaped = _safe_html(part)
        if i % 2 == 1:
            out.append(f"<strong>{escaped}</strong>")
        else:
            out.append(escaped)
    return "".join(out)


def render_callout(message: str, tone: str = "info") -> None:
    css_class = {
        "success": "winprob-callout-success",
        "warning": "winprob-callout-warning",
        "info": "winprob-callout-info",
    }.get(tone, "winprob-callout-info")
    st.markdown(
        f'<div class="winprob-callout {css_class}">{_inline_md(message)}</div>',
        unsafe_allow_html=True,
    )


def render_kpi_grid(items: List[Dict[str, str]]) -> None:
    cards = []
    for item in items:
        label = _safe_html(item["label"])
        value = _safe_html(item["value"])
        sub_html = (
            f'<div class="winprob-kpi-sub">{_safe_html(item["sub"])}</div>'
            if item.get("sub")
            else ""
        )
        cards.append(
            f'<div class="winprob-kpi">'
            f'<div class="winprob-kpi-label">{label}</div>'
            f'<div class="winprob-kpi-value">{value}</div>'
            f"{sub_html}"
            f"</div>"
        )
    st.markdown(f'<div class="winprob-kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_section_header(
    title: str,
    caption: Optional[str] = None,
    *,
    anchor: Optional[str] = None,
    level: str = "subheader",
) -> None:
    if anchor:
        st.markdown(f'<div id="{anchor}"></div>', unsafe_allow_html=True)
    if level == "header":
        st.header(title)
    elif level == "subheader":
        st.subheader(title)
    else:
        st.markdown(f"### {title}")
    if caption:
        st.markdown(
            f'<p class="winprob-section-caption">{_safe_html(caption)}</p>',
            unsafe_allow_html=True,
        )


def decorate_status_column(df: pd.DataFrame, column: str = "Status") -> pd.DataFrame:
    if column not in df.columns:
        return df
    out = df.copy()
    out[column] = out[column].apply(
        lambda s: f"{STATUS_ICONS.get(str(s), '•')} {s}" if pd.notna(s) else s
    )
    return out


def render_scenario_pills(winning_rule_label: str, significance_threshold: str) -> None:
    rule = _safe_html(winning_rule_label)
    threshold = _safe_html(significance_threshold)
    st.markdown(
        f'<div style="margin-bottom: 0.75rem;">'
        f'<span class="winprob-metric-pill">Scenario: {rule}</span>'
        f'<span class="winprob-metric-pill">Significance ≥ {threshold}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _asset_data_uri(relative_path: str) -> str:
    path = Path(relative_path)
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_app_header(
    disney_path: str = "assets/disney.svg",
    hulu_path: str = "assets/hulu.png",
) -> None:
    """Branded header with full logo rendering and tech-style title."""
    disney_uri = _asset_data_uri(disney_path)
    hulu_uri = _asset_data_uri(hulu_path)
    st.markdown(
        f"""
        <div class="winprob-app-header">
            <div class="winprob-header-grid">
                <div class="winprob-header-logo">
                    <img src="{disney_uri}" alt="Disney" />
                </div>
                <div class="winprob-header-center">
                    <div class="winprob-header-eyebrow">BLADE · BAYESIAN TEST INTELLIGENCE</div>
                    <div class="winprob-header-main">Marketing Analytics</div>
                    <div class="winprob-header-sub">WinProb · quantify uncertainty · decide with confidence</div>
                </div>
                <div class="winprob-header-logo winprob-header-logo-right">
                    <img src="{hulu_uri}" alt="Hulu" />
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
