"""
Backtesting Framework for Crypto Trading Bot
Validates trading strategies using historical data and performance metrics.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from ..strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from ..data_sources.price_data import PriceData
from ..risk_management.risk_manager import RiskManager, Position
from ..utils.config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Represents a completed trade in backtesting."""
    symbol: str
    strategy: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    side: str  # "buy" or "sell"
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    duration_hours: float
    exit_reason: str


@dataclass
class BacktestMetrics:
    """Comprehensive backtesting performance metrics."""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Return metrics
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade metrics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    avg_trade_duration: float = 0.0
    
    # Cost metrics
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    # Additional metrics
    best_trade: float = 0.0
    worst_trade: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HistoricalDataGenerator:
    """Generates historical price data for backtesting."""
    
    def __init__(self):
        self.config = get_config()
    
    def generate_sample_data(self, symbol: str, start_date: datetime, end_date: datetime, 
                           interval_hours: int = 1) -> List[PriceData]:
        """
        Generate sample historical data for backtesting.
        In production, this would fetch real historical data.
        """
        data = []
        current_time = start_date
        base_price = 100.0  # Starting price
        
        # Simple random walk with trend and volatility
        np.random.seed(42)  # For reproducible results
        
        while current_time <= end_date:
            # Generate price movement
            trend = 0.0001  # Slight upward trend
            volatility = 0.02  # 2% volatility
            
            price_change = np.random.normal(trend, volatility)
            base_price *= (1 + price_change)
            
            # Generate volume (random around base level)
            base_volume = 1000000
            volume = base_volume * (0.5 + np.random.random())
            
            # Calculate 24h change (simplified)
            change_24h = price_change * 100
            
            price_data = PriceData(
                symbol=symbol,
                price=base_price,
                volume_24h=volume,
                change_24h=change_24h,
                timestamp=current_time,
                source="backtest",
                high_24h=base_price * 1.02,
                low_24h=base_price * 0.98
            )
            
            data.append(price_data)
            current_time += timedelta(hours=interval_hours)
        
        logger.info(f"Generated {len(data)} historical data points for {symbol}")
        return data


