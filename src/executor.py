#!/usr/bin/env python3
"""Safe SQL execution against SQLite databases."""

import re
import sqlite3
from pathlib import Path


FORBIDDEN_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA\s+\w+\s*=)\b",
    re.IGNORECASE,
)

QUERY_TIMEOUT = 5  # seconds


class ExecutionError(Exception):
    """Raised when SQL execution fails."""
    pass


class ValidationError(Exception):
    """Raised when SQL validation fails."""
    pass


def validate_query(sql):
    """Validate that query is SELECT-only (no mutations)."""
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        raise ValidationError("Empty query")

    # Check for forbidden statements
    if FORBIDDEN_PATTERNS.search(stripped):
        raise ValidationError(
            "Only SELECT queries are allowed. "
            "INSERT, UPDATE, DELETE, DROP, ALTER, and CREATE are not permitted."
        )

    # Must start with SELECT or WITH (for CTEs)
    first_word = stripped.split()[0].upper()
    if first_word not in ("SELECT", "WITH"):
        raise ValidationError(
            f"Query must start with SELECT or WITH, got '{first_word}'"
        )

    return True


def execute_query(db_path, sql):
    """Execute a read-only SQL query and return results as list of dicts.

    Args:
        db_path: Path to SQLite database file.
        sql: SQL query string (must be SELECT-only).

    Returns:
        List of dicts, one per row, with column names as keys.

    Raises:
        ValidationError: If query contains forbidden statements.
        ExecutionError: If query execution fails.
    """
    validate_query(sql)

    db_path = Path(db_path)
    if not db_path.exists():
        raise ExecutionError(f"Database not found: {db_path}")

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute(f"PRAGMA busy_timeout = {QUERY_TIMEOUT * 1000}")
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except sqlite3.Error as e:
        raise ExecutionError(f"SQL execution error: {e}")


def execute_query_raw(db_path, sql):
    """Execute a query and return (columns, rows) tuple.

    Args:
        db_path: Path to SQLite database file.
        sql: SQL query string (must be SELECT-only).

    Returns:
        Tuple of (column_names: list[str], rows: list[tuple]).
    """
    validate_query(sql)

    db_path = Path(db_path)
    if not db_path.exists():
        raise ExecutionError(f"Database not found: {db_path}")

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute(f"PRAGMA busy_timeout = {QUERY_TIMEOUT * 1000}")
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        return columns, rows
    except sqlite3.Error as e:
        raise ExecutionError(f"SQL execution error: {e}")


def get_schema(db_path):
    """Extract the full DDL schema from the database.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        String containing all CREATE TABLE statements.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise ExecutionError(f"Database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name")
    tables = cursor.fetchall()
    conn.close()

    return "\n\n".join(t[0] for t in tables)
