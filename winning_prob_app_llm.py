
import streamlit as st

st.set_page_config(
    page_title="Winning Probability App (AI Summary)",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="expanded",
)

from winprob.main import run

run()
