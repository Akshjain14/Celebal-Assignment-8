import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

def write_csv(filename, header, rows):
    with open(DATA / filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def generate_products(n=500):
    categories = {
        "Electronics": ["Mobiles", "Laptops", "Accessories"],
        "Clothing": ["Men", "Women", "Kids"],
        "Home": ["Kitchen", "Furniture", "Decor"],
        "Books": ["Fiction", "Education", "Comics"],
    }
    adjectives = ["Smart", "Premium", "Classic", "Wireless", "Portable", "Essential", "Modern", "Ultra"]
    nouns = ["Phone", "Headphones", "Laptop", "Shirt", "Jacket", "Shoes", "Mixer", "Lamp",
             "Chair", "Book", "Keyboard", "Mouse"]

    rows = []
    for i in range(1, n + 1):
        category = random.choice(list(categories))
        subcategory = random.choice(categories[category])
        name = f"{random.choice(adjectives)} {random.choice(nouns)} {i}"
        cost = round(random.uniform(150, 50000), 2)

        # Intentional issue: extra spaces / mixed case.
        if i % 25 == 0:
            name = "  " + name.lower() + "  "
        elif i % 17 == 0:
            name = name.upper()

        rows.append([f"P{i:04d}", name, category, subcategory, cost])
    return rows

def generate_customers(n=500):
    first_names = ["Aarav", "Vihaan", "Aditya", "Arjun", "Kabir", "Rohan",
                   "Ishaan", "Anaya", "Diya", "Aanya", "Meera", "Priya", "Kavya", "Ira", "Sara"]
    last_names = ["Sharma", "Verma", "Gupta", "Singh", "Mehta", "Kapoor",
                  "Tyagi", "Malhotra", "Joshi", "Bansal"]

    start = datetime.now() - timedelta(days=720)
    rows = []

    for i in range(1, n + 1):
        first = random.choice(first_names)
        last = random.choice(last_names)
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        registration = start + timedelta(days=random.randint(0, 700))
        customer_type = random.choices(
            ["REGULAR", "PREMIUM", "VIP"], weights=[65, 25, 10]
        )[0]
        rows.append([
            f"C{i:04d}", f"{first} {last}", email,
            registration.strftime("%Y-%m-%d"), customer_type
        ])

    # Exactly 2% invalid emails.
    for index in random.sample(range(n), int(n * 0.02)):
        if index % 2 == 0:
            rows[index][2] = rows[index][2].replace("@", "")
        else:
            rows[index][2] = rows[index][2].split("@")[0] + "@"

    return rows

def generate_orders(customer_ids, n=800):
    statuses = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
    regions = ["NORTH", "SOUTH", "EAST", "WEST"]
    weights = [10, 15, 55, 10, 10]
    start = datetime.now() - timedelta(days=540)

    rows = []
    for i in range(1, n + 1):
        dt = start + timedelta(
            days=random.randint(0, 535),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        rows.append([
            f"O{i:05d}",
            random.choice(customer_ids),
            dt,
            random.choices(statuses, weights=weights)[0],
            random.choice(regions)
        ])

    # Exactly 5% missing customer_id.
    for index in random.sample(range(n), int(n * 0.05)):
        rows[index][1] = ""

    # Some dates in DD-MM-YYYY format.
    for index in random.sample(range(n), int(n * 0.05)):
        rows[index][2] = rows[index][2].strftime("%d-%m-%Y %H:%M:%S")

    return rows

def generate_order_items(order_ids, product_ids):
    rows = []
    item_number = 1

    # Only use order_ids from orders, guaranteeing referential integrity.
    for order_id in order_ids:
        for _ in range(random.randint(1, 4)):
            rows.append([
                f"I{item_number:06d}",
                order_id,
                random.choice(product_ids),
                random.randint(1, 5),
                round(random.uniform(200, 60000), 2),
                round(random.uniform(0, 30), 2)
            ])
            item_number += 1

    # Exactly 3% negative quantities.
    for index in random.sample(range(len(rows)), int(len(rows) * 0.03)):
        rows[index][3] = -abs(rows[index][3])

    return rows

def main():
    products = generate_products()
    customers = generate_customers()

    customer_ids = [row[0] for row in customers]
    product_ids = [row[0] for row in products]

    orders = generate_orders(customer_ids)
    order_ids = [row[0] for row in orders]

    order_items = generate_order_items(order_ids, product_ids)

    write_csv(
        "products.csv",
        ["product_id", "product_name", "category", "subcategory", "cost_price"],
        products
    )
    write_csv(
        "customers.csv",
        ["customer_id", "customer_name", "email", "registration_date", "customer_type"],
        customers
    )
    write_csv(
        "orders.csv",
        ["order_id", "customer_id", "order_date", "status", "region_code"],
        [
            [a, b, c if isinstance(c, str) else c.strftime("%Y-%m-%d %H:%M:%S"), d, e]
            for a, b, c, d, e in orders
        ]
    )
    write_csv(
        "order_items.csv",
        ["item_id", "order_id", "product_id", "quantity", "unit_price", "discount_percent"],
        order_items
    )

    print("Data generation complete.")
    print(f"Customers: {len(customers)}")
    print(f"Products: {len(products)}")
    print(f"Orders: {len(orders)}")
    print(f"Order items: {len(order_items)}")
    print("Intentional issues:")
    print(f"- Missing customer_id: {int(len(orders) * 0.05)}")
    print(f"- Negative quantities: {int(len(order_items) * 0.03)}")
    print(f"- Invalid emails: {int(len(customers) * 0.02)}")
    print("- Some order dates use DD-MM-YYYY format")
    print("- Some product names contain spaces/mixed case")

if __name__ == "__main__":
    main()
