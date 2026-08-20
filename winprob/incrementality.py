"""Incrementality test workflow with wizard UI."""

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from scipy.stats import norm

from winprob.dashboard import render_test_banner
from winprob.formatting import fmt_threshold
from winprob.glossary import (
    CONFIGURE_NAV,
    RESULTS_FULL_ANALYSIS_NAV,
    UPLOAD_NAV,
    inject_navigation_styles,
    render_sidebar_glossary,
    section_anchor,
)
from winprob.llm_summary import build_incrementality_summary_context
from winprob.results_views import render_incrementality_results
from winprob.sample_data import get_input_template_df, get_sample_incrementality_df
from winprob.simulation import (
    WINNING_RULES,
    build_posterior_results,
    run_incrementality_simulation,
)
from winprob.ui import render_ai_summary_section
from winprob.ui_styles import render_scenario_pills
from winprob.validation import validate_incrementality_input
from winprob.wizard import init_wizard, next_step, prev_step, render_wizard_progress, set_step


def _standardize_df(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["analysis_date"] = datetime.now().strftime("%Y-%m-%d")
    df["absolute_lift"] = df["Absolute_lift"]
    df["cpis"] = pd.to_numeric(df["CPIS"], errors="coerce")
    df["conversion_segment"] = df["event_type"]
    df["experiment_cost_usd"] = df["spend_usd"]
    df["absolute_lift_confidence_level"] = df["confidence_level"]
    df["treatment_user_count"] = df["n_test"]
    df["control_user_count"] = df["n_control"]
    df["study_name"] = df["cell_name"]
    df["treatment_conversions"] = df["test_conversions"]
    df["control_conversions"] = df["control_conversions"]
    if "relative_lift" in df.columns:
        df["relative_lift"] = pd.to_numeric(df["relative_lift"], errors="coerce")
    if "absolute_lift_CI_max" in df.columns and "absolute_lift_CI_min" in df.columns \
            and df["absolute_lift_CI_max"].notnull().all() and df["absolute_lift_CI_min"].notnull().all():
        df["absolute_lift_CI_max"] = pd.to_numeric(df["absolute_lift_CI_max"])
        df["absolute_lift_CI_min"] = pd.to_numeric(df["absolute_lift_CI_min"])
        df["absolutelift_CI"] = (df["absolute_lift_CI_max"] - df["absolute_lift_CI_min"]) / 2
    else:
        df["z_score"] = norm.ppf(df["absolute_lift_confidence_level"])
        df["standard_error"] = df["absolute_lift"] / df["z_score"]
        df["absolutelift_CI"] = (df["standard_error"] * norm.ppf(0.90)).abs()
    df["absolute_lift"] = df["absolute_lift"].replace(0, 1)
    return df


def _render_sidebar_config(
    namespace: str,
    *,
    glossary_context: str = "configure",
    nav_sections=None,
    full_analysis_nav=None,
    metrics=None,
):
    selected_metric = None
    with st.sidebar:
        st.header("Scenario Settings")
        winning_rule = st.selectbox(
            "Winning rule",
            options=list(WINNING_RULES.keys()),
            format_func=lambda k: WINNING_RULES[k],
            key=f"{namespace}_winning_rule",
        )
        significance_threshold = st.slider(
            "Minimum significance to win",
            min_value=0.0,
            max_value=1.0,
            value=0.90,
            step=0.05,
            key=f"{namespace}_significance",
        )
        n_sims = st.slider(
            "Simulations",
            min_value=1000,
            max_value=50000,
            value=5000,
            step=1000,
            key=f"{namespace}_n_sims",
        )
        if metrics:
            selected_metric = st.selectbox(
                "Conversion metric",
                options=sorted(metrics),
                key=f"{namespace}_results_metric",
            )
        st.caption("Switch scenarios without re-uploading to see how the recommended winner changes.")

    render_sidebar_glossary(
        context=glossary_context,
        nav_sections=nav_sections,
        full_analysis_nav=full_analysis_nav,
        metrics=metrics,
        selected_metric=selected_metric,
    )
    return winning_rule, significance_threshold, n_sims, selected_metric


def run_incrementality_app():
    namespace = "incrementality"
    init_wizard(namespace)
    inject_navigation_styles()
    step = render_wizard_progress(namespace)

    st.header("Incrementality Test (Treatment vs. Control)")

    # ---- Step 1: Upload & Validate ----
    if step == 0:
        winning_rule, significance_threshold, n_sims, _ = _render_sidebar_config(
            namespace, glossary_context="upload", nav_sections=UPLOAD_NAV
        )
        section_anchor("upload-validate", "Upload & Validate")
        col_a, col_b = st.columns(2)
        with col_a:
            use_sample = st.button("Try with sample data", use_container_width=True)
        with col_b:
            template_df = get_input_template_df()
            template_buf = BytesIO()
            template_df.to_excel(template_buf, index=False)
            st.download_button(
                "Download input template",
                data=template_buf.getvalue(),
                file_name="winprob_incrementality_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        input_file = st.file_uploader("Upload test data (CSV or Excel)", type=["csv", "xlsx"])

        raw = None
        test_name = "Untitled Test"
        if use_sample:
            raw = get_sample_incrementality_df()
            test_name = "Sample Incrementality Test"
            st.session_state[f"{namespace}_test_name"] = test_name
        elif input_file is not None:
            test_name = input_file.name.rsplit(".", 1)[0]
            st.session_state[f"{namespace}_test_name"] = test_name
            if input_file.name.endswith(".xlsx"):
                raw = pd.read_excel(input_file)
            else:
                raw = pd.read_csv(input_file)

        if raw is not None:
            validation = validate_incrementality_input(raw)
            section_anchor("input-validation", "Input validation")
            for check in validation["checks"]:
                icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}.get(check["status"], "•")
                st.markdown(f"{icon} **{check['check']}** — {check['detail']}")
            st.dataframe(validation["preview"], use_container_width=True)

            if validation["is_valid"]:
                st.session_state[f"{namespace}_raw"] = validation["cleaned_df"]
                st.success(f"Validated {validation['row_count']} rows.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Next: Configure", type="primary"):
                        next_step(namespace)
                        st.rerun()
            else:
                st.error("Fix validation issues before continuing.")

        st.markdown(f'<div id="column-reference"></div>', unsafe_allow_html=True)
        with st.expander("Input column glossary"):
            st.markdown(
                """
                **Required (must be populated per row):**
                - `spend_usd`, `n_control`, `n_test`, `test_conversions`, `control_conversions`

                **Required columns — nulls handled automatically when possible:**
                - `Absolute_lift` — derived from `test_conv_rate` − `control_conv_rate` × `n_test` if blank
                - `CPIS` — derived as `spend_usd / Absolute_lift` if blank
                - `confidence_level` — null → `0` (cell ineligible unless threshold lowered)

                **Optional:** `relative_lift`, `test_conv_rate`, `control_conv_rate`, CI columns
                """
            )
        return

    # ---- Step 2: Configure ----
    if step == 1:
        winning_rule, significance_threshold, n_sims, _ = _render_sidebar_config(
            namespace, glossary_context="configure", nav_sections=CONFIGURE_NAV
        )
        section_anchor("configure-analysis", "Configure Analysis")
        raw = st.session_state.get(f"{namespace}_raw")
        if raw is None:
            st.warning("Upload data first.")
            set_step(namespace, 0)
            st.rerun()

        df = _standardize_df(raw)
        conversion_metrics = st.multiselect(
            "Conversion metrics to analyze",
            sorted(df["conversion_segment"].unique()),
            default=sorted(df["conversion_segment"].unique()),
        )
        st.session_state[f"{namespace}_conversion_metrics"] = conversion_metrics

        per_cell = df.groupby("cell_name")[["experiment_cost_usd", "n_test"]].mean()
        st.markdown('<div id="test-overview"></div>', unsafe_allow_html=True)
        render_test_banner(
            st.session_state.get(f"{namespace}_test_name", "Test"),
            n_cells=per_cell.shape[0],
            total_spend=per_cell["experiment_cost_usd"].sum(),
            total_reach=int(per_cell["n_test"].sum()),
        )

        render_scenario_pills(
            WINNING_RULES[winning_rule],
            fmt_threshold(significance_threshold),
        )
        st.caption(f"**{n_sims:,}** Monte Carlo simulations will run on the selected metrics.")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Back"):
                prev_step(namespace)
                st.rerun()
        with c3:
            if st.button("Run Analysis", type="primary", disabled=not conversion_metrics):
                st.session_state[f"{namespace}_run"] = True
                next_step(namespace)
                st.rerun()
        return

    # ---- Step 3: Results ----
    raw = st.session_state.get(f"{namespace}_raw")
    conversion_metrics = st.session_state.get(f"{namespace}_conversion_metrics", [])
    if raw is None or not conversion_metrics:
        set_step(namespace, 0)
        st.rerun()

    df = _standardize_df(raw)
    df = df[df["conversion_segment"].isin(conversion_metrics)]
    test_name = st.session_state.get(f"{namespace}_test_name", "Test")

    winning_rule, significance_threshold, n_sims, selected_metric = _render_sidebar_config(
        namespace,
        glossary_context="results",
        full_analysis_nav=RESULTS_FULL_ANALYSIS_NAV,
        metrics=sorted(conversion_metrics),
    )

    per_cell = df.groupby("cell_name")[["experiment_cost_usd", "n_test"]].mean()
    render_test_banner(
        test_name,
        n_cells=per_cell.shape[0],
        total_spend=per_cell["experiment_cost_usd"].sum(),
        total_reach=int(per_cell["n_test"].sum()),
    )

    useful_columns = [
        "analysis_date", "study_name", "treatment_user_count", "control_user_count",
        "treatment_conversions", "control_conversions", "experiment_cost_usd", "cpis",
        "conversion_segment", "absolute_lift_confidence_level",
    ]
    if "relative_lift" in df.columns:
        useful_columns.append("relative_lift")
    metrics_df = df[useful_columns]

    results = build_posterior_results(metrics_df)
    results["significance_eligible"] = results["conf_level"] >= significance_threshold

    win_prob_df, samples_df, pairwise_by_metric, overlap_by_metric = run_incrementality_simulation(
        results,
        n_sims=n_sims,
        significance_threshold=significance_threshold,
        winning_rule=winning_rule,
    )

    summary_context = build_incrementality_summary_context(
        test_name=test_name,
        significance_threshold=significance_threshold,
        results_df=results,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        ci_df=df,
    )

    from winprob.analytics import generate_talking_points
    talking_points = {}
    for metric in win_prob_df["metric"].unique():
        talking_points.update(
            generate_talking_points(
                win_prob_df, metric, significance_threshold, winning_rule=winning_rule
            )
        )

    render_incrementality_results(
        test_name=test_name,
        df=df,
        results=results,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        significance_threshold=significance_threshold,
        winning_rule=winning_rule,
        n_sims=n_sims,
        selected_metric=selected_metric or sorted(conversion_metrics)[0],
        summary_context=summary_context,
        render_ai_summary_fn=lambda ctx, session_namespace: render_ai_summary_section(
            ctx, session_namespace, talking_points=talking_points
        ),
    )

    if st.button("Start over"):
        for key in list(st.session_state.keys()):
            if key.startswith(f"{namespace}_"):
                del st.session_state[key]
        st.rerun()
