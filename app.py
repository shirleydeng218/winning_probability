"""Run with: streamlit run app.py"""

import streamlit as st

st.set_page_config(
    page_title="WinProb: Media Test Evaluator",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

from winprob.main import run

run()
