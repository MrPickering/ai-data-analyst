# AI Data Analyst

Part of the [PickBits.ai](https://pickbits.ai) portfolio — AI tools that demonstrate real-world productivity gains with Claude.

**Replace 4+ hours of manual data analysis with 30 seconds of AI-powered insight.** A Python CLI that converts natural language questions into SQL, executes them safely, detects data quality issues, and generates executive-ready reports — all powered by Claude.

## Example Output

Browse the [`examples/`](examples/) directory to see exactly what this tool produces — no API key needed:

| File | What It Shows |
|------|--------------|
| [`query-results/`](examples/query-results/) | SQL + results + narrative for 5 business questions |
| [`data-quality-report.json`](examples/data-quality-report.json) | 6 detected data quality issues with fix suggestions |
| [`narrative-report.md`](examples/narrative-report.md) | Executive narrative analysis for top products |
| [`anomaly-report.json`](examples/anomaly-report.json) | 7 statistical anomalies flagged for investigation |
| [`benchmark.json`](examples/benchmark.json) | Full run: 28s, 25K tokens, $0.16 total cost |

## How It Works

1. **Natural Language → SQL** — Ask a question in plain English; Claude generates optimized SQLite queries
2. **Safe Execution** — Queries run in read-only mode with validation (SELECT-only, 5s timeout)
3. **Data Quality Scan** — Diagnostic queries detect duplicates, NULL values, format issues, and logical impossibilities
4. **Narrative Generation** — Claude analyzes results and writes executive-ready reports with specific numbers and recommendations
5. **Anomaly Detection** — Statistical analysis identifies spikes, drops, outliers, and suspicious patterns

## Quick Start

```bash
# Clone and install
git clone https://github.com/mrpickering/ai-data-analyst.git
cd ai-data-analyst
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your Anthropic API key

# Set up the demo database (500 customers, 5000 orders, etc.)
python src/main.py setup-db

# Ask a question
python src/main.py ask -q "What were our top 5 products by revenue last quarter?"

# Run data quality analysis
python src/main.py quality

# Detect anomalies
python src/main.py anomaly

# Benchmark all sample questions
python src/main.py benchmark
```

## Token Economics

| Metric | AI Data Analyst | Manual Analysis |
|--------|----------------|-----------------|
| Time per question | ~6 seconds | ~30 minutes |
| Full 5-question run | 28 seconds | 4+ hours |
| Cost per question | ~$0.03 | ~$75 (analyst time) |
| Total cost (5 questions) | $0.16 | $375+ |
| Consistency | 100% repeatable | Varies by analyst |

## Portfolio

| Repository | Description |
|-----------|-------------|
| [ai-data-analyst](https://github.com/mrpickering/ai-data-analyst) | NL-to-SQL + data quality + anomaly detection (this repo) |

Interested in what AI-powered tooling could do for your team? [Get in touch](https://pickbits.ai/contact).

---

*Built by [PickBits.ai](https://pickbits.ai) — AI consulting that proves results before you sign.*
