"""
Alert Management System for Crypto Trading Bot
Handles notifications and alerts for various system events.
"""

import logging
import smtplib
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from pathlib import Path

from ..utils.config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents an alert/notification."""
    id: str
    title: str
    message: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    category: str = "general"
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'category': self.category,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }


class EmailNotifier:
    """Email notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.recipients = config.get('recipients', [])
        
        if not self.username or not self.password or not self.recipients:
            self.enabled = False
            logger.warning("Email notifications disabled: missing configuration")
    
    def send_notification(self, alert: Alert) -> bool:
        """Send email notification."""
        if not self.enabled:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.title}"
            
            # Email body
            body = f"""
Trading Bot Alert

Title: {alert.title}
Severity: {alert.severity.upper()}
Category: {alert.category}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{alert.message}

---
This is an automated message from the Crypto Trading Bot.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.username, self.recipients, text)
            server.quit()
            
            logger.info(f"Email notification sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class TelegramNotifier:
    """Telegram notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')
        
        if not self.bot_token or not self.chat_id:
            self.enabled = False
            logger.warning("Telegram notifications disabled: missing configuration")
    
    def send_notification(self, alert: Alert) -> bool:
        """Send Telegram notification."""
        if not self.enabled:
            return False
        
        try:
            # Format message
            severity_emoji = {
                'low': '🔵',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }
            
            emoji = severity_emoji.get(alert.severity, '⚪')
            
            message = f"""
{emoji} *{alert.title}*

*Severity:* {alert.severity.upper()}
*Category:* {alert.category}
*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

{alert.message}
            """
            
            # Send message
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram notification sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False


