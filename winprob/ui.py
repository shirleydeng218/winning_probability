"""Shared Streamlit UI components."""

import os
import re

import streamlit as st

from winprob.llm_summary import context_cache_key, generate_analysis_summary


def _render_structured_summary(summary_text: str) -> None:
    sections = re.split(r"\n(?=## )", summary_text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if section.startswith("## "):
            title, _, body = section.partition("\n")
            with st.expander(title.replace("## ", ""), expanded=True):
                st.markdown(body.strip())
        else:
            st.markdown(section)


def render_ai_summary_section(context, session_namespace, talking_points=None):
    st.markdown("---")
    st.markdown('<div id="ai-summary"></div>', unsafe_allow_html=True)
    st.subheader("AI Summary")

    audience = st.radio(
        "Summary audience",
        options=["marketer", "analyst"],
        format_func=lambda x: "Explain like I'm a marketer" if x == "marketer" else "Explain like I'm an analyst",
        horizontal=True,
        key=f"{session_namespace}_ai_audience",
    )

    st.caption(
        "Generates a structured executive summary with winner, CPiS/CPS, significance, CI, and density interpretations."
    )

    llm_configured = bool(
        os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    if llm_configured:
        st.info("Azure OpenAI is configured.")
    else:
        st.warning("Azure OpenAI is not configured. A rule-based fallback summary will be used.")

    cache_key = context_cache_key(context)
    summary_state_key = f"{session_namespace}_ai_summary"
    summary_cache_key = f"{session_namespace}_ai_summary_cache_key"
    audience_cache_key = f"{session_namespace}_ai_audience_cache"

    col_generate, col_clear = st.columns([1, 1])
    with col_generate:
        generate_clicked = st.button("Generate AI Summary", key=f"{session_namespace}_generate_ai_summary")
    with col_clear:
        clear_clicked = st.button("Clear Summary", key=f"{session_namespace}_clear_ai_summary")

    if clear_clicked:
        st.session_state.pop(summary_state_key, None)
        st.session_state.pop(summary_cache_key, None)
        st.session_state.pop(audience_cache_key, None)

    if generate_clicked:
        with st.spinner("Generating summary..."):
            result = generate_analysis_summary(
                context,
                use_llm=llm_configured,
                audience=audience,
                talking_points=talking_points,
            )
            st.session_state[summary_state_key] = result
            st.session_state[summary_cache_key] = cache_key
            st.session_state[audience_cache_key] = audience

    stored_result = st.session_state.get(summary_state_key)
    stored_cache_key = st.session_state.get(summary_cache_key)
    stored_audience = st.session_state.get(audience_cache_key)
    if stored_result and stored_cache_key == cache_key and stored_audience == audience:
        source = stored_result.get("source", "unknown")
        if source == "azure_openai":
            st.success("Generated with Azure OpenAI.")
        elif source == "rule_based_fallback":
            st.warning("LLM call failed. Showing rule-based fallback summary.")
        else:
            st.info("Showing rule-based summary.")
        _render_structured_summary(stored_result["summary"])
    elif stored_result and (stored_cache_key != cache_key or stored_audience != audience):
        st.info("Inputs or audience changed. Click **Generate AI Summary** to refresh.")
