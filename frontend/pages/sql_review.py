from frontend.components.api_client import get_client
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


ENGINE_OPTIONS = {
    "Spark SQL": "spark",
    "Hive": "hive",
    "MySQL": "mysql",
    "ClickHouse": "clickhouse",
}


def render() -> None:
    st.set_page_config(page_title="SQL Review", page_icon="DC", layout="wide")
    render_sidebar()
    st.title("SQL Review")

    sql = st.text_area(
        "SQL",
        value="SELECT * FROM dwd_order_detail WHERE create_time >= '2026-06-01'",
        height=260,
    )
    engine_label = st.selectbox("Engine", list(ENGINE_OPTIONS.keys()))
    include_llm = st.checkbox("Include LLM explanation", value=True)

    if not st.button("Review SQL", type="primary"):
        return

    try:
        result = get_client().sql_review(
            sql,
            ENGINE_OPTIONS[engine_label],
            include_llm_explanation=include_llm,
        )
        col1, col2 = st.columns(2)
        col1.metric("Risk Level", result.get("risk_level", "-"))
        col2.metric("Score", result.get("score", 0))

        st.subheader("Issues")
        for issue in result.get("issues", []):
            with st.expander(f"{issue.get('severity')} - {issue.get('title')}"):
                st.write(issue.get("description", ""))
                st.info(issue.get("suggestion", ""))

        st.subheader("Optimization Suggestions")
        for suggestion in result.get("optimization_suggestions", []):
            st.write(f"- {suggestion}")

        st.subheader("LLM Explanation")
        st.write(result.get("llm_explanation", ""))
    except Exception as exc:
        st.error(f"SQL review failed: {exc}")


if __name__ == "__main__":
    render()
