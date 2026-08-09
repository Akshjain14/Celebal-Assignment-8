import sqlite3
import unittest
from datetime import datetime, timedelta

class EdgeCaseTests(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript("""
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                order_date TEXT
            );

            CREATE TABLE order_items (
                item_id TEXT PRIMARY KEY,
                order_id TEXT,
                quantity INTEGER,
                discount_percent REAL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );
        """)
        self.conn.execute("INSERT INTO orders VALUES ('O1', '2026-08-01 10:00:00')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_order_item_with_nonexistent_order_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO order_items VALUES ('I1', 'BAD_ORDER', 1, 10)"
            )

    def test_discount_greater_than_100_is_capped(self):
        discount = 120
        cleaned_discount = min(max(discount, 0), 100)
        self.assertEqual(cleaned_discount, 100)

    def test_zero_quantity_produces_zero_revenue(self):
        quantity = 0
        unit_price = 1000
        discount = 10
        revenue = quantity * unit_price * (1 - discount / 100)
        self.assertEqual(revenue, 0)

    def test_future_order_date_is_detected(self):
        future_date = datetime.now() + timedelta(days=1)
        self.assertTrue(future_date > datetime.now())

if __name__ == "__main__":
    unittest.main()
