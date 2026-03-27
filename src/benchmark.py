#!/usr/bin/env python3
"""Token usage and timing tracker for benchmarking Claude API calls."""

import json
import time
from pathlib import Path


# Approximate costs per token (Claude Sonnet 4)
INPUT_COST_PER_TOKEN = 3.0 / 1_000_000   # $3 per million input tokens
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000  # $15 per million output tokens


class BenchmarkTracker:
    """Tracks timing and token usage across operations."""

    def __init__(self):
        self.operations = []
        self._active = {}

    def start(self, operation):
        """Start timing an operation.

        Args:
            operation: Name/identifier for the operation.
        """
        self._active[operation] = time.time()

    def stop(self, operation, input_tokens=0, output_tokens=0):
        """Stop timing an operation and record token usage.

        Args:
            operation: Name/identifier for the operation.
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens used.
        """
        start_time = self._active.pop(operation, None)
        elapsed = time.time() - start_time if start_time else 0.0

        self.operations.append({
            "operation": operation,
            "elapsed_seconds": round(elapsed, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(
                input_tokens * INPUT_COST_PER_TOKEN + output_tokens * OUTPUT_COST_PER_TOKEN,
                6,
            ),
        })

    def summary(self):
        """Return a summary dict of all operations.

        Returns:
            Dict with total_time, total_input_tokens, total_output_tokens,
            total_cost_usd, and per-operation breakdown.
        """
        total_time = sum(op["elapsed_seconds"] for op in self.operations)
        total_input = sum(op["input_tokens"] for op in self.operations)
        total_output = sum(op["output_tokens"] for op in self.operations)
        total_cost = sum(op["cost_usd"] for op in self.operations)

        return {
            "total_time_seconds": round(total_time, 3),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "operations": self.operations,
        }

    def display(self):
        """Print a formatted summary table."""
        summary = self.summary()
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        print(f"{'Operation':<30} {'Time (s)':<10} {'In Tokens':<12} {'Out Tokens':<12} {'Cost ($)':<10}")
        print(f"{'-'*30} {'-'*10} {'-'*12} {'-'*12} {'-'*10}")

        for op in self.operations:
            print(
                f"{op['operation']:<30} "
                f"{op['elapsed_seconds']:<10.3f} "
                f"{op['input_tokens']:<12} "
                f"{op['output_tokens']:<12} "
                f"${op['cost_usd']:<9.4f}"
            )

        print(f"{'-'*30} {'-'*10} {'-'*12} {'-'*12} {'-'*10}")
        print(
            f"{'TOTAL':<30} "
            f"{summary['total_time_seconds']:<10.3f} "
            f"{summary['total_input_tokens']:<12} "
            f"{summary['total_output_tokens']:<12} "
            f"${summary['total_cost_usd']:<9.4f}"
        )
        print(f"{'='*60}\n")

    def save(self, filepath):
        """Save benchmark results to a JSON file.

        Args:
            filepath: Path to write the JSON output.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.summary(), f, indent=2)
