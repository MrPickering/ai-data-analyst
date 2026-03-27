CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    segment TEXT CHECK(segment IN ('Enterprise', 'SMB', 'Consumer')),
    region TEXT,
    join_date TEXT,
    lifetime_value REAL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    unit_price REAL,
    unit_cost REAL,
    supplier TEXT
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    product_id INTEGER REFERENCES products(product_id),
    sales_rep_id INTEGER REFERENCES sales_reps(sales_rep_id),
    order_date TEXT,
    quantity INTEGER,
    discount REAL DEFAULT 0,
    total REAL,
    status TEXT CHECK(status IN ('completed', 'pending', 'cancelled', 'returned'))
);

CREATE TABLE returns (
    return_id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    return_date TEXT,
    reason TEXT,
    refund_amount REAL,
    condition TEXT CHECK(condition IN ('defective', 'wrong_item', 'not_as_described', 'changed_mind'))
);

CREATE TABLE sales_reps (
    sales_rep_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    territory TEXT,
    quota REAL,
    hire_date TEXT
);
