from frontend.components.api_client import get_client
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


def render() -> None:
    st.set_page_config(
        page_title="DataPilot-AI",
        page_icon="DC",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_style()
    render_sidebar()

    st.title("DataPilot-AI")
    st.caption("AI Agent Platform for Data Engineering")

    try:
        health = get_client().health()
        status = health.get("status", "unknown")
        environment = health.get("environment", "-")
        col1, col2, col3 = st.columns(3)
        col1.metric("Service", health.get("service", "DataPilot-AI"))
        col2.metric("Status", status)
        col3.metric("Environment", environment)
    except Exception as exc:
        st.error(f"Backend health check failed: {exc}")

    st.subheader("Workspace")
    st.write(
        "Use the sidebar pages for knowledge chat, document indexing, Text2SQL, SQL review, "
        "and warehouse design workflows."
    )


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; max-width: 1280px; }
        section[data-testid="stSidebar"] { background: #F8FAFC; border-right: 1px solid #E2E8F0; }
        div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; padding: 0.75rem; border-radius: 8px; }
        code, pre { border-radius: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render()


if __name__ == "__main__":
    main()
