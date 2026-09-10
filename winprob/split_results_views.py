"""Results rendering for split-test analysis."""

from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

from winprob.charts_plotly import (
    render_bump_chart,
    render_interactive_density,
    render_pairwise_heatmap,
    render_split_radar_chart,
)
from winprob.dashboard import render_split_executive_dashboard
from winprob.export import build_readout_html, build_readout_pdf_bytes
from winprob.formatting import (
    LABEL_BUDGET,
    LABEL_CPS,
    LABEL_TEST_CONVERSIONS,
    LABEL_WINNING_PROBABILITY,
    format_split_summary,
    fmt_count,
    fmt_cps,
    fmt_currency,
    fmt_cvr_lift,
)
from winprob.glossary import metric_anchor, render_glossary_dataframe, section_anchor, slugify
from winprob.plotting import apply_dark_axes, cache_and_download_figure, cache_csv
from winprob.split_analytics import build_split_multi_metric_rankings
from winprob.ui import get_applied_ai_summary_for_export
from winprob.ui_styles import render_callout


def _build_summary_views(win_prob_df: pd.DataFrame, compare_on: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_table = win_prob_df[[
        "dt", "cell", "metric", "win_prob", "cps", "users", "conversions",
        "conversion_rate", "impressions", "ci_low", "ci_high", "p_value",
    ]].rename(columns={
        "win_prob": LABEL_WINNING_PROBABILITY,
        "cps": LABEL_CPS,
        "cell": "Cell",
        "users": "Reach",
        "conversions": "Conversions",
        "conversion_rate": "Conversion Rate",
        "impressions": "Impressions",
        "ci_low": "CI Low",
        "ci_high": "CI High",
        "p_value": "p-value",
    })
    to_view = summary_table.drop(columns=["dt"]).copy()
    return summary_table, to_view


def _render_per_cell_table(results: pd.DataFrame, metric: str) -> None:
    section_anchor(
        metric_anchor(metric, "per-cell-metrics"),
        "Per-Cell Performance Metrics",
        caption="Observed spend, reach, conversions, CPS, and conversion rate for this metric.",
    )
    per_cell = results[results["metric"] == metric].copy()
    display = per_cell[[
        "cell", "metric", "spend", "population_test", "conversions",
        "conversion_rate", "impressions", "cps",
    ]].rename(columns={
        "cell": "Cell",
        "metric": "Metric",
        "spend": LABEL_BUDGET,
        "population_test": "Reach",
        "conversions": LABEL_TEST_CONVERSIONS,
        "conversion_rate": "Conversion Rate",
        "impressions": "Impressions",
        "cps": LABEL_CPS,
    })
    if display.empty:
        st.caption("No per-cell rows for this metric.")
        return
    formatted = display.copy()
    formatted[LABEL_BUDGET] = formatted[LABEL_BUDGET].apply(fmt_currency)
    formatted["Reach"] = formatted["Reach"].apply(fmt_count)
    formatted[LABEL_TEST_CONVERSIONS] = formatted[LABEL_TEST_CONVERSIONS].apply(fmt_count)
    formatted["Impressions"] = formatted["Impressions"].apply(fmt_count)
    formatted["Conversion Rate"] = formatted["Conversion Rate"].apply(fmt_cvr_lift)
    formatted[LABEL_CPS] = formatted[LABEL_CPS].apply(fmt_cps)
    render_glossary_dataframe(formatted, use_container_width=True)


def _render_split_ci_plots(win_prob_df: pd.DataFrame, metric: str, compare_on: str) -> None:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return

    if compare_on == "conversion_rate":
        y_vals = sub["conversion_rate"]
        y_label = "Conversion Rate"
        is_percentage = True
    elif compare_on == "conversions":
        y_vals = sub["conversions"]
        y_label = "Conversions"
        is_percentage = False
    elif compare_on == "reach":
        y_vals = sub["users"]
        y_label = "Reach"
        is_percentage = False
    else:
        y_vals = sub["impressions"]
        y_label = "Impressions"
        is_percentage = False

    sub["ci_low"] = sub["ci_low"].fillna(y_vals)
    sub["ci_high"] = sub["ci_high"].fillna(y_vals)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.errorbar(
        x=sub["cell"],
        y=y_vals,
        yerr=[y_vals - sub["ci_low"], sub["ci_high"] - y_vals],
        fmt="o",
        ecolor="#7ED957",
        capsize=5,
        capthick=2,
    )
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_ylim(sub["ci_low"].min() * 0.95, sub["ci_high"].max() * 1.05)
    if is_percentage:
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
    plt.title(f"{metric} — Confidence Intervals", fontsize=14)
    apply_dark_axes(ax, zero_line=False)
    st.pyplot(fig)
    cache_and_download_figure(
        fig,
        key=f"split_ci_{slugify(metric)}_{compare_on}",
        filename_prefix=f"Split_CI_{slugify(metric)}",
    )


def _render_distribution_analysis(
    *,
    win_prob_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    metric: str,
    compare_on: str,
    n_sims: int,
) -> None:
    section_anchor(
        metric_anchor(metric, "distribution-uncertainty"),
        "Distribution & Uncertainty Analysis",
        caption=f"Frequentist confidence intervals and posterior density plots for {metric}.",
    )
    render_callout(
        f"**Winning Probability is built from {n_sims:,} Monte Carlo simulations** per cell "
        f"with ROPE-aware tie-breaking on **{compare_on.replace('_', ' ')}**.",
        tone="info",
    )

    with st.expander("Confidence intervals", expanded=False):
        st.markdown('<div id="confidence-intervals"></div>', unsafe_allow_html=True)
        st.caption("Uncertainty bands for the selected comparison metric by cell.")
        _render_split_ci_plots(win_prob_df, metric, compare_on)

    density_rows = []
    for _, row in samples_df[samples_df["metric"] == metric].iterrows():
        s = np.asarray(row.get("metric_samples", []))
        if s.size <= 1:
            s = np.repeat(s, n_sims) if s.size == 1 else np.full(n_sims, 0)
            s = s + np.random.normal(0, 0.01 * max(float(np.max(s)), 1), size=n_sims)
        density_rows.append(pd.DataFrame({
            "analysis_date": row["analysis_date"],
            "cell": row["cell"],
            "metric": row["metric"],
            "metric_samples": list(s),
        }))

    with st.expander("Interactive density plots", expanded=False):
        st.markdown('<div id="interactive-density-plots"></div>', unsafe_allow_html=True)
        if not density_rows:
            st.caption("No simulation samples for this metric.")
        else:
            density_plot_df = pd.concat(density_rows, ignore_index=True)
            render_interactive_density(
                density_plot_df,
                metric,
                "metric_samples",
                compare_on.replace("_", " ").title(),
                as_percent=compare_on == "conversion_rate",
            )

    with st.expander("Static density plots (export-ready)", expanded=False):
        st.markdown('<div id="static-density-plots"></div>', unsafe_allow_html=True)
        if not density_rows:
            st.caption("No simulation samples for this metric.")
        else:
            density_df = pd.concat(density_rows, ignore_index=True)
            sns.set_context("talk")
            sns.set_style("darkgrid")
            fig, ax = plt.subplots(figsize=(10, 4))
            for cell in density_df["cell"].unique():
                vals = density_df[density_df["cell"] == cell]["metric_samples"].explode()
                sns.kdeplot(vals, ax=ax, shade=True, label=cell)
            ax.set_xlabel(compare_on.replace("_", " ").title())
            if compare_on == "conversion_rate":
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
            apply_dark_axes(ax, zero_line=True)
            ax.legend(title="Cells")
            plt.title(f"{metric} — Density Plot", fontsize=15)
            st.pyplot(fig)
            cache_and_download_figure(
                fig,
                key=f"split_density_{slugify(metric)}",
                filename_prefix=f"Split_Density_{slugify(metric)}",
            )


def _render_advanced_analysis(
    *,
    metric: str,
    pairwise_by_metric,
    overlap_by_metric,
    compare_on_label: str,
) -> None:
    section_anchor(
        metric_anchor(metric, "advanced-analysis"),
        "Advanced Analysis",
        caption="Head-to-head comparisons and posterior overlap for this conversion metric.",
    )

    if metric in pairwise_by_metric:
        with st.expander("Pairwise Win Matrix", expanded=False):
            st.markdown(
                f'<div id="{metric_anchor(metric, "pairwise-win-matrix")}"></div>',
                unsafe_allow_html=True,
            )
            st.caption("Head-to-head Winning Probability between each pair of cells.")
            render_pairwise_heatmap(pairwise_by_metric[metric], metric, compare_on_label)

    if metric in overlap_by_metric and not overlap_by_metric[metric].empty:
        with st.expander("Posterior Overlap", expanded=False):
            st.markdown(
                f'<div id="{metric_anchor(metric, "posterior-overlap")}"></div>',
                unsafe_allow_html=True,
            )
            overlap = overlap_by_metric[metric].copy()
            overlap = overlap.rename(columns={
                "p_a_beats_b": "P(A beats B)",
                "p_b_beats_a": "P(B beats A)",
                "p_similar_cvr": "P(similar CVR)",
            })
            render_glossary_dataframe(overlap, use_container_width=True)


def _render_export_section(
    *,
    test_name: str,
    to_view: pd.DataFrame,
    summary_table: pd.DataFrame,
    compare_on_label: str,
    ai_summary: Optional[str] = None,
) -> None:
    section_anchor(
        "export-readout-pack",
        "Export Readout Pack",
        caption="Download a stakeholder-ready summary across all conversion metrics.",
    )
    formatted = format_split_summary(to_view.copy())
    cache_csv(summary_table, "split_results_csv")
    extra_sections = {"Compare on": compare_on_label}

    col_html, col_pdf, col_csv = st.columns(3)
    if ai_summary:
        st.caption("The applied AI summary will be included in HTML and PDF exports.")
    html_bytes = build_readout_html(
        test_name,
        formatted,
        ai_summary=ai_summary,
        extra_sections=extra_sections,
        charts=[],
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
                ai_summary=ai_summary,
                extra_sections=extra_sections,
                charts=[],
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
            data=st.session_state["split_results_csv"],
            file_name="split_winning_prob.csv",
            mime="text/csv",
            use_container_width=True,
        )


def _render_metric_results(
    *,
    metric: str,
    results: pd.DataFrame,
    win_prob_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    pairwise_by_metric,
    overlap_by_metric,
    compare_on: str,
    compare_on_label: str,
    n_sims: int,
) -> None:
    st.markdown(f'<div id="{slugify(metric)}"></div>', unsafe_allow_html=True)

    section_anchor(
        metric_anchor(metric, "executive-summary"),
        "Executive Summary",
        caption="Start here: recommendation, KPIs, and per-cell takeaways.",
    )
    render_split_executive_dashboard(
        win_prob_df,
        metric,
        compare_on_label,
        skip_header=True,
    )

    _render_per_cell_table(results, metric)

    section_anchor(
        metric_anchor(metric, "multi-metric-rankings"),
        "Multi-Metric Rankings",
        caption="How each cell ranks on Winning Probability, CPS, CVR, conversions, and reach.",
    )
    rank_df = build_split_multi_metric_rankings(win_prob_df, metric)
    if not rank_df.empty:
        render_bump_chart(rank_df, metric)

    section_anchor(
        metric_anchor(metric, "cell-comparison"),
        "Cell Comparison",
        caption="Normalized view of how cells compare across key performance dimensions.",
    )
    render_split_radar_chart(win_prob_df, metric)

    _render_distribution_analysis(
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        metric=metric,
        compare_on=compare_on,
        n_sims=n_sims,
    )

    _render_advanced_analysis(
        metric=metric,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        compare_on_label=compare_on_label,
    )


def render_split_results(
    *,
    test_name: str,
    results: pd.DataFrame,
    win_prob_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    pairwise_by_metric,
    overlap_by_metric,
    compare_on: str,
    compare_on_label: str,
    n_sims: int,
    selected_metric: str,
    summary_context,
    render_ai_summary_fn,
) -> None:
    summary_table, to_view = _build_summary_views(win_prob_df, compare_on)

    section_anchor(
        slugify(selected_metric),
        selected_metric,
        caption="Stakeholder readout for the selected conversion metric.",
        level="subheader",
    )
    _render_metric_results(
        metric=selected_metric,
        results=results,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        compare_on=compare_on,
        compare_on_label=compare_on_label,
        n_sims=n_sims,
    )

    st.markdown("---")
    section_anchor(
        "full-test-summary",
        "Full Test Summary",
        caption="Results, AI summary, and readout export across all conversion metrics in this test.",
        level="subheader",
    )
    section_anchor(
        "winning-probability-summary",
        "Winning Probability & CPS by Cell",
        caption="Full results table across all conversion metrics.",
        glossary_term="Winning Probability",
    )
    render_glossary_dataframe(format_split_summary(to_view), use_container_width=True)

    render_ai_summary_fn(summary_context, session_namespace="split")

    _render_export_section(
        test_name=test_name,
        to_view=to_view,
        summary_table=summary_table,
        compare_on_label=compare_on_label,
        ai_summary=get_applied_ai_summary_for_export(summary_context, "split"),
    )
