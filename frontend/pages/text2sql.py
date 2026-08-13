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
from frontend.components.theme import apply_theme, card_grid, hero, quick_actions, record_activity


ENGINE_OPTIONS = {
    "SQLite（本地演示）": "sqlite",
    "Hive": "hive",
    "Spark SQL": "spark_sql",
    "MySQL": "mysql",
    "ClickHouse": "clickhouse",
}


def render() -> None:
    apply_theme()
    hero("自然语言生成 SQL", "把中文业务需求转换为可审查、可验证、可受控执行的 SQL。")
    card_grid(
        [
            ("多引擎支持", "覆盖 SQLite、Hive、Spark SQL、MySQL 和 ClickHouse。"),
            ("确定性校验", "先检查表字段、JOIN 与只读边界，再决定是否允许后续执行。"),
            ("受控执行", "仅对白名单只读数据源开放，服务端强制超时、行数上限和审计。"),
        ]
    )

    selected = quick_actions(
        "一键示例",
        [
            {
                "tag": "活跃用户分析",
                "title": "最近7天活跃用户",
                "description": "按天和省份统计活跃用户数，适合 Hive/Spark 场景。",
                "button_label": "填入示例",
                "question": "按天统计最近7天活跃用户数，并按省份输出 Top 10",
                "schema": (
                    "dwd_user_behavior_detail(user_id bigint, event_time timestamp, province string, "
                    "event_name string, dt string)\n"
                    "dim_user(user_id bigint, user_level string, province string)"
                ),
            },
            {
                "tag": "订单 GMV 看板",
                "title": "支付 GMV 趋势",
                "description": "按日期统计支付金额、订单数和支付用户数。",
                "button_label": "填入示例",
                "question": "统计最近30天每日支付 GMV、支付订单数和支付用户数",
                "schema": (
                    "dwd_order_pay_detail(order_id bigint, user_id bigint, pay_amount decimal(18,2), "
                    "pay_time timestamp, dt string)\n"
                    "dim_shop(shop_id bigint, category string, province string)"
                ),
            },
        ],
        key_prefix="text2sql-demo",
    )
    if selected:
        st.session_state["text2sql_question"] = selected.get("question", "")
        st.session_state["text2sql_schema_context"] = selected.get("schema", "")
        st.session_state.pop("text2sql_last_result", None)
        record_activity("Text2SQL", f"加载{selected.get('tag', '示例')}示例")

    st.session_state.setdefault("text2sql_question", "统计最近7天活跃用户数")
    st.session_state.setdefault(
        "text2sql_schema_context",
        (
            "user_info(user_id bigint, register_time timestamp, province string)\n"
            "order_info(order_id bigint, user_id bigint, amount decimal(18,2), create_time timestamp)"
        ),
    )

    left, right = st.columns([1, 1])
    with left:
        question = st.text_area("业务需求", key="text2sql_question", height=120)
        schema_context = st.text_area(
            "表结构上下文",
            key="text2sql_schema_context",
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
                st.session_state["text2sql_last_result"] = result
                record_activity("Text2SQL", f"生成 SQL：{question[:28]}")
            except Exception as exc:
                st.error(f"Text2SQL 失败：{exc}")

        result = st.session_state.get("text2sql_last_result")
        if result:
            _render_result(result)


def _render_result(result: dict) -> None:
    sql = result.get("sql", "")
    validation = result.get("validation", {})

    st.subheader("生成 SQL")
    st.code(sql, language="sql")
    st.download_button("下载 SQL", sql, file_name="query.sql")
    st.subheader("生成说明")
    st.write(result.get("explanation", ""))
    st.subheader("校验结果")
    st.json(validation)
    st.subheader("优化建议")
    for suggestion in result.get("optimization_suggestions", []):
        st.write(f"- {suggestion}")

    if validation.get("is_valid") is not True:
        st.warning("SQL 未通过静态校验，因此不会提供执行入口。")
        return

    _render_governed_execution(sql)


def _render_governed_execution(sql: str) -> None:
    st.subheader("受控只读执行")
    try:
        config = get_client().list_query_datasources()
    except Exception as exc:
        st.caption(f"无法读取执行能力：{exc}")
        return

    available = [
        item
        for item in config.get("datasources", [])
        if item.get("available") is True
    ]
    if not config.get("execution_enabled") or not available:
        st.info(
            "当前未启用白名单只读数据源。项目默认禁止执行模型生成的 SQL；"
            "零售演示可先初始化 SQLite 数据库并显式开启执行能力。"
        )
        return

    datasource_names = [item["name"] for item in available]
    datasource = st.selectbox(
        "只读数据源",
        datasource_names,
        key="text2sql_execution_datasource",
    )
    max_rows = st.number_input(
        "最大返回行数",
        min_value=1,
        max_value=200,
        value=50,
        step=10,
        key="text2sql_execution_max_rows",
    )
    st.warning(
        "执行动作仍会由后端重新检查只读策略，并受数据库只读模式、超时、"
        "服务端最大行数和审计日志约束。"
    )
    if st.button("执行只读查询", key="text2sql_execute_query"):
        try:
            executed = get_client().execute_query(
                datasource=datasource,
                sql=sql,
                max_rows=int(max_rows),
            )
            st.success(
                f"执行完成：{executed.get('row_count', 0)} 行，"
                f"耗时 {executed.get('elapsed_ms', 0)} ms"
            )
            if executed.get("truncated"):
                st.info("结果已达到服务端行数上限并被截断。")
            st.dataframe(executed.get("rows", []), use_container_width=True)
            st.caption(f"Query ID: {executed.get('query_id', '')}")
            record_activity("Text2SQL", f"只读执行：{datasource}")
        except Exception as exc:
            st.error(f"只读执行失败：{exc}")


if __name__ == "__main__":
    render()
