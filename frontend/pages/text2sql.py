from pathlib import Path
import sys


def _bootstrap_project_root() -> None:
    project_root = str(Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_bootstrap_project_root()
import frontend.bootstrap  # noqa: E402,F401

from frontend.components.api_client import get_client
from frontend.components.streamlit_compat import st
from frontend.components.theme import apply_theme, card_grid, hero


ENGINE_OPTIONS = {
    "Hive": "hive",
    "Spark SQL": "spark_sql",
    "MySQL": "mysql",
    "ClickHouse": "clickhouse",
}


def render() -> None:
    apply_theme()
    hero("自然语言生成 SQL", "把中文业务需求转换为可审查、可复制、可优化的 SQL。")
    card_grid(
        [
            ("多引擎支持", "覆盖 Hive、Spark SQL、MySQL 和 ClickHouse。"),
            ("表结构上下文", "输入字段、分区和口径，生成更贴近生产的 SQL。"),
            ("优化建议", "输出解释、校验结果和性能优化方向。"),
        ]
    )

    left, right = st.columns([1, 1])
    with left:
        question = st.text_area("业务需求", value="统计最近7天活跃用户数", height=120)
        schema_context = st.text_area(
            "表结构上下文",
            value=(
                "user_info(user_id bigint, register_time timestamp, province string)\n"
                "order_info(order_id bigint, user_id bigint, amount decimal(18,2), create_time timestamp)"
            ),
            height=220,
        )
        engine_label = st.selectbox("SQL 引擎", list(ENGINE_OPTIONS.keys()))
        use_rag = st.checkbox("使用知识库上下文", value=False)

    with right:
        if st.button("生成 SQL", type="primary"):
            try:
                result = get_client().text2sql(
                    question,
                    ENGINE_OPTIONS[engine_label],
                    schema_context,
                    use_rag=use_rag,
                )
                st.subheader("生成 SQL")
                st.code(result.get("sql", ""), language="sql")
                st.download_button("下载 SQL", result.get("sql", ""), file_name="query.sql")
                st.subheader("生成说明")
                st.write(result.get("explanation", ""))
                st.subheader("校验结果")
                st.json(result.get("validation", {}))
                st.subheader("优化建议")
                for suggestion in result.get("optimization_suggestions", []):
                    st.write(f"- {suggestion}")
            except Exception as exc:
                st.error(f"Text2SQL 失败：{exc}")


if __name__ == "__main__":
    render()
