-- E-Commerce Order Analytics System
-- Revenue = quantity * unit_price * (1 - discount_percent / 100)

-- 1. Total revenue per category
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.status <> 'CANCELLED'
GROUP BY p.category
ORDER BY total_revenue DESC;

-- 2. Top 10 customers by total order value
SELECT o.customer_id,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)), 2) AS total_order_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.customer_id <> ''
GROUP BY o.customer_id
ORDER BY total_order_value DESC
LIMIT 10;

-- 3. Month-wise order count for the last 12 months
WITH bounds AS (
    SELECT date(MAX(order_date), '-12 months') AS start_date,
           date(MAX(order_date)) AS end_date
    FROM orders
)
SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS order_count
FROM orders, bounds
WHERE date(order_date) >= start_date AND date(order_date) <= end_date
GROUP BY month
ORDER BY month;

-- 4. Customers who placed orders but never had any item delivered
SELECT DISTINCT o.customer_id
FROM orders o
WHERE o.customer_id <> ''
  AND NOT EXISTS (
      SELECT 1
      FROM orders od
      WHERE od.customer_id = o.customer_id
        AND od.status = 'DELIVERED'
  );

-- 5. Products with more returned quantity than purchased quantity
SELECT p.product_id, p.product_name,
       SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS purchased_qty,
       SUM(CASE WHEN oi.quantity < 0 THEN ABS(oi.quantity) ELSE 0 END) AS returned_qty
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
HAVING returned_qty > purchased_qty;

-- 6. Return rate per category
SELECT p.category,
       SUM(CASE WHEN oi.quantity < 0 THEN ABS(oi.quantity) ELSE 0 END) * 100.0
       / NULLIF(SUM(ABS(oi.quantity)), 0) AS return_rate_percent
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY return_rate_percent DESC;

-- 7. Running total revenue per region ordered by date
WITH daily AS (
    SELECT o.region_code,
           date(o.order_date) AS order_date,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status <> 'CANCELLED'
    GROUP BY o.region_code, date(o.order_date)
)
SELECT region_code, order_date,
       ROUND(daily_revenue,2) AS daily_revenue,
       ROUND(SUM(daily_revenue) OVER (
           PARTITION BY region_code ORDER BY order_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ),2) AS running_total
FROM daily
ORDER BY region_code, order_date;

-- 8. DENSE_RANK products by revenue within each category
WITH product_revenue AS (
    SELECT p.category, p.product_name,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS total_revenue
    FROM products p
    JOIN order_items oi ON oi.product_id = p.product_id
    GROUP BY p.category, p.product_id, p.product_name
)
SELECT category, product_name, ROUND(total_revenue,2) AS total_revenue,
       DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;

-- 9. LAG: days between consecutive orders + At Risk flag
WITH customer_orders AS (
    SELECT customer_id, date(order_date) AS order_date,
           LAG(date(order_date)) OVER (
               PARTITION BY customer_id ORDER BY date(order_date)
           ) AS previous_order_date
    FROM orders
    WHERE customer_id <> ''
),
gaps AS (
    SELECT customer_id, order_date, previous_order_date,
           CAST(julianday(order_date) - julianday(previous_order_date) AS INTEGER) AS days_gap
    FROM customer_orders
)
SELECT customer_id, order_date, previous_order_date, days_gap,
       CASE WHEN AVG(days_gap) OVER (PARTITION BY customer_id) > 30
            THEN 'At Risk' ELSE 'Normal' END AS risk_flag
FROM gaps
ORDER BY customer_id, order_date;

-- 10. Multiple-level CTE: monthly customer revenue categories
WITH monthly_revenue AS (
    SELECT o.customer_id,
           strftime('%Y-%m', o.order_date) AS month,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> ''
    GROUP BY o.customer_id, month
),
categorized AS (
    SELECT customer_id, month, revenue,
           CASE WHEN revenue > 10000 THEN 'High'
                WHEN revenue >= 5000 THEN 'Medium'
                ELSE 'Low' END AS revenue_category
    FROM monthly_revenue
)
SELECT month, revenue_category, COUNT(*) AS customer_count
FROM categorized
GROUP BY month, revenue_category
ORDER BY month, revenue_category;

-- 11. NTILE quartile segmentation by lifetime value
WITH lifetime AS (
    SELECT o.customer_id,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS total_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> ''
    GROUP BY o.customer_id
),
segmented AS (
    SELECT customer_id, total_value,
           NTILE(4) OVER (ORDER BY total_value DESC) AS quartile
    FROM lifetime
)
SELECT customer_id, ROUND(total_value,2) AS total_value, quartile,
       CASE quartile
         WHEN 1 THEN 'Platinum'
         WHEN 2 THEN 'Gold'
         WHEN 3 THEN 'Silver'
         WHEN 4 THEN 'Bronze'
       END AS quartile_label
FROM segmented
ORDER BY quartile, total_value DESC;

