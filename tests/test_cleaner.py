"""Tests for data quality detection."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.cleaner import detect_quality_issues, run_diagnostics


class TestRunDiagnostics:
    def test_returns_all_diagnostic_categories(self, tmp_db):
        results = run_diagnostics(tmp_db)
        assert "duplicate_customers" in results
        assert "null_customer_orders" in results
        assert "mixed_date_formats" in results
        assert "negative_prices" in results
        assert "total_mismatches" in results
        assert "returns_before_orders" in results

    def test_diagnostic_result_structure(self, tmp_db):
        results = run_diagnostics(tmp_db)
        for name, result in results.items():
            assert "description" in result
            assert "count" in result or "error" in result

    def test_no_issues_in_clean_db(self, tmp_db):
        results = run_diagnostics(tmp_db)
        # The tmp_db has clean data, so most diagnostics should find 0 issues
        assert results["negative_prices"]["count"] == 0
        assert results["mixed_date_formats"]["count"] == 0

    def test_diagnostics_on_full_db(self, db_path):
        results = run_diagnostics(db_path)
        # Full DB has injected issues
        assert results["duplicate_customers"]["count"] > 0
        assert results["negative_prices"]["count"] > 0


class TestDetectQualityIssues:
    @patch("src.cleaner._get_client")
    def test_returns_issues_list(self, mock_get_client, tmp_db, mock_claude_response):
        issues_data = [
            {
                "issue_id": "DQ-001",
                "type": "duplicate",
                "table": "customers",
                "affected_rows": 15,
                "severity": "high",
                "description": "15 duplicate customers by email",
                "fix_sql": "DELETE FROM customers WHERE customer_id IN (...)",
                "impact": "Order totals may be inflated",
            }
        ]
        mock_response = mock_claude_response(json.dumps(issues_data))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        issues, usage = detect_quality_issues(tmp_db)

        assert isinstance(issues, list)
        assert len(issues) == 1
        assert issues[0]["issue_id"] == "DQ-001"
        assert issues[0]["severity"] == "high"

    @patch("src.cleaner._get_client")
    def test_issue_structure(self, mock_get_client, tmp_db, mock_claude_response):
        issues_data = [
            {
                "issue_id": "DQ-001",
                "type": "null_values",
                "table": "orders",
                "affected_rows": 30,
                "severity": "medium",
                "description": "30 orders with NULL customer_id",
                "fix_sql": "UPDATE orders SET customer_id = ...",
                "impact": "Cannot attribute revenue to customers",
            }
        ]
        mock_response = mock_claude_response(json.dumps(issues_data))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        issues, usage = detect_quality_issues(tmp_db)

        issue = issues[0]
        assert "issue_id" in issue
        assert "type" in issue
        assert "table" in issue
        assert "affected_rows" in issue
        assert "severity" in issue
        assert "description" in issue
        assert "fix_sql" in issue
        assert "impact" in issue

    @patch("src.cleaner._get_client")
    def test_usage_tracking(self, mock_get_client, tmp_db, mock_claude_response):
        mock_response = mock_claude_response("[]", input_tokens=500, output_tokens=300)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        issues, usage = detect_quality_issues(tmp_db)
        assert usage["input_tokens"] == 500
        assert usage["output_tokens"] == 300