class BacktestEngine:
    """Main backtesting engine."""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.config = get_config()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Backtesting parameters
        self.commission_pct = self.config.backtesting.commission_pct / 100
        self.slippage_pct = self.config.backtesting.slippage_pct / 100
        
        # Data and state
        self.historical_data: Dict[str, List[PriceData]] = {}
        self.strategies: List[BaseStrategy] = []
        self.risk_manager = RiskManager()
        
        # Trade tracking
        self.trades: List[BacktestTrade] = []
        self.open_positions: Dict[str, Position] = {}
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []
        
        # Data generator
        self.data_generator = HistoricalDataGenerator()
        
        logger.info(f"Backtest engine initialized with capital: ${initial_capital:,.2f}")
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Add a strategy to the backtest."""
        self.strategies.append(strategy)
        logger.info(f"Added strategy to backtest: {strategy.name}")
    
    def load_historical_data(self, symbols: List[str], start_date: datetime, 
                           end_date: datetime) -> None:
        """Load historical data for backtesting."""
        for symbol in symbols:
            # In production, would load real historical data
            # For now, generate sample data
            data = self.data_generator.generate_sample_data(symbol, start_date, end_date)
            self.historical_data[symbol] = data
        
        logger.info(f"Loaded historical data for {len(symbols)} symbols")
    
    def run_backtest(self, start_date: datetime, end_date: datetime, 
                    symbols: List[str]) -> Dict[str, Any]:
        """Run the complete backtest."""
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Load historical data
        self.load_historical_data(symbols, start_date, end_date)
        
        # Reset state
        self._reset_backtest_state()
        
        # Get all timestamps
        all_timestamps = set()
        for symbol_data in self.historical_data.values():
            all_timestamps.update(data.timestamp for data in symbol_data)
        
        sorted_timestamps = sorted(all_timestamps)
        
        # Run simulation
        for i, timestamp in enumerate(sorted_timestamps):
            self._process_timestamp(timestamp, symbols)
            
            # Record equity curve
            self.equity_curve.append(self.current_capital)
            
            # Calculate daily returns
            if i > 0:
                daily_return = (self.current_capital - self.equity_curve[i-1]) / self.equity_curve[i-1]
                self.daily_returns.append(daily_return)
            
            # Progress logging
            if i % 1000 == 0:
                logger.info(f"Processed {i}/{len(sorted_timestamps)} timestamps")
        
        # Close any remaining positions
        self._close_all_positions(sorted_timestamps[-1])
        
        # Calculate final metrics
        results = self._calculate_backtest_results()
        
        logger.info(f"Backtest completed. Final capital: ${self.current_capital:,.2f}")
        return results
    
    def _reset_backtest_state(self) -> None:
        """Reset backtest state."""
        self.current_capital = self.initial_capital
        self.trades.clear()
        self.open_positions.clear()
        self.equity_curve.clear()
        self.daily_returns.clear()
        
        # Reset strategies
        for strategy in self.strategies:
            strategy.reset()
    
    def _process_timestamp(self, timestamp: datetime, symbols: List[str]) -> None:
        """Process a single timestamp in the backtest."""
        # Get current price data
        current_prices = {}
        for symbol in symbols:
            symbol_data = self.historical_data.get(symbol, [])
            for data in symbol_data:
                if data.timestamp == timestamp:
                    current_prices[symbol] = data
                    break
        
        if not current_prices:
            return
        
        # Update strategies with current data
        for strategy in self.strategies:
            for symbol, price_data in current_prices.items():
                strategy.update_price_cache(symbol, price_data)
        
        # Generate signals from all strategies
        all_signals = []
        for strategy in self.strategies:
            if strategy.is_enabled():
                signals = strategy.generate_signals(current_prices, {})
                all_signals.extend(signals)
        
        # Process signals and execute trades
        self._process_signals(all_signals, current_prices, timestamp)
        
        # Update existing positions
        self._update_positions(current_prices, timestamp)
        
        # Check for position exits
        self._check_position_exits(current_prices, timestamp)
    
    def _process_signals(self, signals: List[TradingSignal], current_prices: Dict[str, PriceData], 
                        timestamp: datetime) -> None:
        """Process trading signals and execute trades."""
        for signal in signals:
            if signal.symbol not in current_prices:
                continue
            
            current_price = current_prices[signal.symbol].price
            
            # Check if we should enter position
            strategy = next((s for s in self.strategies if s.name == signal.strategy), None)
            if not strategy:
                continue
            
            if not strategy.should_enter_position(signal.symbol, current_price, signal):
                continue
            
            # Check if we already have a position in this symbol
            if signal.symbol in self.open_positions:
                continue
            
            # Calculate position size
            strategy_data = {
                'win_rate': strategy.get_metrics().win_rate or 0.6,
                'avg_win': strategy.get_metrics().avg_win or 0.05,
                'avg_loss': strategy.get_metrics().avg_loss or 0.03,
                'volatility': strategy.calculate_volatility(signal.symbol, 20) or 0.3
            }
            
            position_size = self.risk_manager.calculate_position_size(
                signal.symbol, current_price, self.current_capital, strategy_data
            )
            
            if position_size <= 0:
                continue
            
            # Check risk limits
            position_value = position_size * current_price
            is_allowed, reason = self.risk_manager.check_risk_limits(
                position_value, signal.symbol, self.current_capital
            )
            
            if not is_allowed:
                logger.debug(f"Position rejected: {reason}")
                continue
            
            # Execute trade
            self._execute_trade(signal, position_size, current_price, timestamp)
    
    def _execute_trade(self, signal: TradingSignal, quantity: float, price: float, 
                      timestamp: datetime) -> None:
        """Execute a trade based on signal."""
        # Calculate costs
        trade_value = quantity * price
        commission = trade_value * self.commission_pct
        slippage = trade_value * self.slippage_pct
        total_cost = commission + slippage
        
        # Check if we have enough capital
        if trade_value + total_cost > self.current_capital:
            return
        
        # Create position
        position = Position(
            symbol=signal.symbol,
            size=quantity if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else -quantity,
            entry_price=price,
            current_price=price,
            timestamp=timestamp,
            strategy=signal.strategy
        )
        
        # Calculate stop loss
        volatility = next((s.calculate_volatility(signal.symbol, 20) for s in self.strategies 
                          if s.name == signal.strategy), 0.3)
        
        if position.size > 0:  # Long position
            position.stop_loss = price * (1 - min(0.05, volatility * 2))
        else:  # Short position
            position.stop_loss = price * (1 + min(0.05, volatility * 2))
        
        # Add to positions
        self.open_positions[signal.symbol] = position
        self.risk_manager.add_position(position)
        
        # Update capital
        self.current_capital -= (trade_value + total_cost)
        
        logger.debug(f"Opened position: {signal.symbol} {signal.signal_type.value} "
                    f"qty={quantity:.6f} price=${price:.6f}")
    
    def _update_positions(self, current_prices: Dict[str, PriceData], timestamp: datetime) -> None:
        """Update existing positions with current prices."""
        for symbol, position in self.open_positions.items():
            if symbol in current_prices:
                position.current_price = current_prices[symbol].price
                self.risk_manager.update_position_price(symbol, position.current_price)
    
    def _check_position_exits(self, current_prices: Dict[str, PriceData], timestamp: datetime) -> None:
        """Check if any positions should be exited."""
        positions_to_close = []
        
        for symbol, position in self.open_positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol].price
            position_age = timestamp - position.timestamp
            
            # Check strategy exit conditions
            strategy = next((s for s in self.strategies if s.name == position.strategy), None)
            should_exit = False
            exit_reason = ""
            
            if strategy:
                if strategy.should_exit_position(symbol, current_price, position.entry_price, position_age):
                    should_exit = True
                    exit_reason = "strategy_exit"
            
            # Check stop loss
            if position.stop_loss:
                if ((position.size > 0 and current_price <= position.stop_loss) or
                    (position.size < 0 and current_price >= position.stop_loss)):
                    should_exit = True
                    exit_reason = "stop_loss"
            
            # Check risk manager conditions
            halt_trading, halt_reason = self.risk_manager.should_halt_trading(self.current_capital)
            if halt_trading:
                should_exit = True
                exit_reason = f"risk_halt_{halt_reason}"
            
            if should_exit:
                positions_to_close.append((symbol, exit_reason))
        
        # Close positions
        for symbol, exit_reason in positions_to_close:
            self._close_position(symbol, current_prices[symbol].price, timestamp, exit_reason)
    
    def _close_position(self, symbol: str, exit_price: float, timestamp: datetime, 
                       exit_reason: str) -> None:
        """Close a position and record the trade."""
        if symbol not in self.open_positions:
            return
        
        position = self.open_positions[symbol]
        
        # Calculate trade results
        quantity = abs(position.size)
        trade_value = quantity * exit_price
        commission = trade_value * self.commission_pct
        slippage = trade_value * self.slippage_pct
        total_cost = commission + slippage
        
        # Calculate P&L
        if position.size > 0:  # Long position
            pnl = (exit_price - position.entry_price) * quantity - total_cost
        else:  # Short position
            pnl = (position.entry_price - exit_price) * quantity - total_cost
        
        pnl_pct = pnl / (quantity * position.entry_price) * 100
        
        # Update capital
        self.current_capital += trade_value - total_cost + pnl
        
        # Record trade
        duration_hours = (timestamp - position.timestamp).total_seconds() / 3600
        
        trade = BacktestTrade(
            symbol=symbol,
            strategy=position.strategy,
            entry_time=position.timestamp,
            exit_time=timestamp,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=quantity,
            side="buy" if position.size > 0 else "sell",
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=commission,
            slippage=slippage,
            duration_hours=duration_hours,
            exit_reason=exit_reason
        )
        
        self.trades.append(trade)
        
        # Update strategy
        strategy = next((s for s in self.strategies if s.name == position.strategy), None)
        if strategy:
            strategy.add_trade({
                'symbol': symbol,
                'return': pnl_pct / 100,
                'duration': duration_hours,
                'exit_reason': exit_reason
            })
        
        # Remove from positions
        del self.open_positions[symbol]
        self.risk_manager.remove_position(symbol)
        
        logger.debug(f"Closed position: {symbol} P&L=${pnl:.2f} ({pnl_pct:.2f}%) reason={exit_reason}")
    
    def _close_all_positions(self, final_timestamp: datetime) -> None:
        """Close all remaining positions at the end of backtest."""
        symbols_to_close = list(self.open_positions.keys())
        
        for symbol in symbols_to_close:
            # Use last available price
            symbol_data = self.historical_data.get(symbol, [])
            if symbol_data:
                final_price = symbol_data[-1].price
                self._close_position(symbol, final_price, final_timestamp, "backtest_end")
    
    def _calculate_backtest_results(self) -> Dict[str, Any]:
        """Calculate comprehensive backtest results."""
        if not self.trades:
            return {"error": "No trades executed"}
        
        metrics = BacktestMetrics()
        
        # Basic trade metrics
        metrics.total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        metrics.win_rate = metrics.winning_trades / metrics.total_trades * 100
        
        # Return metrics
        metrics.total_return = self.current_capital - self.initial_capital
        metrics.total_return_pct = metrics.total_return / self.initial_capital * 100
        
        # Calculate annualized return
        if self.daily_returns:
            days = len(self.daily_returns)
            if days > 0:
                daily_return = (self.current_capital / self.initial_capital) ** (1/days) - 1
                metrics.annualized_return = ((1 + daily_return) ** 365 - 1) * 100
        
        # Risk metrics
        if self.equity_curve:
            peak = np.maximum.accumulate(self.equity_curve)
            drawdown = (peak - self.equity_curve) / peak
            metrics.max_drawdown_pct = np.max(drawdown) * 100
            metrics.max_drawdown = np.max(peak - self.equity_curve)
        
        if self.daily_returns:
            metrics.volatility = np.std(self.daily_returns) * np.sqrt(365) * 100
            
            if metrics.volatility > 0:
                metrics.sharpe_ratio = (metrics.annualized_return / 100) / (metrics.volatility / 100)
            
            # Sortino ratio (downside deviation)
            downside_returns = [r for r in self.daily_returns if r < 0]
            if downside_returns:
                downside_deviation = np.std(downside_returns) * np.sqrt(365)
                metrics.sortino_ratio = (metrics.annualized_return / 100) / downside_deviation
        
        # Calmar ratio
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown_pct
        
        # Trade metrics
        if winning_trades:
            metrics.avg_win = np.mean([t.pnl for t in winning_trades])
        
        if losing_trades:
            metrics.avg_loss = abs(np.mean([t.pnl for t in losing_trades]))
        
        if metrics.avg_loss > 0:
            metrics.profit_factor = (metrics.avg_win * metrics.winning_trades) / (metrics.avg_loss * metrics.losing_trades)
        
        metrics.avg_trade_duration = np.mean([t.duration_hours for t in self.trades])
        
        # Cost metrics
        metrics.total_commission = sum(t.commission for t in self.trades)
        metrics.total_slippage = sum(t.slippage for t in self.trades)
        
        # Additional metrics
        if self.trades:
            metrics.best_trade = max(t.pnl for t in self.trades)
            metrics.worst_trade = min(t.pnl for t in self.trades)
        
        # Calculate consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                consecutive_wins = max(consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                consecutive_losses = max(consecutive_losses, current_losses)
        
        metrics.consecutive_wins = consecutive_wins
        metrics.consecutive_losses = consecutive_losses
        
        # Strategy-specific results
        strategy_results = {}
        for strategy in self.strategies:
            strategy_trades = [t for t in self.trades if t.strategy == strategy.name]
            if strategy_trades:
                strategy_pnl = sum(t.pnl for t in strategy_trades)
                strategy_results[strategy.name] = {
                    'trades': len(strategy_trades),
                    'pnl': strategy_pnl,
                    'win_rate': len([t for t in strategy_trades if t.pnl > 0]) / len(strategy_trades) * 100,
                    'metrics': strategy.get_metrics().to_dict() if hasattr(strategy.get_metrics(), 'to_dict') else {}
                }
        
        return {
            'metrics': metrics.to_dict(),
            'strategy_results': strategy_results,
            'trades': [asdict(trade) for trade in self.trades],
            'equity_curve': self.equity_curve,
            'daily_returns': self.daily_returns
        }
    
    def generate_report(self, results: Dict[str, Any], output_dir: str = None) -> str:
        """Generate a comprehensive backtest report."""
        if output_dir is None:
            output_dir = "/home/ubuntu/crypto_trading_bot/backtesting_results"
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate plots
        self._generate_plots(results, output_dir)
        
        # Generate text report
        report_path = Path(output_dir) / "backtest_report.txt"
        
        with open(report_path, 'w') as f:
            f.write("CRYPTO TRADING BOT BACKTEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            metrics = results['metrics']
            
            f.write("PERFORMANCE SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Initial Capital: ${self.initial_capital:,.2f}\n")
            f.write(f"Final Capital: ${self.current_capital:,.2f}\n")
            f.write(f"Total Return: ${metrics['total_return']:,.2f} ({metrics['total_return_pct']:.2f}%)\n")
            f.write(f"Annualized Return: {metrics['annualized_return']:.2f}%\n")
            f.write(f"Max Drawdown: ${metrics['max_drawdown']:,.2f} ({metrics['max_drawdown_pct']:.2f}%)\n")
            f.write(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n")
            f.write(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}\n")
            f.write(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}\n\n")
            
            f.write("TRADE STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Trades: {metrics['total_trades']}\n")
            f.write(f"Winning Trades: {metrics['winning_trades']}\n")
            f.write(f"Losing Trades: {metrics['losing_trades']}\n")
            f.write(f"Win Rate: {metrics['win_rate']:.2f}%\n")
            f.write(f"Profit Factor: {metrics['profit_factor']:.2f}\n")
            f.write(f"Average Win: ${metrics['avg_win']:.2f}\n")
            f.write(f"Average Loss: ${metrics['avg_loss']:.2f}\n")
            f.write(f"Best Trade: ${metrics['best_trade']:.2f}\n")
            f.write(f"Worst Trade: ${metrics['worst_trade']:.2f}\n")
            f.write(f"Average Trade Duration: {metrics['avg_trade_duration']:.1f} hours\n\n")
            
            f.write("COST ANALYSIS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Commission: ${metrics['total_commission']:.2f}\n")
            f.write(f"Total Slippage: ${metrics['total_slippage']:.2f}\n\n")
            
            f.write("STRATEGY BREAKDOWN\n")
            f.write("-" * 20 + "\n")
            for strategy_name, strategy_data in results['strategy_results'].items():
                f.write(f"{strategy_name.upper()}:\n")
                f.write(f"  Trades: {strategy_data['trades']}\n")
                f.write(f"  P&L: ${strategy_data['pnl']:.2f}\n")
                f.write(f"  Win Rate: {strategy_data['win_rate']:.2f}%\n\n")
        
        logger.info(f"Backtest report generated: {report_path}")
        return str(report_path)
    
    def _generate_plots(self, results: Dict[str, Any], output_dir: str) -> None:
        """Generate visualization plots for backtest results."""
        try:
            # Set style
            plt.style.use('seaborn-v0_8')
            
            # 1. Equity Curve
            plt.figure(figsize=(12, 6))
            plt.plot(results['equity_curve'])
            plt.title('Equity Curve')
            plt.xlabel('Time')
            plt.ylabel('Capital ($)')
            plt.grid(True)
            plt.savefig(Path(output_dir) / 'equity_curve.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 2. Daily Returns Distribution
            if results['daily_returns']:
                plt.figure(figsize=(10, 6))
                plt.hist(results['daily_returns'], bins=50, alpha=0.7, edgecolor='black')
                plt.title('Daily Returns Distribution')
                plt.xlabel('Daily Return')
                plt.ylabel('Frequency')
                plt.grid(True)
                plt.savefig(Path(output_dir) / 'returns_distribution.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            # 3. Trade P&L Distribution
            if results['trades']:
                trade_pnls = [trade['pnl'] for trade in results['trades']]
                plt.figure(figsize=(10, 6))
                plt.hist(trade_pnls, bins=30, alpha=0.7, edgecolor='black')
                plt.title('Trade P&L Distribution')
                plt.xlabel('Trade P&L ($)')
                plt.ylabel('Frequency')
                plt.grid(True)
                plt.savefig(Path(output_dir) / 'trade_pnl_distribution.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            logger.info(f"Plots generated in {output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating plots: {e}")
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save backtest results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.json"
        
        output_path = Path("/home/ubuntu/crypto_trading_bot/backtesting_results") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert datetime objects to strings for JSON serialization
        serializable_results = self._make_json_serializable(results)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Backtest results saved: {output_path}")
        return str(output_path)
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj

