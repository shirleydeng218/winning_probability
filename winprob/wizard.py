"""Multi-step wizard helpers."""

import streamlit as st

from winprob.ui_styles import render_wizard_steps

WIZARD_STEPS = ["Upload & Validate", "Configure", "Results & Export"]


def init_wizard(namespace: str) -> None:
    key = f"{namespace}_wizard_step"
    if key not in st.session_state:
        st.session_state[key] = 0


def render_wizard_progress(namespace: str) -> int:
    step = st.session_state.get(f"{namespace}_wizard_step", 0)
    render_wizard_steps(WIZARD_STEPS, step)
    return step


def next_step(namespace: str) -> None:
    key = f"{namespace}_wizard_step"
    st.session_state[key] = min(st.session_state.get(key, 0) + 1, len(WIZARD_STEPS) - 1)


def prev_step(namespace: str) -> None:
    key = f"{namespace}_wizard_step"
    st.session_state[key] = max(st.session_state.get(key, 0) - 1, 0)


def set_step(namespace: str, step: int) -> None:
    st.session_state[f"{namespace}_wizard_step"] = max(0, min(step, len(WIZARD_STEPS) - 1))
