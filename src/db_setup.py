#!/usr/bin/env python3
"""Database schema creation and seed data generation."""

import csv
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

REGIONS = ["Northeast", "Southeast", "Midwest", "West", "International"]

TERRITORIES = [
    "New England", "Mid-Atlantic", "Southeast", "Florida", "Midwest-East",
    "Midwest-West", "Texas", "Mountain", "Pacific Northwest", "California",
    "Southwest", "Great Lakes", "Carolinas", "Gulf Coast", "Plains",
    "Upper Midwest", "Mid-South", "EMEA", "APAC", "LATAM",
]

PRODUCT_DATA = {
    "Electronics": {
        "subcategories": ["Laptops", "Monitors", "Accessories", "Networking", "Storage", "Audio"],
        "products": [
            "Pro Laptop 15", "Pro Laptop 13", "Ultra Laptop", "Business Laptop",
            "Budget Laptop", "4K Monitor 27", "4K Monitor 32", "Ultrawide Monitor",
            "Curved Monitor", "Portable Monitor", "Wireless Mouse", "Mechanical Keyboard",
            "USB-C Hub", "Webcam HD", "Wireless Headset", "Ethernet Switch", "WiFi Router",
            "NAS Drive 4TB", "External SSD 1TB", "Portable Speaker", "Noise-Cancel Headphones",
            "USB Microphone", "Monitor Arm", "Laptop Stand", "Surge Protector",
            "Cable Management Kit", "Bluetooth Adapter", "Card Reader", "Docking Station",
            "Wireless Charger",
        ],
        "price_range": (25, 2500),
        "cost_ratio": (0.4, 0.65),
    },
    "Office": {
        "subcategories": ["Furniture", "Supplies", "Paper", "Organization", "Breakroom"],
        "products": [
            "Ergonomic Chair", "Standing Desk", "Desk Lamp", "Filing Cabinet",
            "Bookshelf", "Whiteboard 4x6", "Desk Organizer", "Monitor Riser",
            "Printer Paper Ream", "Legal Pads 12pk", "Sticky Notes Bulk", "Binder Clips Box",
            "Stapler Heavy-Duty", "Tape Dispenser", "Label Maker", "Paper Shredder",
            "Desk Calendar", "Wall Clock", "Trash Can", "Recycling Bin",
            "Coffee Maker", "Water Filter", "Break Room Supplies", "First Aid Kit",
            "Hand Sanitizer Station",
        ],
        "price_range": (10, 800),
        "cost_ratio": (0.35, 0.6),
    },
    "Software": {
        "subcategories": ["Productivity", "Security", "Design", "Development"],
        "products": [
            "Office Suite Pro", "Office Suite Basic", "Antivirus Enterprise",
            "Antivirus Standard", "VPN Business", "Password Manager Team",
            "Project Management Tool", "CRM License", "Accounting Software",
            "HR Platform License", "Design Suite Pro", "Photo Editor",
            "Video Editor", "PDF Editor Pro", "Code Editor License",
            "Database Manager", "Cloud Storage 1TB", "Backup Solution",
            "Email Security", "Collaboration Platform",
        ],
        "price_range": (30, 500),
        "cost_ratio": (0.1, 0.3),
    },
    "Services": {
        "subcategories": ["Consulting", "Support", "Training", "Installation"],
        "products": [
            "IT Consultation Hour", "Network Setup", "Security Audit",
            "Data Migration Service", "Cloud Setup", "Training Session Basic",
            "Training Session Advanced", "On-site Support Day", "Remote Support Hour",
            "System Integration", "Hardware Installation", "Software Deployment",
            "Compliance Review", "Performance Optimization", "Disaster Recovery Plan",
        ],
        "price_range": (100, 5000),
        "cost_ratio": (0.3, 0.55),
    },
    "Hardware": {
        "subcategories": ["Servers", "Components", "Peripherals"],
        "products": [
            "Rack Server Entry", "Rack Server Pro", "Tower Server",
            "UPS Battery Backup", "Server RAM 32GB", "Server SSD 2TB",
            "Network Cable 50ft", "Patch Panel", "Server Cabinet",
            "KVM Switch",
        ],
        "price_range": (50, 5000),
        "cost_ratio": (0.45, 0.7),
    },
}

