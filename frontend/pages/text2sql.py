from frontend.components.api_client import get_client
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


ENGINE_OPTIONS = {
    "Hive": "hive",
    "Spark SQL": "spark_sql",
    "MySQL": "mysql",
    "ClickHouse": "clickhouse",
}


def render() -> None:
    st.set_page_config(page_title="Text2SQL", page_icon="DC", layout="wide")
    render_sidebar()
    st.title("Text2SQL")

    left, right = st.columns([1, 1])
    with left:
        question = st.text_area("Business Requirement", value="统计最近7天活跃用户数", height=120)
        schema_context = st.text_area(
            "Schema Context",
            value=(
                "user_info(user_id bigint, register_time timestamp, province string)\n"
                "order_info(order_id bigint, user_id bigint, amount decimal(18,2), create_time timestamp)"
            ),
            height=220,
        )
        engine_label = st.selectbox("Engine", list(ENGINE_OPTIONS.keys()))
        use_rag = st.checkbox("Use RAG context", value=False)

    with right:
        if st.button("Generate SQL", type="primary"):
            try:
                result = get_client().text2sql(
                    question,
                    ENGINE_OPTIONS[engine_label],
                    schema_context,
                    use_rag=use_rag,
                )
                st.subheader("Generated SQL")
                st.code(result.get("sql", ""), language="sql")
                st.download_button("Copy SQL", result.get("sql", ""), file_name="query.sql")
                st.subheader("Explanation")
                st.write(result.get("explanation", ""))
                st.subheader("Validation")
                st.json(result.get("validation", {}))
                st.subheader("Optimization Suggestions")
                for suggestion in result.get("optimization_suggestions", []):
                    st.write(f"- {suggestion}")
            except Exception as exc:
                st.error(f"Text2SQL failed: {exc}")


if __name__ == "__main__":
    render()
