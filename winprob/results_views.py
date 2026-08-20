"""Results rendering for incrementality analysis."""

import streamlit as st

from winprob.analytics import (
    build_multi_metric_rankings,
    compute_budget_optimizer,
)
from winprob.charts_plotly import (
    render_bump_chart,
    render_ci_plotly,
    render_interactive_density,
    render_pairwise_heatmap,
    render_radar_chart,
)
from winprob.dashboard import render_executive_dashboard
from winprob.export import build_readout_html, build_simple_pdf_bytes
from winprob.formatting import (
    LABEL_ABSOLUTE_CVR_LIFT,
    LABEL_CPIS,
    LABEL_ELIGIBLE_TO_WIN,
    LABEL_INCREMENTAL_CONVERSIONS,
    LABEL_SIGNIFICANCE,
    LABEL_WINNING_PROBABILITY,
    fmt_threshold,
    format_budget_optimizer,
    format_overlap_table,
    format_per_cell_metrics,
    format_rankings_table,
    format_sensitivity_table,
    format_winning_probability_summary,
)
from winprob.glossary import metric_anchor, section_anchor, slugify
from winprob.plotting import cache_and_download_figure, cache_csv, render_incrementality_density_grid
from winprob.simulation import WINNING_RULES, run_sensitivity_analysis


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
    summary_context,
    render_ai_summary_fn,
):
    winning_rule_label = WINNING_RULES.get(winning_rule, winning_rule)

    for metric in win_prob_df["metric"].unique():
        st.markdown(f'<div id="{slugify(metric)}"></div>', unsafe_allow_html=True)
        st.markdown(f"## {metric}")

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

        section_anchor(
            metric_anchor(metric, "multi-metric-rankings"),
            "Multi-Metric Rankings",
            caption="How each cell ranks on Winning Probability, CPiS, lift, and Significance.",
        )
        rank_df = build_multi_metric_rankings(win_prob_df, metric)
        if not rank_df.empty:
            st.dataframe(format_rankings_table(rank_df), use_container_width=True)
            render_bump_chart(rank_df, metric)

        section_anchor(
            metric_anchor(metric, "cell-comparison"),
            "Cell Comparison",
            caption="Normalized view of how cells compare across key performance dimensions.",
        )
        render_radar_chart(win_prob_df, metric)

        if metric in pairwise_by_metric:
            section_anchor(
                metric_anchor(metric, "pairwise-win-matrix"),
                "Pairwise Win Matrix",
                caption="Head-to-head Winning Probability between each pair of cells.",
            )
            render_pairwise_heatmap(pairwise_by_metric[metric], metric, winning_rule_label)

        if metric in overlap_by_metric and not overlap_by_metric[metric].empty:
            section_anchor(
                metric_anchor(metric, "posterior-overlap"),
                "Posterior Overlap",
                caption="How often two cells look statistically similar in simulation.",
            )
            st.dataframe(format_overlap_table(overlap_by_metric[metric]), use_container_width=True)

        section_anchor(
            metric_anchor(metric, "sensitivity"),
            "Sensitivity — Significance Threshold",
            caption="See whether the recommended winner changes as Significance requirements shift.",
        )
        sensitivity_df = run_sensitivity_analysis(results, n_sims=n_sims, winning_rule=winning_rule)
        sens_metric = sensitivity_df[sensitivity_df["metric"] == metric]
        if not sens_metric.empty:
            st.dataframe(format_sensitivity_table(sens_metric), use_container_width=True)

        section_anchor(
            metric_anchor(metric, "budget-optimizer"),
            "Budget Optimizer",
            caption="Project incremental conversions if you add budget to each cell by CPiS efficiency.",
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
            st.dataframe(format_budget_optimizer(budget_df), use_container_width=True)

    section_anchor(
        "winning-probability-summary",
        "Winning Probability & CPiS by Cell",
        caption="Full results table across all metrics — download CSV below.",
    )
    summary_table = win_prob_df[[
        "dt", "cell", "metric", "win_prob", "cvr_lift", "incremental_conversions",
        "cpis", "conf_level", "significance_eligible",
    ]].rename(columns={
        "win_prob": LABEL_WINNING_PROBABILITY,
        "cpis": LABEL_CPIS,
        "cell": "Cell",
        "cvr_lift": LABEL_ABSOLUTE_CVR_LIFT,
        "incremental_conversions": LABEL_INCREMENTAL_CONVERSIONS,
        "conf_level": LABEL_SIGNIFICANCE,
        "significance_eligible": LABEL_ELIGIBLE_TO_WIN,
    })
    to_view = summary_table.drop(columns=["dt"]).copy()
    st.dataframe(format_winning_probability_summary(to_view), use_container_width=True)
    cache_csv(summary_table, "incrementality_results_csv")
    st.download_button(
        "Download Winning Probability Summary CSV",
        data=st.session_state["incrementality_results_csv"],
        file_name="incrementality_winning_prob.csv",
        mime="text/csv",
    )

    section_anchor(
        "confidence-intervals",
        "Confidence Intervals",
        caption="Uncertainty around absolute lift by cell.",
    )
    for obj in df["conversion_segment"].unique():
        render_ci_plotly(df, obj)

    section_anchor(
        "interactive-density-plots",
        "Interactive Density Plots",
        caption="Posterior distributions from simulation — hover to explore.",
    )
    density_plot_df = samples_df[[
        "analysis_date", "cell", "metric",
        "cvr_lift_samples", "relative_cvr_lift_samples", "incremental_conversion_samples",
    ]].copy()
    for obj in df["conversion_segment"].unique():
        st.markdown(f"**{obj} — Absolute CVR Lift**")
        render_interactive_density(density_plot_df, obj, "cvr_lift_samples", "Absolute CVR Lift", as_percent=True)
        st.markdown(f"**{obj} — Relative CVR Lift**")
        render_interactive_density(density_plot_df, obj, "relative_cvr_lift_samples", "Relative CVR Lift", as_percent=True)
        st.markdown(f"**{obj} — Incremental Conversions**")
        render_interactive_density(density_plot_df, obj, "incremental_conversion_samples", "Incremental Conversions")

    section_anchor(
        "static-density-plots",
        "Static Density Plots (export-ready)",
        caption="Download-ready charts for decks and readouts.",
    )
    density_plot_df = density_plot_df.dropna(subset=["cvr_lift_samples"])
    for title, col, fmt, prefix in [
        ("Absolute CVR Lift", "cvr_lift_samples", "percent", "Absolute_CVR"),
        ("Relative CVR Lift", "relative_cvr_lift_samples", "percent", "Relative_CVR"),
        ("Incremental Conversions", "incremental_conversion_samples", "count", "Incremental"),
    ]:
        sub = density_plot_df.dropna(subset=[col]) if col != "cvr_lift_samples" else density_plot_df
        fig = render_incrementality_density_grid(
            sub[["analysis_date", "cell", "metric", col]],
            col,
            title,
            x_tick_format=fmt,
        )
        st.pyplot(fig)
        cache_and_download_figure(fig, key=f"Incr_{prefix}_Density", filename_prefix=f"Incrementality_{prefix}_Density")

    section_anchor(
        "export-readout-pack",
        "Export Readout Pack",
        caption="Download an HTML or PDF summary to share with stakeholders.",
    )
    html_bytes = build_readout_html(test_name, format_winning_probability_summary(to_view.copy()), extra_sections={
        "Winning Rule": winning_rule_label,
        "Significance Threshold": fmt_threshold(significance_threshold),
    })
    st.download_button(
        "Download Readout HTML",
        data=html_bytes,
        file_name=f"{test_name}_readout.html",
        mime="text/html",
    )
    pdf_lines = [
        f"Test: {test_name}",
        f"Winning rule: {winning_rule_label}",
        f"Significance threshold: {fmt_threshold(significance_threshold)}",
        "",
        format_winning_probability_summary(to_view.copy()).to_string(index=False),
    ]
    pdf_bytes = build_simple_pdf_bytes(f"WinProb Readout — {test_name}", pdf_lines)
    if pdf_bytes:
        st.download_button(
            "Download Readout PDF",
            data=pdf_bytes,
            file_name=f"{test_name}_readout.pdf",
            mime="application/pdf",
        )

    render_ai_summary_fn(summary_context, session_namespace="incrementality")
