# API Reference Guide - Crypto Trading Bot

This comprehensive guide covers all API endpoints, request/response formats, and integration examples for the Crypto Trading Bot.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Bot Control API](#bot-control-api)
4. [Performance API](#performance-api)
5. [Alert Management API](#alert-management-api)
6. [Backtesting API](#backtesting-api)
7. [Configuration API](#configuration-api)
8. [WebSocket API](#websocket-api)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Examples](#examples)

## Overview

The Crypto Trading Bot provides a comprehensive REST API for monitoring, controlling, and integrating with the trading system. All endpoints return JSON responses and follow RESTful conventions.

### Base URL
```
http://localhost:5000/api
```

### Response Format
All API responses follow this standard format:

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Authentication

### API Key Authentication (Production)
```http
Authorization: Bearer YOUR_API_KEY
```

### Development Mode
No authentication required for local development.

### Obtaining API Key
```bash
# Generate API key via CLI
python -m src.utils.api_key_generator --generate

# Or via API (admin only)
POST /api/auth/generate-key
```

## Bot Control API

### Get Bot Status
Retrieve current bot status and basic metrics.

```http
GET /api/bot/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "trading_enabled": true,
    "current_capital": 10500.50,
    "daily_pnl": 500.50,
    "total_trades": 25,
    "successful_trades": 18,
    "success_rate": 72.0,
    "active_positions": 3,
    "total_position_value": 2500.00,
    "last_update": "2024-01-01T12:00:00Z",
    "strategies": [
      {
        "name": "Momentum Strategy",
        "enabled": true,
        "weight": 0.6,
        "trades": 15,
        "pnl": 300.25
      }
    ]
  }
}
```

### Start Bot
Start the trading bot.

```http
POST /api/bot/start
```

**Response:**
```json
{
  "success": true,
  "message": "Trading bot started successfully"
}
```

### Stop Bot
Stop the trading bot.

```http
POST /api/bot/stop
```

**Response:**
```json
{
  "success": true,
  "message": "Trading bot stopped successfully"
}
```

### Enable Trading
Enable trading while keeping bot running.

```http
POST /api/bot/trading/enable
```

### Disable Trading
Disable trading while keeping bot running.

```http
POST /api/bot/trading/disable
```

### Get Bot Health
Check system health status.

```http
GET /api/bot/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "components": {
      "bot": "healthy",
      "performance_monitor": "healthy",
      "alert_manager": "healthy",
      "execution_engine": "healthy"
    },
    "uptime": 86400,
    "memory_usage": 45.2,
    "cpu_usage": 12.5
  }
}
```

## Performance API

### Get Performance Metrics
Retrieve comprehensive performance metrics.

```http
GET /api/bot/performance
```

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-01T12:00:00Z",
    "capital": 10500.50,
    "daily_pnl": 500.50,
    "total_return_pct": 5.0,
    "daily_return_pct": 2.5,
    "annualized_return_pct": 45.2,
    "max_drawdown_abs": 750.00,
    "max_drawdown_pct": 7.5,
    "current_drawdown_pct": 2.1,
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.12,
    "calmar_ratio": 6.03,
    "total_trades": 25,
    "successful_trades": 18,
    "success_rate": 72.0,
    "win_rate": 68.0,
    "profit_factor": 1.45,
    "active_positions": 3,
    "total_position_value": 2500.00
  }
}
```

### Check Performance Targets
Validate performance against configured targets.

```http
GET /api/bot/performance/targets
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "meeting_targets",
    "issues": [],
    "targets": {
      "monthly_return_pct": 20.0,
      "max_drawdown_pct": 15.0,
      "sharpe_ratio": 1.5,
      "win_rate_pct": 60.0
    },
    "current": {
      "monthly_return_pct": 22.5,
      "max_drawdown_pct": 7.5,
      "sharpe_ratio": 1.85,
      "win_rate_pct": 68.0
    }
  }
}
```

### Get Performance History
Retrieve historical performance data.

```http
GET /api/bot/performance/history?period=7d&interval=1h
```

**Query Parameters:**
- `period`: Time period (1d, 7d, 30d, 90d, 1y)
- `interval`: Data interval (1m, 5m, 15m, 1h, 1d)

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "7d",
    "interval": "1h",
    "data_points": [
      {
        "timestamp": "2024-01-01T00:00:00Z",
        "capital": 10000.00,
        "pnl": 0.00,
        "return_pct": 0.00
      },
      {
        "timestamp": "2024-01-01T01:00:00Z",
        "capital": 10025.50,
        "pnl": 25.50,
        "return_pct": 0.26
      }
    ]
  }
}
```

## Alert Management API

### Get Active Alerts
Retrieve list of active alerts.

```http
GET /api/bot/alerts?severity=high&limit=50
```

**Query Parameters:**
- `severity`: Filter by severity (low, medium, high, critical)
- `limit`: Maximum number of alerts to return
- `offset`: Pagination offset

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "alert_1704110400",
      "title": "High Daily Loss",
      "message": "Daily return is -6.5%, exceeding -5% threshold",
      "severity": "high",
      "category": "performance",
      "timestamp": "2024-01-01T12:00:00Z",
      "acknowledged": false,
      "resolved": false
    }
  ],
  "count": 1,
  "total": 1
}
```

### Get Alert Statistics
Retrieve alert statistics and summaries.

```http
GET /api/bot/alerts/statistics
```

**Response:**
```json
{
  "success": true,
  "data": {
    "active_alerts": 3,
    "alerts_24h": 8,
    "alerts_7d": 25,
    "severity_breakdown_24h": {
      "low": 2,
      "medium": 4,
      "high": 2,
      "critical": 0
    },
    "category_breakdown_24h": {
      "performance": 3,
      "risk": 2,
      "system": 2,
      "trading": 1
    },
    "total_historical_alerts": 150
  }
}
```

### Acknowledge Alert
Mark an alert as acknowledged.

```http
POST /api/bot/alerts/{alert_id}/acknowledge
```

**Response:**
```json
{
  "success": true,
  "message": "Alert alert_1704110400 acknowledged"
}
```

### Resolve Alert
Mark an alert as resolved.

```http
POST /api/bot/alerts/{alert_id}/resolve
```

**Response:**
```json
{
  "success": true,
  "message": "Alert alert_1704110400 resolved"
}
```

### Create Custom Alert
Create a custom alert.

```http
POST /api/bot/alerts
```

**Request Body:**
```json
{
  "title": "Custom Alert",
  "message": "Custom alert message",
  "severity": "medium",
  "category": "custom"
}
```

## Backtesting API

### Run Backtest
Execute a strategy backtest.

```http
POST /api/bot/backtest
```

**Request Body:**
```json
{
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2024-01-01T00:00:00Z",
  "initial_capital": 10000.0,
  "symbols": ["BTC", "ETH", "USDC"],
  "strategies": ["momentum", "mean_reversion"],
  "parameters": {
    "momentum": {
      "lookback_period": 20,
      "rsi_threshold": 70
    },
    "mean_reversion": {
      "std_threshold": 2.0
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "backtest_id": "bt_1704110400",
    "status": "completed",
    "results": {
      "metrics": {
        "total_trades": 45,
        "winning_trades": 28,
        "losing_trades": 17,
        "win_rate": 62.22,
        "total_return": 1250.50,
        "total_return_pct": 12.51,
        "annualized_return": 15.2,
        "max_drawdown": 850.00,
        "max_drawdown_pct": 8.5,
        "sharpe_ratio": 1.65,
        "sortino_ratio": 2.1,
        "profit_factor": 1.38
      },
      "strategy_results": {
        "momentum": {
          "trades": 25,
          "pnl": 750.25,
          "win_rate": 64.0
        },
        "mean_reversion": {
          "trades": 20,
          "pnl": 500.25,
          "win_rate": 60.0
        }
      }
    },
    "report_path": "/path/to/backtest_report.pdf"
  }
}
```

### Get Backtest Status
Check the status of a running backtest.

```http
GET /api/bot/backtest/{backtest_id}/status
```

### Get Backtest Results
Retrieve completed backtest results.

```http
GET /api/bot/backtest/{backtest_id}/results
```

### List Backtests
Get list of historical backtests.

```http
GET /api/bot/backtests?limit=20&offset=0
```

## Configuration API

### Get Configuration
Retrieve current bot configuration.

```http
GET /api/bot/config
```

**Response:**
```json
{
  "success": true,
  "data": {
    "trading": {
      "initial_capital": 10000.0,
      "max_position_size_pct": 5.0,
      "max_daily_loss_pct": 5.0,
      "max_weekly_loss_pct": 15.0,
      "max_drawdown_pct": 20.0
    },
    "risk_management": {
      "kelly_fraction": 0.25,
      "volatility_lookback": 20,
      "correlation_threshold": 0.7
    },
    "execution": {
      "gas_strategy": "medium",
      "max_gas_price_gwei": 100,
      "slippage_tolerance_pct": 1.0
    },
    "strategies": {
      "momentum": {
        "enabled": true,
        "weight": 0.6
      },
      "mean_reversion": {
        "enabled": true,
        "weight": 0.4
      }
    }
  }
}
```

### Update Configuration
Update bot configuration (requires restart).

```http
PUT /api/bot/config
```

**Request Body:**
```json
{
  "trading": {
    "max_position_size_pct": 3.0
  },
  "strategies": {
    "momentum": {
      "weight": 0.7
    }
  }
}
```

### Get Strategy Information
Retrieve information about available strategies.

```http
GET /api/bot/strategies
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "Momentum Strategy",
      "description": "Identifies and follows price trends using technical indicators",
      "parameters": {
        "lookback_period": {
          "type": "integer",
          "default": 20,
          "min": 5,
          "max": 100,
          "description": "Number of periods for trend analysis"
        },
        "rsi_threshold": {
          "type": "float",
          "default": 70.0,
          "min": 50.0,
          "max": 90.0,
          "description": "RSI threshold for overbought conditions"
        }
      },
      "enabled": true,
      "weight": 0.6
    }
  ]
}
```

## WebSocket API

### Connection
Connect to real-time data stream.

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onopen = function(event) {
    console.log('Connected to WebSocket');
    
    // Subscribe to updates
    ws.send(JSON.stringify({
        action: 'subscribe',
        channels: ['performance', 'alerts', 'trades']
    }));
};
```

