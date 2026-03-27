#!/usr/bin/env python3
"""Anomaly detection in query results using Claude."""

import json
import os
import re
import sqlite3

import anthropic


SYSTEM_PROMPT = """You are a data scientist performing anomaly detection. Given statistical summaries from a sales database, identify anomalies and business-relevant outliers.

Look for:
1. Sudden spikes or drops in metrics
2. Unusual patterns (weekend orders for B2B, midnight transactions)
3. Outlier customers (unusually high/low activity)
4. Product anomalies (sudden return rate changes)
5. Sales rep anomalies (sudden performance changes)

For each anomaly, output a JSON object with:
- type: "spike", "drop", "outlier", "pattern", or "trend"
- metric: The metric where the anomaly was found
- date: Date or period (if applicable)
- expected_value: What the value should roughly be
- actual_value: What the value actually is
- explanation: Your analysis of what might cause this
- requires_investigation: true/false

Respond with a JSON array of anomaly objects. Do not include any text outside the JSON array."""


STATISTICAL_QUERIES = {
    "monthly_revenue": """
        SELECT strftime('%Y-%m', order_date) as month,
               COUNT(*) as order_count,
               SUM(total) as revenue,
               AVG(total) as avg_order_value
        FROM orders
        WHERE order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
          AND status = 'completed'
        GROUP BY month
        ORDER BY month
    """,
    "category_performance": """
        SELECT p.category,
               COUNT(*) as order_count,
               SUM(o.total) as revenue,
               AVG(o.total) as avg_value
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        WHERE o.status = 'completed'
        GROUP BY p.category
    """,
    "return_rates_by_product": """
        SELECT p.name as product,
               p.category,
               COUNT(DISTINCT o.order_id) as total_orders,
               COUNT(DISTINCT r.return_id) as returns,
               ROUND(COUNT(DISTINCT r.return_id) * 100.0 / MAX(COUNT(DISTINCT o.order_id), 1), 2) as return_rate
        FROM products p
        JOIN orders o ON p.product_id = o.product_id
        LEFT JOIN returns r ON o.order_id = r.order_id
        GROUP BY p.product_id
        HAVING total_orders >= 5
        ORDER BY return_rate DESC
        LIMIT 20
    """,
    "rep_performance": """
        SELECT sr.name as rep_name,
               sr.territory,
               sr.quota,
               SUM(o.total) as total_sales,
               ROUND(SUM(o.total) / sr.quota * 100, 2) as quota_attainment
        FROM sales_reps sr
        JOIN orders o ON sr.sales_rep_id = o.sales_rep_id
        WHERE o.status = 'completed'
        GROUP BY sr.sales_rep_id
        ORDER BY quota_attainment DESC
    """,
    "customer_outliers": """
        SELECT c.name, c.segment,
               COUNT(o.order_id) as order_count,
               SUM(o.total) as total_spent,
               AVG(o.total) as avg_order
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 20
    """,
    "daily_order_volume": """
        SELECT order_date,
               COUNT(*) as order_count,
               SUM(total) as daily_revenue
        FROM orders
        WHERE order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        GROUP BY order_date
        ORDER BY order_count DESC
        LIMIT 20
    """,
}


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _strip_markdown_fences(text):
    """Remove markdown code fences from Claude's response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def run_statistical_queries(db_path):
    """Run all statistical queries for anomaly detection.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Dict mapping query name to results.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {}
    for name, sql in STATISTICAL_QUERIES.items():
        try:
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            results[name] = rows
        except sqlite3.Error as e:
            results[name] = {"error": str(e)}

    conn.close()
    return results


def detect_anomalies(db_path, model=None):
    """Detect anomalies in the database using statistical analysis + Claude.

    Args:
        db_path: Path to SQLite database file.
        model: Claude model to use.

    Returns:
        Tuple of (list of anomaly dicts, usage dict).
    """
    stats = run_statistical_queries(db_path)
    stats_text = json.dumps(stats, indent=2, default=str)

    client = _get_client()
    model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    user_message = f"""Statistical Summary from Sales Database:

{stats_text}

Analyze this data and identify all anomalies, outliers, and suspicious patterns."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    cleaned = _strip_markdown_fences(raw_text)
    anomalies = json.loads(cleaned)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return anomalies, usage
