#!/usr/bin/env python3
"""Data quality detection and fixing using Claude."""

import json
import os
import re
import sqlite3

import anthropic

SYSTEM_PROMPT = """You are a data quality analyst. Given diagnostic results from a database, identify and document all data quality issues.

For each issue found, output a JSON object with these fields:
- issue_id: A unique identifier like "DQ-001"
- type: One of "duplicate", "null_values", "format_inconsistency", "referential_integrity", "logical_impossibility", "calculated_mismatch"
- table: The affected table name
- affected_rows: Number of rows affected
- severity: "high", "medium", or "low"
- description: Clear description of the issue
- fix_sql: A SQL statement that would fix the issue
- impact: Business impact of the issue

Respond with a JSON array of issue objects. Do not include any text outside the JSON array."""


DIAGNOSTIC_QUERIES = {
    "duplicate_customers": {
        "description": "Customers with duplicate emails",
        "sql": """
            SELECT email, COUNT(*) as cnt, GROUP_CONCAT(customer_id) as ids
            FROM customers
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING COUNT(*) > 1
        """,
    },
    "null_customer_orders": {
        "description": "Orders with NULL customer_id",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM orders
            WHERE customer_id IS NULL
        """,
    },
    "mixed_date_formats": {
        "description": "Orders with non-standard date formats",
        "sql": """
            SELECT order_id, order_date
            FROM orders
            WHERE order_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            LIMIT 25
        """,
    },
    "negative_prices": {
        "description": "Products with negative prices",
        "sql": """
            SELECT product_id, name, unit_price
            FROM products
            WHERE unit_price < 0
        """,
    },
    "total_mismatches": {
        "description": "Orders where total doesn't match quantity * unit_price * (1 - discount)",
        "sql": """
            SELECT o.order_id, o.quantity, p.unit_price, o.discount, o.total,
                   ROUND(o.quantity * p.unit_price * (1 - o.discount), 2) as expected_total
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            WHERE ABS(o.total - ROUND(o.quantity * p.unit_price * (1 - o.discount), 2)) > 0.01
            LIMIT 20
        """,
    },
    "returns_before_orders": {
        "description": "Returns with return_date before order_date",
        "sql": """
            SELECT r.return_id, r.order_id, r.return_date, o.order_date
            FROM returns r
            JOIN orders o ON r.order_id = o.order_id
            WHERE r.return_date < o.order_date
              AND o.order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        """,
    },
    "orphan_orders": {
        "description": "Orders referencing non-existent customers",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.customer_id IS NOT NULL AND c.customer_id IS NULL
        """,
    },
    "statistical_outliers": {
        "description": "Orders with total > 3 standard deviations from mean",
        "sql": """
            SELECT order_id, total,
                   (SELECT AVG(total) FROM orders) as mean_total,
                   (SELECT AVG(total * total) - AVG(total) * AVG(total) FROM orders) as variance
            FROM orders
            WHERE ABS(total - (SELECT AVG(total) FROM orders)) >
                  3 * SQRT((SELECT AVG(total * total) - AVG(total) * AVG(total) FROM orders))
            LIMIT 20
        """,
    },
}


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _strip_markdown_fences(text):
    """Remove markdown code fences from Claude's response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def run_diagnostics(db_path):
    """Run all diagnostic queries against the database.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Dict mapping diagnostic name to results.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {}
    for name, diag in DIAGNOSTIC_QUERIES.items():
        try:
            cursor.execute(diag["sql"])
            rows = [dict(row) for row in cursor.fetchall()]
            results[name] = {
                "description": diag["description"],
                "results": rows,
                "count": len(rows),
            }
        except sqlite3.Error as e:
            results[name] = {
                "description": diag["description"],
                "error": str(e),
                "count": 0,
            }

    conn.close()
    return results


def detect_quality_issues(db_path, model=None):
    """Detect data quality issues using diagnostics + Claude analysis.

    Args:
        db_path: Path to SQLite database file.
        model: Claude model to use.

    Returns:
        Tuple of (list of issue dicts, usage dict).
    """
    diagnostics = run_diagnostics(db_path)
    diagnostics_text = json.dumps(diagnostics, indent=2, default=str)

    # Get schema for context
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
    schema = "\n\n".join(row[0] for row in cursor.fetchall())
    conn.close()

    client = _get_client()
    model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    user_message = f"""Database Schema:
{schema}

Diagnostic Results:
{diagnostics_text}

Analyze these diagnostic results and produce a comprehensive data quality report."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    cleaned = _strip_markdown_fences(raw_text)
    issues = json.loads(cleaned)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return issues, usage
