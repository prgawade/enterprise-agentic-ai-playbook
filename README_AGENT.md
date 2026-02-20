# Stock Analyst Agent

An agentic stock analysis tool that accepts a stock ticker/name, pulls live
context from the NSE/BSE MCP server, and runs **16 analytical prompts** through
pluggable LLM backends (Ollama or Gemini).  A `mock` backend is included for
offline testing with no credentials required.

---

## Table of Contents

1. [Features](#features)
2. [Project structure](#project-structure)
3. [Quick start](#quick-start)
4. [Configuration](#configuration)
5. [CLI usage](#cli-usage)
6. [Python API](#python-api)
7. [LLM backends](#llm-backends)
8. [MCP server](#mcp-server)
9. [Output formats](#output-formats)
10. [The 16 analytical prompts](#the-16-analytical-prompts)

---

## Features

- **16 analytical prompts** covering market mindset, trend analysis, bull/bear
  cases, risk/reward, earnings expectations, valuation, scenario planning, and more.
- **Live market data** via the NSE/BSE MCP server (price, fundamentals, news).
- **Pluggable LLM backends**: Ollama (local), Gemini (cloud), or Mock (offline).
- **In-memory cache** with configurable TTL to avoid hammering the MCP server.
- **CLI and Python API** for flexible integration.
- **JSON + Markdown** report output.
- **No secrets in source code** – all credentials via environment variables.

---

## Project structure

```
.
├── main.py                # CLI entry point
├── stock_analyst_agent.py # 16 prompts + StockAnalystAgent class + ModelClients
├── mcp_client.py          # Sync/async MCP HTTP client with caching
├── config.py              # Centralised configuration + env validation
├── example_usage.py       # Smoke-check / usage examples (mock mode)
├── requirements.txt       # Minimal Python dependencies
├── .env.example           # Environment variable template (copy to .env)
└── README_AGENT.md        # This file
```

---

## Quick start

```bash
# 1. Clone the repository (or navigate to it)
cd enterprise-agentic-ai-playbook

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env – at minimum set MCP_URL, and whichever LLM key you want to use.

# 5. Run the smoke-check (no credentials needed)
python example_usage.py

# 6. Analyse a stock with the mock model
python main.py TCS --model mock --no-mcp
```

---

## Configuration

All settings are read from environment variables (loaded automatically from a
`.env` file if present via `python-dotenv`).  See `.env.example` for all
available variables.

| Variable | Default | Description |
|---|---|---|
| `MCP_URL` | `https://lobehub.com/mcp/girishkumardv-live-nse-bse-mcp` | NSE/BSE MCP server URL |
| `MCP_API_KEY` | *(empty)* | Optional MCP server API key |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `GEMINI_API_KEY` | *(required for Gemini)* | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `CACHE_TTL_SECONDS` | `300` | MCP response cache TTL |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## CLI usage

```
usage: main.py [-h] [--model {ollama,gemini,mock}] [--prompts PROMPT_ID [PROMPT_ID ...]]
               [--mcp-url MCP_URL] [--no-mcp] [--export-md] [--interactive]
               [--list-prompts]
               [stock_name]
```

### Examples

```bash
# Analyse TCS with Ollama (requires local Ollama + model)
python main.py TCS --model ollama

# Analyse RELIANCE with Gemini, export Markdown report
python main.py RELIANCE --model gemini --export-md

# Run only two prompts for INFY
python main.py INFY --model mock --prompts 3_bull_vs_bear 9_valuation_sanity

# Use a custom MCP server URL
python main.py HDFC --mcp-url http://my-mcp-server:8080

# Disable live data (no MCP call)
python main.py WIPRO --no-mcp --model mock

# Interactive REPL mode
python main.py --interactive --model mock

# List all available prompt IDs
python main.py --list-prompts
```

---

## Python API

```python
from stock_analyst_agent import StockAnalystAgent, MockModelClient
from mcp_client import SyncMCPStockClient

# --- Mock run (no credentials needed) ---
agent = StockAnalystAgent(model="mock", model_client=MockModelClient())
result = agent.analyze_stock("TCS")
print(agent.to_markdown())

# --- With live MCP data ---
mcp = SyncMCPStockClient()          # reads MCP_URL from env
context = mcp.get_stock_context("RELIANCE")

agent = StockAnalystAgent(model="ollama")   # reads OLLAMA_URL from env
result = agent.analyze_stock("RELIANCE", live_context=context)
agent.save_report()                  # saves JSON
agent.export_markdown_report()       # saves Markdown

# --- Run a subset of prompts ---
result = agent.analyze_stock(
    "INFY",
    prompt_ids=["3_bull_vs_bear", "9_valuation_sanity", "14_decision_clarity"],
)
```

---

## LLM backends

### Mock (offline, no credentials)

The `mock` backend echoes a placeholder response and is ideal for CI and
smoke-testing.  No setup required.

```bash
python main.py TCS --model mock
```

### Ollama (local)

1. Install Ollama: <https://ollama.ai>
2. Pull a model: `ollama pull llama3`
3. Set `OLLAMA_URL` and `OLLAMA_MODEL` in `.env` (or use defaults).
4. Run: `python main.py TCS --model ollama`

### Gemini (Google Cloud)

1. Get an API key from <https://aistudio.google.com/app/apikey>.
2. Set `GEMINI_API_KEY=<your-key>` in `.env`.
3. Optionally set `GEMINI_MODEL` (default: `gemini-1.5-flash`).
4. Run: `python main.py TCS --model gemini`

> **Wiring your own LLM**: Subclass `ModelClient` in `stock_analyst_agent.py`
> and override the `complete(prompt: str) -> str` method.  Pass your instance
> via `StockAnalystAgent(model_client=MyClient())`.

---

## MCP server

The default MCP server is the public NSE/BSE live data endpoint:

```
https://lobehub.com/mcp/girishkumardv-live-nse-bse-mcp
```

The client calls three sub-paths:

| Endpoint | Purpose |
|---|---|
| `/stock/{symbol}/price` | Latest price, change, volume |
| `/stock/{symbol}/fundamentals` | P/E, EPS, market cap, sector, … |
| `/stock/{symbol}/news` | Recent headlines |

Responses are cached in memory for `CACHE_TTL_SECONDS` (default 5 min).
Network errors are caught and logged; the agent continues with partial context.

To use a private/on-premise MCP server:

```bash
python main.py TCS --mcp-url http://my-server:8080
# or permanently via:
export MCP_URL=http://my-server:8080
```

---

## Output formats

### JSON

Saved automatically by `main.py` as `<TICKER>_<timestamp>_analysis.json`.

```json
{
  "stock_name": "TCS",
  "timestamp": "2024-01-15T10:30:00Z",
  "model": "ollama",
  "prompts_run": ["1_market_mindset", "..."],
  "results": {
    "1_market_mindset": {
      "prompt": "Market Mindset Check for TCS: ...",
      "response": "..."
    }
  },
  "summary": "...",
  "live_data": { ... }
}
```

### Markdown

Export with `--export-md` or `agent.export_markdown_report()`.  The report
includes a summary section followed by per-prompt prompt + response blocks.

---

## The 16 analytical prompts

| ID | Title |
|---|---|
| `1_market_mindset` | Market Mindset Check |
| `2_multi_timeframe_trend` | Multi-Timeframe Trend Clarity |
| `3_bull_vs_bear` | Bull vs Bear Case |
| `4_risk_before_reward` | Risk Before Reward Assessment |
| `5_entry_discipline` | Entry Discipline Check |
| `6_exit_framework` | Exit Framework |
| `7_news_detox` | News Detox Analysis |
| `8_earnings_expectations` | Earnings Expectations |
| `9_valuation_sanity` | Valuation Sanity Check |
| `10_sentiment_vs_fundamentals` | Sentiment vs Fundamentals |
| `11_scenario_planning` | Scenario Planning |
| `12_mistake_prevention` | Mistake Prevention Checklist |
| `13_post_loss_reflection` | Post-Loss Reflection Framework |
| `14_decision_clarity` | Decision Clarity |
| `15_macro_sector_check` | Macro & Sector Check |
| `16_conviction_rating` | Conviction Rating |

Each prompt accepts `[STOCK NAME]` and optional context placeholders
(`{price_context}`, `{fundamentals_context}`, `{news_context}`) that are
filled automatically when live MCP data is available.
