# 零售经营指标口径

该文件用于演示 RAG 如何为 Text2SQL 提供业务口径，而不是把指标定义硬编码进 Prompt。

## GMV

- 口径：订单状态不为 `cancelled` 的订单金额之和。
- 时间字段：`orders.created_at`。
- 金额字段：`orders.order_amount`。

## 退款金额

- 口径：`refunds.refund_amount` 之和。
- 时间字段：`refunds.refunded_at`。

## 退款率

- 口径：退款金额 / GMV。
- 当 GMV 为 0 时应避免除零。

## 客单价

- 口径：GMV / 有效订单数。
- 有效订单：`orders.order_status != 'cancelled'`。

## 新客

- 口径：`customers.registered_at` 落在统计周期内的客户。

## 区域

- 使用 `customers.region` 作为经营区域维度。

## 获客渠道

- 使用 `customers.acquisition_channel`，例如 `organic`、`paid_search`、`social`、`affiliate`。

## 使用建议

把本文件上传到知识库后，在 Text2SQL 请求中开启 `use_rag=true`。模型应优先使用检索到的业务口径，而不是自行猜测指标定义。
