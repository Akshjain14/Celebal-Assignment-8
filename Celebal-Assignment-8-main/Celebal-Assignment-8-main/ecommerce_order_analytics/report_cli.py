import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "ecommerce.db"

def get_period(start, end, report_type):
    if report_type == "daily":
        return start, end
    if report_type == "weekly":
        return start, end
    if report_type == "monthly":
        return start, end
    raise ValueError("Report type must be daily, weekly, or monthly")

def previous_period(start, end):
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)

def report(report_type, start_text, end_text):
    start = datetime.strptime(start_text, "%Y-%m-%d")
    end = datetime.strptime(end_text, "%Y-%m-%d")
    prev_start, prev_end = previous_period(start, end)

    conn = sqlite3.connect(DB)
    revenue_sql = """
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price *
               (1 - oi.discount_percent/100.0)), 0)
        FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
        WHERE date(o.order_date) BETWEEN ? AND ?
    """
    orders_sql = "SELECT COUNT(*) FROM orders WHERE date(order_date) BETWEEN ? AND ?"
    customers_sql = """
        SELECT COUNT(DISTINCT customer_id) FROM orders
        WHERE customer_id <> '' AND date(order_date) BETWEEN ? AND ?
    """
    top_sql = """
        SELECT p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id=o.order_id
        JOIN products p ON p.product_id=oi.product_id
        WHERE date(o.order_date) BETWEEN ? AND ?
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC LIMIT 3
    """

    revenue = conn.execute(revenue_sql, (start_text,end_text)).fetchone()[0]
    orders = conn.execute(orders_sql, (start_text,end_text)).fetchone()[0]
    customers = conn.execute(customers_sql, (start_text,end_text)).fetchone()[0]
    prev_revenue = conn.execute(revenue_sql, (prev_start.strftime("%Y-%m-%d"),
                                               prev_end.strftime("%Y-%m-%d"))).fetchone()[0]
    change = None if prev_revenue == 0 else (revenue-prev_revenue)*100/prev_revenue

    print(f"\n{report_type.upper()} REPORT")
    print("-"*40)
    print(f"Date range       : {start_text} to {end_text}")
    print(f"Total orders     : {orders}")
    print(f"Revenue          : {revenue:.2f}")
    print(f"Unique customers : {customers}")
    print(f"Previous revenue : {prev_revenue:.2f}")
    print(f"Period change    : {'N/A' if change is None else f'{change:.2f}%'}")
    print("\nTop 3 products:")
    for name, rev in conn.execute(top_sql, (start_text,end_text)):
        print(f"  {name}: {rev:.2f}")
    conn.close()

if __name__ == "__main__":
    print("E-Commerce Order Analytics Report Tool")
    report_type = input("Report type (daily/weekly/monthly): ").strip().lower()
    start = input("Start date (YYYY-MM-DD): ").strip()
    end = input("End date (YYYY-MM-DD): ").strip()
    report(report_type, start, end)
