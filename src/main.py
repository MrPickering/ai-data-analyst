#!/usr/bin/env python3
"""CLI entry point for the AI Data Analyst tool."""

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src.anomaly import detect_anomalies
from src.benchmark import BenchmarkTracker
from src.cleaner import detect_quality_issues, run_diagnostics
from src.db_setup import setup_database
from src.executor import execute_query, get_schema, ExecutionError, ValidationError
from src.narrator import generate_narrative
from src.nl2sql import nl_to_sql

load_dotenv()

console = Console()

DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "data" / "sales.db")


@click.group()
@click.option("--db", default=DEFAULT_DB, help="Path to SQLite database.", show_default=True)
@click.option("--model", default=None, help="Claude model override.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx, db, model, verbose):
    """AI Data Analyst — Claude-powered data analysis in seconds."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db
    ctx.obj["model"] = model
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--question", "-q", required=True, help="Natural language question about your data.")
@click.pass_context
def ask(ctx, question):
    """Ask a natural language question about your data."""
    db_path = ctx.obj["db"]
    model = ctx.obj["model"]
    verbose = ctx.obj["verbose"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.[/red]")
        sys.exit(1)

    tracker = BenchmarkTracker()

    # Step 1: Get schema
    schema = get_schema(db_path)

    # Step 2: Convert NL to SQL
    console.print(f"\n[bold]Question:[/bold] {question}\n")
    tracker.start("nl2sql")
    try:
        result, usage = nl_to_sql(question, schema, model=model)
    except Exception as e:
        console.print(f"[red]Error generating SQL: {e}[/red]")
        sys.exit(1)
    tracker.stop("nl2sql", **usage)

    sql = result["sql"]
    if verbose:
        console.print(f"[dim]SQL: {sql}[/dim]")
        console.print(f"[dim]Confidence: {result.get('confidence', 'N/A')}[/dim]")
        console.print(f"[dim]Explanation: {result.get('explanation', 'N/A')}[/dim]\n")

    # Step 3: Execute SQL
    tracker.start("execute")
    try:
        rows = execute_query(db_path, sql)
    except (ExecutionError, ValidationError) as e:
        console.print(f"[red]Error executing SQL: {e}[/red]")
        sys.exit(1)
    tracker.stop("execute")

    # Display results table
    if rows:
        table = Table(title="Query Results")
        for col in rows[0].keys():
            table.add_column(col)
        for row in rows[:50]:  # Limit display
            table.add_row(*[str(v) for v in row.values()])
        console.print(table)
    else:
        console.print("[yellow]No results found.[/yellow]")

    # Step 4: Generate narrative
    tracker.start("narrative")
    try:
        narrative, usage = generate_narrative(question, sql, rows, model=model)
    except Exception as e:
        console.print(f"[red]Error generating narrative: {e}[/red]")
        sys.exit(1)
    tracker.stop("narrative", **usage)

    console.print("\n")
    console.print(Markdown(narrative))

    if verbose:
        tracker.display()


@cli.command()
@click.pass_context
def quality(ctx):
    """Detect data quality issues in the database."""
    db_path = ctx.obj["db"]
    model = ctx.obj["model"]
    verbose = ctx.obj["verbose"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.[/red]")
        sys.exit(1)

    tracker = BenchmarkTracker()

    console.print("\n[bold]Running data quality analysis...[/bold]\n")

    if verbose:
        console.print("[dim]Running diagnostic queries...[/dim]")
        diagnostics = run_diagnostics(db_path)
        for name, result in diagnostics.items():
            count = result.get("count", 0)
            console.print(f"  [dim]{name}: {count} issues found[/dim]")
        console.print()

    tracker.start("quality_analysis")
    try:
        issues, usage = detect_quality_issues(db_path, model=model)
    except Exception as e:
        console.print(f"[red]Error detecting quality issues: {e}[/red]")
        sys.exit(1)
    tracker.stop("quality_analysis", **usage)

    # Display issues
    for issue in issues:
        severity = issue.get("severity", "unknown")
        color = {"high": "red", "medium": "yellow", "low": "blue"}.get(severity, "white")
        console.print(f"[{color} bold]{issue.get('issue_id', '?')}[/{color} bold] "
                       f"[{color}][{severity.upper()}][/{color}] "
                       f"{issue.get('description', 'Unknown issue')}")
        console.print(f"  Table: {issue.get('table', '?')} | "
                       f"Affected rows: {issue.get('affected_rows', '?')}")
        console.print(f"  Impact: {issue.get('impact', 'Unknown')}")
        if verbose and issue.get("fix_sql"):
            console.print(f"  [dim]Fix: {issue['fix_sql']}[/dim]")
        console.print()

    console.print(f"[bold]Total issues found: {len(issues)}[/bold]")

    if verbose:
        tracker.display()

    # Save report
    output_dir = Path(db_path).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "data-quality-report.json"
    with open(report_path, "w") as f:
        json.dump(issues, f, indent=2)
    console.print(f"\nReport saved to {report_path}")


@cli.command("anomaly")
@click.pass_context
def anomaly_cmd(ctx):
    """Detect anomalies in the data."""
    db_path = ctx.obj["db"]
    model = ctx.obj["model"]
    verbose = ctx.obj["verbose"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.[/red]")
        sys.exit(1)

    tracker = BenchmarkTracker()

    console.print("\n[bold]Running anomaly detection...[/bold]\n")

    tracker.start("anomaly_detection")
    try:
        anomalies, usage = detect_anomalies(db_path, model=model)
    except Exception as e:
        console.print(f"[red]Error detecting anomalies: {e}[/red]")
        sys.exit(1)
    tracker.stop("anomaly_detection", **usage)

    for anomaly in anomalies:
        atype = anomaly.get("type", "unknown")
        investigate = anomaly.get("requires_investigation", False)
        icon = "[red]![/red]" if investigate else "[green]~[/green]"
        console.print(f"  {icon} [{atype.upper()}] {anomaly.get('metric', 'Unknown metric')}")
        console.print(f"    Expected: {anomaly.get('expected_value', '?')} | "
                       f"Actual: {anomaly.get('actual_value', '?')}")
        console.print(f"    {anomaly.get('explanation', '')}")
        console.print()

    console.print(f"[bold]Total anomalies found: {len(anomalies)}[/bold]")

    if verbose:
        tracker.display()

    # Save report
    output_dir = Path(db_path).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "anomaly-report.json"
    with open(report_path, "w") as f:
        json.dump(anomalies, f, indent=2)
    console.print(f"\nReport saved to {report_path}")


@cli.command("setup-db")
@click.option("--path", default=None, help="Custom database path.")
@click.pass_context
def setup_db(ctx, path):
    """Create or recreate the database with seed data."""
    db_path = path or ctx.obj["db"]
    console.print(f"\n[bold]Setting up database at {db_path}...[/bold]\n")
    setup_database(db_path)
    console.print("\n[green]Database setup complete![/green]")


@cli.command()
@click.option("--questions-file", default=None, help="Path to questions JSON file.")
@click.pass_context
def benchmark(ctx, questions_file):
    """Run all sample questions and track timing/token usage."""
    db_path = ctx.obj["db"]
    model = ctx.obj["model"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.[/red]")
        sys.exit(1)

    if questions_file is None:
        questions_file = Path(__file__).resolve().parent.parent / "data" / "questions" / "basic-queries.json"

    with open(questions_file) as f:
        questions = json.load(f)

    schema = get_schema(db_path)
    tracker = BenchmarkTracker()

    console.print(f"\n[bold]Running benchmark with {len(questions)} questions...[/bold]\n")

    for q in questions:
        question = q["question"]
        console.print(f"[bold]Q{q['id']}:[/bold] {question}")

        # NL to SQL
        tracker.start(f"q{q['id']}_nl2sql")
        try:
            result, usage = nl_to_sql(question, schema, model=model)
            tracker.stop(f"q{q['id']}_nl2sql", **usage)

            # Execute
            tracker.start(f"q{q['id']}_execute")
            rows = execute_query(db_path, result["sql"])
            tracker.stop(f"q{q['id']}_execute")

            # Narrative
            tracker.start(f"q{q['id']}_narrative")
            narrative, usage = generate_narrative(question, result["sql"], rows, model=model)
            tracker.stop(f"q{q['id']}_narrative", **usage)

            console.print(f"  [green]OK[/green] — {len(rows)} rows, "
                           f"confidence: {result.get('confidence', 'N/A')}")
        except Exception as e:
            console.print(f"  [red]FAILED: {e}[/red]")
            # Still stop any active timers
            for key in list(tracker._active.keys()):
                if key.startswith(f"q{q['id']}"):
                    tracker.stop(key)

    tracker.display()

    # Save benchmark results
    output_dir = Path(db_path).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    tracker.save(output_dir / "benchmark.json")
    console.print(f"Results saved to {output_dir / 'benchmark.json'}")


if __name__ == "__main__":
    cli()
