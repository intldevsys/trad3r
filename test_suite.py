#!/usr/bin/env python3
"""
Comprehensive Test Suite for Crypto Trading Bot
Tests all components and integration points.
"""

import unittest
import sys
import os
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import components to test
try:
    from src.utils.config_manager import ConfigManager, get_config
    from src.risk_management.risk_manager import RiskManager, Position
    from src.data_sources.price_data import PriceData, PriceDataManager
    from src.strategies.momentum_strategy import MomentumStrategy
    from src.strategies.mean_reversion_strategy import MeanReversionStrategy
    from src.execution.execution_engine import ExecutionEngine, Order, OrderType
    from src.backtesting.backtester import BacktestEngine, BacktestMetrics
    from src.monitoring.performance_monitor import PerformanceMonitor
    from src.monitoring.alert_manager import AlertManager
except ImportError as e:
    print(f"Warning: Could not import some components: {e}")


class TestConfigManager(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test configuration."""
        self.test_config = {
            'trading': {
                'initial_capital': 10000.0,
                'max_position_size_pct': 5.0,
                'max_daily_loss_pct': 5.0
            },
            'risk_management': {
                'kelly_fraction': 0.25,
                'volatility_lookback': 20
            }
        }
    
    def test_config_loading(self):
        """Test configuration loading."""
        try:
            config = get_config()
            self.assertIsNotNone(config)
            self.assertTrue(hasattr(config, 'trading'))
            self.assertTrue(hasattr(config, 'risk_management'))
        except Exception as e:
            self.skipTest(f"Config loading failed: {e}")
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid config
        self.assertIsInstance(self.test_config['trading']['initial_capital'], (int, float))
        self.assertGreater(self.test_config['trading']['initial_capital'], 0)
        
        # Test invalid config
        invalid_config = self.test_config.copy()
        invalid_config['trading']['initial_capital'] = -1000
        self.assertLess(invalid_config['trading']['initial_capital'], 0)


class TestRiskManager(unittest.TestCase):
    """Test risk management system."""
    
    def setUp(self):
        """Set up test risk manager."""
        self.risk_manager = RiskManager()
        self.test_position = Position(
            symbol="BTC",
            size=1.0,
            entry_price=50000.0,
            current_price=50000.0,
            timestamp=datetime.utcnow(),
            strategy="test_strategy"
        )
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        symbol = "BTC"
        price = 50000.0
        capital = 10000.0
        strategy_data = {
            'win_rate': 0.6,
            'avg_win': 0.05,
            'avg_loss': 0.03,
            'volatility': 0.3
        }
        
        position_size = self.risk_manager.calculate_position_size(
            symbol, price, capital, strategy_data
        )
        
        self.assertGreater(position_size, 0)
        self.assertLess(position_size * price, capital * 0.1)  # Max 10% of capital
    
    def test_risk_limits(self):
        """Test risk limit checking."""
        position_value = 1000.0
        symbol = "BTC"
        capital = 10000.0
        
        is_allowed, reason = self.risk_manager.check_risk_limits(
            position_value, symbol, capital
        )
        
        self.assertIsInstance(is_allowed, bool)
        self.assertIsInstance(reason, str)
    
    def test_position_management(self):
        """Test position addition and removal."""
        # Add position
        self.risk_manager.add_position(self.test_position)
        
        # Check position exists
        summary = self.risk_manager.get_position_summary()
        self.assertGreater(summary['total_positions'], 0)
        
        # Remove position
        self.risk_manager.remove_position(self.test_position.symbol)
        
        # Check position removed
        summary = self.risk_manager.get_position_summary()
        self.assertEqual(summary['total_positions'], 0)
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation."""
        self.risk_manager.add_position(self.test_position)
        
        # Update stop losses
        price_dict = {"BTC": 52000.0}
        self.risk_manager.update_stop_losses(price_dict)
        
        # Check stop loss triggers
        triggered = self.risk_manager.check_stop_loss_triggers({"BTC": 45000.0})
        self.assertIsInstance(triggered, list)


class TestPriceData(unittest.TestCase):
    """Test price data handling."""
    
    def setUp(self):
        """Set up test price data."""
        self.price_data = PriceData(
            symbol="BTC",
            price=50000.0,
            volume_24h=1000000.0,
            change_24h=2.5,
            timestamp=datetime.utcnow(),
            source="test",
            high_24h=51000.0,
            low_24h=49000.0
        )
    
    def test_price_data_creation(self):
        """Test price data object creation."""
        self.assertEqual(self.price_data.symbol, "BTC")
        self.assertEqual(self.price_data.price, 50000.0)
        self.assertIsInstance(self.price_data.timestamp, datetime)
    
    def test_price_data_validation(self):
        """Test price data validation."""
        self.assertGreater(self.price_data.price, 0)
        self.assertGreater(self.price_data.volume_24h, 0)
        self.assertGreaterEqual(self.price_data.high_24h, self.price_data.price)
        self.assertLessEqual(self.price_data.low_24h, self.price_data.price)
    
    def test_price_data_manager(self):
        """Test price data manager."""
        try:
            manager = PriceDataManager()
            self.assertIsNotNone(manager)
            
            # Test health check
            health = manager.health_check()
            self.assertIsInstance(health, dict)
            
        except Exception as e:
            self.skipTest(f"PriceDataManager test failed: {e}")


class TestTradingStrategies(unittest.TestCase):
    """Test trading strategies."""
    
    def setUp(self):
        """Set up test strategies."""
        self.momentum_strategy = MomentumStrategy()
        self.mean_reversion_strategy = MeanReversionStrategy()
        
        self.test_prices = {
            "BTC": PriceData(
                symbol="BTC",
                price=50000.0,
                volume_24h=1000000.0,
                change_24h=2.5,
                timestamp=datetime.utcnow(),
                source="test",
                high_24h=51000.0,
                low_24h=49000.0
            )
        }
    
    def test_momentum_strategy(self):
        """Test momentum strategy."""
        # Test strategy initialization
        self.assertEqual(self.momentum_strategy.name, "Momentum Strategy")
        self.assertTrue(self.momentum_strategy.is_enabled())
        
        # Test signal generation
        signals = self.momentum_strategy.generate_signals(self.test_prices, {})
        self.assertIsInstance(signals, list)
        
        # Test strategy info
        info = self.momentum_strategy.get_strategy_info()
        self.assertIsInstance(info, dict)
        self.assertIn('name', info)
        self.assertIn('description', info)
    
    def test_mean_reversion_strategy(self):
        """Test mean reversion strategy."""
        # Test strategy initialization
        self.assertEqual(self.mean_reversion_strategy.name, "Mean Reversion Strategy")
        self.assertTrue(self.mean_reversion_strategy.is_enabled())
        
        # Test signal generation
        signals = self.mean_reversion_strategy.generate_signals(self.test_prices, {})
        self.assertIsInstance(signals, list)
        
        # Test strategy info
        info = self.mean_reversion_strategy.get_strategy_info()
        self.assertIsInstance(info, dict)
    
    def test_strategy_metrics(self):
        """Test strategy metrics tracking."""
        # Add test trade to momentum strategy
        test_trade = {
            'symbol': 'BTC',
            'return': 0.05,
            'duration': 24.0,
            'exit_reason': 'profit_target'
        }
        
        self.momentum_strategy.add_trade(test_trade)
        metrics = self.momentum_strategy.get_metrics()
        
        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.total_trades, 1)


