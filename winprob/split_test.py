"""Split test workflow with wizard UI."""

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from winprob.dashboard import render_test_banner
from winprob.glossary import (
    CONFIGURE_NAV,
    RESULTS_FULL_ANALYSIS_NAV,
    UPLOAD_NAV,
    inject_navigation_styles,
    render_main_glossary_cards,
    render_sidebar_nav,
    section_anchor,
)
from winprob.llm_summary import build_split_summary_context
from winprob.sample_data import (
    get_sample_split_df,
    get_split_input_template_df,
)
from winprob.session_reset import clear_app_session_state
from winprob.split_analytics import generate_split_talking_points
from winprob.split_results_views import render_split_results
from winprob.split_simulation import (
    COMPARE_ON_OPTIONS,
    build_split_results,
    run_split_simulation,
)
from winprob.ui import render_ai_summary_section
from winprob.ui_styles import render_scenario_pills
from winprob.validation import validate_split_input
from winprob.wizard import init_wizard, next_step, prev_step, render_wizard_progress, set_step


def _standardize_df(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["analysis_date"] = datetime.now().strftime("%Y-%m-%d")
    df["conversion_segment"] = df["event_type"]
    df["experiment_cost_usd"] = df["spend_usd"]
    df["treatment_user_count"] = df["n_test"]
    df["treatment_conversions"] = df["test_conversions"]
    df["study_name"] = df["cell_name"]
    df["cps"] = pd.to_numeric(df["CPS"], errors="coerce")
    df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce")
    if "test_conv_rate" in df.columns:
        df["test_conv_rate"] = pd.to_numeric(df["test_conv_rate"], errors="coerce")
    return df


def _render_sidebar_config(
    namespace: str,
    *,
    nav_sections=None,
    full_analysis_nav=None,
    metrics=None,
):
    selected_metric = None
    with st.sidebar:
        st.header("Scenario Settings")
        compare_on = st.selectbox(
            "Compare on",
            options=list(COMPARE_ON_OPTIONS.keys()),
            format_func=lambda k: COMPARE_ON_OPTIONS[k],
            key=f"{namespace}_compare_on",
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

    render_sidebar_nav(
        nav_sections=nav_sections,
        full_analysis_nav=full_analysis_nav,
        metrics=metrics,
        selected_metric=selected_metric,
    )
    return compare_on, n_sims, selected_metric


def run_split_test_app():
    namespace = "split"
    init_wizard(namespace)
    inject_navigation_styles()
    step = render_wizard_progress(namespace)

    st.header("Split Test (A/B/C, no control)")

    if step == 0:
        compare_on, n_sims, _ = _render_sidebar_config(namespace, nav_sections=UPLOAD_NAV)
        section_anchor("upload-validate", "Upload & Validate")

        col_a, col_b = st.columns(2)
        with col_a:
            use_sample = st.button("Try with sample data", use_container_width=True)
        with col_b:
            template_df = get_split_input_template_df()
            template_buf = BytesIO()
            template_df.to_excel(template_buf, index=False)
            st.download_button(
                "Download input template",
                data=template_buf.getvalue(),
                file_name="winprob_split_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        input_file = st.file_uploader("Upload test data (CSV or Excel)", type=["csv", "xlsx"])
        sample_mode_key = f"{namespace}_sample_mode"
        raw = None
        if use_sample:
            st.session_state[sample_mode_key] = True
            st.session_state[f"{namespace}_test_name"] = "Sample Split Test"
            raw = get_sample_split_df()
        elif input_file is not None:
            st.session_state[sample_mode_key] = False
            st.session_state[f"{namespace}_test_name"] = input_file.name.rsplit(".", 1)[0]
            if input_file.name.endswith(".xlsx"):
                raw = pd.read_excel(input_file)
            else:
                raw = pd.read_csv(input_file)
        elif st.session_state.get(sample_mode_key):
            raw = get_sample_split_df()

        validation = None
        if raw is not None:
            validation = validate_split_input(raw)
            section_anchor("input-validation", "Input validation")
            for check in validation["checks"]:
                icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}.get(check["status"], "•")
                st.markdown(f"{icon} **{check['check']}** — {check['detail']}")
            st.dataframe(validation["preview"], use_container_width=True)

            if validation["is_valid"]:
                st.session_state[f"{namespace}_raw"] = validation["cleaned_df"]
            else:
                st.session_state.pop(f"{namespace}_raw", None)

        ready_to_configure = st.session_state.get(f"{namespace}_raw") is not None
        if ready_to_configure and validation is not None and validation["is_valid"]:
            st.success(f"Validated {validation['row_count']} rows.")
        elif validation is not None and not validation["is_valid"]:
            st.error("Fix validation issues before continuing.")

        if ready_to_configure:
            if st.button("Next: Configure", type="primary", key=f"{namespace}_next_configure"):
                next_step(namespace)
                st.rerun()

        st.markdown('<div id="column-reference"></div>', unsafe_allow_html=True)
        with st.expander("Input column glossary"):
            st.caption("Hover the ⓘ icon on any term for its definition.")
            render_main_glossary_cards("split_upload")
            st.markdown("**Optional columns:** `test_conv_rate` (derived from conversions / reach when blank)")
        return

    if step == 1:
        compare_on, n_sims, _ = _render_sidebar_config(namespace, nav_sections=CONFIGURE_NAV)
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

        render_scenario_pills(COMPARE_ON_OPTIONS[compare_on])
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

    raw = st.session_state.get(f"{namespace}_raw")
    conversion_metrics = st.session_state.get(f"{namespace}_conversion_metrics", [])
    if raw is None or not conversion_metrics:
        set_step(namespace, 0)
        st.rerun()

    df = _standardize_df(raw)
    df = df[df["conversion_segment"].isin(conversion_metrics)]
    test_name = st.session_state.get(f"{namespace}_test_name", "Test")

    compare_on, n_sims, selected_metric = _render_sidebar_config(
        namespace,
        full_analysis_nav=RESULTS_FULL_ANALYSIS_NAV,
        metrics=sorted(conversion_metrics),
    )
    compare_on_label = COMPARE_ON_OPTIONS[compare_on]

    per_cell = df.groupby("cell_name")[["experiment_cost_usd", "n_test"]].mean()
    render_test_banner(
        test_name,
        n_cells=per_cell.shape[0],
        total_spend=per_cell["experiment_cost_usd"].sum(),
        total_reach=int(per_cell["n_test"].sum()),
    )

    metrics_df = df[[
        "analysis_date", "study_name", "treatment_user_count", "treatment_conversions",
        "experiment_cost_usd", "cps", "conversion_segment", "impressions",
    ]]
    results = build_split_results(metrics_df)

    win_prob_df, samples_df, pairwise_by_metric, overlap_by_metric = run_split_simulation(
        results,
        n_sims=n_sims,
        compare_on=compare_on,
    )

    summary_context = build_split_summary_context(
        test_name=test_name,
        compare_on=compare_on,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
    )

    talking_points = {}
    for metric in win_prob_df["metric"].unique():
        talking_points.update(generate_split_talking_points(win_prob_df, metric))

    render_split_results(
        test_name=test_name,
        results=results,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        pairwise_by_metric=pairwise_by_metric,
        overlap_by_metric=overlap_by_metric,
        compare_on=compare_on,
        compare_on_label=compare_on_label,
        n_sims=n_sims,
        selected_metric=selected_metric or sorted(conversion_metrics)[0],
        summary_context=summary_context,
        render_ai_summary_fn=lambda ctx, session_namespace: render_ai_summary_section(
            ctx, session_namespace, talking_points=talking_points
        ),
    )

    if st.button("Start over"):
        clear_app_session_state()
        st.rerun()
