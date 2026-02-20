"""
Stock Analyst Agent – multi-prompt analysis engine.

Contains:
- 16 analytical prompt templates (each accepting [STOCK NAME] and optional
  context variables).
- A pluggable ModelClient interface with concrete implementations for Ollama,
  Gemini, and a no-op Mock client (for testing / smoke-checks).
- :class:`StockAnalystAgent`: orchestrates data → prompt → LLM → report.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 16 Analytical Prompt Templates
# ---------------------------------------------------------------------------

PROMPTS: Dict[str, str] = {
    "1_market_mindset": (
        "Market Mindset Check for [STOCK NAME]:\n"
        "Current price context: {price_context}\n"
        "Before analyzing [STOCK NAME], reflect on the broader market mood today. "
        "Are you approaching this with clarity, or is fear/greed influencing your view? "
        "Describe the dominant market sentiment and how it should affect your interpretation of [STOCK NAME] data."
    ),
    "2_multi_timeframe_trend": (
        "Multi-Timeframe Trend Clarity for [STOCK NAME]:\n"
        "Price data: {price_context}\n"
        "Analyze [STOCK NAME] across weekly, daily, and intraday timeframes. "
        "Is the trend aligned across all timeframes? Where are the key support and resistance levels? "
        "Summarize the trend structure and note any divergences between timeframes."
    ),
    "3_bull_vs_bear": (
        "Bull vs Bear Case for [STOCK NAME]:\n"
        "Fundamentals summary: {fundamentals_context}\n"
        "Price: {price_context}\n"
        "Present the strongest arguments for both the bullish and bearish scenarios for [STOCK NAME]. "
        "Which side has more evidence right now, and why?"
    ),
    "4_risk_before_reward": (
        "Risk Before Reward Assessment for [STOCK NAME]:\n"
        "Price: {price_context}\n"
        "Before thinking about profits, identify the top 3 risks of investing in [STOCK NAME] right now. "
        "What is the maximum downside, and how would you manage each risk?"
    ),
    "5_entry_discipline": (
        "Entry Discipline Check for [STOCK NAME]:\n"
        "Price: {price_context}\n"
        "Fundamentals: {fundamentals_context}\n"
        "What are the ideal entry conditions for [STOCK NAME]? "
        "Is the current price a reasonable entry, or should you wait for a better setup? "
        "Define clear entry criteria (price level, volume confirmation, catalyst)."
    ),
    "6_exit_framework": (
        "Exit Framework for [STOCK NAME]:\n"
        "Price: {price_context}\n"
        "Design a complete exit strategy for a position in [STOCK NAME]. "
        "Include: profit target levels, stop-loss placement, time-based exit criteria, "
        "and conditions that would invalidate the trade thesis."
    ),
    "7_news_detox": (
        "News Detox Analysis for [STOCK NAME]:\n"
        "Recent headlines: {news_context}\n"
        "Review the latest news about [STOCK NAME]. Separate signal from noise. "
        "Which news items have genuine fundamental impact, and which are just market noise? "
        "Provide a balanced view that filters out emotional or sensational reporting."
    ),
    "8_earnings_expectations": (
        "Earnings Expectations for [STOCK NAME]:\n"
        "Fundamentals: {fundamentals_context}\n"
        "What are the current earnings expectations for [STOCK NAME]? "
        "Is the stock priced for perfection, or is there room to beat estimates? "
        "Analyze EPS trends, revenue growth, and margin trajectories."
    ),
    "9_valuation_sanity": (
        "Valuation Sanity Check for [STOCK NAME]:\n"
        "Fundamentals: {fundamentals_context}\n"
        "Price: {price_context}\n"
        "Is [STOCK NAME] cheap, fair, or expensive based on current fundamentals? "
        "Compare P/E, P/B, EV/EBITDA to sector peers and historical averages. "
        "At what price would [STOCK NAME] become compelling value?"
    ),
    "10_sentiment_vs_fundamentals": (
        "Sentiment vs Fundamentals for [STOCK NAME]:\n"
        "News: {news_context}\n"
        "Fundamentals: {fundamentals_context}\n"
        "Is market sentiment for [STOCK NAME] aligned with or diverging from its fundamentals? "
        "Identify any disconnect and explain whether it represents opportunity or a warning sign."
    ),
    "11_scenario_planning": (
        "Scenario Planning for [STOCK NAME]:\n"
        "Price: {price_context}\n"
        "Fundamentals: {fundamentals_context}\n"
        "Map out three scenarios for [STOCK NAME] over the next 6–12 months: "
        "Bull case (price target + catalysts), Base case (most likely outcome), "
        "and Bear case (downside risks + triggers). Assign rough probabilities to each."
    ),
    "12_mistake_prevention": (
        "Mistake Prevention Checklist for [STOCK NAME]:\n"
        "What are the most common investor mistakes made with stocks like [STOCK NAME]? "
        "List 5 cognitive biases or behavioral errors that could lead to a bad outcome, "
        "and explain how to guard against each one specifically for [STOCK NAME]."
    ),
    "13_post_loss_reflection": (
        "Post-Loss Reflection Framework for [STOCK NAME]:\n"
        "Imagine you took a 15% loss on [STOCK NAME]. Walk through a structured post-mortem: "
        "What was the original thesis? Where did the analysis go wrong? "
        "What early warning signs were missed? What would you do differently next time?"
    ),
    "14_decision_clarity": (
        "Decision Clarity for [STOCK NAME]:\n"
        "Price: {price_context}\n"
        "Fundamentals: {fundamentals_context}\n"
        "News: {news_context}\n"
        "Synthesize everything and provide a clear, actionable decision for [STOCK NAME]: "
        "Buy / Hold / Sell / Avoid – with a specific rationale, position sizing suggestion, "
        "and the single most important factor that would change this view."
    ),
    "15_macro_sector_check": (
        "Macro & Sector Check for [STOCK NAME]:\n"
        "Fundamentals: {fundamentals_context}\n"
        "How are macroeconomic factors (interest rates, inflation, currency) and sector "
        "dynamics currently affecting [STOCK NAME]? "
        "Is the sector a tailwind or headwind for the stock right now?"
    ),
    "16_conviction_rating": (
        "Conviction Rating for [STOCK NAME]:\n"
        "After completing all analyses, rate your conviction in a long position on [STOCK NAME] "
        "from 1 (very low) to 10 (very high). Break down the score by: "
        "fundamental quality (x/10), technical setup (x/10), valuation attractiveness (x/10), "
        "risk/reward profile (x/10). Provide one sentence justification for each sub-score."
    ),
}

# ---------------------------------------------------------------------------
# Model client interface & implementations
# ---------------------------------------------------------------------------


class ModelClient:
    """Base interface for LLM clients. Override :meth:`complete` in subclasses."""

    def complete(self, prompt: str) -> str:  # noqa: D401
        """Send *prompt* to the LLM and return the text response."""
        raise NotImplementedError


class MockModelClient(ModelClient):
    """No-op client that echoes back a placeholder response (useful for testing)."""

    def complete(self, prompt: str) -> str:  # noqa: D401
        stock_line = next(
            (line for line in prompt.splitlines() if "[STOCK NAME]" not in line and line.strip()),
            "N/A",
        )
        return (
            f"[MOCK RESPONSE] Prompt received ({len(prompt)} chars). "
            f"First data line: {stock_line[:80]}"
        )


class OllamaModelClient(ModelClient):
    """Calls a locally running Ollama server via its HTTP API.

    Parameters
    ----------
    base_url:
        Ollama server base URL (default: ``http://localhost:11434``).
    model:
        Ollama model name (default: ``llama3``).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            return f"[ERROR] Ollama request failed: {exc}"


class GeminiModelClient(ModelClient):
    """Calls the Google Gemini REST API.

    Requires ``GEMINI_API_KEY`` to be set in the environment.

    Parameters
    ----------
    api_key:
        Gemini API key.  Falls back to ``GEMINI_API_KEY`` env var.
    model:
        Gemini model name (default: ``gemini-1.5-flash``).
    """

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or ""
        self.model = model
        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY is not set. "
                "Gemini calls will fail until a key is provided."
            )

    def complete(self, prompt: str) -> str:
        url = f"{self._BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if candidates:
                return (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
            return ""
        except requests.exceptions.RequestException as exc:
            logger.error("Gemini request failed: %s", exc)
            return f"[ERROR] Gemini request failed: {exc}"


def build_model_client(model_type: str, config: Any = None) -> ModelClient:
    """Factory: return an appropriate :class:`ModelClient` for *model_type*.

    Parameters
    ----------
    model_type:
        One of ``"ollama"``, ``"gemini"``, or ``"mock"``.
    config:
        Optional :class:`~config.AgentConfig` instance.  When supplied, model
        URLs and keys are read from it; otherwise environment variables / defaults
        are used.
    """
    if model_type == "mock":
        return MockModelClient()
    if model_type == "ollama":
        base_url = getattr(config, "ollama_url", None) or os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )
        model = getattr(config, "ollama_model", None) or os.getenv("OLLAMA_MODEL", "llama3")
        return OllamaModelClient(base_url=base_url, model=model)
    if model_type == "gemini":
        api_key = getattr(config, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY", "")
        model = getattr(config, "gemini_model", None) or os.getenv(
            "GEMINI_MODEL", "gemini-1.5-flash"
        )
        return GeminiModelClient(api_key=api_key, model=model)
    raise ValueError(
        f"Unknown model_type '{model_type}'. Supported: ollama, gemini, mock."
    )


# ---------------------------------------------------------------------------
# Context formatters
# ---------------------------------------------------------------------------


def _format_price_context(price_data: Dict[str, Any]) -> str:
    if not price_data:
        return "N/A"
    return (
        f"Price: {price_data.get('price', 'N/A')} | "
        f"Change: {price_data.get('change', 'N/A')} ({price_data.get('change_pct', 'N/A')}%) | "
        f"Volume: {price_data.get('volume', 'N/A')} | "
        f"As of: {price_data.get('timestamp', 'N/A')}"
    )


def _format_fundamentals_context(fund_data: Dict[str, Any]) -> str:
    if not fund_data:
        return "N/A"
    return (
        f"Market Cap: {fund_data.get('market_cap', 'N/A')} | "
        f"P/E: {fund_data.get('pe_ratio', 'N/A')} | "
        f"EPS: {fund_data.get('eps', 'N/A')} | "
        f"Dividend Yield: {fund_data.get('dividend_yield', 'N/A')}% | "
        f"52W High: {fund_data.get('52w_high', 'N/A')} | "
        f"52W Low: {fund_data.get('52w_low', 'N/A')} | "
        f"Sector: {fund_data.get('sector', 'N/A')}"
    )


def _format_news_context(news_list: List[Dict[str, Any]]) -> str:
    if not news_list:
        return "No recent news available."
    lines = []
    for i, item in enumerate(news_list[:5], 1):
        lines.append(
            f"{i}. [{item.get('published_at', '')}] {item.get('headline', '')} "
            f"({item.get('source', '')})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------


class StockAnalystAgent:
    """Orchestrates stock data → prompt filling → LLM → structured report.

    Parameters
    ----------
    model:
        Model type string: ``"ollama"``, ``"gemini"``, or ``"mock"``.
    model_client:
        Pre-built :class:`ModelClient` instance.  When supplied, *model* is
        ignored for client construction.
    config:
        Optional :class:`~config.AgentConfig` for endpoint/key overrides.
    """

    PROMPTS = PROMPTS

    def __init__(
        self,
        model: str = "mock",
        model_client: Optional[ModelClient] = None,
        config: Any = None,
    ) -> None:
        self.model_type = model
        self.config = config
        self.model_client: ModelClient = model_client or build_model_client(model, config)
        self._results: Dict[str, Any] = {}
        self._stock_name: str = ""

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_prompt(
        self, prompt_id: str, stock_name: str, live_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Return the prompt text for *prompt_id*, filled with *stock_name* and context."""
        template = self.PROMPTS[prompt_id]
        live_context = live_context or {}

        price_ctx = _format_price_context(live_context.get("price", {}))
        fund_ctx = _format_fundamentals_context(live_context.get("fundamentals", {}))
        news_ctx = _format_news_context(live_context.get("news", []))

        filled = (
            template.replace("[STOCK NAME]", stock_name)
            .replace("{price_context}", price_ctx)
            .replace("{fundamentals_context}", fund_ctx)
            .replace("{news_context}", news_ctx)
        )
        return filled

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze_stock(
        self,
        stock_name: str,
        prompt_ids: Optional[List[str]] = None,
        live_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run analysis prompts for *stock_name* and return a structured dict.

        Parameters
        ----------
        stock_name:
            Ticker or company name (e.g. ``"TCS"``, ``"RELIANCE"``).
        prompt_ids:
            Subset of prompt keys to run.  Defaults to all 16.
        live_context:
            Pre-fetched context dict from the MCP client.

        Returns
        -------
        dict
            ``{"stock_name": ..., "timestamp": ..., "model": ...,
               "results": {prompt_id: {"prompt": ..., "response": ...}},
               "summary": ...}``
        """
        self._stock_name = stock_name.upper()
        ids_to_run = prompt_ids if prompt_ids else list(self.PROMPTS.keys())

        per_prompt: Dict[str, Any] = {}
        for pid in ids_to_run:
            if pid not in self.PROMPTS:
                logger.warning("Unknown prompt id '%s' – skipping.", pid)
                continue
            prompt_text = self.build_prompt(pid, self._stock_name, live_context)
            logger.info("Running prompt '%s' for %s …", pid, self._stock_name)
            response = self.model_client.complete(prompt_text)
            per_prompt[pid] = {"prompt": prompt_text, "response": response}

        summary = self._build_summary(per_prompt)
        self._results = {
            "stock_name": self._stock_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": self.model_type,
            "prompts_run": ids_to_run,
            "results": per_prompt,
            "summary": summary,
        }
        return self._results

    def _build_summary(self, per_prompt: Dict[str, Any]) -> str:
        """Produce a one-paragraph text summary from individual responses."""
        if not per_prompt:
            return "No prompts were executed."
        highlights = []
        for pid, data in per_prompt.items():
            resp = data.get("response", "")
            first_sentence = resp.split(".")[0].strip() if resp else ""
            if first_sentence:
                highlights.append(f"[{pid}] {first_sentence}.")
        return " ".join(highlights) if highlights else "Analysis complete."

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise results to a JSON string."""
        return json.dumps(self._results, indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Serialise results to a Markdown report string."""
        if not self._results:
            return "# No results available.\n"
        lines = [
            f"# Stock Analysis Report: {self._results.get('stock_name', 'N/A')}",
            "",
            f"**Generated:** {self._results.get('timestamp', 'N/A')}  ",
            f"**Model:** {self._results.get('model', 'N/A')}  ",
            f"**Prompts run:** {len(self._results.get('prompts_run', []))}",
            "",
            "---",
            "",
            "## Summary",
            "",
            self._results.get("summary", ""),
            "",
            "---",
            "",
        ]
        for pid, data in self._results.get("results", {}).items():
            lines += [
                f"## {pid.replace('_', ' ').title()}",
                "",
                "### Prompt",
                "",
                "```",
                data.get("prompt", ""),
                "```",
                "",
                "### Response",
                "",
                data.get("response", ""),
                "",
                "---",
                "",
            ]
        return "\n".join(lines)

    def save_report(self, path: Optional[str] = None) -> str:
        """Save JSON results to disk.  Returns the file path."""
        if path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = f"{self._stock_name}_{ts}_analysis.json"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())
        logger.info("JSON report saved to %s", path)
        return path

    def export_markdown_report(self, path: Optional[str] = None) -> str:
        """Save Markdown report to disk.  Returns the file path."""
        if path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = f"{self._stock_name}_{ts}_analysis.md"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_markdown())
        logger.info("Markdown report saved to %s", path)
        return path
