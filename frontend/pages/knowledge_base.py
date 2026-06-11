from frontend.components.api_client import get_client
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


def render() -> None:
    st.set_page_config(page_title="Knowledge Base", page_icon="DC", layout="wide")
    render_sidebar()
    st.title("Knowledge Base")

    upload_tab, documents_tab, query_tab = st.tabs(["Upload", "Documents", "RAG Query"])

    with upload_tab:
        collection_name = st.text_input("Collection", value="knowledge_base", key="upload_collection")
        domain = st.text_input("Domain", value="general")
        tags = st.text_input("Tags", value="")
        uploaded_file = st.file_uploader(
            "Upload PDF, DOCX, TXT, or Markdown",
            type=["pdf", "docx", "txt", "md", "markdown"],
        )
        if st.button("Index Document", type="primary") and uploaded_file is not None:
            try:
                result = get_client().upload_document(
                    file_name=uploaded_file.name,
                    file_bytes=uploaded_file.getvalue(),
                    collection_name=collection_name,
                    domain=domain,
                    tags=tags,
                )
                st.success(f"Indexed {result.get('filename', uploaded_file.name)}")
                st.json(result)
            except Exception as exc:
                st.error(f"Upload failed: {exc}")

    with documents_tab:
        if st.button("Refresh Documents"):
            st.session_state["documents_cache"] = get_client().list_documents()
        documents = st.session_state.get("documents_cache")
        if documents is None:
            try:
                documents = get_client().list_documents()
            except Exception as exc:
                st.error(f"Failed to load documents: {exc}")
                documents = {"documents": []}
        for document in documents.get("documents", []):
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.write(f"**{document.get('filename')}**")
            col2.write(document.get("domain", "general"))
            if col3.button("Delete", key=f"delete-{document.get('document_id')}"):
                try:
                    get_client().delete_document(document["document_id"])
                    st.success("Deleted")
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")

    with query_tab:
        question = st.text_area("Question", value="How does Spark AQE help?")
        collection = st.text_input("Collection", value="knowledge_base", key="query_collection")
        top_k = st.slider("Top K", min_value=1, max_value=20, value=5, key="query_top_k")
        if st.button("Run RAG Query", type="primary"):
            try:
                result = get_client().query_knowledge(question, collection_name=collection, top_k=top_k)
                st.subheader("Answer")
                st.write(result.get("answer", ""))
                st.subheader("Citations")
                st.json(result.get("citations", []))
            except Exception as exc:
                st.error(f"Query failed: {exc}")


if __name__ == "__main__":
    render()
