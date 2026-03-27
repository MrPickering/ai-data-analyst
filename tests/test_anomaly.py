"""Tests for anomaly detection."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.anomaly import detect_anomalies, run_statistical_queries


class TestRunStatisticalQueries:
    def test_returns_all_query_categories(self, tmp_db):
        results = run_statistical_queries(tmp_db)
        assert "monthly_revenue" in results
        assert "category_performance" in results
        assert "return_rates_by_product" in results
        assert "rep_performance" in results
        assert "customer_outliers" in results
        assert "daily_order_volume" in results

    def test_results_are_lists(self, tmp_db):
        results = run_statistical_queries(tmp_db)
        for name, data in results.items():
            assert isinstance(data, list), f"{name} should return a list"

    def test_monthly_revenue_structure(self, tmp_db):
        results = run_statistical_queries(tmp_db)
        if results["monthly_revenue"]:
            row = results["monthly_revenue"][0]
            assert "month" in row
            assert "order_count" in row
            assert "revenue" in row


class TestDetectAnomalies:
    @patch("src.anomaly._get_client")
    def test_returns_anomalies_list(self, mock_get_client, tmp_db, mock_claude_response):
        anomalies_data = [
            {
                "type": "spike",
                "metric": "daily_order_count",
                "date": "2024-11-29",
                "expected_value": 25,
                "actual_value": 180,
                "explanation": "Black Friday — expected seasonal spike",
                "requires_investigation": False,
            },
            {
                "type": "outlier",
                "metric": "customer_total_spend",
                "date": None,
                "expected_value": 5000,
                "actual_value": 85000,
                "explanation": "Single Enterprise customer with unusually high volume",
                "requires_investigation": True,
            },
        ]
        mock_response = mock_claude_response(json.dumps(anomalies_data))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        anomalies, usage = detect_anomalies(tmp_db)

        assert isinstance(anomalies, list)
        assert len(anomalies) == 2

    @patch("src.anomaly._get_client")
    def test_anomaly_structure(self, mock_get_client, tmp_db, mock_claude_response):
        anomalies_data = [
            {
                "type": "drop",
                "metric": "monthly_revenue",
                "date": "2024-02",
                "expected_value": 100000,
                "actual_value": 45000,
                "explanation": "Significant revenue drop in February",
                "requires_investigation": True,
            }
        ]
        mock_response = mock_claude_response(json.dumps(anomalies_data))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        anomalies, usage = detect_anomalies(tmp_db)
        anomaly = anomalies[0]

        assert "type" in anomaly
        assert "metric" in anomaly
        assert "expected_value" in anomaly
        assert "actual_value" in anomaly
        assert "explanation" in anomaly
        assert "requires_investigation" in anomaly

    @patch("src.anomaly._get_client")
    def test_usage_tracking(self, mock_get_client, tmp_db, mock_claude_response):
        mock_response = mock_claude_response("[]", input_tokens=1200, output_tokens=600)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        _, usage = detect_anomalies(tmp_db)
        assert usage["input_tokens"] == 1200
        assert usage["output_tokens"] == 600