### Message Format
```json
{
  "channel": "performance",
  "type": "update",
  "data": {
    "capital": 10500.50,
    "daily_pnl": 500.50,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Available Channels
- `performance`: Real-time performance updates
- `alerts`: New alerts and alert status changes
- `trades`: Trade execution notifications
- `positions`: Position updates
- `system`: System status changes

## Error Handling

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Server error

### Error Response Examples

#### Validation Error
```json
{
  "success": false,
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {
    "field": "initial_capital",
    "message": "Must be greater than 0"
  }
}
```

#### Rate Limit Error
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

#### System Error
```json
{
  "success": false,
  "error": "Trading bot is not running",
  "code": "BOT_NOT_RUNNING"
}
```

## Rate Limiting

### Default Limits
- **General API**: 60 requests per minute
- **Backtesting**: 5 requests per minute
- **Configuration**: 10 requests per minute

### Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704110460
```

### Handling Rate Limits
```python
import time
import requests

def api_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

## Examples

### Python Client Example

```python
import requests
import json
from datetime import datetime, timedelta

class TradingBotClient:
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_status(self):
        """Get bot status"""
        response = self.session.get(f"{self.base_url}/bot/status")
        return response.json()
    
    def start_bot(self):
        """Start the trading bot"""
        response = self.session.post(f"{self.base_url}/bot/start")
        return response.json()
    
    def get_performance(self):
        """Get performance metrics"""
        response = self.session.get(f"{self.base_url}/bot/performance")
        return response.json()
    
    def run_backtest(self, start_date, end_date, strategies=None):
        """Run a backtest"""
        if strategies is None:
            strategies = ["momentum", "mean_reversion"]
        
        data = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": 10000.0,
            "symbols": ["BTC", "ETH", "USDC"],
            "strategies": strategies
        }
        
        response = self.session.post(
            f"{self.base_url}/bot/backtest",
            json=data
        )
        return response.json()

