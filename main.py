"""
Main entry point for Stock Analyst Agent
Demonstrates the complete workflow
"""

import sys
import argparse
from typing import Optional
from stock_analyst_agent import StockAnalystAgent
from config import AgentConfig
from mcp_client import SyncMCPStockClient
import json


class StockAnalysisOrchestrator:
    """Orchestrates the complete stock analysis workflow"""
    
    def __init__(self, model_type: str = "ollama", use_mcp: bool = True, mcp_base_url: str = "http://localhost:5000"):
        """Initialize orchestrator"""
        self.config = AgentConfig(
            model_type=model_type,
            use_mcp=use_mcp,
        )
        self.agent = StockAnalystAgent(model=model_type, use_mcp=use_mcp)
        self.mcp_client = SyncMCPStockClient(base_url=mcp_base_url) if use_mcp else None
    
    def fetch_live_data(self, stock_symbol: str) -> dict:
        """Fetch live stock data from MCP server"""
        if not self.mcp_client:
            print("MCP client not initialized. Skipping live data fetch.")
            return {}
        
        try:
            print(f"\nFetching live data for {stock_symbol}...")
            context = self.mcp_client.get_stock_context(stock_symbol)
            
            print(f"Successfully fetched data:")
            print(json.dumps(context, indent=2, default=str))
            
            return context
        except Exception as e:
            print(f"Error fetching live data: {str(e)}")
            return {}
    
    def run_analysis(self, stock_name: str, specific_prompts: Optional[list] = None) -> dict:
        """Run complete stock analysis"""
        print(f"\n{'='*80}")
        print(f"STOCK ANALYSIS: {stock_name.upper()}")
        print(f"{'='*80}")
        
        # Fetch live data if available
        live_data = self.fetch_live_data(stock_name)
        
        # Run analysis
        analysis_result = self.agent.analyze_stock(stock_name, specific_prompts)
        
        # Combine results
        analysis_result['live_data'] = live_data
        
        return analysis_result
    
    def interactive_mode(self):
        """Interactive mode for continuous analysis"""
        print("\n" + "="*80)
        print("STOCK ANALYST AGENT - INTERACTIVE MODE")
        print("="*80)
        print("\nAvailable prompts:")
        for prompt_id, prompt_text in self.agent.PROMPTS.items():
            print(f"  {prompt_id}: {prompt_text.split(chr(10))[0][:50]}...")
        
        while True:
            print("\n" + "-"*80)
            stock_input = input("Enter stock name (or 'quit' to exit): ").strip().upper()
            
            if stock_input.lower() == 'quit':
                print("Exiting...")
                break
            
            prompts_input = input("Enter prompt IDs (comma-separated, or 'all' for all): ").strip()
            
            if prompts_input.lower() == 'all' or not prompts_input:
                specific_prompts = None
            else:
                specific_prompts = [p.strip() for p in prompts_input.split(',')]
            
            # Run analysis
            result = self.run_analysis(stock_input, specific_prompts)
            
            # Save option
            save_input = input("\nSave report? (y/n): ").strip().lower()
            if save_input == 'y':
                self.agent.save_report()
                export_md = input("Also export as markdown? (y/n): ").strip().lower()
                if export_md == 'y':
                    self.agent.export_markdown_report()


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Stock Analyst Agent - Multi-Prompt Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze TCS with Ollama
  python main.py TCS --model ollama
  
  # Analyze RELIANCE with Gemini using specific prompts
  python main.py RELIANCE --model gemini --prompts 1_market_mindset 4_bull_vs_bear
  
  # Interactive mode
  python main.py --interactive --model claude
  
  # Without MCP (no live data)
  python main.py INFY --no-mcp
        """
    )
    
    parser.add_argument(
        "stock_name",
        nargs='?',
        help="Stock name to analyze (e.g., TCS, RELIANCE, INFY)"
    )
    
    parser.add_argument(
        "--model",
        choices=["ollama", "gemini", "claude"],
        default="ollama",
        help="LLM model to use (default: ollama)"
    )
    
    parser.add_argument(
        "--prompts",
        nargs="+",
        help="Specific prompt IDs to run (if not specified, runs all)"
    )
    
    parser.add_argument(
        "--export-md",
        action="store_true",
        help="Export analysis as markdown report"
    )
    
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Don't use MCP server for live data"
    )
    
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:5000",
        help="MCP server base URL"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="List all available prompts"
    )
    
    args = parser.parse_args()
    
    # Handle list prompts
    if args.list_prompts:
        print("\nAvailable Prompts:")
        print("="*80)
        agent = StockAnalystAgent()
        for prompt_id, prompt_text in agent.PROMPTS.items():
            print(f"\n{prompt_id}:")
            print("-" * 40)
            print(prompt_text[:200] + "..." if len(prompt_text) > 200 else prompt_text)
        return
    
    # Initialize orchestrator
    orchestrator = StockAnalysisOrchestrator(
        model_type=args.model,
        use_mcp=not args.no_mcp,
        mcp_base_url=args.mcp_url,
    )
    
    # Interactive mode
    if args.interactive:
        orchestrator.interactive_mode()
        return
    
    # Check if stock name provided
    if not args.stock_name:
        parser.print_help()
        sys.exit(1)
    
    # Run analysis
    result = orchestrator.run_analysis(args.stock_name, args.prompts)
    
    # Save reports
    orchestrator.agent.save_report()
    if args.export_md:
        orchestrator.agent.export_markdown_report()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()