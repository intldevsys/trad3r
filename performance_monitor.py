"""
Performance Monitoring System for Crypto Trading Bot
Tracks and analyzes trading performance metrics in real-time.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

from ..utils.config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    timestamp: datetime
    capital: float
    daily_pnl: float
    total_trades: int
    successful_trades: int
    active_positions: int
    total_position_value: float
    drawdown_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class PerformanceMetrics:
    """Calculates various performance metrics."""
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = np.array(returns) - risk_free_rate / 252  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = np.array(returns) - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, float]:
        """Calculate maximum drawdown in absolute and percentage terms."""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0, 0.0
        
        peak = np.maximum.accumulate(equity_curve)
        drawdown = peak - equity_curve
        max_drawdown_abs = np.max(drawdown)
        max_drawdown_pct = np.max(drawdown / peak) * 100
        
        return max_drawdown_abs, max_drawdown_pct
    
    @staticmethod
    def calculate_calmar_ratio(annual_return: float, max_drawdown_pct: float) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown_pct == 0:
            return 0.0
        return annual_return / max_drawdown_pct
    
    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate from trade history."""
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
        return winning_trades / len(trades) * 100
    
    @staticmethod
    def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
        """Calculate profit factor."""
        if not trades:
            return 0.0
        
        gross_profit = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) > 0)
        gross_loss = abs(sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss


class PerformanceMonitor:
    """Main performance monitoring system."""
    
    def __init__(self):
        self.config = get_config()
        
        # Performance data storage
        self.snapshots: List[PerformanceSnapshot] = []
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = []
        self.trade_history: List[Dict[str, Any]] = []
        
        # Performance targets from config
        self.targets = self.config.monitoring.performance_targets
        
        # Metrics calculator
        self.metrics = PerformanceMetrics()
        
        # Storage paths
        self.data_dir = Path("/home/ubuntu/crypto_trading_bot/data/performance")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        self._load_historical_data()
        
        logger.info("Performance Monitor initialized")
    
    def update_metrics(self, data: Dict[str, Any]) -> None:
        """Update performance metrics with new data."""
        try:
            snapshot = PerformanceSnapshot(
                timestamp=data.get('timestamp', datetime.utcnow()),
                capital=data.get('capital', 0.0),
                daily_pnl=data.get('daily_pnl', 0.0),
                total_trades=data.get('total_trades', 0),
                successful_trades=data.get('successful_trades', 0),
                active_positions=data.get('active_positions', 0),
                total_position_value=data.get('total_position_value', 0.0),
                drawdown_pct=self._calculate_current_drawdown(data.get('capital', 0.0))
            )
            
            self.snapshots.append(snapshot)
            self.equity_curve.append(snapshot.capital)
            
            # Calculate daily return
            if len(self.equity_curve) > 1:
                daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
                self.daily_returns.append(daily_return)
            
            # Keep only recent data (last 365 days)
            self._trim_historical_data()
            
            # Save data periodically
            if len(self.snapshots) % 100 == 0:
                self._save_data()
            
            logger.debug(f"Performance metrics updated: Capital=${snapshot.capital:.2f}, "
                        f"Daily P&L=${snapshot.daily_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    def add_trade(self, trade_data: Dict[str, Any]) -> None:
        """Add a completed trade to history."""
        trade_data['timestamp'] = trade_data.get('timestamp', datetime.utcnow())
        self.trade_history.append(trade_data)
        
        # Keep only recent trades
        if len(self.trade_history) > 10000:
            self.trade_history = self.trade_history[-10000:]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        if not self.snapshots:
            return {}
        
        latest_snapshot = self.snapshots[-1]
        
        # Calculate returns
        if len(self.equity_curve) > 1:
            total_return = (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0] * 100
            
            if len(self.daily_returns) > 0:
                daily_return = self.daily_returns[-1] * 100
                
                # Calculate annualized return
                if len(self.daily_returns) >= 30:
                    avg_daily_return = np.mean(self.daily_returns[-30:])
                    annualized_return = ((1 + avg_daily_return) ** 252 - 1) * 100
                else:
                    annualized_return = 0.0
            else:
                daily_return = 0.0
                annualized_return = 0.0
        else:
            total_return = 0.0
            daily_return = 0.0
            annualized_return = 0.0
        
        # Calculate risk metrics
        max_drawdown_abs, max_drawdown_pct = self.metrics.calculate_max_drawdown(self.equity_curve)
        sharpe_ratio = self.metrics.calculate_sharpe_ratio(self.daily_returns)
        sortino_ratio = self.metrics.calculate_sortino_ratio(self.daily_returns)
        calmar_ratio = self.metrics.calculate_calmar_ratio(annualized_return, max_drawdown_pct)
        
        # Calculate trade metrics
        win_rate = self.metrics.calculate_win_rate(self.trade_history)
        profit_factor = self.metrics.calculate_profit_factor(self.trade_history)
        
        # Success rate
        success_rate = (latest_snapshot.successful_trades / latest_snapshot.total_trades * 100) if latest_snapshot.total_trades > 0 else 0
        
        return {
            'timestamp': latest_snapshot.timestamp.isoformat(),
            'capital': latest_snapshot.capital,
            'daily_pnl': latest_snapshot.daily_pnl,
            'total_return_pct': total_return,
            'daily_return_pct': daily_return,
            'annualized_return_pct': annualized_return,
            'max_drawdown_abs': max_drawdown_abs,
            'max_drawdown_pct': max_drawdown_pct,
            'current_drawdown_pct': latest_snapshot.drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'total_trades': latest_snapshot.total_trades,
            'successful_trades': latest_snapshot.successful_trades,
            'success_rate': success_rate,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'active_positions': latest_snapshot.active_positions,
            'total_position_value': latest_snapshot.total_position_value
        }
    
    def check_performance_targets(self) -> Dict[str, Any]:
        """Check if performance targets are being met."""
        current_metrics = self.get_current_metrics()
        
        if not current_metrics:
            return {'status': 'no_data', 'issues': []}
        
        issues = []
        
        # Check monthly return target
        target_monthly_return = self.targets.get('monthly_return_pct', 20.0)
        if len(self.daily_returns) >= 30:
            monthly_return = np.mean(self.daily_returns[-30:]) * 30 * 100
            if monthly_return < target_monthly_return:
                issues.append(f"Monthly return below target: {monthly_return:.2f}% < {target_monthly_return}%")
        
        # Check max drawdown target
        target_max_drawdown = self.targets.get('max_drawdown_pct', 15.0)
        if current_metrics['max_drawdown_pct'] > target_max_drawdown:
            issues.append(f"Max drawdown exceeded: {current_metrics['max_drawdown_pct']:.2f}% > {target_max_drawdown}%")
        
        # Check Sharpe ratio target
        target_sharpe = self.targets.get('sharpe_ratio', 1.5)
        if current_metrics['sharpe_ratio'] < target_sharpe:
            issues.append(f"Sharpe ratio below target: {current_metrics['sharpe_ratio']:.2f} < {target_sharpe}")
        
        # Check win rate target
        target_win_rate = self.targets.get('win_rate_pct', 60.0)
        if current_metrics['win_rate'] < target_win_rate:
            issues.append(f"Win rate below target: {current_metrics['win_rate']:.2f}% < {target_win_rate}%")
        
        return {
            'status': 'meeting_targets' if not issues else 'below_targets',
            'issues': issues,
            'targets': self.targets,
            'current': current_metrics
        }
    
    def generate_daily_report(self) -> str:
        """Generate daily performance report."""
        try:
            current_metrics = self.get_current_metrics()
            
            if not current_metrics:
                return "No performance data available"
            
            report_date = datetime.now().strftime("%Y-%m-%d")
            report_path = self.data_dir / f"daily_report_{report_date}.txt"
            
            with open(report_path, 'w') as f:
                f.write(f"DAILY PERFORMANCE REPORT - {report_date}\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("PERFORMANCE SUMMARY\n")
                f.write("-" * 20 + "\n")
                f.write(f"Current Capital: ${current_metrics['capital']:,.2f}\n")
                f.write(f"Daily P&L: ${current_metrics['daily_pnl']:,.2f}\n")
                f.write(f"Daily Return: {current_metrics['daily_return_pct']:.2f}%\n")
                f.write(f"Total Return: {current_metrics['total_return_pct']:.2f}%\n")
                f.write(f"Current Drawdown: {current_metrics['current_drawdown_pct']:.2f}%\n\n")
                
                f.write("RISK METRICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Max Drawdown: {current_metrics['max_drawdown_pct']:.2f}%\n")
                f.write(f"Sharpe Ratio: {current_metrics['sharpe_ratio']:.2f}\n")
                f.write(f"Sortino Ratio: {current_metrics['sortino_ratio']:.2f}\n\n")
                
                f.write("TRADING ACTIVITY\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total Trades: {current_metrics['total_trades']}\n")
                f.write(f"Success Rate: {current_metrics['success_rate']:.2f}%\n")
                f.write(f"Win Rate: {current_metrics['win_rate']:.2f}%\n")
                f.write(f"Active Positions: {current_metrics['active_positions']}\n")
                f.write(f"Position Value: ${current_metrics['total_position_value']:,.2f}\n\n")
                
                # Performance targets check
                target_check = self.check_performance_targets()
                f.write("PERFORMANCE TARGETS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Status: {target_check['status'].upper()}\n")
                
                if target_check['issues']:
                    f.write("Issues:\n")
                    for issue in target_check['issues']:
                        f.write(f"  - {issue}\n")
                else:
                    f.write("All targets are being met.\n")
            
            logger.info(f"Daily report generated: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return ""
    
    def generate_weekly_report(self) -> str:
        """Generate weekly performance report with charts."""
        try:
            current_metrics = self.get_current_metrics()
            
            if not current_metrics:
                return "No performance data available"
            
            report_date = datetime.now().strftime("%Y-%m-%d")
            report_dir = self.data_dir / f"weekly_report_{report_date}"
            report_dir.mkdir(exist_ok=True)
            
            # Generate charts
            self._generate_performance_charts(str(report_dir))
            
            # Generate text report
            report_path = report_dir / "weekly_report.txt"
            
            with open(report_path, 'w') as f:
                f.write(f"WEEKLY PERFORMANCE REPORT - {report_date}\n")
                f.write("=" * 50 + "\n\n")
                
                # Weekly statistics
                if len(self.daily_returns) >= 7:
                    weekly_returns = self.daily_returns[-7:]
                    weekly_return = sum(weekly_returns) * 100
                    weekly_volatility = np.std(weekly_returns) * np.sqrt(7) * 100
                    
                    f.write("WEEKLY PERFORMANCE\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Weekly Return: {weekly_return:.2f}%\n")
                    f.write(f"Weekly Volatility: {weekly_volatility:.2f}%\n")
                    f.write(f"Best Day: {max(weekly_returns) * 100:.2f}%\n")
                    f.write(f"Worst Day: {min(weekly_returns) * 100:.2f}%\n\n")
                
                # Include current metrics
                f.write("OVERALL PERFORMANCE\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total Return: {current_metrics['total_return_pct']:.2f}%\n")
                f.write(f"Annualized Return: {current_metrics['annualized_return_pct']:.2f}%\n")
                f.write(f"Max Drawdown: {current_metrics['max_drawdown_pct']:.2f}%\n")
                f.write(f"Sharpe Ratio: {current_metrics['sharpe_ratio']:.2f}\n")
                f.write(f"Profit Factor: {current_metrics['profit_factor']:.2f}\n\n")
                
                # Trade analysis
                if self.trade_history:
                    recent_trades = [t for t in self.trade_history 
                                   if (datetime.utcnow() - t.get('timestamp', datetime.utcnow())).days <= 7]
                    
                    if recent_trades:
                        f.write("WEEKLY TRADING ACTIVITY\n")
                        f.write("-" * 20 + "\n")
                        f.write(f"Trades This Week: {len(recent_trades)}\n")
                        
                        weekly_pnl = sum(t.get('pnl', 0) for t in recent_trades)
                        f.write(f"Weekly P&L: ${weekly_pnl:.2f}\n")
                        
                        winning_trades = [t for t in recent_trades if t.get('pnl', 0) > 0]
                        weekly_win_rate = len(winning_trades) / len(recent_trades) * 100 if recent_trades else 0
                        f.write(f"Weekly Win Rate: {weekly_win_rate:.2f}%\n\n")
            
            logger.info(f"Weekly report generated: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return ""
    
    def _generate_performance_charts(self, output_dir: str) -> None:
        """Generate performance visualization charts."""
        try:
            if not self.equity_curve or not self.daily_returns:
                return
            
            # Set style
            plt.style.use('seaborn-v0_8')
            
            # 1. Equity Curve
            plt.figure(figsize=(12, 6))
            plt.plot(self.equity_curve, linewidth=2)
            plt.title('Equity Curve', fontsize=16, fontweight='bold')
            plt.xlabel('Time')
            plt.ylabel('Capital ($)')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(Path(output_dir) / 'equity_curve.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 2. Daily Returns
            plt.figure(figsize=(12, 6))
            returns_pct = [r * 100 for r in self.daily_returns]
            plt.plot(returns_pct, alpha=0.7)
            plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)
            plt.title('Daily Returns', fontsize=16, fontweight='bold')
            plt.xlabel('Time')
            plt.ylabel('Daily Return (%)')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(Path(output_dir) / 'daily_returns.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 3. Returns Distribution
            plt.figure(figsize=(10, 6))
            plt.hist(returns_pct, bins=30, alpha=0.7, edgecolor='black')
            plt.axvline(x=np.mean(returns_pct), color='red', linestyle='--', 
                       label=f'Mean: {np.mean(returns_pct):.2f}%')
            plt.title('Daily Returns Distribution', fontsize=16, fontweight='bold')
            plt.xlabel('Daily Return (%)')
            plt.ylabel('Frequency')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(Path(output_dir) / 'returns_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 4. Drawdown Chart
            if len(self.equity_curve) > 1:
                peak = np.maximum.accumulate(self.equity_curve)
                drawdown = (peak - self.equity_curve) / peak * 100
                
                plt.figure(figsize=(12, 6))
                plt.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color='red')
                plt.plot(drawdown, color='red', linewidth=2)
                plt.title('Drawdown', fontsize=16, fontweight='bold')
                plt.xlabel('Time')
                plt.ylabel('Drawdown (%)')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(Path(output_dir) / 'drawdown.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            logger.info(f"Performance charts generated in {output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating performance charts: {e}")
    
    def _calculate_current_drawdown(self, current_capital: float) -> float:
        """Calculate current drawdown percentage."""
        if not self.equity_curve:
            return 0.0
        
        peak = max(self.equity_curve + [current_capital])
        drawdown = (peak - current_capital) / peak * 100
        
        return max(0.0, drawdown)
    
    def _trim_historical_data(self) -> None:
        """Keep only recent historical data."""
        max_days = 365
        
        if len(self.snapshots) > max_days * 24:  # Assuming hourly snapshots
            self.snapshots = self.snapshots[-max_days * 24:]
        
        if len(self.equity_curve) > max_days:
            self.equity_curve = self.equity_curve[-max_days:]
        
        if len(self.daily_returns) > max_days:
            self.daily_returns = self.daily_returns[-max_days:]
    
    def _save_data(self) -> None:
        """Save performance data to disk."""
        try:
            # Save snapshots
            snapshots_data = [snapshot.to_dict() for snapshot in self.snapshots]
            with open(self.data_dir / 'snapshots.json', 'w') as f:
                json.dump(snapshots_data, f, indent=2)
            
            # Save other data
            data = {
                'daily_returns': self.daily_returns,
                'equity_curve': self.equity_curve,
                'trade_history': self.trade_history
            }
            
            with open(self.data_dir / 'performance_data.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")
    
    def _load_historical_data(self) -> None:
        """Load historical performance data."""
        try:
            # Load snapshots
            snapshots_file = self.data_dir / 'snapshots.json'
            if snapshots_file.exists():
                with open(snapshots_file, 'r') as f:
                    snapshots_data = json.load(f)
                
                for data in snapshots_data:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    self.snapshots.append(PerformanceSnapshot(**data))
            
            # Load other data
            data_file = self.data_dir / 'performance_data.json'
            if data_file.exists():
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                self.daily_returns = data.get('daily_returns', [])
                self.equity_curve = data.get('equity_curve', [])
                self.trade_history = data.get('trade_history', [])
            
            logger.info(f"Loaded {len(self.snapshots)} performance snapshots")
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    def export_data(self, format: str = 'csv') -> str:
        """Export performance data to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == 'csv':
                # Export to CSV
                df_data = []
                for snapshot in self.snapshots:
                    df_data.append(snapshot.to_dict())
                
                df = pd.DataFrame(df_data)
                export_path = self.data_dir / f'performance_export_{timestamp}.csv'
                df.to_csv(export_path, index=False)
                
            else:  # JSON
                export_data = {
                    'snapshots': [s.to_dict() for s in self.snapshots],
                    'daily_returns': self.daily_returns,
                    'equity_curve': self.equity_curve,
                    'trade_history': self.trade_history,
                    'export_timestamp': datetime.now().isoformat()
                }
                
                export_path = self.data_dir / f'performance_export_{timestamp}.json'
                with open(export_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Performance data exported: {export_path}")
            return str(export_path)
            
        except Exception as e:
            logger.error(f"Error exporting performance data: {e}")
            return ""