RETURN_REASONS = [
    "Product was defective on arrival",
    "Wrong item shipped",
    "Product not as described",
    "Changed mind after purchase",
    "Better price found elsewhere",
    "No longer needed",
    "Duplicate order",
    "Incompatible with existing setup",
]

RETURN_CONDITIONS = ["defective", "wrong_item", "not_as_described", "changed_mind"]


def get_data_dir():
    return Path(__file__).resolve().parent.parent / "data"


def get_db_path():
    return get_data_dir() / "sales.db"


def generate_sales_reps(rng):
    """Generate 20 sales reps with varying performance levels."""
    reps = []
    for i in range(1, 21):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        territory = TERRITORIES[i - 1]
        quota = rng.choice([200000, 250000, 300000, 350000, 400000, 500000])
        hire_year = rng.randint(2019, 2024)
        hire_month = rng.randint(1, 12)
        hire_day = rng.randint(1, 28)
        hire_date = f"{hire_year:04d}-{hire_month:02d}-{hire_day:02d}"
        reps.append({
            "sales_rep_id": i,
            "name": f"{first} {last}",
            "territory": territory,
            "quota": quota,
            "hire_date": hire_date,
        })
    return reps


def generate_customers(rng):
    """Generate 500 customers across segments and regions."""
    customers = []
    segments = (["Enterprise"] * 50) + (["SMB"] * 200) + (["Consumer"] * 250)
    rng.shuffle(segments)

    email_set = set()
    for i in range(1, 501):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        name = f"{first} {last}"
        email_base = f"{first.lower()}.{last.lower()}"
        email = f"{email_base}@example.com"
        # Ensure unique emails for clean data
        suffix = 1
        while email in email_set:
            email = f"{email_base}{suffix}@example.com"
            suffix += 1
        email_set.add(email)

        segment = segments[i - 1]
        region = rng.choice(REGIONS)
        join_year = rng.randint(2021, 2025)
        join_month = rng.randint(1, 12)
        join_day = rng.randint(1, 28)
        join_date = f"{join_year:04d}-{join_month:02d}-{join_day:02d}"

        if segment == "Enterprise":
            ltv = round(rng.uniform(50000, 500000), 2)
        elif segment == "SMB":
            ltv = round(rng.uniform(5000, 75000), 2)
        else:
            ltv = round(rng.uniform(100, 10000), 2)

        customers.append({
            "customer_id": i,
            "name": name,
            "email": email,
            "segment": segment,
            "region": region,
            "join_date": join_date,
            "lifetime_value": ltv,
        })

    return customers


def generate_products(rng):
    """Generate 100 products across categories."""
    products = []
    product_id = 1

    for category, info in PRODUCT_DATA.items():
        for product_name in info["products"]:
            low, high = info["price_range"]
            price = round(rng.uniform(low, high), 2)
            cost_low, cost_high = info["cost_ratio"]
            cost = round(price * rng.uniform(cost_low, cost_high), 2)
            subcategory = rng.choice(info["subcategories"])
            supplier = f"Supplier-{rng.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Echo', 'Foxtrot'])}"

            products.append({
                "product_id": product_id,
                "name": product_name,
                "category": category,
                "subcategory": subcategory,
                "unit_price": price,
                "unit_cost": cost,
                "supplier": supplier,
            })
            product_id += 1

    return products


