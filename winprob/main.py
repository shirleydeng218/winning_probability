"""WinProb Streamlit application entrypoint."""

import streamlit as st

from winprob.config import configure_plot_theme
from winprob.incrementality import run_incrementality_app
from winprob.split_test import run_split_test_app


def render_header() -> None:
    logo_col1, logo_col2, logo_col3 = st.columns([1, 3, 1])

    with logo_col1:
        st.image("assets/disney.svg", width=120)

    with logo_col2:
        st.markdown(
            "<h2 style='text-align: center; color: #B8F2E6;'>Marketing Analytics</h2>",
            unsafe_allow_html=True,
        )

    with logo_col3:
        st.image("assets/hulu.png", width=120)

    st.markdown("---")


def run() -> None:
    configure_plot_theme()
    render_header()

    st.title("WinProb: Media Test Evaluator")

    st.markdown(
        """
This application evaluates media test performance for Disney+ and Hulu by estimating the probability
that each test cell is the top performer (winning probability). It supports both *Incrementality tests*
(with a control group) and *Split tests* (e.g., A/B/C tests without a control group) conducted with media partners.

For incrementality tests, winning probability is based on the lowest simulated CPiS among cells that meet a
minimum significance threshold and produce positive incremental conversions. Per-cell absolute CVR lift and
incremental conversions are shown alongside existing media metrics.

At the end of each analysis, an **AI Summary** section interprets the winner, CPiS/CPS, significance,
confidence intervals, and density plots. Configure Azure OpenAI via environment variables to enable
LLM-generated summaries; otherwise a rule-based fallback is used.

For additional details, please refer to [the App Documentation](https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0).
For questions or support, contact Max Wilson or Shirley Deng on the BLADE team.
        """
    )

    test_type = st.radio(
        "Please select a test type:",
        [
            "Incrementality test (Treatment vs Control)",
            "Split test (A/B/C without control)",
        ],
        index=None,
    )

    if test_type is None:
        st.info("Select a test type to continue.")
        st.stop()

    st.markdown("---")

    if test_type == "Incrementality test (Treatment vs Control)":
        run_incrementality_app()
    elif test_type == "Split test (A/B/C without control)":
        run_split_test_app()
