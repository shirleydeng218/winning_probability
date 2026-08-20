"""WinProb Streamlit application entrypoint."""

import streamlit as st

from winprob.config import configure_plot_theme
from winprob.glossary import inject_navigation_styles, render_sidebar_glossary
from winprob.incrementality import run_incrementality_app
from winprob.intro import render_app_intro
from winprob.split_test import run_split_test_app
from winprob.ui_styles import render_app_header


def run() -> None:
    configure_plot_theme()
    inject_navigation_styles()
    render_app_header()

    st.title("WinProb: Media Test Evaluator")

    render_app_intro()

    test_type = st.radio(
        "Select your test type",
        [
            "Incrementality test (Treatment vs Control)",
            "Split test (A/B/C without control)",
        ],
        index=None,
        horizontal=True,
    )

    if test_type is None:
        render_sidebar_glossary(context="home")
        st.markdown(
            '<p class="winprob-section-caption">Choose an incrementality or split test flow to begin.</p>',
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown("---")

    if test_type == "Incrementality test (Treatment vs Control)":
        run_incrementality_app()
    elif test_type == "Split test (A/B/C without control)":
        run_split_test_app()
