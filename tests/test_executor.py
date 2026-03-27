"""Tests for the safe SQL executor."""

import pytest

from src.executor import (
    ExecutionError,
    ValidationError,
    execute_query,
    execute_query_raw,
    get_schema,
    validate_query,
)


class TestValidateQuery:
    def test_valid_select(self):
        assert validate_query("SELECT * FROM customers") is True

    def test_valid_with_cte(self):
        assert validate_query("WITH cte AS (SELECT 1) SELECT * FROM cte") is True

    def test_reject_insert(self):
        with pytest.raises(ValidationError):
            validate_query("INSERT INTO customers VALUES (1, 'test')")

    def test_reject_update(self):
        with pytest.raises(ValidationError):
            validate_query("UPDATE customers SET name = 'test'")

    def test_reject_delete(self):
        with pytest.raises(ValidationError):
            validate_query("DELETE FROM customers")

    def test_reject_drop(self):
        with pytest.raises(ValidationError):
            validate_query("DROP TABLE customers")

    def test_reject_alter(self):
        with pytest.raises(ValidationError):
            validate_query("ALTER TABLE customers ADD COLUMN age INTEGER")

    def test_reject_create(self):
        with pytest.raises(ValidationError):
            validate_query("CREATE TABLE test (id INTEGER)")

    def test_reject_empty(self):
        with pytest.raises(ValidationError):
            validate_query("")

    def test_reject_non_select(self):
        with pytest.raises(ValidationError):
            validate_query("EXPLAIN SELECT * FROM customers")


class TestExecuteQuery:
    def test_basic_select(self, tmp_db):
        results = execute_query(tmp_db, "SELECT * FROM customers")
        assert len(results) == 3
        assert "customer_id" in results[0]
        assert "name" in results[0]

    def test_select_with_where(self, tmp_db):
        results = execute_query(tmp_db, "SELECT * FROM customers WHERE segment = 'Enterprise'")
        assert len(results) == 1
        assert results[0]["name"] == "Acme Corp"

    def test_select_with_join(self, tmp_db):
        results = execute_query(
            tmp_db,
            "SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.customer_id = c.customer_id"
        )
        assert len(results) > 0
        assert "order_id" in results[0]
        assert "name" in results[0]

    def test_aggregation(self, tmp_db):
        results = execute_query(
            tmp_db,
            "SELECT segment, COUNT(*) as cnt FROM customers GROUP BY segment"
        )
        assert len(results) == 3

    def test_returns_list_of_dicts(self, tmp_db):
        results = execute_query(tmp_db, "SELECT customer_id, name FROM customers LIMIT 1")
        assert isinstance(results, list)
        assert isinstance(results[0], dict)

    def test_mutation_rejected(self, tmp_db):
        with pytest.raises(ValidationError):
            execute_query(tmp_db, "INSERT INTO customers VALUES (99, 'Hacker', NULL, NULL, NULL, NULL, NULL)")

    def test_nonexistent_db(self):
        with pytest.raises(ExecutionError, match="Database not found"):
            execute_query("/nonexistent/path.db", "SELECT 1")

    def test_bad_sql(self, tmp_db):
        with pytest.raises(ExecutionError, match="SQL execution error"):
            execute_query(tmp_db, "SELECT * FROM nonexistent_table")


class TestExecuteQueryRaw:
    def test_returns_columns_and_rows(self, tmp_db):
        columns, rows = execute_query_raw(tmp_db, "SELECT customer_id, name FROM customers")
        assert columns == ["customer_id", "name"]
        assert len(rows) == 3
        assert isinstance(rows[0], tuple)


class TestGetSchema:
    def test_returns_schema(self, tmp_db):
        schema = get_schema(tmp_db)
        assert "CREATE TABLE" in schema
        assert "customers" in schema
        assert "orders" in schema
        assert "products" in schema

    def test_nonexistent_db(self):
        with pytest.raises(ExecutionError, match="Database not found"):
            get_schema("/nonexistent/path.db")
