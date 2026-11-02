# evaluation/golden_cases.py

GOLDEN_CASES = [
    {
        "id": "Q01",
        "question": "What is the total net revenue from completed orders?",
        "reference_sql": """
            SELECT COALESCE(
                SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)),
                0
            ) AS total_net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
        """,
        "expected_columns": ["total_net_revenue"]
    },
    {
        "id": "Q02",
        "question": "Which 5 products generated the highest net revenue?",
        "reference_sql": """
            SELECT p.product_name,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN products p ON p.product_id = oi.product_id
            WHERE o.status = 'completed'
            GROUP BY p.product_id, p.product_name
            ORDER BY net_revenue DESC, p.product_name ASC
            LIMIT 5
        """,
        "expected_columns": ["product_name", "net_revenue"]
    },
    {
        "id": "Q03",
        "question": "What is the net revenue by customer region?",
        "reference_sql": """
            SELECT c.region,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.status = 'completed'
            GROUP BY c.region
            ORDER BY c.region
        """,
        "expected_columns": ["region", "net_revenue"]
    },
    {
        "id": "Q04",
        "question": "How many completed orders were placed in Q2 2026?",
        "reference_sql": """
            SELECT COUNT(*) AS completed_order_count
            FROM orders
            WHERE status = 'completed'
              AND order_date >= DATE '2026-04-01'
              AND order_date < DATE '2026-07-01'
        """,
        "expected_columns": ["completed_order_count"]
    },
    {
        "id": "Q05",
        "question": "What is the average order value for completed orders?",
        "reference_sql": """
            WITH order_totals AS (
                SELECT o.order_id,
                       SUM(
                           oi.quantity * oi.unit_price
                           * (1 - oi.discount_pct)
                       ) AS net_revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.status = 'completed'
                GROUP BY o.order_id
            )
            SELECT COALESCE(AVG(net_revenue), 0) AS average_order_value
            FROM order_totals
        """,
        "expected_columns": ["average_order_value"]
    },
    {
        "id": "Q06",
        "question": "Which products have no revenue from completed orders?",
        "reference_sql": """
            SELECT p.product_id, p.product_name
            FROM products p
            LEFT JOIN order_items oi ON oi.product_id = p.product_id
            LEFT JOIN orders o
                ON o.order_id = oi.order_id
               AND o.status = 'completed'
            GROUP BY p.product_id, p.product_name
            HAVING COUNT(o.order_id) = 0
            ORDER BY p.product_id
        """,
        "expected_columns": ["product_id", "product_name"]
    },
    {
        "id": "Q07",
        "question": "What is the net revenue by product category?",
        "reference_sql": """
            SELECT p.category,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN products p ON p.product_id = oi.product_id
            WHERE o.status = 'completed'
            GROUP BY p.category
            ORDER BY p.category
        """,
        "expected_columns": ["category", "net_revenue"]
    },
    {
        "id": "Q08",
        "question": "What is the monthly net revenue for 2026?",
        "reference_sql": """
            SELECT DATE_TRUNC('month', o.order_date)::date AS month,
                   SUM(
                       oi.quantity * oi.unit_price * (1 - oi.discount_pct)
                   ) AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
              AND o.order_date >= DATE '2026-01-01'
              AND o.order_date < DATE '2027-01-01'
            GROUP BY DATE_TRUNC('month', o.order_date)
            ORDER BY month
        """,
        "expected_columns": ["month", "net_revenue"]
    },
    {
        "id": "Q09",
        "question": (
            "What is the net line value associated with cancelled orders, "
            "for reconciliation purposes?"
        ),
        "reference_sql": """
            SELECT COALESCE(
                SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)),
                0
            ) AS cancelled_order_line_value
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'cancelled'
        """,
        "expected_columns": ["cancelled_order_line_value"]
    },
    {
        "id": "Q10",
        "question": "Which customers generated the highest net revenue?",
        "reference_sql": """
            SELECT c.customer_name,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.status = 'completed'
            GROUP BY c.customer_id, c.customer_name
            ORDER BY net_revenue DESC, c.customer_name ASC
        """,
        "expected_columns": ["customer_name", "net_revenue"]
    },
    {
        "id": "Q11",
        "question": "What is the total discount amount on completed orders?",
        "reference_sql": """
            SELECT COALESCE(
                SUM(oi.quantity * oi.unit_price * oi.discount_pct),
                0
            ) AS total_discount
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
        """,
        "expected_columns": ["total_discount"]
    },
    {
        "id": "Q12",
        "question": (
            "What is the total net revenue from completed orders "
            "between 2027-01-01 and 2027-02-01?"
        ),
        "reference_sql": """
            SELECT COALESCE(
                SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)),
                0
            ) AS total_net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
              AND o.order_date >= DATE '2027-01-01'
              AND o.order_date < DATE '2027-02-01'
        """,
        "expected_columns": ["total_net_revenue"]
    },
]


GOLDEN_CASES = [
    {
        "id": "Q02",
        "question": "Which 5 products generated the highest net revenue?",
        "reference_sql": """
            SELECT p.product_name,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN products p ON p.product_id = oi.product_id
            WHERE o.status = 'completed'
            GROUP BY p.product_id, p.product_name
            ORDER BY net_revenue DESC, p.product_name ASC
            LIMIT 5
        """,
        "expected_columns": ["product_name", "net_revenue"]
    },
    {
        "id": "Q03",
        "question": "What is the net revenue by customer region?",
        "reference_sql": """
            SELECT c.region,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.status = 'completed'
            GROUP BY c.region
            ORDER BY c.region
        """,
        "expected_columns": ["region", "net_revenue"]
    },
    {
        "id": "Q04",
        "question": "How many completed orders were placed in Q2 2026?",
        "reference_sql": """
            SELECT COUNT(*) AS completed_order_count
            FROM orders
            WHERE status = 'completed'
              AND order_date >= DATE '2026-04-01'
              AND order_date < DATE '2026-07-01'
        """,
        "expected_columns": ["completed_order_count"]
    },
    {
        "id": "Q07",
        "question": "What is the net revenue by product category?",
        "reference_sql": """
            SELECT p.category,
                   SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct))
                       AS net_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN products p ON p.product_id = oi.product_id
            WHERE o.status = 'completed'
            GROUP BY p.category
            ORDER BY p.category
        """,
        "expected_columns": ["category", "net_revenue"]
    },
    {
        "id": "Q09",
        "question": (
            "What is the net line value associated with cancelled orders, "
            "for reconciliation purposes?"
        ),
        "reference_sql": """
            SELECT COALESCE(
                SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)),
                0
            ) AS cancelled_order_line_value
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status = 'cancelled'
        """,
        "expected_columns": ["cancelled_order_line_value"]
    },
]