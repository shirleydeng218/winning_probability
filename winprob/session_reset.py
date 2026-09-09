"""Reset app session state and cached results."""

import streamlit as st


def clear_app_session_state() -> None:
    """Clear workflow state, exports, AI summaries, and Streamlit caches."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()


def render_sidebar_restart() -> None:
    """Sidebar control to restart the app from any step."""
    with st.sidebar:
        if st.button(
            "Restart app",
            type="secondary",
            use_container_width=True,
            key="winprob_restart_app",
            help="Clear cached results and return to the starting screen.",
        ):
            clear_app_session_state()
            st.rerun()
        st.caption("Clear cache and return to the home screen.")
        st.markdown("---")
