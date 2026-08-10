"""Shared Streamlit UI components."""

import os

import streamlit as st

from winprob.llm_summary import context_cache_key, generate_analysis_summary


def render_ai_summary_section(context, session_namespace):
    st.markdown("---")
    st.subheader("AI Summary")
    st.caption(
        "Generates an executive summary of the winner, CPiS/CPS, significance, confidence intervals, "
        "and density plot implications. Configure Azure OpenAI via environment variables to enable LLM output."
    )

    llm_configured = bool(
        os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    if llm_configured:
        st.info("Azure OpenAI is configured. The summary will use the LLM when generated.")
    else:
        st.warning(
            "Azure OpenAI is not configured. A rule-based fallback summary will be used. "
            "Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` to enable LLM summaries."
        )

    cache_key = context_cache_key(context)
    summary_state_key = f"{session_namespace}_ai_summary"
    summary_cache_key = f"{session_namespace}_ai_summary_cache_key"

    col_generate, col_clear = st.columns([1, 1])
    with col_generate:
        generate_clicked = st.button("Generate AI Summary", key=f"{session_namespace}_generate_ai_summary")
    with col_clear:
        clear_clicked = st.button("Clear Summary", key=f"{session_namespace}_clear_ai_summary")

    if clear_clicked:
        st.session_state.pop(summary_state_key, None)
        st.session_state.pop(summary_cache_key, None)

    if generate_clicked:
        with st.spinner("Generating summary..."):
            result = generate_analysis_summary(context, use_llm=llm_configured)
            st.session_state[summary_state_key] = result
            st.session_state[summary_cache_key] = cache_key

    stored_result = st.session_state.get(summary_state_key)
    stored_cache_key = st.session_state.get(summary_cache_key)
    if stored_result and stored_cache_key == cache_key:
        source = stored_result.get("source", "unknown")
        if source == "azure_openai":
            st.success("Generated with Azure OpenAI.")
        elif source == "rule_based_fallback":
            st.warning("LLM call failed. Showing rule-based fallback summary.")
        else:
            st.info("Showing rule-based summary.")

        st.markdown(stored_result["summary"])
    elif stored_result and stored_cache_key != cache_key:
        st.info("Inputs changed since the last summary was generated. Click **Generate AI Summary** to refresh.")