"""Shared test fixtures for the AI Data Analyst test suite."""

import sqlite3
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def data_dir():
    """Return the path to the data directory."""
    return Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def db_path(data_dir):
    """Return the path to the pre-built sales database."""
    path = data_dir / "sales.db"
    assert path.exists(), f"Database not found at {path}. Run `python src/db_setup.py` first."
    return str(path)


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database with the schema and minimal data."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE sales_reps (
            sales_rep_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            territory TEXT,
            quota REAL,
            hire_date TEXT
        );

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

        INSERT INTO sales_reps VALUES (1, 'Alice Rep', 'Northeast', 300000, '2022-01-15');
        INSERT INTO sales_reps VALUES (2, 'Bob Rep', 'West', 250000, '2023-06-01');

        INSERT INTO customers VALUES (1, 'Acme Corp', 'acme@example.com', 'Enterprise', 'Northeast', '2023-01-01', 150000);
        INSERT INTO customers VALUES (2, 'Small Biz', 'small@example.com', 'SMB', 'West', '2023-06-15', 5000);
        INSERT INTO customers VALUES (3, 'Jane Consumer', 'jane@example.com', 'Consumer', 'Southeast', '2024-01-01', 500);

        INSERT INTO products VALUES (1, 'Pro Laptop', 'Electronics', 'Laptops', 1500.00, 900.00, 'Supplier-Alpha');
        INSERT INTO products VALUES (2, 'Office Chair', 'Office', 'Furniture', 350.00, 175.00, 'Supplier-Beta');
        INSERT INTO products VALUES (3, 'Antivirus Pro', 'Software', 'Security', 99.99, 15.00, 'Supplier-Gamma');

        INSERT INTO orders VALUES (1, 1, 1, 1, '2024-06-15', 2, 0.1, 2700.00, 'completed');
        INSERT INTO orders VALUES (2, 2, 2, 2, '2024-07-20', 5, 0.0, 1750.00, 'completed');
        INSERT INTO orders VALUES (3, 3, 3, 1, '2024-08-01', 1, 0.0, 99.99, 'completed');
        INSERT INTO orders VALUES (4, 1, 2, 2, '2024-09-10', 3, 0.15, 892.50, 'pending');
        INSERT INTO orders VALUES (5, 2, 1, 1, '2024-10-05', 1, 0.0, 1500.00, 'returned');

        INSERT INTO returns VALUES (1, 5, '2024-10-15', 'Wrong item shipped', 1500.00, 'wrong_item');
    """)

    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude API response."""
    def _make_response(text, input_tokens=100, output_tokens=200):
        response = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        response.content = [content_block]
        response.usage = MagicMock()
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        return response
    return _make_response
