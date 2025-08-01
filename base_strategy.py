"""
Base Strategy Class for Crypto Trading Bot
Provides common interface and functionality for all trading strategies.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ..utils.config_manager import get_config
from ..data_sources.price_data import PriceData

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """Represents a trading signal."""
    symbol: str
    signal_type: SignalType
    strength: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    strategy: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    def update_metrics(self, trades: List[Dict[str, Any]]) -> None:
        """Update metrics based on trade history."""
        if not trades:
            return
        
        self.total_trades = len(trades)
        
        returns = [trade.get('return', 0.0) for trade in trades]
        winning_returns = [r for r in returns if r > 0]
        losing_returns = [r for r in returns if r < 0]
        
        self.winning_trades = len(winning_returns)
        self.losing_trades = len(losing_returns)
        self.total_return = sum(returns)
        
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
        
        if winning_returns:
            self.avg_win = np.mean(winning_returns)
        
        if losing_returns:
            self.avg_loss = abs(np.mean(losing_returns))
        
        if self.avg_loss > 0:
            self.profit_factor = (self.avg_win * self.winning_trades) / (self.avg_loss * self.losing_trades)
        
        # Calculate Sharpe ratio (simplified)
        if len(returns) > 1:
            self.sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Calculate max drawdown
        cumulative_returns = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (peak - cumulative_returns) / peak
        self.max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0


class TechnicalIndicators:
    """Technical analysis indicators."""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> List[float]:
        """Simple Moving Average."""
        if len(prices) < period:
            return []
        
        sma_values = []
        for i in range(period - 1, len(prices)):
            sma_values.append(np.mean(prices[i - period + 1:i + 1]))
        
        return sma_values
    
    @staticmethod
    def ema(prices: List[float], period: int) -> List[float]:
        """Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = [np.mean(prices[:period])]  # Start with SMA
        
        for i in range(period, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema_value)
        
        return ema_values
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return []
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = []
        avg_losses = []
        
        # Initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        avg_gains.append(avg_gain)
        avg_losses.append(avg_loss)
        
        # Subsequent averages using smoothing
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            avg_gains.append(avg_gain)
            avg_losses.append(avg_loss)
        
        rsi_values = []
        for avg_gain, avg_loss in zip(avg_gains, avg_losses):
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow_period:
            return [], [], []
        
        ema_fast = TechnicalIndicators.ema(prices, fast_period)
        ema_slow = TechnicalIndicators.ema(prices, slow_period)
        
        # Align the arrays
        min_length = min(len(ema_fast), len(ema_slow))
        ema_fast = ema_fast[-min_length:]
        ema_slow = ema_slow[-min_length:]
        
        macd_line = [fast - slow for fast, slow in zip(ema_fast, ema_slow)]
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        
        # Align signal line with MACD line
        macd_aligned = macd_line[-len(signal_line):]
        histogram = [macd - signal for macd, signal in zip(macd_aligned, signal_line)]
        
        return macd_aligned, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Bollinger Bands."""
        if len(prices) < period:
            return [], [], []
        
        sma_values = TechnicalIndicators.sma(prices, period)
        
        upper_bands = []
        lower_bands = []
        
        for i in range(len(sma_values)):
            price_slice = prices[i:i + period]
            std = np.std(price_slice)
            
            upper_bands.append(sma_values[i] + (std_dev * std))
            lower_bands.append(sma_values[i] - (std_dev * std))
        
        return upper_bands, sma_values, lower_bands
    
    @staticmethod
    def stochastic(highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3) -> Tuple[List[float], List[float]]:
        """Stochastic Oscillator."""
        if len(closes) < k_period:
            return [], []
        
        k_values = []
        
        for i in range(k_period - 1, len(closes)):
            high_max = max(highs[i - k_period + 1:i + 1])
            low_min = min(lows[i - k_period + 1:i + 1])
            
            if high_max == low_min:
                k_values.append(50)  # Avoid division by zero
            else:
                k = ((closes[i] - low_min) / (high_max - low_min)) * 100
                k_values.append(k)
        
        d_values = TechnicalIndicators.sma(k_values, d_period)
        
        return k_values, d_values


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.weight = self.config.get('weight', 0.2)
        
        # Strategy state
        self.signals_history: List[TradingSignal] = []
        self.trades_history: List[Dict[str, Any]] = []
        self.metrics = StrategyMetrics()
        
        # Technical indicators
        self.indicators = TechnicalIndicators()
        
        # Price data cache
        self.price_cache: Dict[str, List[PriceData]] = {}
        
        logger.info(f"Strategy initialized: {self.name}")
    
    @abstractmethod
    def generate_signals(self, price_data: Dict[str, PriceData], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """
        Generate trading signals based on current market data.
        
        Args:
            price_data: Current price data for all symbols
            market_data: Additional market data (sentiment, volume, etc.)
            
        Returns:
            List of trading signals
        """
        pass
    
    @abstractmethod
    def should_enter_position(self, symbol: str, current_price: float, signal: TradingSignal) -> bool:
        """
        Determine if a position should be entered based on signal.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            signal: Generated trading signal
            
        Returns:
            True if position should be entered
        """
        pass
    
    @abstractmethod
    def should_exit_position(self, symbol: str, current_price: float, entry_price: float, 
                           position_age: timedelta) -> bool:
        """
        Determine if a position should be exited.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            position_age: Time since position was opened
            
        Returns:
            True if position should be exited
        """
        pass
    
    def update_price_cache(self, symbol: str, price_data: PriceData) -> None:
        """Update price data cache for a symbol."""
        if symbol not in self.price_cache:
            self.price_cache[symbol] = []
        
        self.price_cache[symbol].append(price_data)
        
        # Keep only recent data (e.g., last 1000 points)
        max_cache_size = 1000
        if len(self.price_cache[symbol]) > max_cache_size:
            self.price_cache[symbol] = self.price_cache[symbol][-max_cache_size:]
    
    def get_price_history(self, symbol: str, periods: int) -> List[float]:
        """Get price history for a symbol."""
        if symbol not in self.price_cache:
            return []
        
        prices = [data.price for data in self.price_cache[symbol]]
        return prices[-periods:] if len(prices) >= periods else prices
    
    def get_volume_history(self, symbol: str, periods: int) -> List[float]:
        """Get volume history for a symbol."""
        if symbol not in self.price_cache:
            return []
        
        volumes = [data.volume_24h for data in self.price_cache[symbol]]
        return volumes[-periods:] if len(volumes) >= periods else volumes
    
    def calculate_volatility(self, symbol: str, periods: int = 30) -> float:
        """Calculate price volatility for a symbol."""
        prices = self.get_price_history(symbol, periods)
        
        if len(prices) < 2:
            return 0.0
        
        returns = np.diff(np.log(prices))
        return np.std(returns) * np.sqrt(252)  # Annualized volatility
    
    def add_signal(self, signal: TradingSignal) -> None:
        """Add a signal to history."""
        self.signals_history.append(signal)
        
        # Keep only recent signals
        max_signals = 10000
        if len(self.signals_history) > max_signals:
            self.signals_history = self.signals_history[-max_signals:]
    
    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Add a trade to history."""
        self.trades_history.append(trade)
        
        # Update metrics
        self.metrics.update_metrics(self.trades_history)
        
        logger.info(f"Trade recorded for {self.name}: {trade}")
    
    def get_recent_signals(self, symbol: str, hours: int = 24) -> List[TradingSignal]:
        """Get recent signals for a symbol."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            signal for signal in self.signals_history
            if signal.symbol == symbol and signal.timestamp >= cutoff_time
        ]
    
    def get_signal_strength(self, signals: List[TradingSignal]) -> float:
        """Calculate combined signal strength."""
        if not signals:
            return 0.0
        
        # Weight recent signals more heavily
        total_weight = 0.0
        weighted_strength = 0.0
        
        for signal in signals:
            age_hours = (datetime.utcnow() - signal.timestamp).total_seconds() / 3600
            weight = max(0.1, 1.0 - (age_hours / 24))  # Decay over 24 hours
            
            total_weight += weight
            weighted_strength += signal.strength * weight
        
        return weighted_strength / total_weight if total_weight > 0 else 0.0
    
    def is_enabled(self) -> bool:
        """Check if strategy is enabled."""
        return self.enabled
    
    def get_weight(self) -> float:
        """Get strategy weight."""
        return self.weight
    
    def get_metrics(self) -> StrategyMetrics:
        """Get strategy performance metrics."""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status summary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "weight": self.weight,
            "total_signals": len(self.signals_history),
            "total_trades": len(self.trades_history),
            "metrics": {
                "win_rate": self.metrics.win_rate,
                "total_return": self.metrics.total_return,
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "max_drawdown": self.metrics.max_drawdown
            }
        }
    
    def reset(self) -> None:
        """Reset strategy state."""
        self.signals_history.clear()
        self.trades_history.clear()
        self.price_cache.clear()
        self.metrics = StrategyMetrics()
        
        logger.info(f"Strategy reset: {self.name}")
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """Validate a trading signal."""
        # Basic validation
        if signal.strength < 0 or signal.strength > 1:
            return False
        
        if signal.confidence < 0 or signal.confidence > 1:
            return False
        
        if signal.price <= 0:
            return False
        
        return True
    
    def filter_signals(self, signals: List[TradingSignal], min_strength: float = 0.5) -> List[TradingSignal]:
        """Filter signals based on strength and other criteria."""
        filtered = []
        
        for signal in signals:
            if not self.validate_signal(signal):
                continue
            
            if signal.strength < min_strength:
                continue
            
            # Avoid duplicate signals for same symbol within short time
            recent_signals = self.get_recent_signals(signal.symbol, hours=1)
            if any(s.signal_type == signal.signal_type for s in recent_signals):
                continue
            
            filtered.append(signal)
        
        return filtered

