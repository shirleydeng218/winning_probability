"""Run with: streamlit run app.py"""

import streamlit as st

from winprob.main import run

st.set_page_config(
    page_title="WinProb: Media Test Evaluator",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="expanded",
)

run()