def generate_orders(rng, customers, products, sales_reps):
    """Generate 5000 orders over 2 years with seasonal patterns."""
    orders = []
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days

    for i in range(1, 5001):
        # Seasonal weighting: Q4 gets more orders
        while True:
            day_offset = rng.randint(0, total_days)
            order_date = start_date + timedelta(days=day_offset)
            month = order_date.month
            # Q4 spike: 40% more likely to keep Q4 dates
            if month in (10, 11, 12):
                break
            elif rng.random() < 0.75:
                break

        customer = rng.choice(customers)
        product = rng.choice(products)
        sales_rep = rng.choice(sales_reps)
        quantity = rng.choices([1, 2, 3, 4, 5, 10, 20, 50], weights=[40, 25, 15, 8, 5, 4, 2, 1])[0]
        discount = rng.choices([0, 0.05, 0.1, 0.15, 0.2, 0.25], weights=[50, 20, 15, 8, 5, 2])[0]
        total = round(quantity * product["unit_price"] * (1 - discount), 2)
        status = rng.choices(
            ["completed", "pending", "cancelled", "returned"],
            weights=[75, 10, 10, 5],
        )[0]

        orders.append({
            "order_id": i,
            "customer_id": customer["customer_id"],
            "product_id": product["product_id"],
            "sales_rep_id": sales_rep["sales_rep_id"],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "quantity": quantity,
            "discount": discount,
            "total": total,
            "status": status,
        })

    return orders


def generate_returns(rng, orders):
    """Generate 500 returns from completed/returned orders."""
    eligible = [o for o in orders if o["status"] in ("completed", "returned")]
    return_orders = rng.sample(eligible, min(500, len(eligible)))
    returns = []

    for i, order in enumerate(return_orders, 1):
        order_date = datetime.strptime(order["order_date"], "%Y-%m-%d")
        days_after = rng.randint(1, 60)
        return_date = order_date + timedelta(days=days_after)
        reason = rng.choice(RETURN_REASONS)
        condition = rng.choice(RETURN_CONDITIONS)
        refund_amount = round(order["total"] * rng.uniform(0.5, 1.0), 2)

        returns.append({
            "return_id": i,
            "order_id": order["order_id"],
            "return_date": return_date.strftime("%Y-%m-%d"),
            "reason": reason,
            "refund_amount": refund_amount,
            "condition": condition,
        })

    return returns


def inject_quality_issues(rng, customers, products, orders, returns):
    """Inject intentional data quality issues for the cleaning demo."""

    # 1. 15 duplicate customer records (same email, different customer_id)
    max_id = max(c["customer_id"] for c in customers)
    source_customers = rng.sample(customers[:485], 15)
    for i, src in enumerate(source_customers):
        dup = dict(src)
        dup["customer_id"] = max_id + i + 1
        dup["name"] = src["name"]  # Same name
        dup["email"] = src["email"]  # Same email = duplicate
        customers.append(dup)

    # 2. 30 orders with NULL customer_id
    null_candidates = rng.sample(range(len(orders)), 30)
    for idx in null_candidates:
        orders[idx]["customer_id"] = None

    # 3. 20 orders with mixed date formats
    mixed_candidates = rng.sample(range(len(orders)), 20)
    for idx in mixed_candidates:
        date_str = orders[idx]["order_date"]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        fmt = rng.choice(["us", "eu"])
        if fmt == "us":
            orders[idx]["order_date"] = dt.strftime("%m/%d/%Y")
        else:
            orders[idx]["order_date"] = dt.strftime("%d-%b-%Y")

    # 4. 10 products with negative prices
    neg_candidates = rng.sample(range(len(products)), 10)
    for idx in neg_candidates:
        products[idx]["unit_price"] = -abs(products[idx]["unit_price"])

    # 5. 5 orders where total != quantity * unit_price * (1 - discount)
    mismatch_candidates = rng.sample(range(len(orders)), 5)
    for idx in mismatch_candidates:
        orders[idx]["total"] = round(orders[idx]["total"] * rng.uniform(1.5, 3.0), 2)

    # 6. 8 returns with return_date before order_date
    early_candidates = rng.sample(range(len(returns)), min(8, len(returns)))
    for idx in early_candidates:
        ret = returns[idx]
        matching_order = next((o for o in orders if o["order_id"] == ret["order_id"]), None)
        if matching_order and matching_order["order_date"]:
            try:
                order_dt = datetime.strptime(matching_order["order_date"], "%Y-%m-%d")
                ret["return_date"] = (order_dt - timedelta(days=rng.randint(5, 30))).strftime("%Y-%m-%d")
            except ValueError:
                # Order date might be in mixed format, just set an early date
                ret["return_date"] = "2023-01-01"

    return customers, products, orders, returns


