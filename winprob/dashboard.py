"""Executive dashboard and branded banner components."""

from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

from winprob.analytics import (
    build_metric_bottom_line,
    build_stakeholder_summary_table,
    summarize_metric_leader,
)
from winprob.formatting import (
    LABEL_WINNING_PROBABILITY,
    format_stakeholder_summary,
    fmt_count,
    fmt_cpis,
    fmt_currency,
    fmt_significance,
    fmt_threshold,
    fmt_winning_probability,
)
from winprob.ui_styles import (
    _safe_html,
    decorate_status_column,
    render_callout,
    render_kpi_grid,
    render_scenario_pills,
    render_section_header,
)


def render_test_banner(test_name: str, n_cells: int, total_spend: float, total_reach: int) -> None:
    safe_name = _safe_html(test_name)
    date_str = datetime.now().strftime("%B %d, %Y")
    st.markdown(
        f'<div style="background: linear-gradient(90deg, #0B1C2D 0%, #12263A 100%);'
        f'padding: 1rem 1.25rem; border-radius: 12px; border: 1px solid #2F5175;'
        f'margin-bottom: 1rem;">'
        f'<div style="color:#B8F2E6; font-size:0.85rem; letter-spacing:0.08em;">WINPROB TEST READOUT</div>'
        f'<div style="color:#E6F2F0; font-size:1.35rem; font-weight:700; margin-top:0.25rem;">{safe_name}</div>'
        f'<div style="color:#9FB3C8; font-size:0.95rem; margin-top:0.5rem;">'
        f"{date_str} · {n_cells} cells · {fmt_currency(total_spend)} spend · {fmt_count(total_reach)} reach"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def render_executive_dashboard(
    win_prob_df,
    metric: str,
    winning_rule_label: str,
    significance_threshold: float,
    winning_rule: str = "lowest_cpis",
    ai_one_liner: Optional[str] = None,
    skip_header: bool = False,
) -> None:
    leader = summarize_metric_leader(win_prob_df, metric, winning_rule)
    if not leader:
        st.warning("No results available for executive dashboard.")
        return

    if not skip_header:
        render_section_header(
            "Executive Summary",
            "Your stakeholder readout: recommended cell, key metrics, and one-line takeaways for every cell.",
            level="subheader",
        )

    bottom_line = build_metric_bottom_line(
        win_prob_df, metric, significance_threshold, winning_rule=winning_rule
    )
    if ai_one_liner:
        render_callout(ai_one_liner, tone="info")
    elif bottom_line:
        render_callout(bottom_line, tone="success" if leader["eligible"] else "warning")

    render_kpi_grid([
        {"label": "Recommended Winner", "value": leader["winner_cell"]},
        {"label": LABEL_WINNING_PROBABILITY, "value": fmt_winning_probability(leader["win_prob"])},
        {"label": "CPiS", "value": fmt_cpis(leader["cpis"])},
        {
            "label": "Significance",
            "value": fmt_significance(leader["significance"]),
            "sub": "Eligible" if leader["eligible"] else "Not eligible",
        },
    ])

    takeaway_table = format_stakeholder_summary(
        build_stakeholder_summary_table(
            win_prob_df, metric, significance_threshold, winning_rule=winning_rule
        )
    )
    if not takeaway_table.empty:
        st.dataframe(
            decorate_status_column(takeaway_table),
            use_container_width=True,
            hide_index=True,
        )

    render_scenario_pills(winning_rule_label, fmt_threshold(significance_threshold))


def render_metric_cards_row(cards: Dict[str, Any]) -> None:
    cols = st.columns(len(cards))
    for col, (label, value) in zip(cols, cards.items()):
        with col:
            st.metric(label, value)
