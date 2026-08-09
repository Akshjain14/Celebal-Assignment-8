import pandas as pd
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
CLEAN = DATA / "cleaned"
REPORTS = BASE / "reports"
CLEAN.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

def clean_orders():
    df = pd.read_csv(DATA / "orders.csv", dtype=str)
    issues = []

    missing = df["customer_id"].isna() | (df["customer_id"].fillna("").str.strip() == "")
    issues.append(f"Missing customer_id rows: {int(missing.sum())}")

    # Parse both YYYY-MM-DD and DD-MM-YYYY formats.
    original = df["order_date"].copy()
    parsed = pd.to_datetime(original, errors="coerce", dayfirst=False)
    bad = parsed.isna()
    if bad.any():
        parsed2 = pd.to_datetime(original[bad], errors="coerce", dayfirst=True)
        parsed.loc[bad] = parsed2
    issues.append(f"Unparseable order_date rows: {int(parsed.isna().sum())}")

    df["order_date"] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["customer_id"] = df["customer_id"].fillna("").str.strip()
    # Preserve the order while making the missing customer explicit.
    df.loc[df["customer_id"] == "", "customer_id"] = "UNKNOWN_CUSTOMER"
    df.to_csv(CLEAN / "orders_cleaned.csv", index=False)
    return issues

def clean_products():
    df = pd.read_csv(DATA / "products.csv", dtype=str)
    before = df["product_name"].copy()
    df["product_name"] = df["product_name"].fillna("").str.strip().str.title()
    changed = int((before != df["product_name"]).sum())
    df.to_csv(CLEAN / "products_cleaned.csv", index=False)
    return [f"Product names normalized: {changed}"]

def validate_emails():
    df = pd.read_csv(DATA / "customers.csv", dtype=str)
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    invalid = df.loc[~df["email"].fillna("").str.match(pattern), "customer_id"].tolist()
    with open(REPORTS / "invalid_emails.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(invalid))
    return invalid

def check_referential_integrity():
    orders = pd.read_csv(DATA / "orders.csv", dtype=str)
    items = pd.read_csv(DATA / "order_items.csv", dtype=str)
    valid_orders = set(orders["order_id"].dropna())
    bad = items[~items["order_id"].isin(valid_orders)]
    bad.to_csv(REPORTS / "invalid_order_items.csv", index=False)
    return bad

def clean_order_items():
    df = pd.read_csv(DATA / "order_items.csv")
    negative = int((df["quantity"] < 0).sum())
    zero = int((df["quantity"] == 0).sum())
    over_discount = int((df["discount_percent"] > 100).sum())
    df["quantity"] = df["quantity"].astype(int)
    df["unit_price"] = df["unit_price"].astype(float)
    df["discount_percent"] = df["discount_percent"].clip(lower=0, upper=100)
    df.to_csv(CLEAN / "order_items_cleaned.csv", index=False)
    return [f"Negative quantities (returns): {negative}",
            f"Zero quantities: {zero}",
            f"Discounts > 100 corrected: {over_discount}"]

def clean_customers():
    # Keep original customer email values so invalid emails remain reportable.
    df = pd.read_csv(DATA / "customers.csv", dtype=str)
    df["customer_name"] = df["customer_name"].str.strip()
    if "UNKNOWN_CUSTOMER" not in set(df["customer_id"]):
        df.loc[len(df)] = ["UNKNOWN_CUSTOMER", "Unknown Customer", "unknown@example.com",
                            "1900-01-01", "REGULAR"]
    df.to_csv(CLEAN / "customers_cleaned.csv", index=False)

def main():
    report = []
    report += clean_orders()
    report += clean_products()
    invalid = validate_emails()
    report.append(f"Invalid emails: {len(invalid)}")
    bad_refs = check_referential_integrity()
    report.append(f"Invalid order references: {len(bad_refs)}")
    report += clean_order_items()
    clean_customers()
    with open(REPORTS / "cleaning_report.txt", "w", encoding="utf-8") as f:
        f.write("DATA CLEANING REPORT\n" + "="*40 + "\n")
        f.write("\n".join(report))
    print("\n".join(report))

if __name__ == "__main__":
    main()
