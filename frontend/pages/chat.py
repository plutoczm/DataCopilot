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
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


def render() -> None:
    st.set_page_config(page_title="DataPilot-AI Agent Chat", page_icon="DC", layout="wide")
    render_sidebar()
    st.title("Agent Chat")

    st.session_state.setdefault("chat_history", [])
    with st.expander("Context Settings", expanded=False):
        collection_name = st.text_input("Collection", value="knowledge_base")
        top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
        engine = st.selectbox("SQL Engine", ["hive", "spark_sql", "mysql", "clickhouse"])
        schema_context = st.text_area("Schema Context", height=120)
        use_rag = st.checkbox("Use RAG for specialist tools", value=False)

    for item in st.session_state["chat_history"]:
        render_message(item["role"], item["content"])
        render_citations(item.get("citations", []))
        _render_agent_result(item.get("result"))

    prompt = st.chat_input("Ask DataPilot-AI anything")
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
                        "Intent: "
                        f"{data.get('intent', '-')}"
                        " | Route: "
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
            st.error(f"Streaming failed: {exc}")


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
            f"Risk: {review.get('risk_level', '-')} | Score: {review.get('score', '-')}/100"
        )
    if "ods" in result and "dwd" in result:
        st.caption(
            "Warehouse layers: "
            f"ODS {len(result.get('ods', []))}, "
            f"DWD {len(result.get('dwd', []))}, "
            f"DWS {len(result.get('dws', []))}, "
            f"ADS {len(result.get('ads', []))}"
        )


if __name__ == "__main__":
    render()
