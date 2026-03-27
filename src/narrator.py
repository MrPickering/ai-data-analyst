#!/usr/bin/env python3
"""Report narrative generation using Claude."""

import os

import anthropic
from tabulate import tabulate


SYSTEM_PROMPT = """You are a business intelligence analyst writing an executive report. Given query results (data tables), generate a narrative summary.

Requirements:
1. Lead with the key insight (the "so what")
2. Support with specific numbers from the data
3. Compare to context (month-over-month, year-over-year if available)
4. Identify trends and patterns
5. Recommend actions based on findings
6. Use business language, not technical jargon

Tone: Confident, data-driven, actionable. As if presenting to a VP of Sales.

Format your response in markdown with clear headings and bullet points."""


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def generate_narrative(question, sql, results, model=None):
    """Generate a narrative report from query results using Claude.

    Args:
        question: The original natural language question.
        sql: The SQL query that was executed.
        results: List of dicts (query results).
        model: Claude model to use.

    Returns:
        Tuple of (narrative markdown string, usage dict).
    """
    client = _get_client()
    model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # Format results as a table
    if results:
        headers = list(results[0].keys())
        rows = [list(r.values()) for r in results]
        table_str = tabulate(rows, headers=headers, tablefmt="grid")
    else:
        table_str = "(No results)"

    user_message = f"""Question: {question}

SQL Query Used:
{sql}

Query Results:
{table_str}

Please provide an executive narrative analysis of these results."""

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    narrative = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return narrative, usage
