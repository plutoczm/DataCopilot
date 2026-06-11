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
from frontend.components.streamlit_compat import st
from frontend.components.theme import apply_theme, card_grid, hero


def render() -> None:
    apply_theme()
    hero("数仓设计", "根据业务需求生成 ODS、DWD、DWS、ADS 分层方案、指标定义和 Hive DDL。")
    card_grid(
        [
            ("分层建模", "自动组织明细层、汇总层和应用层。"),
            ("指标口径", "沉淀指标定义、计算逻辑和业务含义。"),
            ("DDL 输出", "生成可复制的建表 SQL，便于继续落地。"),
        ]
    )

    requirement = st.text_area("业务需求", value="设计电商订单分析数仓", height=120)
    use_rag = st.checkbox("使用知识库上下文", value=True)

    if not st.button("生成数仓方案", type="primary"):
        return

    try:
        result = get_client().warehouse_design(requirement, use_rag=use_rag)
        st.success("数仓方案已生成")
        st.download_button(
            "导出结果",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name="warehouse_design.json",
            mime="application/json",
        )

        layer_tabs = st.tabs(["ODS", "DWD", "DWS", "ADS", "指标", "DDL", "建议"])
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
        st.error(f"数仓设计失败：{exc}")


def _render_tables(tables: list[dict]) -> None:
    for table in tables:
        with st.expander(table.get("name", "表"), expanded=True):
            st.write(table.get("description", ""))
            st.json(table.get("columns", []))


if __name__ == "__main__":
    render()
