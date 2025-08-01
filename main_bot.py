"""
Main Trading Bot Application
Orchestrates all components of the crypto trading bot system.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import schedule

from .utils.config_manager import get_config
from .data_sources.price_data import PriceDataManager
from .strategies.momentum_strategy import MomentumStrategy
from .strategies.mean_reversion_strategy import MeanReversionStrategy
from .risk_management.risk_manager import RiskManager
from .execution.execution_engine import ExecutionEngine, Order, OrderType
from .monitoring.performance_monitor import PerformanceMonitor
from .monitoring.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize components
        self.price_manager = PriceDataManager()
        self.risk_manager = RiskManager()
        self.execution_engine = ExecutionEngine()
        self.performance_monitor = PerformanceMonitor()
        self.alert_manager = AlertManager()
        
        # Initialize strategies
        self.strategies = []
        self._initialize_strategies()
        
        # Bot state
        self.running = False
        self.current_capital = self.config.trading.initial_capital
        self.trading_enabled = True
        self.last_update = datetime.utcnow()
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=self.config.system.max_workers)
        self.main_loop_thread = None
        
        # Symbols to trade
        self.trading_symbols = [
            "BTC", "ETH", "USDC", "LINK", "UNI", "AAVE", "COMP", "MKR", "SNX", "YFI"
        ]
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        logger.info("Trading Bot initialized successfully")
    
    def _initialize_strategies(self) -> None:
        """Initialize trading strategies based on configuration."""
        config_strategies = self.config.strategies
        
        # Momentum strategy
        if config_strategies.get("momentum", {}).get("enabled", False):
            momentum_config = config_strategies["momentum"].__dict__ if hasattr(config_strategies["momentum"], "__dict__") else {}
            self.strategies.append(MomentumStrategy(momentum_config))
        
        # Mean reversion strategy
        if config_strategies.get("mean_reversion", {}).get("enabled", False):
            mean_reversion_config = config_strategies["mean_reversion"].__dict__ if hasattr(config_strategies["mean_reversion"], "__dict__") else {}
            self.strategies.append(MeanReversionStrategy(mean_reversion_config))
        
        logger.info(f"Initialized {len(self.strategies)} trading strategies")
    
    def start(self) -> None:
        """Start the trading bot."""
        if self.running:
            logger.warning("Trading bot is already running")
            return
        
        logger.info("Starting trading bot...")
        
        self.running = True
        
        # Start data feeds
        self.price_manager.start_realtime_stream(self.trading_symbols)
        
        # Start main trading loop
        self.main_loop_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_loop_thread.start()
        
        # Schedule periodic tasks
        self._schedule_periodic_tasks()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Trading bot started successfully")
    
    def stop(self) -> None:
        """Stop the trading bot."""
        if not self.running:
            logger.warning("Trading bot is not running")
            return
        
        logger.info("Stopping trading bot...")
        
        self.running = False
        
        # Stop data feeds
        self.price_manager.stop_realtime_stream()
        
        # Wait for main loop to finish
        if self.main_loop_thread and self.main_loop_thread.is_alive():
            self.main_loop_thread.join(timeout=10)
        
        # Cleanup components
        self._cleanup()
        
        logger.info("Trading bot stopped successfully")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _main_loop(self) -> None:
        """Main trading loop."""
        logger.info("Main trading loop started")
        
        while self.running:
            try:
                loop_start_time = time.time()
                
                # Update current prices
                current_prices = self._get_current_prices()
                
                if not current_prices:
                    time.sleep(1)
                    continue
                
                # Check if trading should be halted
                if not self._should_continue_trading():
                    logger.warning("Trading halted due to risk conditions")
                    time.sleep(60)  # Wait 1 minute before checking again
                    continue
                
                # Generate signals from all strategies
                all_signals = self._generate_signals(current_prices)
                
                # Process signals and execute trades
                if all_signals:
                    self._process_signals(all_signals, current_prices)
                
                # Update existing positions
                self._update_positions(current_prices)
                
                # Check for position exits
                self._check_position_exits(current_prices)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Update last update time
                self.last_update = datetime.utcnow()
                
                # Sleep to maintain loop frequency
                loop_duration = time.time() - loop_start_time
                sleep_time = max(0, self.config.data.price_update_interval - loop_duration)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in main trading loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info("Main trading loop stopped")
    
    def _get_current_prices(self) -> Dict[str, Any]:
        """Get current price data for all trading symbols."""
        try:
            price_data = self.price_manager.get_price_data(self.trading_symbols, use_cache=True)
            return price_data
        except Exception as e:
            logger.error(f"Error getting current prices: {e}")
            return {}
    
    def _should_continue_trading(self) -> bool:
        """Check if trading should continue based on risk conditions."""
        # Check risk manager conditions
        should_halt, reason = self.risk_manager.should_halt_trading(self.current_capital)
        
        if should_halt:
            self.alert_manager.send_alert(
                "Trading Halted",
                f"Trading has been halted: {reason}",
                "high"
            )
            return False
        
        # Check if trading is manually disabled
        if not self.trading_enabled:
            return False
        
        return True
    
    def _generate_signals(self, current_prices: Dict[str, Any]) -> List[Any]:
        """Generate trading signals from all strategies."""
        all_signals = []
        
        for strategy in self.strategies:
            if not strategy.is_enabled():
                continue
            
            try:
                # Update strategy with current price data
                for symbol, price_data in current_prices.items():
                    strategy.update_price_cache(symbol, price_data)
                
                # Generate signals
                signals = strategy.generate_signals(current_prices, {})
                
                # Weight signals by strategy weight
                for signal in signals:
                    signal.strength *= strategy.get_weight()
                
                all_signals.extend(signals)
                
            except Exception as e:
                logger.error(f"Error generating signals from {strategy.name}: {e}")
        
        # Sort signals by strength (strongest first)
        all_signals.sort(key=lambda s: s.strength, reverse=True)
        
        logger.debug(f"Generated {len(all_signals)} signals from {len(self.strategies)} strategies")
        return all_signals
    
    def _process_signals(self, signals: List[Any], current_prices: Dict[str, Any]) -> None:
        """Process trading signals and execute trades."""
        for signal in signals:
            try:
                if signal.symbol not in current_prices:
                    continue
                
                current_price = current_prices[signal.symbol].price
                
                # Check if we should enter position
                strategy = next((s for s in self.strategies if s.name == signal.strategy), None)
                if not strategy:
                    continue
                
                if not strategy.should_enter_position(signal.symbol, current_price, signal):
                    continue
                
                # Check if we already have a position
                existing_positions = self.risk_manager.get_position_summary()
                if any(pos['symbol'] == signal.symbol for pos in existing_positions['positions']):
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
                    logger.debug(f"Position rejected for {signal.symbol}: {reason}")
                    continue
                
                # Create and execute order
                order = Order(
                    id=f"order_{signal.symbol}_{int(time.time())}",
                    symbol=signal.symbol,
                    side="buy" if signal.signal_type.value in ["buy", "strong_buy"] else "sell",
                    order_type=OrderType.MARKET,
                    quantity=position_size,
                    price=current_price,
                    strategy=signal.strategy
                )
                
                # Execute order asynchronously
                self.executor.submit(self._execute_order_async, order)
                
            except Exception as e:
                logger.error(f"Error processing signal for {signal.symbol}: {e}")
    
    def _execute_order_async(self, order: Order) -> None:
        """Execute order asynchronously."""
        try:
            # Execute order
            result = asyncio.run(self.execution_engine.execute_order(order))
            
            if result.success:
                # Create position for risk manager
                from .risk_management.risk_manager import Position
                
                position = Position(
                    symbol=order.symbol,
                    size=order.quantity if order.side == "buy" else -order.quantity,
                    entry_price=result.order.average_price,
                    current_price=result.order.average_price,
                    timestamp=result.order.timestamp,
                    strategy=order.strategy
                )
                
                self.risk_manager.add_position(position)
                
                # Update capital
                trade_value = order.quantity * result.order.average_price
                self.current_capital -= trade_value + result.gas_cost
                
                # Update trade statistics
                self.total_trades += 1
                self.successful_trades += 1
                
                logger.info(f"Order executed successfully: {order.symbol} {order.side} "
                           f"{order.quantity:.6f} @ ${result.order.average_price:.6f}")
                
                # Send alert for significant trades
                if trade_value > self.current_capital * 0.02:  # > 2% of capital
                    self.alert_manager.send_alert(
                        "Large Trade Executed",
                        f"Executed {order.side} order for {order.symbol}: "
                        f"{order.quantity:.6f} @ ${result.order.average_price:.6f}",
                        "medium"
                    )
            else:
                logger.error(f"Order execution failed: {order.symbol} - {result.message}")
                
        except Exception as e:
            logger.error(f"Error executing order {order.id}: {e}")
    
    def _update_positions(self, current_prices: Dict[str, Any]) -> None:
        """Update existing positions with current prices."""
        try:
            # Update risk manager positions
            price_dict = {symbol: data.price for symbol, data in current_prices.items()}
            self.risk_manager.update_stop_losses(price_dict)
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    def _check_position_exits(self, current_prices: Dict[str, Any]) -> None:
        """Check if any positions should be exited."""
        try:
            # Check for stop-loss triggers
            price_dict = {symbol: data.price for symbol, data in current_prices.items()}
            triggered_positions = self.risk_manager.check_stop_loss_triggers(price_dict)
            
            for symbol in triggered_positions:
                self._close_position(symbol, current_prices[symbol].price, "stop_loss")
            
            # Check strategy exit conditions
            position_summary = self.risk_manager.get_position_summary()
            
            for position_data in position_summary['positions']:
                symbol = position_data['symbol']
                strategy_name = position_data['strategy']
                
                if symbol not in current_prices:
                    continue
                
                strategy = next((s for s in self.strategies if s.name == strategy_name), None)
                if not strategy:
                    continue
                
                current_price = current_prices[symbol].price
                entry_price = position_data['entry_price']
                entry_time = datetime.fromisoformat(position_data['timestamp']) if isinstance(position_data['timestamp'], str) else position_data['timestamp']
                position_age = datetime.utcnow() - entry_time
                
                if strategy.should_exit_position(symbol, current_price, entry_price, position_age):
                    self._close_position(symbol, current_price, "strategy_exit")
                    
        except Exception as e:
            logger.error(f"Error checking position exits: {e}")
    
    def _close_position(self, symbol: str, exit_price: float, exit_reason: str) -> None:
        """Close a position."""
        try:
            position_summary = self.risk_manager.get_position_summary()
            position_data = next((p for p in position_summary['positions'] if p['symbol'] == symbol), None)
            
            if not position_data:
                return
            
            # Create exit order
            order = Order(
                id=f"exit_{symbol}_{int(time.time())}",
                symbol=symbol,
                side="sell" if position_data['size'] > 0 else "buy",
                order_type=OrderType.MARKET,
                quantity=abs(position_data['size']),
                price=exit_price
            )
            
            # Execute exit order
            result = asyncio.run(self.execution_engine.execute_order(order))
            
            if result.success:
                # Calculate P&L
                pnl = position_data['pnl']
                
                # Update capital
                trade_value = abs(position_data['size']) * exit_price
                self.current_capital += trade_value - result.gas_cost
                
                # Update daily P&L
                self.daily_pnl += pnl
                
                # Remove position from risk manager
                self.risk_manager.remove_position(symbol)
                
                logger.info(f"Position closed: {symbol} P&L=${pnl:.2f} reason={exit_reason}")
                
                # Send alert for significant losses
                if pnl < -self.current_capital * 0.01:  # > 1% loss
                    self.alert_manager.send_alert(
                        "Significant Loss",
                        f"Closed position {symbol} with loss: ${pnl:.2f}",
                        "high"
                    )
                    
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        try:
            # Update risk manager
            self.risk_manager.end_of_day_update(self.current_capital)
            
            # Update performance monitor
            self.performance_monitor.update_metrics({
                'capital': self.current_capital,
                'daily_pnl': self.daily_pnl,
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'timestamp': datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    def _schedule_periodic_tasks(self) -> None:
        """Schedule periodic maintenance tasks."""
        # Daily tasks
        schedule.every().day.at("00:00").do(self._daily_maintenance)
        
        # Weekly tasks
        schedule.every().week.do(self._weekly_maintenance)
        
        # Hourly tasks
        schedule.every().hour.do(self._hourly_maintenance)
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
    
    def _run_scheduler(self) -> None:
        """Run scheduled tasks."""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _daily_maintenance(self) -> None:
        """Daily maintenance tasks."""
        logger.info("Running daily maintenance...")
        
        # Reset daily P&L
        self.daily_pnl = 0.0
        
        # Generate daily report
        self.performance_monitor.generate_daily_report()
        
        # Check performance targets
        metrics = self.performance_monitor.get_current_metrics()
        
        if metrics.get('daily_return_pct', 0) < -5:  # Daily loss > 5%
            self.alert_manager.send_alert(
                "Daily Performance Alert",
                f"Daily loss exceeded 5%: {metrics.get('daily_return_pct', 0):.2f}%",
                "high"
            )
    
    def _weekly_maintenance(self) -> None:
        """Weekly maintenance tasks."""
        logger.info("Running weekly maintenance...")
        
        # Reset weekly P&L
        self.weekly_pnl = 0.0
        
        # Generate weekly report
        self.performance_monitor.generate_weekly_report()
        
        # Rebalance strategies if needed
        self._rebalance_strategies()
    
    def _hourly_maintenance(self) -> None:
        """Hourly maintenance tasks."""
        # Health check
        health_status = self._health_check()
        
        if not health_status['healthy']:
            self.alert_manager.send_alert(
                "System Health Alert",
                f"System health check failed: {health_status['issues']}",
                "medium"
            )
    
    def _rebalance_strategies(self) -> None:
        """Rebalance strategy weights based on performance."""
        try:
            total_performance = 0.0
            strategy_performances = {}
            
            for strategy in self.strategies:
                metrics = strategy.get_metrics()
                performance_score = metrics.sharpe_ratio if metrics.sharpe_ratio > 0 else 0.1
                strategy_performances[strategy.name] = performance_score
                total_performance += performance_score
            
            # Adjust weights based on performance
            if total_performance > 0:
                for strategy in self.strategies:
                    new_weight = strategy_performances[strategy.name] / total_performance
                    strategy.weight = new_weight
                    logger.info(f"Updated {strategy.name} weight to {new_weight:.3f}")
                    
        except Exception as e:
            logger.error(f"Error rebalancing strategies: {e}")
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        issues = []
        
        # Check data feeds
        try:
            health_status = self.price_manager.health_check()
            unhealthy_sources = [source for source, status in health_status.items() 
                               if status['status'] != 'healthy']
            if unhealthy_sources:
                issues.append(f"Unhealthy data sources: {unhealthy_sources}")
        except Exception as e:
            issues.append(f"Data feed health check failed: {e}")
        
        # Check execution engine
        try:
            exec_stats = self.execution_engine.get_execution_stats()
            if exec_stats.get('success_rate', 100) < 90:
                issues.append(f"Low execution success rate: {exec_stats['success_rate']:.1f}%")
        except Exception as e:
            issues.append(f"Execution engine health check failed: {e}")
        
        # Check capital levels
        if self.current_capital < self.config.trading.initial_capital * 0.8:
            issues.append(f"Capital below 80% of initial: ${self.current_capital:.2f}")
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.utcnow()
        }
    
    def _cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Close all positions
            position_summary = self.risk_manager.get_position_summary()
            for position_data in position_summary['positions']:
                symbol = position_data['symbol']
                # Get current price for closing
                current_prices = self._get_current_prices()
                if symbol in current_prices:
                    self._close_position(symbol, current_prices[symbol].price, "shutdown")
            
            # Cleanup components
            self.price_manager.cleanup()
            self.execution_engine.cleanup()
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        position_summary = self.risk_manager.get_position_summary()
        
        return {
            'running': self.running,
            'trading_enabled': self.trading_enabled,
            'current_capital': self.current_capital,
            'daily_pnl': self.daily_pnl,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'active_positions': position_summary['total_positions'],
            'total_position_value': position_summary['total_value'],
            'last_update': self.last_update.isoformat(),
            'strategies': [strategy.get_status() for strategy in self.strategies]
        }
    
    def enable_trading(self) -> None:
        """Enable trading."""
        self.trading_enabled = True
        logger.info("Trading enabled")
    
    def disable_trading(self) -> None:
        """Disable trading."""
        self.trading_enabled = False
        logger.info("Trading disabled")


def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/ubuntu/crypto_trading_bot/logs/trading_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create and start bot
    bot = TradingBot()
    
    try:
        bot.start()
        
        # Keep main thread alive
        while bot.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        bot.stop()


if __name__ == "__main__":
    main()

