"""
Price Data Sources for Crypto Trading Bot
Handles real-time price data from multiple APIs with redundancy and caching.
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import requests
import websocket
import threading
from concurrent.futures import ThreadPoolExecutor
import redis

from ..utils.config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Represents price data for a trading pair."""
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: datetime
    source: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    market_cap: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceData':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        with self.lock:
            now = time.time()
            # Remove old calls outside the time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0]) + 0.1
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
            
            self.calls.append(now)


class CoinGeckoAPI:
    """CoinGecko API client for price data."""
    
    def __init__(self):
        self.config = get_config().api.get("coingecko")
        self.base_url = self.config.base_url
        self.rate_limiter = RateLimiter(self.config.rate_limit, 60)  # per minute
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoTradingBot/1.0'
        })
    
    def get_price_data(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get current price data for multiple symbols."""
        self.rate_limiter.wait_if_needed()
        
        try:
            # Convert symbols to CoinGecko IDs (simplified mapping)
            coin_ids = [self._symbol_to_id(symbol) for symbol in symbols]
            ids_str = ','.join(coin_ids)
            
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': ids_str,
                'vs_currencies': 'usd',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            result = {}
            
            for i, symbol in enumerate(symbols):
                coin_id = coin_ids[i]
                if coin_id in data:
                    coin_data = data[coin_id]
                    result[symbol] = PriceData(
                        symbol=symbol,
                        price=coin_data.get('usd', 0.0),
                        volume_24h=coin_data.get('usd_24h_vol', 0.0),
                        change_24h=coin_data.get('usd_24h_change', 0.0),
                        market_cap=coin_data.get('usd_market_cap'),
                        timestamp=datetime.utcnow(),
                        source='coingecko'
                    )
            
            logger.debug(f"Retrieved price data for {len(result)} symbols from CoinGecko")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching price data from CoinGecko: {e}")
            return {}
    
    def _symbol_to_id(self, symbol: str) -> str:
        """Convert trading symbol to CoinGecko ID."""
        # Simplified mapping - in practice, would use a comprehensive mapping
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDC': 'usd-coin',
            'USDT': 'tether',
            'DAI': 'dai',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'MKR': 'maker',
            'SNX': 'havven',
            'YFI': 'yearn-finance',
            'SUSHI': 'sushi',
            'CRV': 'curve-dao-token'
        }
        return mapping.get(symbol.upper(), symbol.lower())


class CoinMarketCapAPI:
    """CoinMarketCap API client for price data."""
    
    def __init__(self):
        self.config = get_config().api.get("coinmarketcap")
        self.base_url = self.config.base_url
        self.api_key = self.config.api_key
        self.rate_limiter = RateLimiter(self.config.rate_limit, 60)  # per minute
        self.session = requests.Session()
        self.session.headers.update({
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        })
    
    def get_price_data(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get current price data for multiple symbols."""
        if not self.api_key:
            logger.warning("CoinMarketCap API key not configured")
            return {}
        
        self.rate_limiter.wait_if_needed()
        
        try:
            url = f"{self.base_url}/cryptocurrency/quotes/latest"
            params = {
                'symbol': ','.join(symbols),
                'convert': 'USD'
            }
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            result = {}
            
            if 'data' in data:
                for symbol in symbols:
                    if symbol in data['data']:
                        coin_data = data['data'][symbol]
                        quote = coin_data['quote']['USD']
                        
                        result[symbol] = PriceData(
                            symbol=symbol,
                            price=quote['price'],
                            volume_24h=quote['volume_24h'],
                            change_24h=quote['percent_change_24h'],
                            market_cap=quote['market_cap'],
                            timestamp=datetime.utcnow(),
                            source='coinmarketcap'
                        )
            
            logger.debug(f"Retrieved price data for {len(result)} symbols from CoinMarketCap")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching price data from CoinMarketCap: {e}")
            return {}


class DeFiPulseAPI:
    """DeFiPulse API client for DeFi-specific data."""
    
    def __init__(self):
        self.config = get_config().api.get("defipulse", {})
        self.base_url = self.config.get("base_url", "https://data-api.defipulse.com/api/v1")
        self.rate_limiter = RateLimiter(self.config.get("rate_limit", 60), 60)
        self.session = requests.Session()
    
    def get_defi_data(self, protocols: List[str]) -> Dict[str, Any]:
        """Get DeFi protocol data."""
        # Simplified implementation - would need actual DeFiPulse API integration
        logger.debug("DeFiPulse API integration placeholder")
        return {}


class WebSocketPriceStream:
    """WebSocket client for real-time price streams."""
    
    def __init__(self, callback: Callable[[PriceData], None]):
        self.callback = callback
        self.ws = None
        self.running = False
        self.thread = None
        
    def start(self, symbols: List[str]) -> None:
        """Start WebSocket connection for real-time data."""
        self.running = True
        self.thread = threading.Thread(target=self._run_websocket, args=(symbols,))
        self.thread.start()
        logger.info("WebSocket price stream started")
    
    def stop(self) -> None:
        """Stop WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join()
        logger.info("WebSocket price stream stopped")
    
    def _run_websocket(self, symbols: List[str]) -> None:
        """Run WebSocket connection in separate thread."""
        # Simplified WebSocket implementation
        # In practice, would connect to exchange WebSocket APIs
        while self.running:
            try:
                # Simulate real-time data updates
                time.sleep(1)
                # Would process actual WebSocket messages here
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                time.sleep(5)


class PriceDataManager:
    """Main price data manager with multiple sources and caching."""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.Redis(**self.config.redis.dict())
        
        # Initialize data sources
        self.sources = {
            'coingecko': CoinGeckoAPI(),
            'coinmarketcap': CoinMarketCapAPI(),
            'defipulse': DeFiPulseAPI()
        }
        
        # WebSocket stream
        self.ws_stream = WebSocketPriceStream(self._handle_realtime_data)
        
        # Cache settings
        self.cache_ttl = 60  # seconds
        self.price_cache = {}
        self.last_update = {}
        
        # Executor for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Price Data Manager initialized")
    
    def get_price_data(self, symbols: List[str], use_cache: bool = True) -> Dict[str, PriceData]:
        """
        Get price data for multiple symbols with fallback sources.
        
        Args:
            symbols: List of trading symbols
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary of symbol -> PriceData
        """
        result = {}
        symbols_to_fetch = []
        
        # Check cache first
        if use_cache:
            for symbol in symbols:
                cached_data = self._get_cached_price(symbol)
                if cached_data:
                    result[symbol] = cached_data
                else:
                    symbols_to_fetch.append(symbol)
        else:
            symbols_to_fetch = symbols
        
        if not symbols_to_fetch:
            return result
        
        # Try primary source (CoinGecko)
        try:
            primary_data = self.sources['coingecko'].get_price_data(symbols_to_fetch)
            result.update(primary_data)
            
            # Cache the data
            for symbol, price_data in primary_data.items():
                self._cache_price_data(symbol, price_data)
            
            # Remove successfully fetched symbols
            symbols_to_fetch = [s for s in symbols_to_fetch if s not in primary_data]
            
        except Exception as e:
            logger.error(f"Primary source failed: {e}")
        
        # Try fallback source (CoinMarketCap) for remaining symbols
        if symbols_to_fetch:
            try:
                fallback_data = self.sources['coinmarketcap'].get_price_data(symbols_to_fetch)
                result.update(fallback_data)
                
                # Cache the data
                for symbol, price_data in fallback_data.items():
                    self._cache_price_data(symbol, price_data)
                    
            except Exception as e:
                logger.error(f"Fallback source failed: {e}")
        
        logger.info(f"Retrieved price data for {len(result)}/{len(symbols)} symbols")
        return result
    
    def get_single_price(self, symbol: str, use_cache: bool = True) -> Optional[PriceData]:
        """Get price data for a single symbol."""
        data = self.get_price_data([symbol], use_cache)
        return data.get(symbol)
    
    def start_realtime_stream(self, symbols: List[str]) -> None:
        """Start real-time price streaming for symbols."""
        self.ws_stream.start(symbols)
    
    def stop_realtime_stream(self) -> None:
        """Stop real-time price streaming."""
        self.ws_stream.stop()
    
    def _handle_realtime_data(self, price_data: PriceData) -> None:
        """Handle real-time price data from WebSocket."""
        # Cache the real-time data
        self._cache_price_data(price_data.symbol, price_data)
        
        # Trigger any registered callbacks
        logger.debug(f"Real-time price update: {price_data.symbol} = ${price_data.price:.6f}")
    
    def _get_cached_price(self, symbol: str) -> Optional[PriceData]:
        """Get cached price data for a symbol."""
        try:
            cache_key = f"price:{symbol}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data_dict = json.loads(cached_data)
                return PriceData.from_dict(data_dict)
                
        except Exception as e:
            logger.debug(f"Cache read error for {symbol}: {e}")
        
        return None
    
    def _cache_price_data(self, symbol: str, price_data: PriceData) -> None:
        """Cache price data for a symbol."""
        try:
            cache_key = f"price:{symbol}"
            data_json = json.dumps(price_data.to_dict())
            self.redis_client.setex(cache_key, self.cache_ttl, data_json)
            
        except Exception as e:
            logger.debug(f"Cache write error for {symbol}: {e}")
    
    def get_historical_data(self, symbol: str, days: int = 30) -> List[PriceData]:
        """Get historical price data for a symbol."""
        # Simplified implementation - would fetch from data sources
        logger.debug(f"Historical data request for {symbol}, {days} days")
        return []
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary."""
        # Get data for major cryptocurrencies
        major_symbols = ['BTC', 'ETH', 'USDC', 'USDT']
        price_data = self.get_price_data(major_symbols)
        
        total_volume = sum(data.volume_24h for data in price_data.values())
        avg_change = sum(data.change_24h for data in price_data.values()) / len(price_data) if price_data else 0
        
        return {
            'total_symbols': len(price_data),
            'total_volume_24h': total_volume,
            'average_change_24h': avg_change,
            'last_update': datetime.utcnow().isoformat(),
            'data_sources': list(self.sources.keys())
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all data sources."""
        health_status = {}
        
        for source_name, source in self.sources.items():
            try:
                # Test with a simple request
                test_data = source.get_price_data(['BTC'])
                health_status[source_name] = {
                    'status': 'healthy' if test_data else 'degraded',
                    'last_check': datetime.utcnow().isoformat()
                }
            except Exception as e:
                health_status[source_name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_check': datetime.utcnow().isoformat()
                }
        
        return health_status
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.stop_realtime_stream()
        self.executor.shutdown(wait=True)
        logger.info("Price Data Manager cleaned up")