-- 12. Year-over-Year comparison
WITH monthly AS (
    SELECT strftime('%Y', order_date) AS year,
           strftime('%m', order_date) AS month,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY year, month
),
with_prev AS (
    SELECT year, month, revenue,
           LAG(revenue, 12) OVER (ORDER BY year, month) AS prev_year_revenue
    FROM monthly
)
SELECT year, month, ROUND(revenue,2) AS revenue,
       ROUND(prev_year_revenue,2) AS prev_year_revenue,
       CASE WHEN prev_year_revenue IS NULL OR prev_year_revenue = 0 THEN NULL
            ELSE ROUND((revenue-prev_year_revenue)*100.0/prev_year_revenue,2)
       END AS yoy_growth_percent
FROM with_prev
ORDER BY year, month;

-- 13. First/Last purchased category
WITH ranked AS (
    SELECT o.customer_id, p.category, o.order_date,
           ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date, oi.item_id) AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC, oi.item_id DESC) AS rn_last
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.customer_id <> ''
),
first_last AS (
    SELECT customer_id,
           MAX(CASE WHEN rn_first=1 THEN category END) AS first_category,
           MAX(CASE WHEN rn_last=1 THEN category END) AS recent_category
    FROM ranked
    GROUP BY customer_id
)
SELECT customer_id, first_category, recent_category,
       CASE WHEN first_category <> recent_category THEN 'Yes' ELSE 'No' END AS category_shift
FROM first_last;

-- 14. Cumulative distribution of revenue
WITH customer_revenue AS (
    SELECT o.customer_id,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> ''
    GROUP BY o.customer_id
),
ranked AS (
    SELECT customer_id, revenue,
           SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
           SUM(revenue) OVER () AS total_revenue
    FROM customer_revenue
)
SELECT customer_id, ROUND(revenue,2) AS revenue,
       ROUND(cumulative_revenue,2) AS cumulative_revenue,
       ROUND(cumulative_revenue*100.0/NULLIF(total_revenue,0),2) AS cumulative_percent
FROM ranked
ORDER BY revenue DESC;

-- 15. Cohort analysis: registration month and month 0-3 retention
WITH cohorts AS (
    SELECT customer_id,
           strftime('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
customer_months AS (
    SELECT DISTINCT o.customer_id,
           strftime('%Y-%m', o.order_date) AS order_month
    FROM orders o
    WHERE o.customer_id <> ''
),
activity AS (
    SELECT c.customer_id, c.cohort_month, cm.order_month,
           (CAST(strftime('%Y', cm.order_month||'-01') AS INTEGER)*12 + CAST(strftime('%m', cm.order_month||'-01') AS INTEGER))
           - (CAST(strftime('%Y', c.cohort_month||'-01') AS INTEGER)*12 + CAST(strftime('%m', c.cohort_month||'-01') AS INTEGER)) AS month_number
    FROM cohorts c
    JOIN customer_months cm ON cm.customer_id = c.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM cohorts
    GROUP BY cohort_month
)
SELECT a.cohort_month,
       cs.cohort_customers,
       COUNT(DISTINCT CASE WHEN month_number=0 THEN a.customer_id END) AS month_0,
       COUNT(DISTINCT CASE WHEN month_number=1 THEN a.customer_id END) AS month_1,
       COUNT(DISTINCT CASE WHEN month_number=2 THEN a.customer_id END) AS month_2,
       COUNT(DISTINCT CASE WHEN month_number=3 THEN a.customer_id END) AS month_3,
       ROUND(COUNT(DISTINCT CASE WHEN month_number=0 THEN a.customer_id END)*100.0/cs.cohort_customers,2) AS retention_0_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number=1 THEN a.customer_id END)*100.0/cs.cohort_customers,2) AS retention_1_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number=2 THEN a.customer_id END)*100.0/cs.cohort_customers,2) AS retention_2_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number=3 THEN a.customer_id END)*100.0/cs.cohort_customers,2) AS retention_3_pct
FROM activity a
JOIN cohort_size cs ON cs.cohort_month = a.cohort_month
GROUP BY a.cohort_month, cs.cohort_customers
ORDER BY a.cohort_month;

-- 16. Self-Join with Window Function: frequently bought together
WITH product_pairs AS (
    SELECT a.product_id AS product_a,
           b.product_id AS product_b,
           COUNT(DISTINCT a.order_id) AS times_bought_together
    FROM order_items a
    JOIN order_items b
      ON a.order_id = b.order_id
     AND a.product_id < b.product_id
    GROUP BY a.product_id, b.product_id
)
SELECT pa.product_name AS product_a,
       pb.product_name AS product_b,
       pp.times_bought_together
FROM product_pairs pp
JOIN products pa ON pa.product_id = pp.product_a
JOIN products pb ON pb.product_id = pp.product_b
ORDER BY pp.times_bought_together DESC
LIMIT 50;
