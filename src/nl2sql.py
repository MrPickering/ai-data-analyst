#!/usr/bin/env python3
"""Natural language to SQL conversion using Claude."""

import json
import os
import re

import anthropic


SYSTEM_PROMPT = """You are a SQL expert. Given a database schema and a natural language question, generate a SQLite-compatible SQL query.

Rules:
1. Only generate SELECT queries (never INSERT, UPDATE, DELETE, DROP)
2. Use proper JOINs (never implicit cross joins)
3. Handle NULLs explicitly
4. Use appropriate aggregations
5. Format dates consistently (strftime for SQLite)
6. Add LIMIT for potentially large result sets
7. Include column aliases for readability

You MUST respond with valid JSON in this exact format:
{
  "sql": "SELECT ...",
  "explanation": "This query finds... by joining... and filtering...",
  "assumptions": ["Assuming 'last quarter' means Q4 2025", "Excluding cancelled orders"],
  "confidence": 0.95
}

Do not include any text outside the JSON object."""


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _strip_markdown_fences(text):
    """Remove markdown code fences from Claude's response."""
    text = text.strip()
    # Remove ```json ... ``` or ```sql ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json|sql)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def nl_to_sql(question, schema, model=None):
    """Convert a natural language question to SQL using Claude.

    Args:
        question: Natural language question about the data.
        schema: Database schema DDL string.
        model: Claude model to use (defaults to CLAUDE_MODEL env var).

    Returns:
        Dict with keys: sql, explanation, assumptions, confidence.
    """
    client = _get_client()
    model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    user_message = f"""Database Schema:
{schema}

Question: {question}"""

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    cleaned = _strip_markdown_fences(raw_text)

    result = json.loads(cleaned)

    # Validate the SQL is SELECT-only
    sql = result.get("sql", "").strip()
    first_word = sql.split()[0].upper() if sql else ""
    if first_word not in ("SELECT", "WITH"):
        raise ValueError(f"Generated SQL is not a SELECT query: {sql[:50]}")

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return result, usage
