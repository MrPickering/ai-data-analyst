"""Tests for the benchmark tracker."""

import json
import time

from src.benchmark import BenchmarkTracker, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN


class TestBenchmarkTracker:
    def test_start_stop(self):
        tracker = BenchmarkTracker()
        tracker.start("test_op")
        time.sleep(0.05)
        tracker.stop("test_op", input_tokens=100, output_tokens=50)

        assert len(tracker.operations) == 1
        op = tracker.operations[0]
        assert op["operation"] == "test_op"
        assert op["elapsed_seconds"] >= 0.04  # Allow some timing slack
        assert op["input_tokens"] == 100
        assert op["output_tokens"] == 50

    def test_cost_calculation(self):
        tracker = BenchmarkTracker()
        tracker.start("op")
        tracker.stop("op", input_tokens=1000, output_tokens=500)

        op = tracker.operations[0]
        expected_cost = 1000 * INPUT_COST_PER_TOKEN + 500 * OUTPUT_COST_PER_TOKEN
        assert abs(op["cost_usd"] - expected_cost) < 0.000001

    def test_summary(self):
        tracker = BenchmarkTracker()

        tracker.start("op1")
        tracker.stop("op1", input_tokens=100, output_tokens=50)

        tracker.start("op2")
        tracker.stop("op2", input_tokens=200, output_tokens=100)

        summary = tracker.summary()
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150
        assert len(summary["operations"]) == 2
        assert summary["total_time_seconds"] >= 0

    def test_multiple_operations(self):
        tracker = BenchmarkTracker()

        for i in range(5):
            tracker.start(f"op_{i}")
            tracker.stop(f"op_{i}", input_tokens=10 * i, output_tokens=5 * i)

        summary = tracker.summary()
        assert len(summary["operations"]) == 5
        assert summary["total_input_tokens"] == sum(10 * i for i in range(5))

    def test_save(self, tmp_path):
        tracker = BenchmarkTracker()
        tracker.start("op")
        tracker.stop("op", input_tokens=100, output_tokens=50)

        filepath = tmp_path / "benchmark.json"
        tracker.save(filepath)

        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert "total_time_seconds" in data
        assert "total_input_tokens" in data
        assert "operations" in data

    def test_display(self, capsys):
        tracker = BenchmarkTracker()
        tracker.start("test_op")
        tracker.stop("test_op", input_tokens=100, output_tokens=50)

        tracker.display()
        captured = capsys.readouterr()
        assert "BENCHMARK SUMMARY" in captured.out
        assert "test_op" in captured.out
        assert "TOTAL" in captured.out

    def test_zero_tokens(self):
        tracker = BenchmarkTracker()
        tracker.start("op")
        tracker.stop("op")

        op = tracker.operations[0]
        assert op["input_tokens"] == 0
        assert op["output_tokens"] == 0
        assert op["cost_usd"] == 0.0
