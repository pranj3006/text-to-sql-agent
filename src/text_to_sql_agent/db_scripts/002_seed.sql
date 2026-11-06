INSERT INTO customers (customer_name, region) VALUES
    ('Customer A', 'West'),
    ('Customer B', 'North'),
    ('Customer C', 'South'),
    ('Customer D', 'East'),
    ('Customer E', 'West'),
    ('Customer F', 'North');

INSERT INTO products (product_name, category) VALUES
    ('Coffee', 'Beverages'),
    ('Tea', 'Beverages'),
    ('Biscuits', 'Snacks'),
    ('Chips', 'Snacks'),
    ('Shampoo', 'Personal Care'),
    ('Soap', 'Personal Care');

INSERT INTO orders (customer_id, order_date, status) VALUES
    (1, '2026-01-15', 'completed'),
    (2, '2026-02-10', 'completed'),
    (3, '2026-03-05', 'completed'),
    (1, '2026-04-12', 'completed'),
    (4, '2026-04-20', 'cancelled'),
    (5, '2026-05-18', 'completed'),
    (6, '2026-06-08', 'completed'),
    (2, '2026-07-14', 'completed'),
    (3, '2026-08-22', 'completed'),
    (4, '2026-09-09', 'completed'),
    (5, '2026-10-05', 'completed'),
    (6, '2026-10-12', 'completed');

INSERT INTO order_items
    (order_id, product_id, quantity, unit_price, discount_pct)
VALUES
    (1, 1, 10, 200.00, 0.00),
    (1, 2,  5, 150.00, 0.10),
    (2, 1,  8, 200.00, 0.05),
    (2, 3, 20,  50.00, 0.00),
    (3, 4, 15,  40.00, 0.00),
    (3, 5,  4, 300.00, 0.10),
    (4, 1, 12, 200.00, 0.10),
    (4, 6, 10,  80.00, 0.00),
    (5, 1, 50, 200.00, 0.00),
    (6, 2, 20, 150.00, 0.05),
    (6, 3, 30,  50.00, 0.10),
    (7, 1, 15, 200.00, 0.00),
    (7, 4, 25,  40.00, 0.00),
    (8, 5, 10, 300.00, 0.15),
    (8, 6, 15,  80.00, 0.00),
    (9, 1, 20, 200.00, 0.05),
    (9, 2, 10, 150.00, 0.00),
    (10, 3, 40,  50.00, 0.00),
    (10, 4, 20,  40.00, 0.10),
    (11, 1, 25, 200.00, 0.10),
    (11, 5,  8, 300.00, 0.00),
    (12, 2, 30, 150.00, 0.10),
    (12, 6, 20,  80.00, 0.05);