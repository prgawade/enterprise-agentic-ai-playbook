"""
Smoke-check / example usage for the Stock Analyst Agent.

Run this script to validate the plumbing without any real LLM or MCP calls:

    python example_usage.py

All three examples use model="mock" and --no-mcp so no credentials or
network access are required.
"""

from stock_analyst_agent import StockAnalystAgent, MockModelClient


def example_1_mock_analysis() -> None:
    """Analyse TCS with the mock model (no LLM or MCP)."""
    print("\n" + "=" * 60)
    print("Example 1: Mock analysis of TCS (all 16 prompts)")
    print("=" * 60)

    agent = StockAnalystAgent(model="mock", model_client=MockModelClient())
    result = agent.analyze_stock("TCS")

    print(f"Stock    : {result['stock_name']}")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Prompts  : {len(result['results'])} run")
    print(f"Summary  : {result['summary'][:120]}…")


def example_2_subset_of_prompts() -> None:
    """Run only two prompts for RELIANCE."""
    print("\n" + "=" * 60)
    print("Example 2: Subset of prompts for RELIANCE")
    print("=" * 60)

    agent = StockAnalystAgent(model="mock", model_client=MockModelClient())
    result = agent.analyze_stock(
        "RELIANCE",
        prompt_ids=["3_bull_vs_bear", "9_valuation_sanity"],
    )

    for pid, data in result["results"].items():
        print(f"\n--- {pid} ---")
        print(data["response"])


def example_3_export_markdown() -> None:
    """Analyse INFY and export a Markdown report to /tmp."""
    import os

    print("\n" + "=" * 60)
    print("Example 3: Export Markdown report for INFY")
    print("=" * 60)

    agent = StockAnalystAgent(model="mock", model_client=MockModelClient())
    agent.analyze_stock("INFY")

    md_path = agent.export_markdown_report("/tmp/INFY_analysis.md")
    json_path = agent.save_report("/tmp/INFY_analysis.json")

    print(f"Markdown : {md_path}")
    print(f"JSON     : {json_path}")
    assert os.path.exists(md_path), "Markdown file was not created!"
    assert os.path.exists(json_path), "JSON file was not created!"
    print("Both report files verified ✓")


def example_4_with_live_context() -> None:
    """Demonstrate injecting a mock live-data context into the agent."""
    print("\n" + "=" * 60)
    print("Example 4: Injecting mock live context for WIPRO")
    print("=" * 60)

    mock_context = {
        "symbol": "WIPRO",
        "price": {
            "price": 475.50,
            "change": -3.20,
            "change_pct": -0.67,
            "volume": 1200000,
            "timestamp": "2024-01-15T10:30:00Z",
        },
        "fundamentals": {
            "market_cap": 2500000000000,
            "pe_ratio": 22.4,
            "eps": 21.2,
            "dividend_yield": 0.42,
            "52w_high": 560.0,
            "52w_low": 380.0,
            "sector": "Information Technology",
            "industry": "IT Services",
        },
        "news": [
            {
                "headline": "Wipro wins $500M deal from European bank",
                "source": "Economic Times",
                "published_at": "2024-01-14",
                "link": "https://example.com/news/1",
            }
        ],
    }

    agent = StockAnalystAgent(model="mock", model_client=MockModelClient())
    result = agent.analyze_stock(
        "WIPRO",
        prompt_ids=["14_decision_clarity"],
        live_context=mock_context,
    )

    response = result["results"]["14_decision_clarity"]["response"]
    print(f"Decision clarity response:\n{response}")


if __name__ == "__main__":
    example_1_mock_analysis()
    example_2_subset_of_prompts()
    example_3_export_markdown()
    example_4_with_live_context()

    print("\n" + "=" * 60)
    print("All examples completed successfully ✓")
    print("=" * 60)