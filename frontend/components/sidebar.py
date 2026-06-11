from frontend.components.api_client import get_client
from frontend.components.streamlit_compat import st


NAV_ITEMS = {
    "Chat": "pages/chat.py",
    "Knowledge Base": "pages/knowledge_base.py",
    "Text2SQL": "pages/text2sql.py",
    "SQL Review": "pages/sql_review.py",
    "Warehouse Designer": "pages/warehouse_design.py",
}


def render() -> None:
    st.sidebar.title("DataPilot-AI")
    st.sidebar.caption("AI Agent Platform for Data Engineering")
    try:
        health = get_client().health()
        status = health.get("status", "unknown")
        st.sidebar.success(f"Backend: {status}")
    except Exception as exc:
        st.sidebar.error(f"Backend unavailable: {exc}")
    st.sidebar.divider()
    st.sidebar.caption("Tools")
    for label in NAV_ITEMS:
        st.sidebar.write(label)
