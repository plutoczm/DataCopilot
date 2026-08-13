CREATE TABLE customers (
    customer_id BIGINT PRIMARY KEY,
    region VARCHAR(32) NOT NULL,
    acquisition_channel VARCHAR(32) NOT NULL,
    registered_at DATETIME NOT NULL
);

CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    product_name VARCHAR(128) NOT NULL,
    list_price DECIMAL(18, 2) NOT NULL
);

CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_status VARCHAR(32) NOT NULL,
    order_amount DECIMAL(18, 2) NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    paid_amount DECIMAL(18, 2) NOT NULL
);

CREATE TABLE refunds (
    refund_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    refund_amount DECIMAL(18, 2) NOT NULL,
    refund_reason VARCHAR(128),
    refunded_at DATETIME NOT NULL
);
