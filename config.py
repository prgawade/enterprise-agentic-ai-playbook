"""
Centralized configuration for the Stock Analyst Agent.

Reads runtime settings from environment variables (via python-dotenv) and
provides validated, typed config objects consumed by the rest of the package.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

SUPPORTED_MODELS: List[str] = ["ollama", "gemini", "mock"]

DEFAULT_MCP_URL: str = os.getenv(
    "MCP_URL",
    "https://lobehub.com/mcp/girishkumardv-live-nse-bse-mcp",
)

DEFAULT_OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Cache time-to-live in seconds (5 minutes)
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# Default prompts to run (None = all)
DEFAULT_PROMPT_IDS: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class AgentConfig:
    """Top-level configuration for the Stock Analyst Agent."""

    model_type: str = "ollama"
    use_mcp: bool = True
    mcp_url: str = field(default_factory=lambda: DEFAULT_MCP_URL)
    ollama_url: str = field(default_factory=lambda: DEFAULT_OLLAMA_URL)
    ollama_model: str = field(default_factory=lambda: DEFAULT_OLLAMA_MODEL)
    gemini_api_key: Optional[str] = field(default_factory=lambda: GEMINI_API_KEY)
    gemini_model: str = field(default_factory=lambda: DEFAULT_GEMINI_MODEL)
    cache_ttl: int = CACHE_TTL_SECONDS

    def __post_init__(self) -> None:
        """Validate configuration after initialisation."""
        if self.model_type not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model_type '{self.model_type}'. "
                f"Choose from: {SUPPORTED_MODELS}"
            )
        if self.model_type == "gemini" and not self.gemini_api_key:
            logger.warning(
                "GEMINI_API_KEY is not set. "
                "Set it in your environment or .env file before using Gemini."
            )
        logger.debug("AgentConfig initialised: model=%s, use_mcp=%s", self.model_type, self.use_mcp)