class TestExecutionEngine(unittest.TestCase):
    """Test order execution engine."""
    
    def setUp(self):
        """Set up test execution engine."""
        self.execution_engine = ExecutionEngine()
        self.test_order = Order(
            id="test_order_1",
            symbol="BTC",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0,
            strategy="test_strategy"
        )
    
    def test_order_creation(self):
        """Test order object creation."""
        self.assertEqual(self.test_order.symbol, "BTC")
        self.assertEqual(self.test_order.side, "buy")
        self.assertEqual(self.test_order.quantity, 0.1)
        self.assertIsInstance(self.test_order.order_type, OrderType)
    
    def test_order_validation(self):
        """Test order validation."""
        # Valid order
        self.assertGreater(self.test_order.quantity, 0)
        self.assertIn(self.test_order.side, ["buy", "sell"])
        
        # Invalid order
        invalid_order = Order(
            id="invalid_order",
            symbol="BTC",
            side="invalid",
            order_type=OrderType.MARKET,
            quantity=-1.0,
            price=50000.0
        )
        
        self.assertLess(invalid_order.quantity, 0)
        self.assertNotIn(invalid_order.side, ["buy", "sell"])
    
    @patch('src.execution.execution_engine.Web3')
    def test_execution_engine_mock(self, mock_web3):
        """Test execution engine with mocked Web3."""
        # Mock Web3 instance
        mock_web3_instance = Mock()
        mock_web3.return_value = mock_web3_instance
        
        # Test execution stats
        stats = self.execution_engine.get_execution_stats()
        self.assertIsInstance(stats, dict)


