"""Results rendering for incrementality analysis."""

import streamlit as st

from winprob.analytics import (
    build_multi_metric_rankings,
    compute_budget_optimizer,
)
from winprob.charts_plotly import (
    render_bump_chart,
    render_incrementality_ci_plots,
    render_interactive_density,
    render_pairwise_heatmap,
    render_radar_chart,
)
from winprob.dashboard import render_executive_dashboard
from winprob.export import build_readout_charts, build_readout_html, build_readout_pdf_bytes
from winprob.formatting import (
    LABEL_ABSOLUTE_CVR_LIFT,
    LABEL_BUDGET,
    LABEL_CPIS,
    LABEL_ELIGIBLE_TO_WIN,
    LABEL_INCREMENTAL_CONVERSIONS,
    LABEL_RELATIVE_CVR_LIFT,
    LABEL_SIGNIFICANCE,
    LABEL_TEST_CONVERSIONS,
    LABEL_WINNING_PROBABILITY,
    fmt_threshold,
    format_budget_optimizer,
    format_overlap_table,
    format_per_cell_metrics,
    format_winning_probability_summary,
    style_budget_optimizer_table,
)
from winprob.glossary import metric_anchor, section_anchor, slugify
from winprob.plotting import cache_and_download_figure, cache_csv, render_incrementality_density_grid
from winprob.simulation import WINNING_RULES
from winprob.ui_styles import render_callout


def _build_summary_views(win_prob_df):
    summary_table = win_prob_df[[
        "dt", "cell", "metric", "win_prob", "relative_cvr_lift", "cvr_lift",
        "incremental_conversions", "cpis", "conf_level", "significance_eligible",
    ]].rename(columns={
        "win_prob": LABEL_WINNING_PROBABILITY,
        "cpis": LABEL_CPIS,
        "cell": "Cell",
        "relative_cvr_lift": LABEL_RELATIVE_CVR_LIFT,
        "cvr_lift": LABEL_ABSOLUTE_CVR_LIFT,
        "incremental_conversions": LABEL_INCREMENTAL_CONVERSIONS,
        "conf_level": LABEL_SIGNIFICANCE,
        "significance_eligible": LABEL_ELIGIBLE_TO_WIN,
    })
    to_view = summary_table.drop(columns=["dt"]).copy()
    return summary_table, to_view


def _render_per_cell_table(results, metric: str) -> None:
    section_anchor(
        metric_anchor(metric, "per-cell-metrics"),
        "Per-Cell Performance Metrics",
        caption="Observed spend, conversions, lift, CPiS, and Significance for this conversion metric.",
    )
    per_cell_display = results[results["metric"] == metric][[
        "cell", "metric", "spend", "test_conversions", "cvr_lift", "relative_cvr_lift",
        "incremental_conversions", "cpis", "conf_level", "significance_eligible",
    ]].rename(columns={
        "cell": "Cell",
        "metric": "Metric",
        "spend": LABEL_BUDGET,
        "test_conversions": LABEL_TEST_CONVERSIONS,
        "cvr_lift": LABEL_ABSOLUTE_CVR_LIFT,
        "relative_cvr_lift": LABEL_RELATIVE_CVR_LIFT,
        "incremental_conversions": LABEL_INCREMENTAL_CONVERSIONS,
        "cpis": LABEL_CPIS,
        "conf_level": LABEL_SIGNIFICANCE,
        "significance_eligible": LABEL_ELIGIBLE_TO_WIN,
    })
    if per_cell_display.empty:
        st.caption("No per-cell rows for this metric.")
        return
    st.dataframe(format_per_cell_metrics(per_cell_display), use_container_width=True)


