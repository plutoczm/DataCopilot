INSERT INTO customers(customer_id, region, acquisition_channel, registered_at) VALUES
    (1, 'North', 'organic', datetime('now', '-120 day')),
    (2, 'East', 'paid_search', datetime('now', '-80 day')),
    (3, 'South', 'social', datetime('now', '-40 day')),
    (4, 'West', 'affiliate', datetime('now', '-25 day')),
    (5, 'North', 'social', datetime('now', '-15 day')),
    (6, 'East', 'organic', datetime('now', '-7 day'));

INSERT INTO products(product_id, category, product_name, list_price) VALUES
    (11, 'Electronics', 'Wireless Earbuds', 99.00),
    (12, 'Electronics', 'Mechanical Keyboard', 129.00),
    (21, 'Home', 'Desk Lamp', 49.00),
    (22, 'Home', 'Coffee Grinder', 79.00),
    (31, 'Sports', 'Yoga Mat', 39.00),
    (32, 'Sports', 'Running Belt', 29.00);

INSERT INTO orders(order_id, customer_id, order_status, order_amount, created_at) VALUES
    (101, 1, 'paid', 198.00, datetime('now', '-3 day')),
    (102, 2, 'paid', 129.00, datetime('now', '-5 day')),
    (103, 3, 'refunded', 79.00, datetime('now', '-8 day')),
    (104, 4, 'paid', 88.00, datetime('now', '-10 day')),
    (105, 5, 'paid', 158.00, datetime('now', '-12 day')),
    (106, 6, 'paid', 49.00, datetime('now', '-14 day')),
    (107, 1, 'cancelled', 39.00, datetime('now', '-16 day')),
    (108, 2, 'paid', 99.00, datetime('now', '-20 day')),
    (109, 3, 'paid', 128.00, datetime('now', '-27 day')),
    (110, 4, 'paid', 79.00, datetime('now', '-35 day'));

INSERT INTO order_items(order_id, product_id, quantity, paid_amount) VALUES
    (101, 11, 2, 198.00),
    (102, 12, 1, 129.00),
    (103, 22, 1, 79.00),
    (104, 31, 1, 39.00),
    (104, 21, 1, 49.00),
    (105, 22, 2, 158.00),
    (106, 21, 1, 49.00),
    (107, 31, 1, 39.00),
    (108, 11, 1, 99.00),
    (109, 11, 1, 99.00),
    (109, 32, 1, 29.00),
    (110, 22, 1, 79.00);

INSERT INTO refunds(refund_id, order_id, refund_amount, refund_reason, refunded_at) VALUES
    (1001, 103, 79.00, 'quality_issue', datetime('now', '-7 day')),
    (1002, 105, 40.00, 'partial_refund', datetime('now', '-11 day')),
    (1003, 108, 20.00, 'late_delivery', datetime('now', '-18 day'));
