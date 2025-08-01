"""
Risk Management System for Crypto Trading Bot
Implements position sizing, stop-loss management, and risk controls.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math

from ..utils.config_manager import get_config

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    size: float
    entry_price: float
    current_price: float
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None
    
    @property
    def value(self) -> float:
        """Current position value."""
        return self.size * self.current_price
    
    @property
    def pnl(self) -> float:
        """Current profit/loss."""
        return (self.current_price - self.entry_price) * self.size
    
    @property
    def pnl_pct(self) -> float:
        """Current profit/loss percentage."""
        return (self.current_price - self.entry_price) / self.entry_price * 100


@dataclass
class RiskMetrics:
    """Risk metrics for portfolio assessment."""
    total_exposure: float
    max_position_size: float
    current_drawdown: float
    daily_pnl: float
    weekly_pnl: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    max_correlation: float
    risk_level: RiskLevel


class PositionSizer:
    """Handles position sizing calculations."""
    
    def __init__(self, config):
        self.config = config
        self.kelly_fraction = config.risk_management.kelly_fraction
        
    def calculate_kelly_size(self, win_rate: float, avg_win: float, avg_loss: float, 
                           capital: float) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive value)
            capital: Available capital
            
        Returns:
            Optimal position size
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Apply conservative scaling
        kelly_fraction *= self.kelly_fraction
        
        # Ensure within bounds
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Max 25% of capital
        
        return capital * kelly_fraction
    
    def calculate_volatility_size(self, volatility: float, capital: float, 
                                target_risk: float = 0.02) -> float:
        """
        Calculate position size based on volatility targeting.
        
        Args:
            volatility: Asset volatility (annualized)
            capital: Available capital
            target_risk: Target risk per trade (default 2%)
            
        Returns:
            Position size based on volatility
        """
        if volatility <= 0:
            return 0.0
        
        # Daily volatility
        daily_vol = volatility / math.sqrt(252)
        
        # Position size to achieve target risk
        position_size = (capital * target_risk) / daily_vol
        
        return position_size
    
    def calculate_fixed_size(self, capital: float, fixed_pct: float = 0.02) -> float:
        """
        Calculate fixed percentage position size.
        
        Args:
            capital: Available capital
            fixed_pct: Fixed percentage (default 2%)
            
        Returns:
            Fixed position size
        """
        return capital * fixed_pct


class StopLossManager:
    """Manages stop-loss orders and trailing stops."""
    
    def __init__(self, config):
        self.config = config
        self.default_stop_pct = config.risk_management.stop_loss.get("default_pct", 5.0)
        self.trailing_pct = config.risk_management.stop_loss.get("trailing_pct", 2.0)
        self.max_stop_pct = config.risk_management.stop_loss.get("max_pct", 10.0)
    
    def calculate_stop_loss(self, entry_price: float, position_type: str = "long",
                          volatility: Optional[float] = None) -> float:
        """
        Calculate stop-loss level for a position.
        
        Args:
            entry_price: Entry price of the position
            position_type: "long" or "short"
            volatility: Asset volatility for dynamic stop-loss
            
        Returns:
            Stop-loss price level
        """
        if volatility:
            # Dynamic stop-loss based on volatility
            stop_pct = min(volatility * 2, self.max_stop_pct / 100)
        else:
            # Fixed stop-loss
            stop_pct = self.default_stop_pct / 100
        
        if position_type == "long":
            return entry_price * (1 - stop_pct)
        else:  # short
            return entry_price * (1 + stop_pct)
    
    def update_trailing_stop(self, position: Position, current_price: float) -> Optional[float]:
        """
        Update trailing stop-loss for a position.
        
        Args:
            position: Current position
            current_price: Current market price
            
        Returns:
            Updated stop-loss level or None if no update
        """
        if not position.stop_loss:
            return None
        
        trailing_distance = current_price * (self.trailing_pct / 100)
        
        if position.size > 0:  # Long position
            new_stop = current_price - trailing_distance
            if new_stop > position.stop_loss:
                return new_stop
        else:  # Short position
            new_stop = current_price + trailing_distance
            if new_stop < position.stop_loss:
                return new_stop
        
        return None


class RiskManager:
    """Main risk management system."""
    
    def __init__(self):
        self.config = get_config()
        self.position_sizer = PositionSizer(self.config)
        self.stop_loss_manager = StopLossManager(self.config)
        
        # Risk limits
        self.max_position_size_pct = self.config.trading.max_position_size_pct
        self.max_daily_loss_pct = self.config.trading.max_daily_loss_pct
        self.max_weekly_loss_pct = self.config.trading.max_weekly_loss_pct
        self.max_drawdown_pct = self.config.trading.max_drawdown_pct
        self.correlation_threshold = self.config.risk_management.correlation_threshold
        
        # Portfolio tracking
        self.positions: Dict[str, Position] = {}
        self.daily_pnl_history: List[float] = []
        self.equity_curve: List[float] = []
        self.peak_equity = 0.0
        
        logger.info("Risk Manager initialized")
    
    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        self.positions[position.symbol] = position
        logger.info(f"Added position: {position.symbol}, size: {position.size}")
    
    def remove_position(self, symbol: str) -> None:
        """Remove a position from the portfolio."""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Removed position: {symbol}")
    
    def update_position_price(self, symbol: str, current_price: float) -> None:
        """Update the current price for a position."""
        if symbol in self.positions:
            self.positions[symbol].current_price = current_price
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              capital: float, strategy_data: Dict[str, Any]) -> float:
        """
        Calculate optimal position size for a new trade.
        
        Args:
            symbol: Trading symbol
            entry_price: Planned entry price
            capital: Available capital
            strategy_data: Strategy-specific data (win_rate, avg_win, avg_loss, volatility)
            
        Returns:
            Recommended position size
        """
        method = self.config.risk_management.position_sizing.get("method", "kelly")
        
        if method == "kelly":
            win_rate = strategy_data.get("win_rate", 0.6)
            avg_win = strategy_data.get("avg_win", 0.05)
            avg_loss = strategy_data.get("avg_loss", 0.03)
            size = self.position_sizer.calculate_kelly_size(win_rate, avg_win, avg_loss, capital)
            
        elif method == "volatility":
            volatility = strategy_data.get("volatility", 0.3)
            target_risk = strategy_data.get("target_risk", 0.02)
            size = self.position_sizer.calculate_volatility_size(volatility, capital, target_risk)
            
        else:  # fixed
            fixed_pct = strategy_data.get("fixed_pct", 0.02)
            size = self.position_sizer.calculate_fixed_size(capital, fixed_pct)
        
        # Apply position size limits
        max_size = capital * (self.max_position_size_pct / 100)
        min_size = self.config.risk_management.position_sizing.get("min_size", 50.0)
        
        size = max(min_size, min(size, max_size))
        
        # Convert to number of tokens
        token_size = size / entry_price
        
        logger.info(f"Calculated position size for {symbol}: {token_size:.6f} tokens (${size:.2f})")
        
        return token_size
    
    def check_risk_limits(self, new_position_size: float, symbol: str, 
                         current_capital: float) -> Tuple[bool, str]:
        """
        Check if a new position would violate risk limits.
        
        Args:
            new_position_size: Size of the new position
            symbol: Trading symbol
            current_capital: Current portfolio capital
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check position size limit
        position_value = new_position_size
        if position_value > current_capital * (self.max_position_size_pct / 100):
            return False, f"Position size exceeds maximum limit ({self.max_position_size_pct}%)"
        
        # Check total exposure
        total_exposure = sum(abs(pos.value) for pos in self.positions.values()) + position_value
        if total_exposure > current_capital * 2:  # Max 200% exposure
            return False, "Total exposure exceeds maximum limit (200%)"
        
        # Check correlation with existing positions
        if self._check_correlation_risk(symbol):
            return False, f"High correlation with existing positions (>{self.correlation_threshold})"
        
        # Check daily loss limit
        daily_pnl = self.calculate_daily_pnl()
        if daily_pnl < -current_capital * (self.max_daily_loss_pct / 100):
            return False, f"Daily loss limit exceeded ({self.max_daily_loss_pct}%)"
        
        # Check drawdown limit
        current_drawdown = self.calculate_current_drawdown(current_capital)
        if current_drawdown > self.max_drawdown_pct:
            return False, f"Maximum drawdown exceeded ({self.max_drawdown_pct}%)"
        
        return True, "Risk limits satisfied"
    
    def _check_correlation_risk(self, symbol: str) -> bool:
        """Check if adding a position would create excessive correlation."""
        # Simplified correlation check - in practice, would use historical price correlations
        existing_symbols = list(self.positions.keys())
        
        # Basic check for same base token (e.g., ETH in ETH/USDC and ETH/DAI)
        for existing_symbol in existing_symbols:
            if symbol.split('/')[0] == existing_symbol.split('/')[0]:
                return True
        
        return False
    
    def calculate_portfolio_metrics(self, current_capital: float) -> RiskMetrics:
        """Calculate comprehensive risk metrics for the portfolio."""
        total_exposure = sum(abs(pos.value) for pos in self.positions.values())
        max_position_size = max([pos.value for pos in self.positions.values()], default=0)
        
        current_drawdown = self.calculate_current_drawdown(current_capital)
        daily_pnl = self.calculate_daily_pnl()
        weekly_pnl = self.calculate_weekly_pnl()
        
        # Calculate VaR (simplified)
        if len(self.daily_pnl_history) > 30:
            var_95 = np.percentile(self.daily_pnl_history[-30:], 5)
        else:
            var_95 = 0.0
        
        # Calculate Sharpe ratio (simplified)
        if len(self.daily_pnl_history) > 30:
            returns = np.array(self.daily_pnl_history[-30:]) / current_capital
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0.0
        
        # Determine risk level
        risk_level = self._determine_risk_level(current_drawdown, total_exposure / current_capital)
        
        return RiskMetrics(
            total_exposure=total_exposure,
            max_position_size=max_position_size,
            current_drawdown=current_drawdown,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            var_95=var_95,
            sharpe_ratio=sharpe_ratio,
            max_correlation=0.0,  # Simplified
            risk_level=risk_level
        )
    
    def calculate_daily_pnl(self) -> float:
        """Calculate current daily P&L."""
        return sum(pos.pnl for pos in self.positions.values())
    
    def calculate_weekly_pnl(self) -> float:
        """Calculate current weekly P&L."""
        if len(self.daily_pnl_history) >= 7:
            return sum(self.daily_pnl_history[-7:])
        return 0.0
    
    def calculate_current_drawdown(self, current_capital: float) -> float:
        """Calculate current drawdown percentage."""
        if self.peak_equity == 0:
            self.peak_equity = current_capital
        
        self.peak_equity = max(self.peak_equity, current_capital)
        drawdown = (self.peak_equity - current_capital) / self.peak_equity * 100
        
        return drawdown
    
    def _determine_risk_level(self, drawdown: float, exposure_ratio: float) -> RiskLevel:
        """Determine current risk level based on metrics."""
        if drawdown > 10 or exposure_ratio > 1.5:
            return RiskLevel.EXTREME
        elif drawdown > 7 or exposure_ratio > 1.2:
            return RiskLevel.HIGH
        elif drawdown > 4 or exposure_ratio > 0.8:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def should_halt_trading(self, current_capital: float) -> Tuple[bool, str]:
        """Determine if trading should be halted due to risk conditions."""
        metrics = self.calculate_portfolio_metrics(current_capital)
        
        # Halt if daily loss limit exceeded
        if metrics.daily_pnl < -current_capital * (self.max_daily_loss_pct / 100):
            return True, f"Daily loss limit exceeded: {metrics.daily_pnl:.2f}"
        
        # Halt if weekly loss limit exceeded
        if metrics.weekly_pnl < -current_capital * (self.max_weekly_loss_pct / 100):
            return True, f"Weekly loss limit exceeded: {metrics.weekly_pnl:.2f}"
        
        # Halt if maximum drawdown exceeded
        if metrics.current_drawdown > self.max_drawdown_pct:
            return True, f"Maximum drawdown exceeded: {metrics.current_drawdown:.2f}%"
        
        # Halt if risk level is extreme
        if metrics.risk_level == RiskLevel.EXTREME:
            return True, "Risk level is extreme"
        
        return False, "Trading allowed"
    
    def update_stop_losses(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """Update stop-loss levels for all positions."""
        updated_stops = {}
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                position.current_price = current_price
                
                new_stop = self.stop_loss_manager.update_trailing_stop(position, current_price)
                if new_stop:
                    position.stop_loss = new_stop
                    updated_stops[symbol] = new_stop
                    logger.info(f"Updated trailing stop for {symbol}: {new_stop:.6f}")
        
        return updated_stops
    
    def check_stop_loss_triggers(self, current_prices: Dict[str, float]) -> List[str]:
        """Check which positions have triggered stop-losses."""
        triggered_positions = []
        
        for symbol, position in self.positions.items():
            if symbol in current_prices and position.stop_loss:
                current_price = current_prices[symbol]
                
                if position.size > 0:  # Long position
                    if current_price <= position.stop_loss:
                        triggered_positions.append(symbol)
                        logger.warning(f"Stop-loss triggered for {symbol}: {current_price} <= {position.stop_loss}")
                else:  # Short position
                    if current_price >= position.stop_loss:
                        triggered_positions.append(symbol)
                        logger.warning(f"Stop-loss triggered for {symbol}: {current_price} >= {position.stop_loss}")
        
        return triggered_positions
    
    def end_of_day_update(self, current_capital: float) -> None:
        """Perform end-of-day risk management updates."""
        daily_pnl = self.calculate_daily_pnl()
        self.daily_pnl_history.append(daily_pnl)
        self.equity_curve.append(current_capital)
        
        # Keep only last 365 days of history
        if len(self.daily_pnl_history) > 365:
            self.daily_pnl_history = self.daily_pnl_history[-365:]
            self.equity_curve = self.equity_curve[-365:]
        
        logger.info(f"End of day update - Capital: ${current_capital:.2f}, Daily P&L: ${daily_pnl:.2f}")
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all current positions."""
        summary = {
            "total_positions": len(self.positions),
            "total_value": sum(pos.value for pos in self.positions.values()),
            "total_pnl": sum(pos.pnl for pos in self.positions.values()),
            "positions": []
        }
        
        for symbol, position in self.positions.items():
            summary["positions"].append({
                "symbol": symbol,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "value": position.value,
                "pnl": position.pnl,
                "pnl_pct": position.pnl_pct,
                "stop_loss": position.stop_loss,
                "strategy": position.strategy
            })
        
        return summary

