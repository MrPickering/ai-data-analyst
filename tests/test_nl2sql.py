"""Tests for natural language to SQL conversion."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.nl2sql import nl_to_sql, _strip_markdown_fences


class TestStripMarkdownFences:
    def test_strips_json_fences(self):
        text = '```json\n{"sql": "SELECT 1"}\n```'
        assert _strip_markdown_fences(text) == '{"sql": "SELECT 1"}'

    def test_strips_sql_fences(self):
        text = '```sql\nSELECT 1\n```'
        assert _strip_markdown_fences(text) == "SELECT 1"

    def test_strips_plain_fences(self):
        text = '```\n{"sql": "SELECT 1"}\n```'
        assert _strip_markdown_fences(text) == '{"sql": "SELECT 1"}'

    def test_no_fences(self):
        text = '{"sql": "SELECT 1"}'
        assert _strip_markdown_fences(text) == '{"sql": "SELECT 1"}'


class TestNlToSql:
    @patch("src.nl2sql._get_client")
    def test_basic_conversion(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response(json.dumps({
            "sql": "SELECT * FROM customers LIMIT 10",
            "explanation": "Returns all customers",
            "assumptions": ["Limiting to 10 rows"],
            "confidence": 0.95,
        }))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result, usage = nl_to_sql("Show me all customers", "CREATE TABLE customers (...)")

        assert "sql" in result
        assert result["sql"] == "SELECT * FROM customers LIMIT 10"
        assert result["confidence"] == 0.95
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 200

    @patch("src.nl2sql._get_client")
    def test_strips_markdown_from_response(self, mock_get_client, mock_claude_response):
        response_text = '```json\n' + json.dumps({
            "sql": "SELECT COUNT(*) FROM orders",
            "explanation": "Counts orders",
            "assumptions": [],
            "confidence": 0.9,
        }) + '\n```'
        mock_response = mock_claude_response(response_text)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result, usage = nl_to_sql("How many orders?", "CREATE TABLE orders (...)")
        assert result["sql"] == "SELECT COUNT(*) FROM orders"

    @patch("src.nl2sql._get_client")
    def test_rejects_non_select(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response(json.dumps({
            "sql": "DELETE FROM customers",
            "explanation": "Deletes all",
            "assumptions": [],
            "confidence": 0.5,
        }))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="not a SELECT query"):
            nl_to_sql("Delete everything", "CREATE TABLE customers (...)")

    @patch("src.nl2sql._get_client")
    def test_schema_included_in_prompt(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response(json.dumps({
            "sql": "SELECT 1",
            "explanation": "Test",
            "assumptions": [],
            "confidence": 1.0,
        }))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        schema = "CREATE TABLE test_table (id INTEGER PRIMARY KEY)"
        nl_to_sql("test question", schema)

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "test_table" in user_msg

    @patch("src.nl2sql._get_client")
    def test_with_cte(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response(json.dumps({
            "sql": "WITH cte AS (SELECT 1) SELECT * FROM cte",
            "explanation": "CTE query",
            "assumptions": [],
            "confidence": 0.9,
        }))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result, usage = nl_to_sql("test", "schema")
        assert result["sql"].startswith("WITH")