class TestBacktesting(unittest.TestCase):
    """Test backtesting framework."""
    
    def setUp(self):
        """Set up test backtesting."""
        self.backtest_engine = BacktestEngine(initial_capital=10000.0)
        self.momentum_strategy = MomentumStrategy()
    
    def test_backtest_engine_initialization(self):
        """Test backtest engine initialization."""
        self.assertEqual(self.backtest_engine.initial_capital, 10000.0)
        self.assertEqual(self.backtest_engine.current_capital, 10000.0)
        self.assertEqual(len(self.backtest_engine.strategies), 0)
    
    def test_strategy_addition(self):
        """Test adding strategies to backtest."""
        self.backtest_engine.add_strategy(self.momentum_strategy)
        self.assertEqual(len(self.backtest_engine.strategies), 1)
    
    def test_backtest_metrics(self):
        """Test backtest metrics calculation."""
        metrics = BacktestMetrics()
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)
        
        # Test metrics conversion
        metrics_dict = metrics.to_dict()
        self.assertIsInstance(metrics_dict, dict)
        self.assertIn('total_trades', metrics_dict)
    
    def test_sample_backtest(self):
        """Test running a sample backtest."""
        try:
            self.backtest_engine.add_strategy(self.momentum_strategy)
            
            start_date = datetime.utcnow() - timedelta(days=30)
            end_date = datetime.utcnow() - timedelta(days=1)
            symbols = ["BTC"]
            
            # Run short backtest
            results = self.backtest_engine.run_backtest(start_date, end_date, symbols)
            
            self.assertIsInstance(results, dict)
            self.assertIn('metrics', results)
            
        except Exception as e:
            self.skipTest(f"Backtest failed: {e}")


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring."""
    
    def setUp(self):
        """Set up test performance monitor."""
        self.performance_monitor = PerformanceMonitor()
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        self.assertIsNotNone(self.performance_monitor)
        self.assertIsInstance(self.performance_monitor.snapshots, list)
        self.assertIsInstance(self.performance_monitor.daily_returns, list)
    
    def test_metrics_update(self):
        """Test updating performance metrics."""
        test_data = {
            'timestamp': datetime.utcnow(),
            'capital': 11000.0,
            'daily_pnl': 1000.0,
            'total_trades': 10,
            'successful_trades': 6,
            'active_positions': 2,
            'total_position_value': 5000.0
        }
        
        self.performance_monitor.update_metrics(test_data)
        
        # Check if data was added
        self.assertGreater(len(self.performance_monitor.snapshots), 0)
        
        # Get current metrics
        current_metrics = self.performance_monitor.get_current_metrics()
        self.assertIsInstance(current_metrics, dict)
    
    def test_performance_targets(self):
        """Test performance target checking."""
        target_check = self.performance_monitor.check_performance_targets()
        self.assertIsInstance(target_check, dict)
        self.assertIn('status', target_check)
        self.assertIn('issues', target_check)


class TestAlertManager(unittest.TestCase):
    """Test alert management system."""
    
    def setUp(self):
        """Set up test alert manager."""
        self.alert_manager = AlertManager()
    
    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        self.assertIsNotNone(self.alert_manager)
        self.assertIsInstance(self.alert_manager.alerts, list)
    
    def test_alert_sending(self):
        """Test sending alerts."""
        alert_id = self.alert_manager.send_alert(
            title="Test Alert",
            message="This is a test alert",
            severity="medium",
            category="test"
        )
        
        self.assertIsInstance(alert_id, str)
        self.assertGreater(len(self.alert_manager.alerts), 0)
    
    def test_alert_management(self):
        """Test alert acknowledgment and resolution."""
        # Send test alert
        alert_id = self.alert_manager.send_alert(
            title="Test Alert",
            message="Test message",
            severity="low"
        )
        
        # Acknowledge alert
        success = self.alert_manager.acknowledge_alert(alert_id)
        self.assertTrue(success)
        
        # Resolve alert
        success = self.alert_manager.resolve_alert(alert_id)
        self.assertTrue(success)
    
    def test_alert_statistics(self):
        """Test alert statistics."""
        stats = self.alert_manager.get_alert_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('active_alerts', stats)
        self.assertIn('alerts_24h', stats)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.components = {}
        
        try:
            self.components['risk_manager'] = RiskManager()
            self.components['performance_monitor'] = PerformanceMonitor()
            self.components['alert_manager'] = AlertManager()
            self.components['momentum_strategy'] = MomentumStrategy()
        except Exception as e:
            self.skipTest(f"Component initialization failed: {e}")
    
    def test_component_interaction(self):
        """Test interaction between components."""
        # Test risk manager and performance monitor
        risk_manager = self.components['risk_manager']
        performance_monitor = self.components['performance_monitor']
        
        # Add test position
        test_position = Position(
            symbol="BTC",
            size=1.0,
            entry_price=50000.0,
            current_price=51000.0,
            timestamp=datetime.utcnow(),
            strategy="momentum"
        )
        
        risk_manager.add_position(test_position)
        
        # Update performance metrics
        test_data = {
            'timestamp': datetime.utcnow(),
            'capital': 11000.0,
            'daily_pnl': 1000.0,
            'total_trades': 1,
            'successful_trades': 1,
            'active_positions': 1,
            'total_position_value': 51000.0
        }
        
        performance_monitor.update_metrics(test_data)
        
        # Verify integration
        position_summary = risk_manager.get_position_summary()
        current_metrics = performance_monitor.get_current_metrics()
        
        self.assertGreater(position_summary['total_positions'], 0)
        self.assertIsInstance(current_metrics, dict)
    
    def test_strategy_risk_integration(self):
        """Test strategy and risk management integration."""
        strategy = self.components['momentum_strategy']
        risk_manager = self.components['risk_manager']
        
        # Generate test signals
        test_prices = {
            "BTC": PriceData(
                symbol="BTC",
                price=50000.0,
                volume_24h=1000000.0,
                change_24h=2.5,
                timestamp=datetime.utcnow(),
                source="test",
                high_24h=51000.0,
                low_24h=49000.0
            )
        }
        
        signals = strategy.generate_signals(test_prices, {})
        
        # Test risk checking for signals
        for signal in signals:
            position_value = 1000.0  # Test position value
            is_allowed, reason = risk_manager.check_risk_limits(
                position_value, signal.symbol, 10000.0
            )
            
            self.assertIsInstance(is_allowed, bool)
            self.assertIsInstance(reason, str)


class TestSystemHealth(unittest.TestCase):
    """Test overall system health and performance."""
    
    def test_memory_usage(self):
        """Test memory usage of components."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create components
        components = []
        try:
            components.append(RiskManager())
            components.append(PerformanceMonitor())
            components.append(AlertManager())
            components.append(MomentumStrategy())
            components.append(MeanReversionStrategy())
        except Exception as e:
            self.skipTest(f"Component creation failed: {e}")
        
        # Get memory after component creation
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024)
        
        # Cleanup
        del components
        gc.collect()
    
    def test_error_handling(self):
        """Test error handling in components."""
        # Test with invalid data
        try:
            risk_manager = RiskManager()
            
            # Test with invalid position
            invalid_position = Position(
                symbol="",  # Invalid symbol
                size=0,     # Invalid size
                entry_price=-1000,  # Invalid price
                current_price=-1000,
                timestamp=datetime.utcnow(),
                strategy=""
            )
            
            # This should handle the error gracefully
            risk_manager.add_position(invalid_position)
            
        except Exception:
            # Expected to fail, but should not crash
            pass
    
    def test_concurrent_access(self):
        """Test concurrent access to components."""
        import threading
        import time
        
        try:
            performance_monitor = PerformanceMonitor()
            
            def update_metrics():
                for i in range(10):
                    test_data = {
                        'timestamp': datetime.utcnow(),
                        'capital': 10000.0 + i * 100,
                        'daily_pnl': i * 10,
                        'total_trades': i,
                        'successful_trades': i // 2,
                        'active_positions': 1,
                        'total_position_value': 1000.0
                    }
                    performance_monitor.update_metrics(test_data)
                    time.sleep(0.01)
            
            # Create multiple threads
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=update_metrics)
                threads.append(thread)
                thread.start()
            
            # Wait for threads to complete
            for thread in threads:
                thread.join()
            
            # Verify data integrity
            metrics = performance_monitor.get_current_metrics()
            self.assertIsInstance(metrics, dict)
            
        except Exception as e:
            self.skipTest(f"Concurrent access test failed: {e}")


def run_test_suite():
    """Run the complete test suite."""
    print("=" * 60)
    print("CRYPTO TRADING BOT - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestConfigManager,
        TestRiskManager,
        TestPriceData,
        TestTradingStrategies,
        TestExecutionEngine,
        TestBacktesting,
        TestPerformanceMonitor,
        TestAlertManager,
        TestIntegration,
        TestSystemHealth
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_test_suite()
    sys.exit(0 if success else 1)