def write_csv(filepath, data, fieldnames):
    """Write data to a CSV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def create_database(db_path, schema_path, customers, products, orders, returns, sales_reps):
    """Create SQLite database from schema and seed data."""
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables (sales_reps first due to foreign keys)
    with open(schema_path) as f:
        schema_sql = f.read()

    # Execute each CREATE TABLE statement separately
    for statement in schema_sql.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)

    # Insert sales_reps
    for rep in sales_reps:
        cursor.execute(
            "INSERT INTO sales_reps VALUES (?, ?, ?, ?, ?)",
            (rep["sales_rep_id"], rep["name"], rep["territory"], rep["quota"], rep["hire_date"]),
        )

    # Insert customers
    for c in customers:
        cursor.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)",
            (c["customer_id"], c["name"], c["email"], c["segment"], c["region"],
             c["join_date"], c["lifetime_value"]),
        )

    # Insert products
    for p in products:
        cursor.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p["product_id"], p["name"], p["category"], p["subcategory"],
             p["unit_price"], p["unit_cost"], p["supplier"]),
        )

    # Insert orders
    for o in orders:
        cursor.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (o["order_id"], o["customer_id"], o["product_id"], o["sales_rep_id"],
             o["order_date"], o["quantity"], o["discount"], o["total"], o["status"]),
        )

    # Insert returns
    for r in returns:
        cursor.execute(
            "INSERT INTO returns VALUES (?, ?, ?, ?, ?, ?)",
            (r["return_id"], r["order_id"], r["return_date"], r["reason"],
             r["refund_amount"], r["condition"]),
        )

    conn.commit()
    conn.close()


def setup_database(db_path=None):
    """Main function to generate all seed data and create the database."""
    rng = random.Random(SEED)
    data_dir = get_data_dir()
    seed_dir = data_dir / "seed_data"

    if db_path is None:
        db_path = get_db_path()
    else:
        db_path = Path(db_path)

    schema_path = data_dir / "schema.sql"

    print("Generating seed data...")
    sales_reps = generate_sales_reps(rng)
    customers = generate_customers(rng)
    products = generate_products(rng)
    orders = generate_orders(rng, customers, products, sales_reps)
    returns = generate_returns(rng, orders)

    print("Injecting data quality issues...")
    customers, products, orders, returns = inject_quality_issues(
        rng, customers, products, orders, returns
    )

    print("Writing CSV files...")
    write_csv(seed_dir / "customers.csv", customers,
              ["customer_id", "name", "email", "segment", "region", "join_date", "lifetime_value"])
    write_csv(seed_dir / "products.csv", products,
              ["product_id", "name", "category", "subcategory", "unit_price", "unit_cost", "supplier"])
    write_csv(seed_dir / "orders.csv", orders,
              ["order_id", "customer_id", "product_id", "sales_rep_id", "order_date",
               "quantity", "discount", "total", "status"])
    write_csv(seed_dir / "returns.csv", returns,
              ["return_id", "order_id", "return_date", "reason", "refund_amount", "condition"])
    write_csv(seed_dir / "sales_reps.csv", sales_reps,
              ["sales_rep_id", "name", "territory", "quota", "hire_date"])

    print("Creating database...")
    create_database(db_path, schema_path, customers, products, orders, returns, sales_reps)

    # Verify counts
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for table in ["customers", "products", "orders", "returns", "sales_reps"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()

    print(f"Database created at {db_path}")
    return db_path


if __name__ == "__main__":
    setup_database()
