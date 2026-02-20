"""
Main CLI entry point for the Stock Analyst Agent.

Usage examples
--------------
# Analyse TCS with the mock model (no LLM calls):
  python main.py TCS --model mock

# Analyse RELIANCE with Ollama and export Markdown:
  python main.py RELIANCE --model ollama --export-md

# Analyse INFY using specific prompts with Gemini:
  python main.py INFY --model gemini --prompts 3_bull_vs_bear 9_valuation_sanity

# Interactive mode:
  python main.py --interactive --model mock

# List available prompts:
  python main.py --list-prompts
"""

import json
import logging
import sys
import argparse
from typing import Optional

from config import AgentConfig
from mcp_client import SyncMCPStockClient
from stock_analyst_agent import StockAnalystAgent, build_model_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class StockAnalysisOrchestrator:
    """Wires together config, MCP client, model client, and the agent."""

    def __init__(
        self,
        model_type: str = "mock",
        use_mcp: bool = True,
        mcp_url: str = "https://lobehub.com/mcp/girishkumardv-live-nse-bse-mcp",
    ) -> None:
        self.config = AgentConfig(model_type=model_type, use_mcp=use_mcp, mcp_url=mcp_url)
        self.model_client = build_model_client(model_type, self.config)
        self.agent = StockAnalystAgent(
            model=model_type,
            model_client=self.model_client,
            config=self.config,
        )
        self.mcp_client: Optional[SyncMCPStockClient] = (
            SyncMCPStockClient(
                base_url=mcp_url,
                cache_ttl=self.config.cache_ttl,
            )
            if use_mcp
            else None
        )

    # ------------------------------------------------------------------

    def fetch_live_data(self, stock_symbol: str) -> dict:
        """Return live context from the MCP server, or an empty dict."""
        if not self.mcp_client:
            logger.info("MCP disabled – skipping live data fetch.")
            return {}
        try:
            print(f"\nFetching live data for {stock_symbol} …")
            context = self.mcp_client.get_stock_context(stock_symbol)
            print("Live data fetched:\n" + json.dumps(context, indent=2, default=str))
            return context
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch live data for %s: %s", stock_symbol, exc)
            return {}

    def run_analysis(
        self, stock_name: str, specific_prompts: Optional[list] = None
    ) -> dict:
        """Fetch data, run prompts, return results dict."""
        print(f"\n{'='*80}")
        print(f"STOCK ANALYSIS: {stock_name.upper()}")
        print(f"{'='*80}")

        live_data = self.fetch_live_data(stock_name)
        result = self.agent.analyze_stock(
            stock_name, prompt_ids=specific_prompts, live_context=live_data
        )
        result["live_data"] = live_data
        return result

    def interactive_mode(self) -> None:
        """Interactive REPL for continuous analysis."""
        print("\n" + "=" * 80)
        print("STOCK ANALYST AGENT – INTERACTIVE MODE")
        print("=" * 80)
        print("\nAvailable prompts:")
        for pid in self.agent.PROMPTS:
            print(f"  {pid}")

        while True:
            print("\n" + "-" * 80)
            stock_input = input("Enter stock name (or 'quit' to exit): ").strip().upper()
            if stock_input.lower() in {"quit", "exit", "q"}:
                print("Exiting.")
                break

            prompts_input = input(
                "Prompt IDs (comma-separated, or press Enter for all): "
            ).strip()
            specific_prompts = (
                None
                if not prompts_input or prompts_input.lower() == "all"
                else [p.strip() for p in prompts_input.split(",")]
            )

            result = self.run_analysis(stock_input, specific_prompts)

            save_input = input("\nSave JSON report? (y/n): ").strip().lower()
            if save_input == "y":
                path = self.agent.save_report()
                print(f"Saved to {path}")

            md_input = input("Export Markdown report? (y/n): ").strip().lower()
            if md_input == "y":
                path = self.agent.export_markdown_report()
                print(f"Saved to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run analysis."""
    parser = argparse.ArgumentParser(
        description="Stock Analyst Agent – Multi-Prompt Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "stock_name",
        nargs="?",
        help="Stock ticker/name to analyse (e.g. TCS, RELIANCE, INFY).",
    )
    parser.add_argument(
        "--model",
        choices=["ollama", "gemini", "mock"],
        default="mock",
        help="LLM backend to use (default: mock).",
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        metavar="PROMPT_ID",
        help="Run only these prompt IDs (space-separated). Omit to run all.",
    )
    parser.add_argument(
        "--mcp-url",
        default=None,
        help="Override the MCP server URL.",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Disable live MCP data fetch.",
    )
    parser.add_argument(
        "--export-md",
        action="store_true",
        help="Write a Markdown report alongside the JSON report.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive mode.",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="Print all available prompt IDs and exit.",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    if args.list_prompts:
        from stock_analyst_agent import PROMPTS

        print("\nAvailable prompts:")
        print("=" * 80)
        for pid, text in PROMPTS.items():
            preview = text.split("\n")[0][:70]
            print(f"  {pid:35s}  {preview}")
        return

    # Resolve MCP URL
    from config import DEFAULT_MCP_URL

    mcp_url = args.mcp_url or DEFAULT_MCP_URL

    orchestrator = StockAnalysisOrchestrator(
        model_type=args.model,
        use_mcp=not args.no_mcp,
        mcp_url=mcp_url,
    )

    if args.interactive:
        orchestrator.interactive_mode()
        return

    if not args.stock_name:
        parser.print_help()
        sys.exit(1)

    result = orchestrator.run_analysis(args.stock_name, args.prompts)

    json_path = orchestrator.agent.save_report()
    print(f"\nJSON report saved to: {json_path}")

    if args.export_md:
        md_path = orchestrator.agent.export_markdown_report()
        print(f"Markdown report saved to: {md_path}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()