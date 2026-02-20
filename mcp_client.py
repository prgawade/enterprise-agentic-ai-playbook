"""
MCP (Model Context Protocol) client for live NSE/BSE stock data.

Provides typed data classes (StockPrice, StockFundamentals, StockNews) and
a synchronous client with a simple in-memory cache (5-minute TTL).
An async variant is also included for use in async contexts.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore[assignment]
    _AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StockPrice:
    """Current price snapshot for a stock."""

    symbol: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    timestamp: str = ""


@dataclass
class StockFundamentals:
    """Key fundamental metrics for a stock."""

    symbol: str
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    earnings_per_share: float = 0.0
    dividend_yield: float = 0.0
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    sector: str = ""
    industry: str = ""


@dataclass
class StockNews:
    """A single news headline for a stock."""

    symbol: str
    headline: str
    source: str = ""
    link: str = ""
    published_at: str = ""


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------


@dataclass
class _CacheEntry:
    data: Any
    expires_at: float


class _SimpleCache:
    """Thread-unsafe in-memory cache with per-entry TTL."""

    def __init__(self, ttl: int = 300) -> None:
        self._ttl = ttl
        self._store: Dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry and time.monotonic() < entry.expires_at:
            return entry.data
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _CacheEntry(
            data=value,
            expires_at=time.monotonic() + self._ttl,
        )


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://lobehub.com/mcp/girishkumardv-live-nse-bse-mcp"


class SyncMCPStockClient:
    """Synchronous HTTP client for the live NSE/BSE MCP server.

    Parameters
    ----------
    base_url:
        Root URL of the MCP server.  Defaults to the public NSE/BSE endpoint.
    api_key:
        Optional API key read from the ``MCP_API_KEY`` environment variable.
    cache_ttl:
        Cache time-to-live in seconds (default 300 = 5 minutes).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        cache_ttl: int = 300,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache = _SimpleCache(ttl=cache_ttl)

        # Read API key from env if not supplied directly
        import os
        self._api_key = api_key or os.getenv("MCP_API_KEY")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _get(self, path: str) -> Dict[str, Any]:
        """Perform a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        logger.debug("GET %s", url)
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching %s", url)
            raise
        except requests.exceptions.RequestException as exc:
            logger.error("Request error for %s: %s", url, exc)
            raise

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def fetch_stock_price(self, symbol: str) -> StockPrice:
        """Fetch the latest price for *symbol*."""
        cache_key = f"price:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        data = self._get(f"/stock/{symbol}/price")
        result = StockPrice(
            symbol=symbol,
            price=float(data.get("price", 0)),
            change=float(data.get("change", 0)),
            change_pct=float(data.get("change_pct", 0)),
            volume=int(data.get("volume", 0)),
            timestamp=str(data.get("timestamp", "")),
        )
        self._cache.set(cache_key, result)
        return result

    def fetch_stock_fundamentals(self, symbol: str) -> StockFundamentals:
        """Fetch key fundamental metrics for *symbol*."""
        cache_key = f"fundamentals:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        data = self._get(f"/stock/{symbol}/fundamentals")
        result = StockFundamentals(
            symbol=symbol,
            market_cap=float(data.get("market_cap", 0)),
            pe_ratio=float(data.get("pe_ratio", 0)),
            earnings_per_share=float(data.get("earnings_per_share", 0)),
            dividend_yield=float(data.get("dividend_yield", 0)),
            week_52_high=float(data.get("week_52_high", 0)),
            week_52_low=float(data.get("week_52_low", 0)),
            sector=str(data.get("sector", "")),
            industry=str(data.get("industry", "")),
        )
        self._cache.set(cache_key, result)
        return result

    def fetch_stock_news(self, symbol: str) -> List[StockNews]:
        """Fetch recent news headlines for *symbol*."""
        cache_key = f"news:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        items = self._get(f"/stock/{symbol}/news")
        if not isinstance(items, list):
            items = items.get("news", [])
        result = [
            StockNews(
                symbol=symbol,
                headline=str(item.get("headline", "")),
                source=str(item.get("source", "")),
                link=str(item.get("link", "")),
                published_at=str(item.get("published_at", "")),
            )
            for item in items
        ]
        self._cache.set(cache_key, result)
        return result

    def get_stock_context(self, symbol: str) -> Dict[str, Any]:
        """Return a combined context dict with price, fundamentals, and news.

        Individual fetch errors are caught and logged so a partial context is
        still returned when some endpoints are unavailable.
        """
        context: Dict[str, Any] = {"symbol": symbol}

        try:
            price = self.fetch_stock_price(symbol)
            context["price"] = {
                "price": price.price,
                "change": price.change,
                "change_pct": price.change_pct,
                "volume": price.volume,
                "timestamp": price.timestamp,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch price for %s: %s", symbol, exc)
            context["price"] = {}

        try:
            fundamentals = self.fetch_stock_fundamentals(symbol)
            context["fundamentals"] = {
                "market_cap": fundamentals.market_cap,
                "pe_ratio": fundamentals.pe_ratio,
                "eps": fundamentals.earnings_per_share,
                "dividend_yield": fundamentals.dividend_yield,
                "52w_high": fundamentals.week_52_high,
                "52w_low": fundamentals.week_52_low,
                "sector": fundamentals.sector,
                "industry": fundamentals.industry,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch fundamentals for %s: %s", symbol, exc)
            context["fundamentals"] = {}

        try:
            news = self.fetch_stock_news(symbol)
            context["news"] = [
                {
                    "headline": n.headline,
                    "source": n.source,
                    "published_at": n.published_at,
                    "link": n.link,
                }
                for n in news[:5]
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch news for %s: %s", symbol, exc)
            context["news"] = []

        return context


# ---------------------------------------------------------------------------
# Async client (optional – requires aiohttp)
# ---------------------------------------------------------------------------


class AsyncMCPStockClient:
    """Asynchronous HTTP client for the live NSE/BSE MCP server.

    Requires ``aiohttp`` to be installed.  Use :class:`SyncMCPStockClient`
    if async is not needed.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        cache_ttl: int = 300,
        timeout: int = 10,
    ) -> None:
        if not _AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for AsyncMCPStockClient. "
                "Install it with: pip install aiohttp"
            )
        import os
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache = _SimpleCache(ttl=cache_ttl)
        self._api_key = api_key or os.getenv("MCP_API_KEY")

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _get(self, session: Any, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        logger.debug("async GET %s", url)
        async with session.get(
            url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def fetch_stock_price(self, session: Any, symbol: str) -> StockPrice:
        """Async version of :meth:`SyncMCPStockClient.fetch_stock_price`."""
        data = await self._get(session, f"/stock/{symbol}/price")
        return StockPrice(
            symbol=symbol,
            price=float(data.get("price", 0)),
            change=float(data.get("change", 0)),
            change_pct=float(data.get("change_pct", 0)),
            volume=int(data.get("volume", 0)),
            timestamp=str(data.get("timestamp", "")),
        )

    async def fetch_stock_fundamentals(self, session: Any, symbol: str) -> StockFundamentals:
        """Async version of :meth:`SyncMCPStockClient.fetch_stock_fundamentals`."""
        data = await self._get(session, f"/stock/{symbol}/fundamentals")
        return StockFundamentals(
            symbol=symbol,
            market_cap=float(data.get("market_cap", 0)),
            pe_ratio=float(data.get("pe_ratio", 0)),
            earnings_per_share=float(data.get("earnings_per_share", 0)),
            dividend_yield=float(data.get("dividend_yield", 0)),
            week_52_high=float(data.get("week_52_high", 0)),
            week_52_low=float(data.get("week_52_low", 0)),
            sector=str(data.get("sector", "")),
            industry=str(data.get("industry", "")),
        )

    async def fetch_stock_news(self, session: Any, symbol: str) -> List[StockNews]:
        """Async version of :meth:`SyncMCPStockClient.fetch_stock_news`."""
        items = await self._get(session, f"/stock/{symbol}/news")
        if not isinstance(items, list):
            items = items.get("news", [])
        return [
            StockNews(
                symbol=symbol,
                headline=str(item.get("headline", "")),
                source=str(item.get("source", "")),
                link=str(item.get("link", "")),
                published_at=str(item.get("published_at", "")),
            )
            for item in items
        ]

    async def get_stock_context(self, symbol: str) -> Dict[str, Any]:
        """Async combined context fetch (price + fundamentals + news)."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_stock_price(session, symbol),
                self.fetch_stock_fundamentals(session, symbol),
                self.fetch_stock_news(session, symbol),
            ]
            price, fundamentals, news = await asyncio.gather(*tasks, return_exceptions=True)

        context: Dict[str, Any] = {"symbol": symbol}

        if isinstance(price, StockPrice):
            context["price"] = {
                "price": price.price,
                "change": price.change,
                "change_pct": price.change_pct,
                "volume": price.volume,
                "timestamp": price.timestamp,
            }
        else:
            logger.warning("Could not fetch price for %s: %s", symbol, price)
            context["price"] = {}

        if isinstance(fundamentals, StockFundamentals):
            context["fundamentals"] = {
                "market_cap": fundamentals.market_cap,
                "pe_ratio": fundamentals.pe_ratio,
                "eps": fundamentals.earnings_per_share,
                "dividend_yield": fundamentals.dividend_yield,
                "52w_high": fundamentals.week_52_high,
                "52w_low": fundamentals.week_52_low,
                "sector": fundamentals.sector,
                "industry": fundamentals.industry,
            }
        else:
            logger.warning("Could not fetch fundamentals for %s: %s", symbol, fundamentals)
            context["fundamentals"] = {}

        if isinstance(news, list):
            context["news"] = [
                {
                    "headline": n.headline,
                    "source": n.source,
                    "published_at": n.published_at,
                    "link": n.link,
                }
                for n in news[:5]
            ]
        else:
            logger.warning("Could not fetch news for %s: %s", symbol, news)
            context["news"] = []

        return context
