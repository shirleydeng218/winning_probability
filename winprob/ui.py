"""Shared Streamlit UI components."""

import os
import re

import streamlit as st

from winprob.glossary import section_anchor
from winprob.llm_summary import (
    build_manual_prompt_text,
    context_cache_key,
    generate_analysis_summary,
    prepare_manual_summary,
)


def _render_recommended_winner_body(body: str) -> None:
    """Render each conversion metric block with a visible divider between them."""
    parts = [part.strip() for part in re.split(r"\n---\n", body.strip()) if part.strip()]
    if len(parts) <= 1:
        parts = [
            part.strip()
            for part in re.split(r"(?=\*\*Conversion metric:\*\*)", body.strip())
            if part.strip()
        ]
    for index, part in enumerate(parts):
        if index > 0:
            st.divider()
        st.markdown(part)


def _render_structured_summary(summary_text: str) -> None:
    sections = re.split(r"\n(?=## )", summary_text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if section.startswith("## "):
            title, _, body = section.partition("\n")
            title = title.replace("## ", "")
            with st.expander(title, expanded=True):
                if title == "Recommended Winner":
                    _render_recommended_winner_body(body.strip())
                else:
                    st.markdown(body.strip())
        else:
            st.markdown(section)


def _render_summary_source_banner(source: str) -> None:
    if source == "azure_openai":
        st.success("Generated with Azure OpenAI.")
    elif source == "manual_paste":
        st.success("Showing pasted GPT summary.")
    elif source == "rule_based_fallback":
        st.warning("LLM call failed. Showing rule-based fallback summary.")
    else:
        st.info("Showing rule-based summary.")


def _clear_ai_summary_state(session_namespace: str) -> None:
    for suffix in (
        "_ai_summary",
        "_ai_summary_cache_key",
        "_ai_audience_cache",
        "_ai_summary_mode_cache",
        "_ai_manual_draft",
    ):
        st.session_state.pop(f"{session_namespace}{suffix}", None)


def _render_automatic_ai_summary(
    *,
    context,
    session_namespace: str,
    audience: str,
    cache_key: str,
    talking_points,
) -> None:
    llm_configured = bool(
        os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    if llm_configured:
        st.info("Azure OpenAI is configured.")
    else:
        st.warning(
            "Azure OpenAI is not configured. **Generate AI Summary** will use the "
            "rule-based fallback, or switch to **Manual** to paste a GPT response."
        )

    summary_state_key = f"{session_namespace}_ai_summary"
    summary_cache_key = f"{session_namespace}_ai_summary_cache_key"
    audience_cache_key = f"{session_namespace}_ai_audience_cache"
    mode_cache_key = f"{session_namespace}_ai_summary_mode_cache"

    col_generate, col_clear = st.columns([1, 1])
    with col_generate:
        generate_clicked = st.button("Generate AI Summary", key=f"{session_namespace}_generate_ai_summary")
    with col_clear:
        clear_clicked = st.button("Clear Summary", key=f"{session_namespace}_clear_ai_summary_auto")

    if clear_clicked:
        _clear_ai_summary_state(session_namespace)

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
            st.session_state[mode_cache_key] = "automatic"

    _render_stored_summary(
        session_namespace=session_namespace,
        cache_key=cache_key,
        audience=audience,
        mode="automatic",
    )


def _render_manual_ai_summary(
    *,
    context,
    session_namespace: str,
    audience: str,
    cache_key: str,
) -> None:
    st.info(
        "Copy the prompt below into ChatGPT (or another approved GPT tool), then paste "
        "the markdown response back here. No Azure API key is required in the app."
    )

    prompt_text = build_manual_prompt_text(context, audience=audience)
    test_name = context.get("test_name", "test").replace(" ", "_")
    st.download_button(
        "Download GPT prompt (.txt)",
        data=prompt_text.encode("utf-8"),
        file_name=f"{test_name}_ai_summary_prompt.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("Preview prompt", expanded=False):
        st.text_area(
            "Prompt to paste into ChatGPT",
            value=prompt_text,
            height=320,
            key=f"{session_namespace}_ai_manual_prompt_preview",
            label_visibility="collapsed",
        )

    pasted_summary = st.text_area(
        "Paste GPT response (markdown)",
        height=280,
        key=f"{session_namespace}_ai_manual_draft",
        placeholder="Paste the markdown summary returned by ChatGPT here…",
    )

    col_apply, col_clear = st.columns([1, 1])
    with col_apply:
        apply_clicked = st.button(
            "Apply pasted summary",
            type="primary",
            key=f"{session_namespace}_apply_manual_summary",
        )
    with col_clear:
        clear_clicked = st.button("Clear Summary", key=f"{session_namespace}_clear_ai_summary_manual")

    summary_state_key = f"{session_namespace}_ai_summary"
    summary_cache_key = f"{session_namespace}_ai_summary_cache_key"
    audience_cache_key = f"{session_namespace}_ai_audience_cache"
    mode_cache_key = f"{session_namespace}_ai_summary_mode_cache"

    if clear_clicked:
        _clear_ai_summary_state(session_namespace)

    if apply_clicked:
        try:
            result = prepare_manual_summary(pasted_summary, context, audience=audience)
            st.session_state[summary_state_key] = result
            st.session_state[summary_cache_key] = cache_key
            st.session_state[audience_cache_key] = audience
            st.session_state[mode_cache_key] = "manual"
        except ValueError as exc:
            st.error(str(exc))

    _render_stored_summary(
        session_namespace=session_namespace,
        cache_key=cache_key,
        audience=audience,
        mode="manual",
    )


def _render_stored_summary(
    *,
    session_namespace: str,
    cache_key: str,
    audience: str,
    mode: str,
) -> None:
    summary_state_key = f"{session_namespace}_ai_summary"
    summary_cache_key = f"{session_namespace}_ai_summary_cache_key"
    audience_cache_key = f"{session_namespace}_ai_audience_cache"
    mode_cache_key = f"{session_namespace}_ai_summary_mode_cache"

    stored_result = st.session_state.get(summary_state_key)
    stored_cache_key = st.session_state.get(summary_cache_key)
    stored_audience = st.session_state.get(audience_cache_key)
    stored_mode = st.session_state.get(mode_cache_key)

    if (
        stored_result
        and stored_cache_key == cache_key
        and stored_audience == audience
        and stored_mode == mode
    ):
        _render_summary_source_banner(stored_result.get("source", "unknown"))
        _render_structured_summary(stored_result["summary"])
    elif stored_result and (
        stored_cache_key != cache_key
        or stored_audience != audience
        or stored_mode != mode
    ):
        st.info("Inputs, audience, or generation mode changed. Refresh the summary to update.")


def render_ai_summary_section(context, session_namespace, talking_points=None):
    section_anchor(
        "ai-summary",
        "AI Summary",
        caption="Summarizes the full test across all conversion metrics and cells.",
    )

    audience = st.radio(
        "Summary audience",
        options=["marketer", "analyst"],
        format_func=lambda x: "Explain like I'm a marketer" if x == "marketer" else "Explain like I'm an analyst",
        horizontal=True,
        key=f"{session_namespace}_ai_audience",
    )

    summary_mode = st.radio(
        "Summary generation",
        options=["manual", "automatic"],
        format_func=lambda x: (
            "Manual — copy prompt to ChatGPT"
            if x == "manual"
            else "Automatic — Azure OpenAI (legacy)"
        ),
        horizontal=True,
        key=f"{session_namespace}_ai_summary_mode",
        index=0,
    )

    st.caption(
        "Structured executive summary with winner, CPiS/CPS, significance, CI, and density interpretations."
    )

    cache_key = context_cache_key(context)

    if summary_mode == "manual":
        _render_manual_ai_summary(
            context=context,
            session_namespace=session_namespace,
            audience=audience,
            cache_key=cache_key,
        )
    else:
        _render_automatic_ai_summary(
            context=context,
            session_namespace=session_namespace,
            audience=audience,
            cache_key=cache_key,
            talking_points=talking_points,
        )
