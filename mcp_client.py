from dataclasses import dataclass
from typing import List, Dict, Any
import requests
import asyncio
import aiohttp


@dataclass
class StockPrice:
    symbol: str
    price: float
    timestamp: str

@dataclass
class StockFundamentals:
    symbol: str
    earnings_per_share: float
    market_cap: float
    pe_ratio: float

@dataclass
class StockNews:
    symbol: str
    headline: str
    link: str
    published_at: str


class SyncMCPStockClient:
    BASE_URL = 'http://mcp-server/api'

    @staticmethod
    def fetch_stock_price(symbol: str) -> StockPrice:
        response = requests.get(f'{SyncMCPStockClient.BASE_URL}/stock/{symbol}/price')
        data = response.json()
        return StockPrice(symbol=symbol, price=data['price'], timestamp=data['timestamp'])

    @staticmethod
    def fetch_stock_fundamentals(symbol: str) -> StockFundamentals:
        response = requests.get(f'{SyncMCPStockClient.BASE_URL}/stock/{symbol}/fundamentals')
        data = response.json()
        return StockFundamentals(symbol=symbol, earnings_per_share=data['earnings_per_share'], market_cap=data['market_cap'], pe_ratio=data['pe_ratio'])

    @staticmethod
    def fetch_stock_news(symbol: str) -> List[StockNews]:
        response = requests.get(f'{SyncMCPStockClient.BASE_URL}/stock/{symbol}/news')
        news_items = response.json()
        return [StockNews(symbol=symbol, headline=item['headline'], link=item['link'], published_at=item['published_at']) for item in news_items]


class AsyncMCPStockClient:
    BASE_URL = 'http://mcp-server/api'

    async def fetch_stock_price(self, session: aiohttp.ClientSession, symbol: str) -> StockPrice:
        async with session.get(f'{AsyncMCPStockClient.BASE_URL}/stock/{symbol}/price') as response:
            data = await response.json()
            return StockPrice(symbol=symbol, price=data['price'], timestamp=data['timestamp'])

    async def fetch_stock_fundamentals(self, session: aiohttp.ClientSession, symbol: str) -> StockFundamentals:
        async with session.get(f'{AsyncMCPStockClient.BASE_URL}/stock/{symbol}/fundamentals') as response:
            data = await response.json()
            return StockFundamentals(symbol=symbol, earnings_per_share=data['earnings_per_share'], market_cap=data['market_cap'], pe_ratio=data['pe_ratio'])

    async def fetch_stock_news(self, session: aiohttp.ClientSession, symbol: str) -> List[StockNews]:
        async with session.get(f'{AsyncMCPStockClient.BASE_URL}/stock/{symbol}/news') as response:
            news_items = await response.json()
            return [StockNews(symbol=symbol, headline=item['headline'], link=item['link'], published_at=item['published_at']) for item in news_items]

    async def fetch_all(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for symbol in symbols:
                tasks.append(self.fetch_stock_price(session, symbol))
                tasks.append(self.fetch_stock_fundamentals(session, symbol))
                tasks.append(self.fetch_stock_news(session, symbol))
            results = await asyncio.gather(*tasks)
            return results
