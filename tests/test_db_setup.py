"""Tests for database setup and seed data generation."""

import sqlite3
from pathlib import Path

from src.db_setup import (
    generate_customers,
    generate_orders,
    generate_products,
    generate_returns,
    generate_sales_reps,
    inject_quality_issues,
    setup_database,
)
import random


def test_setup_database_creates_file(tmp_path):
    """Test that setup_database creates a database file."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))
    assert db_path.exists()


def test_setup_database_row_counts(tmp_path):
    """Test that the database has the expected number of rows."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sales_reps")
    assert cursor.fetchone()[0] == 20

    cursor.execute("SELECT COUNT(*) FROM customers")
    # 500 + 15 duplicates
    assert cursor.fetchone()[0] == 515

    cursor.execute("SELECT COUNT(*) FROM products")
    assert cursor.fetchone()[0] == 100

    cursor.execute("SELECT COUNT(*) FROM orders")
    assert cursor.fetchone()[0] == 5000

    cursor.execute("SELECT COUNT(*) FROM returns")
    assert cursor.fetchone()[0] == 500

    conn.close()


def test_customer_segments(tmp_path):
    """Test customer segment distribution."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT segment, COUNT(*) FROM customers GROUP BY segment ORDER BY segment")
    segments = dict(cursor.fetchall())

    # Should have all three segments
    assert "Enterprise" in segments
    assert "SMB" in segments
    assert "Consumer" in segments

    conn.close()


def test_data_quality_duplicate_customers(tmp_path):
    """Test that duplicate customer records were injected."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email, COUNT(*) as cnt
        FROM customers
        WHERE email IS NOT NULL
        GROUP BY email
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    assert len(duplicates) == 15

    conn.close()


def test_data_quality_null_customer_orders(tmp_path):
    """Test that orders with NULL customer_id were injected."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_id IS NULL")
    count = cursor.fetchone()[0]
    assert count == 30

    conn.close()


def test_data_quality_negative_prices(tmp_path):
    """Test that products with negative prices were injected."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM products WHERE unit_price < 0")
    count = cursor.fetchone()[0]
    assert count == 10

    conn.close()


def test_data_quality_mixed_date_formats(tmp_path):
    """Test that orders with mixed date formats were injected."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    """)
    count = cursor.fetchone()[0]
    assert count == 20

    conn.close()


def test_data_quality_returns_before_orders(tmp_path):
    """Test that returns with return_date before order_date were injected."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM returns r
        JOIN orders o ON r.order_id = o.order_id
        WHERE r.return_date < o.order_date
          AND o.order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    """)
    count = cursor.fetchone()[0]
    assert count >= 1  # At least some returns before orders

    conn.close()


def test_deterministic_generation():
    """Test that seed data generation is deterministic."""
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    reps1 = generate_sales_reps(rng1)
    reps2 = generate_sales_reps(rng2)

    assert reps1 == reps2


def test_csv_files_created(tmp_path):
    """Test that CSV files are created."""
    db_path = tmp_path / "test_sales.db"
    setup_database(str(db_path))

    seed_dir = Path(__file__).resolve().parent.parent / "data" / "seed_data"
    assert (seed_dir / "customers.csv").exists()
    assert (seed_dir / "products.csv").exists()
    assert (seed_dir / "orders.csv").exists()
    assert (seed_dir / "returns.csv").exists()
    assert (seed_dir / "sales_reps.csv").exists()