def _render_metric_advanced_analysis(
    *,
    metric: str,
    win_prob_df,
    pairwise_by_metric,
    overlap_by_metric,
    winning_rule_label: str,
) -> None:
    section_anchor(
        metric_anchor(metric, "advanced-analysis"),
        "Advanced Analysis",
        caption="Head-to-head comparisons, posterior overlap, and budget projection for this conversion metric.",
    )

    if metric in pairwise_by_metric:
        with st.expander("Pairwise Win Matrix", expanded=False):
            st.markdown(
                f'<div id="{metric_anchor(metric, "pairwise-win-matrix")}"></div>',
                unsafe_allow_html=True,
            )
            st.caption("Head-to-head Winning Probability between each pair of cells.")
            render_pairwise_heatmap(pairwise_by_metric[metric], metric, winning_rule_label)

    if metric in overlap_by_metric and not overlap_by_metric[metric].empty:
        with st.expander("Posterior Overlap", expanded=False):
            st.markdown(
                f'<div id="{metric_anchor(metric, "posterior-overlap")}"></div>',
                unsafe_allow_html=True,
            )
            st.caption("How often two cells look statistically similar in simulation.")
            st.dataframe(format_overlap_table(overlap_by_metric[metric]), use_container_width=True)

    with st.expander("Budget Optimizer", expanded=False):
        st.markdown(
            f'<div id="{metric_anchor(metric, "budget-optimizer")}"></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Each row shows the outcome if the added budget were allocated to that cell. "
            "Highlighted columns are projected values; other columns show current performance."
        )
        added_budget = st.number_input(
            "Additional budget to simulate ($)",
            min_value=0.0,
            value=100000.0,
            step=10000.0,
            key=f"budget_{metric}",
        )
        budget_df = compute_budget_optimizer(win_prob_df, metric, added_budget)
        if not budget_df.empty:
            st.dataframe(style_budget_optimizer_table(budget_df), use_container_width=True)
        elif added_budget <= 0:
            st.caption("Enter an additional budget amount to see projections.")


def _render_metric_results(
    *,
    metric: str,
    df,
    samples_df,
    n_sims: int,
    results,
    win_prob_df,
    pairwise_by_metric,
    overlap_by_metric,
    significance_threshold: float,
    winning_rule: str,
    winning_rule_label: str,
) -> None:
    st.markdown(f'<div id="{slugify(metric)}"></div>', unsafe_allow_html=True)

    section_anchor(
        metric_anchor(metric, "executive-summary"),
        "Executive Summary",
        caption="Start here: recommendation, KPIs, and per-cell takeaways.",
    )
    render_executive_dashboard(
        win_prob_df,
        metric,
        winning_rule_label,
        significance_threshold,
        winning_rule=winning_rule,
        skip_header=True,
    )

    _render_per_cell_table(results, metric)

    section_anchor(
        metric_anchor(metric, "multi-metric-rankings"),
        "Multi-Metric Rankings",
        caption="How each cell ranks on Winning Probability, CPiS, Relative CVR Lift, and Significance.",
    )
    rank_df = build_multi_metric_rankings(win_prob_df, metric)
    if not rank_df.empty:
        render_bump_chart(rank_df, metric)

    section_anchor(
        metric_anchor(metric, "cell-comparison"),
        "Cell Comparison",
        caption="Normalized view of how cells compare across key performance dimensions.",
    )
    render_radar_chart(win_prob_df, metric)

    _render_distribution_analysis(
        df=df,
        samples_df=samples_df,
        metric=metric,
        n_sims=n_sims,
    )

    _render_metric_advanced_analysis(
        metric=metric,
        win_prob_df=win_prob_df,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        winning_rule_label=winning_rule_label,
    )


