"""Tests for report narrative generation."""

from unittest.mock import patch, MagicMock

import pytest

from src.narrator import generate_narrative


class TestGenerateNarrative:
    @patch("src.narrator._get_client")
    def test_basic_narrative(self, mock_get_client, mock_claude_response):
        narrative_text = """## Key Findings

Revenue increased by 15% this quarter, driven by Enterprise segment growth.

### Recommendations
- Focus on Enterprise upsells
- Investigate SMB churn
"""
        mock_response = mock_claude_response(narrative_text)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        results = [
            {"segment": "Enterprise", "revenue": 150000},
            {"segment": "SMB", "revenue": 75000},
        ]

        narrative, usage = generate_narrative(
            "What is revenue by segment?",
            "SELECT segment, SUM(total) as revenue FROM orders GROUP BY segment",
            results,
        )

        assert "Key Findings" in narrative
        assert isinstance(narrative, str)
        assert usage["input_tokens"] == 100

    @patch("src.narrator._get_client")
    def test_empty_results(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response("No data available for this query.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        narrative, usage = generate_narrative(
            "Show me Q5 data",
            "SELECT * FROM orders WHERE 1=0",
            [],
        )

        assert isinstance(narrative, str)

    @patch("src.narrator._get_client")
    def test_prompt_includes_question_and_results(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response("Analysis here.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        results = [{"product": "Laptop", "revenue": 50000}]
        generate_narrative(
            "Top products by revenue?",
            "SELECT product, SUM(total) FROM orders",
            results,
        )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "Top products by revenue?" in user_msg
        assert "Laptop" in user_msg

    @patch("src.narrator._get_client")
    def test_usage_tracking(self, mock_get_client, mock_claude_response):
        mock_response = mock_claude_response("Report.", input_tokens=800, output_tokens=400)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        _, usage = generate_narrative("Q?", "SELECT 1", [{"a": 1}])
        assert usage["input_tokens"] == 800
        assert usage["output_tokens"] == 400