class WebhookNotifier:
    """Webhook notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.webhook_url = config.get('webhook_url', '')
        self.headers = config.get('headers', {})
        
        if not self.webhook_url:
            self.enabled = False
            logger.warning("Webhook notifications disabled: missing URL")
    
    def send_notification(self, alert: Alert) -> bool:
        """Send webhook notification."""
        if not self.enabled:
            return False
        
        try:
            payload = {
                'alert': alert.to_dict(),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'crypto_trading_bot'
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class AlertManager:
    """Main alert management system."""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize notifiers
        alert_config = self.config.monitoring.alerts
        
        self.notifiers = []
        
        # Email notifier
        if hasattr(alert_config, 'email'):
            email_config = alert_config.email.__dict__ if hasattr(alert_config.email, '__dict__') else {}
            self.notifiers.append(EmailNotifier(email_config))
        
        # Telegram notifier
        if hasattr(alert_config, 'telegram'):
            telegram_config = alert_config.telegram.__dict__ if hasattr(alert_config.telegram, '__dict__') else {}
            self.notifiers.append(TelegramNotifier(telegram_config))
        
        # Webhook notifier
        if hasattr(alert_config, 'webhook'):
            webhook_config = alert_config.webhook.__dict__ if hasattr(alert_config.webhook, '__dict__') else {}
            self.notifiers.append(WebhookNotifier(webhook_config))
        
        # Alert storage
        self.alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        
        # Alert rules and thresholds
        self.alert_rules = self._load_alert_rules()
        
        # Rate limiting
        self.last_alert_times: Dict[str, datetime] = {}
        self.rate_limit_minutes = 5  # Minimum time between similar alerts
        
        # Storage
        self.data_dir = Path("/home/ubuntu/crypto_trading_bot/data/alerts")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load historical alerts
        self._load_alert_history()
        
        logger.info(f"Alert Manager initialized with {len(self.notifiers)} notifiers")
    
    def send_alert(self, title: str, message: str, severity: str = "medium", 
                  category: str = "general") -> str:
        """Send an alert through all configured channels."""
        
        # Generate alert ID
        alert_id = f"alert_{int(datetime.utcnow().timestamp())}"
        
        # Create alert
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity.lower(),
            timestamp=datetime.utcnow(),
            category=category
        )
        
        # Check rate limiting
        if self._is_rate_limited(alert):
            logger.debug(f"Alert rate limited: {title}")
            return alert_id
        
        # Add to active alerts
        self.alerts.append(alert)
        
        # Send through all notifiers
        success_count = 0
        for notifier in self.notifiers:
            try:
                if notifier.send_notification(alert):
                    success_count += 1
            except Exception as e:
                logger.error(f"Notifier failed: {e}")
        
        # Log alert
        logger.info(f"Alert sent: {title} (severity: {severity}, "
                   f"sent to {success_count}/{len(self.notifiers)} channels)")
        
        # Update rate limiting
        self.last_alert_times[self._get_alert_key(alert)] = alert.timestamp
        
        # Save to history
        self._save_alert_to_history(alert)
        
        return alert_id
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert.title}")
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for i, alert in enumerate(self.alerts):
            if alert.id == alert_id:
                alert.resolved = True
                # Move to history
                self.alert_history.append(alert)
                del self.alerts[i]
                logger.info(f"Alert resolved: {alert.title}")
                return True
        
        return False
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        if severity:
            return [alert for alert in self.alerts if alert.severity == severity.lower()]
        return self.alerts.copy()
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        now = datetime.utcnow()
        
        # Last 24 hours
        last_24h = [alert for alert in self.alert_history 
                   if (now - alert.timestamp).total_seconds() < 86400]
        
        # Last 7 days
        last_7d = [alert for alert in self.alert_history 
                  if (now - alert.timestamp).total_seconds() < 604800]
        
        # Count by severity
        severity_counts = {}
        for severity in ['low', 'medium', 'high', 'critical']:
            severity_counts[severity] = len([a for a in last_24h if a.severity == severity])
        
        # Count by category
        category_counts = {}
        for alert in last_24h:
            category_counts[alert.category] = category_counts.get(alert.category, 0) + 1
        
        return {
            'active_alerts': len(self.alerts),
            'alerts_24h': len(last_24h),
            'alerts_7d': len(last_7d),
            'severity_breakdown_24h': severity_counts,
            'category_breakdown_24h': category_counts,
            'total_historical_alerts': len(self.alert_history)
        }
    
    def check_system_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check system metrics and generate alerts if needed."""
        try:
            # Check performance metrics
            if 'daily_return_pct' in metrics:
                daily_return = metrics['daily_return_pct']
                
                if daily_return < -5:  # Daily loss > 5%
                    self.send_alert(
                        "High Daily Loss",
                        f"Daily return is {daily_return:.2f}%, exceeding -5% threshold",
                        "high",
                        "performance"
                    )
                elif daily_return < -10:  # Daily loss > 10%
                    self.send_alert(
                        "Critical Daily Loss",
                        f"Daily return is {daily_return:.2f}%, exceeding -10% threshold",
                        "critical",
                        "performance"
                    )
            
            # Check drawdown
            if 'current_drawdown_pct' in metrics:
                drawdown = metrics['current_drawdown_pct']
                
                if drawdown > 10:  # Drawdown > 10%
                    self.send_alert(
                        "High Drawdown",
                        f"Current drawdown is {drawdown:.2f}%, exceeding 10% threshold",
                        "high",
                        "risk"
                    )
                elif drawdown > 15:  # Drawdown > 15%
                    self.send_alert(
                        "Critical Drawdown",
                        f"Current drawdown is {drawdown:.2f}%, exceeding 15% threshold",
                        "critical",
                        "risk"
                    )
            
            # Check capital levels
            if 'capital' in metrics:
                capital = metrics['capital']
                initial_capital = self.config.trading.initial_capital
                
                capital_ratio = capital / initial_capital
                
                if capital_ratio < 0.8:  # Capital below 80%
                    self.send_alert(
                        "Low Capital Level",
                        f"Capital is ${capital:,.2f}, below 80% of initial capital",
                        "medium",
                        "capital"
                    )
                elif capital_ratio < 0.7:  # Capital below 70%
                    self.send_alert(
                        "Critical Capital Level",
                        f"Capital is ${capital:,.2f}, below 70% of initial capital",
                        "critical",
                        "capital"
                    )
            
            # Check success rate
            if 'success_rate' in metrics:
                success_rate = metrics['success_rate']
                
                if success_rate < 50:  # Success rate < 50%
                    self.send_alert(
                        "Low Success Rate",
                        f"Trading success rate is {success_rate:.1f}%, below 50% threshold",
                        "medium",
                        "performance"
                    )
        
        except Exception as e:
            logger.error(f"Error checking system alerts: {e}")
    
    def _is_rate_limited(self, alert: Alert) -> bool:
        """Check if alert is rate limited."""
        alert_key = self._get_alert_key(alert)
        
        if alert_key in self.last_alert_times:
            time_diff = alert.timestamp - self.last_alert_times[alert_key]
            if time_diff.total_seconds() < self.rate_limit_minutes * 60:
                return True
        
        return False
    
    def _get_alert_key(self, alert: Alert) -> str:
        """Get unique key for alert rate limiting."""
        return f"{alert.category}_{alert.severity}_{hash(alert.title) % 1000}"
    
    def _load_alert_rules(self) -> Dict[str, Any]:
        """Load alert rules configuration."""
        # Default alert rules
        return {
            'performance': {
                'daily_loss_threshold': -5.0,
                'critical_daily_loss_threshold': -10.0,
                'drawdown_threshold': 10.0,
                'critical_drawdown_threshold': 15.0
            },
            'capital': {
                'low_capital_threshold': 0.8,
                'critical_capital_threshold': 0.7
            },
            'trading': {
                'low_success_rate_threshold': 50.0,
                'high_failure_rate_threshold': 70.0
            }
        }
    
    def _save_alert_to_history(self, alert: Alert) -> None:
        """Save alert to persistent history."""
        try:
            history_file = self.data_dir / "alert_history.jsonl"
            
            with open(history_file, 'a') as f:
                f.write(json.dumps(alert.to_dict()) + '\n')
                
        except Exception as e:
            logger.error(f"Error saving alert to history: {e}")
    
    def _load_alert_history(self) -> None:
        """Load alert history from disk."""
        try:
            history_file = self.data_dir / "alert_history.jsonl"
            
            if not history_file.exists():
                return
            
            with open(history_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                        
                        alert = Alert(
                            id=data['id'],
                            title=data['title'],
                            message=data['message'],
                            severity=data['severity'],
                            timestamp=data['timestamp'],
                            category=data['category'],
                            acknowledged=data.get('acknowledged', False),
                            resolved=data.get('resolved', False)
                        )
                        
                        self.alert_history.append(alert)
                        
                    except Exception as e:
                        logger.error(f"Error parsing alert history line: {e}")
            
            # Keep only recent history (last 30 days)
            cutoff_time = datetime.utcnow() - timedelta(days=30)
            self.alert_history = [alert for alert in self.alert_history 
                                if alert.timestamp >= cutoff_time]
            
            logger.info(f"Loaded {len(self.alert_history)} alerts from history")
            
        except Exception as e:
            logger.error(f"Error loading alert history: {e}")
    
    def generate_alert_report(self) -> str:
        """Generate alert summary report."""
        try:
            stats = self.get_alert_statistics()
            
            report_date = datetime.now().strftime("%Y-%m-%d")
            report_path = self.data_dir / f"alert_report_{report_date}.txt"
            
            with open(report_path, 'w') as f:
                f.write(f"ALERT SUMMARY REPORT - {report_date}\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("ALERT STATISTICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Active Alerts: {stats['active_alerts']}\n")
                f.write(f"Alerts (24h): {stats['alerts_24h']}\n")
                f.write(f"Alerts (7d): {stats['alerts_7d']}\n\n")
                
                f.write("SEVERITY BREAKDOWN (24h)\n")
                f.write("-" * 20 + "\n")
                for severity, count in stats['severity_breakdown_24h'].items():
                    f.write(f"{severity.capitalize()}: {count}\n")
                f.write("\n")
                
                f.write("CATEGORY BREAKDOWN (24h)\n")
                f.write("-" * 20 + "\n")
                for category, count in stats['category_breakdown_24h'].items():
                    f.write(f"{category.capitalize()}: {count}\n")
                f.write("\n")
                
                # Recent critical alerts
                critical_alerts = [alert for alert in self.get_alert_history(24) 
                                 if alert.severity == 'critical']
                
                if critical_alerts:
                    f.write("RECENT CRITICAL ALERTS\n")
                    f.write("-" * 20 + "\n")
                    for alert in critical_alerts[-5:]:  # Last 5 critical alerts
                        f.write(f"{alert.timestamp.strftime('%H:%M')} - {alert.title}\n")
                        f.write(f"  {alert.message}\n\n")
            
            logger.info(f"Alert report generated: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error generating alert report: {e}")
            return ""
    
    def cleanup_old_alerts(self, days: int = 30) -> None:
        """Clean up old alerts from history."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Remove old alerts from memory
            old_count = len(self.alert_history)
            self.alert_history = [alert for alert in self.alert_history 
                                if alert.timestamp >= cutoff_time]
            
            removed_count = old_count - len(self.alert_history)
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old alerts")
            
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels."""
        test_alert = Alert(
            id="test_alert",
            title="Test Notification",
            message="This is a test notification from the Crypto Trading Bot.",
            severity="low",
            timestamp=datetime.utcnow(),
            category="test"
        )
        
        results = {}
        
        for i, notifier in enumerate(self.notifiers):
            notifier_name = notifier.__class__.__name__
            try:
                success = notifier.send_notification(test_alert)
                results[notifier_name] = success
            except Exception as e:
                logger.error(f"Test notification failed for {notifier_name}: {e}")
                results[notifier_name] = False
        
        return results

