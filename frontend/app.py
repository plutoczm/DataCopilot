from pathlib import Path
import sys


def _bootstrap_project_root() -> None:
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_bootstrap_project_root()
import frontend.bootstrap  # noqa: E402,F401

from frontend.components.api_client import get_client
from frontend.components.streamlit_compat import st
from frontend.components.theme import apply_theme, card_grid, hero, status_badge
from frontend.pages import chat, knowledge_base, sql_review, text2sql, warehouse_design


def render() -> None:
    st.set_page_config(
        page_title="DataPilot-AI 数据工程工作台",
        page_icon="DC",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    hero(
        "数据工程 AI 工作台",
        "把知识库问答、Text2SQL、SQL 审查和数仓设计放在一个可演示、可扩展的智能平台里。",
    )

    try:
        health = get_client().health()
        status = health.get("status", "unknown")
        environment = health.get("environment", "-")
        vector_store = health.get("vector_store", {})
        llm_provider = health.get("llm_provider", {})
        st.subheader("系统状态")
        status_badge("后端服务正常" if status == "ok" else f"后端状态：{status}")
        col1, col2, col3 = st.columns(3)
        col1.metric("服务", health.get("service", "DataPilot-AI"))
        col2.metric("运行环境", environment)
        col3.metric("知识块", vector_store.get("document_count", 0))
        st.caption(
            "LLM: "
            f"{llm_provider.get('provider', '-')}"
            " | 模型: "
            f"{llm_provider.get('model', '-')}"
        )
    except Exception as exc:
        st.error(f"后端健康检查失败：{exc}")

    st.subheader("工作区")
    card_grid(
        [
            ("智能问答", "自动识别意图，路由到知识库、SQL 生成、SQL 审查或数仓设计。"),
            ("知识库", "上传技术文档，构建可引用的 RAG 问答能力。"),
            ("Text2SQL", "把中文业务口径转成 Hive、Spark SQL、MySQL 或 ClickHouse 查询。"),
            ("SQL 审查", "识别性能风险、规范问题和优化建议。"),
            ("数仓设计", "生成 ODS、DWD、DWS、ADS 分层方案、指标和 DDL。"),
        ]
    )


def main() -> None:
    pages = [
        st.Page(render, title="首页", icon=":material/dashboard:"),
        st.Page(chat.render, title="智能问答", icon=":material/forum:"),
        st.Page(knowledge_base.render, title="知识库", icon=":material/library_books:"),
        st.Page(text2sql.render, title="Text2SQL", icon=":material/code:"),
        st.Page(sql_review.render, title="SQL 审查", icon=":material/rule:"),
        st.Page(warehouse_design.render, title="数仓设计", icon=":material/schema:"),
    ]
    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()
