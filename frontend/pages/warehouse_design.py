import json
from pathlib import Path
import sys


def _bootstrap_project_root() -> None:
    project_root = str(Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_bootstrap_project_root()
import frontend.bootstrap  # noqa: E402,F401

from frontend.components.api_client import get_client
from frontend.components.sidebar import render as render_sidebar
from frontend.components.streamlit_compat import st


def render() -> None:
    st.set_page_config(page_title="Warehouse Designer", page_icon="DC", layout="wide")
    render_sidebar()
    st.title("Warehouse Designer")

    requirement = st.text_area("Business Requirement", value="设计电商订单分析数仓", height=120)
    use_rag = st.checkbox("Use RAG context", value=True)

    if not st.button("Generate Warehouse Design", type="primary"):
        return

    try:
        result = get_client().warehouse_design(requirement, use_rag=use_rag)
        st.success("Warehouse design generated")
        st.download_button(
            "Export Results",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name="warehouse_design.json",
            mime="application/json",
        )

        layer_tabs = st.tabs(["ODS", "DWD", "DWS", "ADS", "Metrics", "DDL", "Recommendations"])
        for tab, key in zip(layer_tabs[:4], ["ods", "dwd", "dws", "ads"], strict=True):
            with tab:
                _render_tables(result.get(key, []))

        with layer_tabs[4]:
            for metric in result.get("metrics", []):
                with st.expander(metric.get("name", "Metric")):
                    st.write(metric.get("definition", ""))
                    st.code(metric.get("calculation_logic", ""), language="sql")
                    st.caption(metric.get("business_meaning", ""))

        with layer_tabs[5]:
            for ddl in result.get("ddl", []):
                st.caption(ddl.get("table_name", "table"))
                st.code(ddl.get("sql", ""), language="sql")

        with layer_tabs[6]:
            for recommendation in result.get("recommendations", []):
                st.write(f"- {recommendation}")
    except Exception as exc:
        st.error(f"Warehouse design failed: {exc}")


def _render_tables(tables: list[dict]) -> None:
    for table in tables:
        with st.expander(table.get("name", "table"), expanded=True):
            st.write(table.get("description", ""))
            st.json(table.get("columns", []))


if __name__ == "__main__":
    render()
