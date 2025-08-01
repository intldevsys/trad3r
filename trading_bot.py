"""
Trading Bot API Routes
Provides REST API endpoints for monitoring and controlling the trading bot.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
import json

# Import trading bot components
try:
    from src.main_bot import TradingBot
    from src.monitoring.performance_monitor import PerformanceMonitor
    from src.monitoring.alert_manager import AlertManager
    from src.backtesting.backtester import BacktestEngine
    from src.strategies.momentum_strategy import MomentumStrategy
    from src.strategies.mean_reversion_strategy import MeanReversionStrategy
    from src.utils.config_manager import get_config
except ImportError as e:
    print(f"Warning: Could not import trading bot components: {e}")
    # Create mock classes for development
    class TradingBot:
        def __init__(self): pass
        def get_status(self): return {}
        def enable_trading(self): pass
        def disable_trading(self): pass
    
    class PerformanceMonitor:
        def __init__(self): pass
        def get_current_metrics(self): return {}
    
    class AlertManager:
        def __init__(self): pass
        def get_active_alerts(self): return []
        def get_alert_statistics(self): return {}

logger = logging.getLogger(__name__)

# Create blueprint
trading_bot_bp = Blueprint('trading_bot', __name__)

# Global instances (in production, these would be properly managed)
bot_instance = None
performance_monitor = None
alert_manager = None

def get_bot_instance():
    """Get or create bot instance."""
    global bot_instance
    if bot_instance is None:
        try:
            bot_instance = TradingBot()
        except Exception as e:
            logger.error(f"Error creating bot instance: {e}")
            bot_instance = TradingBot()  # Mock instance
    return bot_instance

def get_performance_monitor():
    """Get or create performance monitor instance."""
    global performance_monitor
    if performance_monitor is None:
        try:
            performance_monitor = PerformanceMonitor()
        except Exception as e:
            logger.error(f"Error creating performance monitor: {e}")
            performance_monitor = PerformanceMonitor()  # Mock instance
    return performance_monitor

def get_alert_manager():
    """Get or create alert manager instance."""
    global alert_manager
    if alert_manager is None:
        try:
            alert_manager = AlertManager()
        except Exception as e:
            logger.error(f"Error creating alert manager: {e}")
            alert_manager = AlertManager()  # Mock instance
    return alert_manager

@trading_bot_bp.route('/status', methods=['GET'])
def get_bot_status():
    """Get current bot status."""
    try:
        bot = get_bot_instance()
        status = bot.get_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/start', methods=['POST'])
def start_bot():
    """Start the trading bot."""
    try:
        bot = get_bot_instance()
        bot.start()
        
        return jsonify({
            'success': True,
            'message': 'Trading bot started successfully'
        })
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot."""
    try:
        bot = get_bot_instance()
        bot.stop()
        
        return jsonify({
            'success': True,
            'message': 'Trading bot stopped successfully'
        })
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/trading/enable', methods=['POST'])
def enable_trading():
    """Enable trading."""
    try:
        bot = get_bot_instance()
        bot.enable_trading()
        
        return jsonify({
            'success': True,
            'message': 'Trading enabled'
        })
    except Exception as e:
        logger.error(f"Error enabling trading: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/trading/disable', methods=['POST'])
def disable_trading():
    """Disable trading."""
    try:
        bot = get_bot_instance()
        bot.disable_trading()
        
        return jsonify({
            'success': True,
            'message': 'Trading disabled'
        })
    except Exception as e:
        logger.error(f"Error disabling trading: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/performance', methods=['GET'])
def get_performance_metrics():
    """Get current performance metrics."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        return jsonify({
            'success': True,
            'data': metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/performance/targets', methods=['GET'])
def check_performance_targets():
    """Check if performance targets are being met."""
    try:
        monitor = get_performance_monitor()
        target_check = monitor.check_performance_targets()
        
        return jsonify({
            'success': True,
            'data': target_check,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking performance targets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts."""
    try:
        alert_mgr = get_alert_manager()
        severity = request.args.get('severity')
        alerts = alert_mgr.get_active_alerts(severity)
        
        alert_data = [alert.to_dict() for alert in alerts]
        
        return jsonify({
            'success': True,
            'data': alert_data,
            'count': len(alert_data),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """Get alert statistics."""
    try:
        alert_mgr = get_alert_manager()
        stats = alert_mgr.get_alert_statistics()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/alerts/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    try:
        alert_mgr = get_alert_manager()
        success = alert_mgr.acknowledge_alert(alert_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Alert {alert_id} acknowledged'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve an alert."""
    try:
        alert_mgr = get_alert_manager()
        success = alert_mgr.resolve_alert(alert_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Alert {alert_id} resolved'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """Run a backtest."""
    try:
        data = request.get_json()
        
        # Parse parameters
        start_date = datetime.fromisoformat(data.get('start_date', '2023-01-01'))
        end_date = datetime.fromisoformat(data.get('end_date', '2024-01-01'))
        initial_capital = data.get('initial_capital', 10000.0)
        symbols = data.get('symbols', ['BTC', 'ETH', 'USDC'])
        strategies = data.get('strategies', ['momentum', 'mean_reversion'])
        
        # Create backtest engine
        backtest_engine = BacktestEngine(initial_capital)
        
        # Add strategies
        if 'momentum' in strategies:
            backtest_engine.add_strategy(MomentumStrategy())
        if 'mean_reversion' in strategies:
            backtest_engine.add_strategy(MeanReversionStrategy())
        
        # Run backtest
        results = backtest_engine.run_backtest(start_date, end_date, symbols)
        
        # Generate report
        report_path = backtest_engine.generate_report(results)
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'report_path': report_path
            },
            'message': 'Backtest completed successfully'
        })
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """Get information about available strategies."""
    try:
        strategies = []
        
        # Momentum strategy info
        momentum_strategy = MomentumStrategy()
        strategies.append(momentum_strategy.get_strategy_info())
        
        # Mean reversion strategy info
        mean_reversion_strategy = MeanReversionStrategy()
        strategies.append(mean_reversion_strategy.get_strategy_info())
        
        return jsonify({
            'success': True,
            'data': strategies,
            'count': len(strategies)
        })
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    try:
        config = get_config()
        
        # Convert config to dict (simplified)
        config_dict = {
            'trading': {
                'initial_capital': config.trading.initial_capital,
                'max_position_size_pct': config.trading.max_position_size_pct,
                'max_daily_loss_pct': config.trading.max_daily_loss_pct,
                'max_weekly_loss_pct': config.trading.max_weekly_loss_pct,
                'max_drawdown_pct': config.trading.max_drawdown_pct
            },
            'risk_management': {
                'kelly_fraction': config.risk_management.kelly_fraction,
                'volatility_lookback': config.risk_management.volatility_lookback,
                'correlation_threshold': config.risk_management.correlation_threshold
            },
            'execution': {
                'gas_strategy': config.execution.gas_strategy,
                'max_gas_price_gwei': config.execution.max_gas_price_gwei,
                'slippage_tolerance_pct': config.execution.slippage_tolerance_pct
            }
        }
        
        return jsonify({
            'success': True,
            'data': config_dict
        })
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        bot = get_bot_instance()
        
        # Perform basic health checks
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'bot': 'healthy',
                'performance_monitor': 'healthy',
                'alert_manager': 'healthy'
            }
        }
        
        # Check bot status
        try:
            bot_status = bot.get_status()
            if not bot_status:
                health_status['components']['bot'] = 'degraded'
                health_status['status'] = 'degraded'
        except Exception:
            health_status['components']['bot'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
        
        return jsonify({
            'success': True,
            'data': health_status
        })
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'unhealthy'
        }), 500

@trading_bot_bp.route('/logs', methods=['GET'])
def get_logs():
    """Get recent log entries."""
    try:
        lines = int(request.args.get('lines', 100))
        level = request.args.get('level', 'INFO')
        
        log_file = '/home/ubuntu/crypto_trading_bot/logs/trading_bot.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Log file not found'
            })
        
        # Read last N lines from log file
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        # Filter by level if specified
        if level != 'ALL':
            log_lines = [line for line in log_lines if level in line]
        
        # Get last N lines
        recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return jsonify({
            'success': True,
            'data': recent_logs,
            'count': len(recent_logs)
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bot_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get comprehensive dashboard data."""
    try:
        bot = get_bot_instance()
        monitor = get_performance_monitor()
        alert_mgr = get_alert_manager()
        
        # Get all dashboard data
        dashboard_data = {
            'bot_status': bot.get_status(),
            'performance': monitor.get_current_metrics(),
            'alerts': {
                'active': [alert.to_dict() for alert in alert_mgr.get_active_alerts()],
                'statistics': alert_mgr.get_alert_statistics()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@trading_bot_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@trading_bot_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

