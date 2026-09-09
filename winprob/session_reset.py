"""Reset app session state and cached results."""

import streamlit as st

_RESTART_COUNT_KEY = "_winprob_restart_count"


def test_type_radio_key() -> str:
    """Fresh widget key after restart so test type starts unselected."""
    restart_count = st.session_state.get(_RESTART_COUNT_KEY, 0)
    return f"winprob_test_type_{restart_count}"


def clear_app_session_state() -> None:
    """Clear workflow state, exports, AI summaries, and Streamlit caches."""
    restart_count = st.session_state.get(_RESTART_COUNT_KEY, 0) + 1
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state[_RESTART_COUNT_KEY] = restart_count
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