def _render_export_section(
    *,
    test_name: str,
    to_view,
    summary_table,
    df,
    samples_df,
    winning_rule_label: str,
    significance_threshold: float,
) -> None:
    section_anchor(
        "export-readout-pack",
        "Export Readout Pack",
        caption="Download a stakeholder-ready summary across all conversion metrics — table, confidence intervals, and density plots.",
    )
    formatted = format_winning_probability_summary(to_view.copy())
    cache_csv(summary_table, "incrementality_results_csv")
    readout_charts = build_readout_charts(df, samples_df)
    extra_sections = {
        "Winning Rule": winning_rule_label,
        "Significance Threshold": fmt_threshold(significance_threshold),
    }

    col_html, col_pdf, col_csv = st.columns(3)
    html_bytes = build_readout_html(
        test_name,
        formatted,
        extra_sections=extra_sections,
        charts=readout_charts,
    )
    with col_html:
        st.download_button(
            "Download Readout HTML",
            data=html_bytes,
            file_name=f"{test_name}_readout.html",
            mime="text/html",
            use_container_width=True,
        )
    with col_pdf:
        try:
            pdf_bytes = build_readout_pdf_bytes(
                test_name,
                formatted,
                extra_sections=extra_sections,
                charts=readout_charts,
            )
        except Exception as exc:
            pdf_bytes = b""
            st.error(f"PDF export failed: {exc}")
        if pdf_bytes:
            st.download_button(
                "Download Readout PDF",
                data=pdf_bytes,
                file_name=f"{test_name}_readout.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.caption("PDF export unavailable.")
    with col_csv:
        st.download_button(
            "Download Summary CSV",
            data=st.session_state["incrementality_results_csv"],
            file_name="incrementality_winning_prob.csv",
            mime="text/csv",
            use_container_width=True,
        )


def _render_distribution_analysis(*, df, samples_df, metric: str, n_sims: int) -> None:
    section_anchor(
        metric_anchor(metric, "distribution-uncertainty"),
        "Distribution & Uncertainty Analysis",
        caption=f"Input-based confidence intervals and Monte Carlo density plots for {metric}.",
    )
    render_callout(
        f"**Winning Probability is built from {n_sims:,} Monte Carlo simulations** per cell. "
        "Use **density plots** below to explore simulated outcomes for this conversion metric.",
        tone="info",
    )

    with st.expander("Confidence intervals", expanded=False):
        st.markdown('<div id="confidence-intervals"></div>', unsafe_allow_html=True)
        st.caption("Uncertainty bands from the test input — Relative CVR Lift and Incremental Conversions by cell.")
        render_incrementality_ci_plots(df, metric)

    density_plot_df = samples_df[samples_df["metric"] == metric][[
        "analysis_date", "cell", "metric",
        "relative_cvr_lift_samples", "incremental_conversion_samples",
    ]].copy()

    with st.expander("Interactive density plots", expanded=False):
        st.markdown('<div id="interactive-density-plots"></div>', unsafe_allow_html=True)
        st.caption("Posterior distributions from Monte Carlo simulation — hover to explore the spread behind each cell.")
        if density_plot_df.empty:
            st.caption("No simulation samples for this metric.")
        else:
            st.markdown(f"**{metric} — Relative CVR Lift**")
            render_interactive_density(
                density_plot_df, metric, "relative_cvr_lift_samples", "Relative CVR Lift", as_percent=True
            )
            st.markdown(f"**{metric} — Incremental Conversions**")
            render_interactive_density(
                density_plot_df, metric, "incremental_conversion_samples", "Incremental Conversions"
            )

    with st.expander("Static density plots (export-ready)", expanded=False):
        st.markdown('<div id="static-density-plots"></div>', unsafe_allow_html=True)
        st.caption("Download-ready charts for decks and stakeholder readouts.")
        if density_plot_df.empty:
            st.caption("No simulation samples for this metric.")
        else:
            metric_slug = slugify(metric)
            plot_df = density_plot_df.dropna(subset=["relative_cvr_lift_samples"])
            for title, col, fmt, prefix in [
                ("Relative CVR Lift", "relative_cvr_lift_samples", "percent", "Relative_CVR"),
                ("Incremental Conversions", "incremental_conversion_samples", "count", "Incremental"),
            ]:
                sub = plot_df.dropna(subset=[col])
                if sub.empty:
                    continue
                fig = render_incrementality_density_grid(
                    sub[["analysis_date", "cell", "metric", col]],
                    col,
                    title,
                    x_tick_format=fmt,
                )
                st.pyplot(fig)
                cache_and_download_figure(
                    fig,
                    key=f"Incr_{prefix}_Density_{metric_slug}",
                    filename_prefix=f"Incrementality_{prefix}_Density_{metric_slug}",
                )


def render_incrementality_results(
    *,
    test_name,
    df,
    results,
    win_prob_df,
    samples_df,
    pairwise_by_metric,
    overlap_by_metric,
    significance_threshold,
    winning_rule,
    n_sims,
    selected_metric,
    summary_context,
    render_ai_summary_fn,
):
    winning_rule_label = WINNING_RULES.get(winning_rule, winning_rule)
    summary_table, to_view = _build_summary_views(win_prob_df)

    section_anchor(
        slugify(selected_metric),
        selected_metric,
        caption="Stakeholder readout for the selected conversion metric.",
        level="subheader",
    )
    _render_metric_results(
        metric=selected_metric,
        df=df,
        samples_df=samples_df,
        n_sims=n_sims,
        results=results,
        win_prob_df=win_prob_df,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        significance_threshold=significance_threshold,
        winning_rule=winning_rule,
        winning_rule_label=winning_rule_label,
    )

    st.markdown("---")
    section_anchor(
        "full-test-summary",
        "Full Test Summary",
        caption="Results, exports, and AI summary across all conversion metrics in this test.",
        level="subheader",
    )

    section_anchor(
        "winning-probability-summary",
        "Winning Probability & CPiS by Cell",
        caption="Full results table across all conversion metrics.",
    )
    st.dataframe(format_winning_probability_summary(to_view), use_container_width=True)

    _render_export_section(
        test_name=test_name,
        to_view=to_view,
        summary_table=summary_table,
        df=df,
        samples_df=samples_df,
        winning_rule_label=winning_rule_label,
        significance_threshold=significance_threshold,
    )

    render_ai_summary_fn(summary_context, session_namespace="incrementality")
