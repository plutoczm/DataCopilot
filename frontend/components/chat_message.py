from typing import Any

from frontend.components.streamlit_compat import st


def render_message(role: str, content: str) -> None:
    with st.chat_message(role):
        st.markdown(content)


def render(role: str = "assistant", content: str = "") -> None:
    render_message(role, content)


def render_citations(citations: list[dict[str, Any]]) -> None:
    if not citations:
        return
    with st.expander("Citations", expanded=False):
        for citation in citations:
            st.markdown(
                "\n".join(
                    [
                        f"**{citation.get('document_name', 'document')}**",
                        f"Chunk: `{citation.get('chunk_reference', '-')}`",
                        f"Score: `{citation.get('similarity_score', 0):.4f}`",
                    ]
                )
            )
