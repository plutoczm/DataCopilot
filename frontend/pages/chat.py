from pathlib import Path
import sys


def _bootstrap_project_root() -> None:
    project_root = str(Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_bootstrap_project_root()
import frontend.bootstrap  # noqa: E402,F401

from frontend.components.api_client import get_client
from frontend.components.chat_message import render_citations, render_message
from frontend.components.streamlit_compat import st
from frontend.components.theme import apply_theme, card_grid, hero


def render() -> None:
    apply_theme()
    hero("智能问答", "用自然语言触发 RAG、Text2SQL、SQL 审查和数仓设计，让数据工程任务从一个入口开始。")
    card_grid(
        [
            ("自动意图识别", "根据问题内容选择最合适的工具链。"),
            ("流式响应", "回答生成过程中实时展示意图和路由路径。"),
            ("结构化结果", "SQL、审查分数、引用来源和数仓层级可直接查看。"),
        ]
    )

    st.session_state.setdefault("chat_history", [])
    with st.expander("上下文设置", expanded=False):
        collection_name = st.text_input("知识库集合", value="knowledge_base")
        top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
        engine = st.selectbox("SQL 引擎", ["hive", "spark_sql", "mysql", "clickhouse"])
        schema_context = st.text_area("表结构上下文", height=120)
        use_rag = st.checkbox("专业工具启用 RAG 上下文", value=False)

    for item in st.session_state["chat_history"]:
        render_message(item["role"], item["content"])
        render_citations(item.get("citations", []))
        _render_agent_result(item.get("result"))

    prompt = st.chat_input("向 DataPilot-AI 提问，例如：统计最近7天活跃用户并检查SQL")
    if not prompt:
        return

    st.session_state["chat_history"].append({"role": "user", "content": prompt})
    render_message("user", prompt)

    answer = ""
    citations = []
    result = None
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            for event in get_client().stream_agent_chat(
                prompt,
                engine=engine,
                schema_context=schema_context or None,
                collection_name=collection_name,
                top_k=top_k,
                use_rag=use_rag,
            ):
                if event["event"] == "metadata":
                    data = event["data"]
                    st.caption(
                        "意图："
                        f"{data.get('intent', '-')}"
                        " | 路由："
                        f"{' -> '.join(data.get('routing_path', []))}"
                    )
                if event["event"] == "token":
                    answer += event["data"].get("text", "")
                    placeholder.markdown(answer)
                elif event["event"] == "result":
                    result = event["data"].get("result")
                    citations = _extract_citations(result)
            render_citations(citations)
            _render_agent_result(result)
            st.session_state["chat_history"].append(
                {
                    "role": "assistant",
                    "content": answer,
                    "citations": citations,
                    "result": result,
                }
            )
        except Exception as exc:
            st.error(f"流式问答失败：{exc}")


def _extract_citations(result):
    if not isinstance(result, dict):
        return []
    if isinstance(result.get("citations"), list):
        return result["citations"]
    if isinstance(result.get("rag"), dict):
        return result["rag"].get("citations", [])
    return []


def _render_agent_result(result) -> None:
    if not isinstance(result, dict):
        return
    if "sql" in result:
        st.code(result.get("sql", ""), language="sql")
    generated_sql = result.get("generated_sql")
    if isinstance(generated_sql, dict):
        st.code(generated_sql.get("sql", ""), language="sql")
    review = result.get("review") if isinstance(result.get("review"), dict) else result
    if isinstance(review, dict) and "risk_level" in review:
        st.caption(
            f"风险：{review.get('risk_level', '-')} | 分数：{review.get('score', '-')}/100"
        )
    if "ods" in result and "dwd" in result:
        st.caption(
            "数仓层级："
            f"ODS {len(result.get('ods', []))}, "
            f"DWD {len(result.get('dwd', []))}, "
            f"DWS {len(result.get('dws', []))}, "
            f"ADS {len(result.get('ads', []))}"
        )


if __name__ == "__main__":
    render()