# Usage example
client = TradingBotClient()

# Get current status
status = client.get_status()
print(f"Bot running: {status['data']['running']}")

# Run backtest
start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now() - timedelta(days=1)
backtest_result = client.run_backtest(start_date, end_date)
print(f"Backtest completed: {backtest_result['data']['results']['metrics']['total_trades']} trades")
```

### JavaScript Client Example

```javascript
class TradingBotClient {
    constructor(baseUrl = 'http://localhost:5000/api') {
        this.baseUrl = baseUrl;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        return await response.json();
    }
    
    async getStatus() {
        return await this.request('/bot/status');
    }
    
    async getPerformance() {
        return await this.request('/bot/performance');
    }
    
    async getAlerts(severity = null) {
        const params = severity ? `?severity=${severity}` : '';
        return await this.request(`/bot/alerts${params}`);
    }
    
    async acknowledgeAlert(alertId) {
        return await this.request(`/bot/alerts/${alertId}/acknowledge`, {
            method: 'POST'
        });
    }
}

// Usage example
const client = new TradingBotClient();

// Get status and update UI
client.getStatus().then(response => {
    if (response.success) {
        document.getElementById('capital').textContent = 
            `$${response.data.current_capital.toFixed(2)}`;
        document.getElementById('daily-pnl').textContent = 
            `$${response.data.daily_pnl.toFixed(2)}`;
    }
});

// Real-time updates via WebSocket
const ws = new WebSocket('ws://localhost:5000/ws');
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    if (message.channel === 'performance') {
        updatePerformanceDisplay(message.data);
    } else if (message.channel === 'alerts') {
        showNewAlert(message.data);
    }
};
```

### cURL Examples

```bash
# Get bot status
curl -X GET http://localhost:5000/api/bot/status

# Start bot
curl -X POST http://localhost:5000/api/bot/start

# Get performance metrics
curl -X GET http://localhost:5000/api/bot/performance

# Run backtest
curl -X POST http://localhost:5000/api/bot/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2024-01-01T00:00:00Z",
    "initial_capital": 10000.0,
    "symbols": ["BTC", "ETH"],
    "strategies": ["momentum"]
  }'

# Get alerts
curl -X GET "http://localhost:5000/api/bot/alerts?severity=high&limit=10"

# Acknowledge alert
curl -X POST http://localhost:5000/api/bot/alerts/alert_1704110400/acknowledge
```

This API guide provides comprehensive coverage of all available endpoints and integration patterns for the Crypto Trading Bot system.

