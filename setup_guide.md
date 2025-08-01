# Setup Guide - Crypto Trading Bot

This comprehensive guide will walk you through setting up the Crypto Trading Bot from initial installation to running your first trades.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Initial Setup](#initial-setup)
5. [Testing](#testing)
6. [First Run](#first-run)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Operating System**: Ubuntu 20.04+ (or compatible Linux distribution)
- **Python**: Version 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB minimum, 20GB recommended for data storage
- **Network**: Stable internet connection with low latency

### Recommended Requirements
- **Operating System**: Ubuntu 22.04 LTS
- **Python**: Version 3.11
- **RAM**: 8GB for optimal performance
- **Storage**: 50GB SSD for high-frequency trading
- **Network**: Dedicated server with <50ms latency to exchanges

### Dependencies
- **System Packages**: curl, git, build-essential
- **Python Packages**: Listed in requirements.txt
- **Optional**: Docker for containerized deployment

## Installation

### Step 1: System Preparation

Update your system and install required packages:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3 python3-pip python3-venv git curl build-essential

# Install optional packages for enhanced functionality
sudo apt install -y postgresql postgresql-contrib redis-server nginx
```

### Step 2: Clone Repository

```bash
# Clone the trading bot repository
git clone <repository-url>
cd crypto_trading_bot

# Verify the project structure
ls -la
```

### Step 3: Python Environment Setup

```bash
# Create virtual environment
python3 -m venv trading_bot_env

# Activate virtual environment
source trading_bot_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

### Step 4: Directory Structure Creation

```bash
# Create necessary directories
mkdir -p logs data/performance data/alerts backtesting_results

# Set appropriate permissions
chmod 755 logs data
chmod 644 config/main_config.yaml
```

## Configuration

### Step 1: Main Configuration

Copy the example configuration and customize it:

```bash
# Copy example configuration
cp config/main_config.yaml.example config/main_config.yaml

# Edit configuration (use your preferred editor)
nano config/main_config.yaml
```

### Step 2: Trading Configuration

Configure your trading parameters in `config/main_config.yaml`:

```yaml
trading:
  initial_capital: 10000.0          # Starting capital in USD
  max_position_size_pct: 5.0        # Maximum position size (% of capital)
  max_daily_loss_pct: 5.0           # Daily loss limit (% of capital)
  max_weekly_loss_pct: 15.0         # Weekly loss limit (% of capital)
  max_drawdown_pct: 20.0            # Maximum drawdown limit
  
  # Supported tokens for trading
  allowed_tokens:
    - "BTC"
    - "ETH"
    - "USDC"
    - "LINK"
    - "UNI"
    - "AAVE"
```

### Step 3: Blockchain Configuration

Configure blockchain connection settings:

```yaml
execution:
  # Ethereum mainnet configuration
  rpc_url: "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
  chain_id: 1
  
  # Private key (use environment variable in production)
  private_key: "YOUR_PRIVATE_KEY_HERE"
  
  # Gas optimization
  gas_strategy: "medium"            # slow, medium, fast
  max_gas_price_gwei: 100
  slippage_tolerance_pct: 1.0
```

### Step 4: Strategy Configuration

Enable and configure trading strategies:

```yaml
strategies:
  momentum:
    enabled: true
    weight: 0.6                     # Strategy allocation weight
    lookback_period: 20             # Price history lookback
    rsi_threshold: 70               # RSI overbought threshold
    volume_threshold: 1.5           # Volume confirmation multiplier
    
  mean_reversion:
    enabled: true
    weight: 0.4
    lookback_period: 20
    std_threshold: 2.0              # Standard deviation threshold
    min_reversion_pct: 0.5          # Minimum reversion percentage
```

### Step 5: Risk Management Configuration

Configure risk management parameters:

```yaml
risk_management:
  kelly_fraction: 0.25              # Kelly criterion fraction
  volatility_lookback: 20           # Volatility calculation period
  correlation_threshold: 0.7        # Maximum correlation between positions
  max_positions: 10                 # Maximum concurrent positions
  
  # Stop loss configuration
  stop_loss:
    enabled: true
    default_pct: 5.0                # Default stop loss percentage
    trailing_enabled: true          # Enable trailing stops
    volatility_multiplier: 2.0      # Volatility-based stop adjustment
```

### Step 6: Monitoring Configuration

Configure monitoring and alerting:

```yaml
monitoring:
  performance_targets:
    monthly_return_pct: 20.0        # Target monthly return
    max_drawdown_pct: 15.0          # Maximum acceptable drawdown
    sharpe_ratio: 1.5               # Target Sharpe ratio
    win_rate_pct: 60.0              # Target win rate
    
  alerts:
    email:
      enabled: false                # Enable email alerts
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "your_email@gmail.com"
      password: "your_app_password"
      recipients:
        - "alerts@yourdomain.com"
    
    telegram:
      enabled: false                # Enable Telegram alerts
      bot_token: "YOUR_BOT_TOKEN"
      chat_id: "YOUR_CHAT_ID"
```

## Initial Setup

### Step 1: Environment Variables

Set up environment variables for sensitive data:

```bash
# Create environment file
cat > .env << EOF
PRIVATE_KEY=your_private_key_here
INFURA_KEY=your_infura_key_here
EMAIL_PASSWORD=your_email_app_password
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
EOF

# Secure the environment file
chmod 600 .env

# Load environment variables
source .env
```

### Step 2: Database Setup (Optional)

If using PostgreSQL for enhanced data storage:

```bash
# Create database user and database
sudo -u postgres createuser --interactive trading_bot
sudo -u postgres createdb trading_bot_db

# Update configuration to use PostgreSQL
# Edit config/main_config.yaml:
# database:
#   type: "postgresql"
#   url: "postgresql://trading_bot:password@localhost/trading_bot_db"
```

### Step 3: API Keys Setup

Obtain necessary API keys:

1. **Infura/Alchemy**: For Ethereum RPC access
   - Sign up at infura.io or alchemy.com
   - Create a new project
   - Copy the project ID/URL

2. **CoinGecko/CoinMarketCap**: For price data (optional)
   - Sign up for API access
   - Obtain API key

3. **Email Provider**: For alert notifications
   - Gmail: Enable 2FA and create app password
   - Other providers: Configure SMTP settings

4. **Telegram**: For instant notifications
   - Create bot via @BotFather
   - Obtain bot token and chat ID

### Step 4: Wallet Setup

Prepare your trading wallet:

```bash
# Generate new wallet (optional)
python3 -c "
from eth_account import Account
account = Account.create()
print(f'Address: {account.address}')
print(f'Private Key: {account.privateKey.hex()}')
"

# Fund your wallet with:
# - ETH for gas fees
# - USDC/USDT for trading capital
# - Small amounts of tokens you plan to trade
```

## Testing

### Step 1: Configuration Validation

Validate your configuration:

```bash
# Test configuration loading
python3 -c "
from src.utils.config_manager import get_config
config = get_config()
print('Configuration loaded successfully')
print(f'Initial capital: {config.trading.initial_capital}')
"
```

### Step 2: Connection Testing

Test blockchain connectivity:

```bash
# Test RPC connection
python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
print(f'Connected: {w3.isConnected()}')
print(f'Latest block: {w3.eth.block_number}')
"
```

### Step 3: Component Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_suite.py

# Run specific component tests
python -m unittest test_suite.TestConfigManager
python -m unittest test_suite.TestRiskManager
python -m unittest test_suite.TestTradingStrategies
```

### Step 4: Backtesting Validation

Run a sample backtest to validate strategies:

```bash
# Run sample backtest
python3 -c "
from src.backtesting.backtester import BacktestEngine
from src.strategies.momentum_strategy import MomentumStrategy
from datetime import datetime, timedelta

engine = BacktestEngine(10000.0)
engine.add_strategy(MomentumStrategy())

start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now() - timedelta(days=1)

results = engine.run_backtest(start_date, end_date, ['BTC'])
print(f'Backtest completed: {results[\"metrics\"][\"total_trades\"]} trades')
"
```

## First Run

### Step 1: Dry Run Mode

Start with paper trading to validate everything works:

```bash
# Enable dry run mode in config
# Set: execution.dry_run: true

# Start the bot
python -m src.main_bot
```

### Step 2: Monitor Initial Operation

In another terminal, monitor the logs:

```bash
# Watch main log file
tail -f logs/trading_bot.log

# Watch for specific events
grep "TRADE" logs/trading_bot.log
grep "ERROR" logs/trading_bot.log
```

### Step 3: Web Dashboard Access

Access the web dashboard:

```bash
# Start the API server (in another terminal)
cd trading_bot_api
source venv/bin/activate
python src/main.py

# Open browser to http://localhost:5000
```

### Step 4: Live Trading Transition

Once satisfied with dry run performance:

1. **Disable dry run mode**:
   ```yaml
   execution:
     dry_run: false
   ```

2. **Start with small capital**:
   ```yaml
   trading:
     initial_capital: 100.0  # Start small
   ```

3. **Monitor closely**:
   - Watch first few trades carefully
   - Verify execution prices and gas costs
   - Check position sizing and risk limits

## Troubleshooting

### Common Issues

#### 1. Configuration Errors

**Problem**: Bot fails to start with configuration errors

**Solution**:
```bash
# Validate YAML syntax
python3 -c "
import yaml
with open('config/main_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('Configuration is valid')
"

# Check for missing required fields
python3 -c "
from src.utils.config_manager import get_config
config = get_config()
print('All required fields present')
"
```

#### 2. Connection Issues

**Problem**: Cannot connect to blockchain RPC

**Solution**:
```bash
# Test RPC endpoint
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  YOUR_RPC_URL

# Try alternative RPC providers
# - Infura: https://infura.io
# - Alchemy: https://alchemy.com
# - QuickNode: https://quicknode.com
```

#### 3. Permission Errors

**Problem**: File permission errors

**Solution**:
```bash
# Fix file permissions
chmod 755 logs data
chmod 644 config/main_config.yaml
chmod 600 .env

# Fix ownership if needed
sudo chown -R $USER:$USER crypto_trading_bot/
```

#### 4. Memory Issues

**Problem**: Bot crashes with memory errors

**Solution**:
```bash
# Monitor memory usage
htop

# Reduce memory usage in config
# - Decrease data retention periods
# - Reduce concurrent positions
# - Lower update frequencies

# Add swap space if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 5. Gas Price Issues

**Problem**: Transactions failing due to gas prices

**Solution**:
```yaml
# Adjust gas configuration
execution:
  gas_strategy: "fast"        # Use faster gas
  max_gas_price_gwei: 200     # Increase max gas price
  gas_multiplier: 1.2         # Add gas buffer
```

### Getting Help

1. **Check Logs**: Always start by examining log files
2. **Test Components**: Use the test suite to isolate issues
3. **Documentation**: Review relevant documentation sections
4. **Community**: Join community discussions for support
5. **Issues**: Report bugs via GitHub issues

### Performance Optimization

#### 1. System Optimization

```bash
# Optimize system for trading
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Set CPU governor to performance
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 2. Database Optimization

```bash
# For PostgreSQL
sudo -u postgres psql -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
"
```

#### 3. Network Optimization

```bash
# Use fastest RPC endpoints
# Test latency to different providers
ping mainnet.infura.io
ping eth-mainnet.alchemyapi.io

# Consider running local node for best performance
# geth --syncmode "fast" --cache 2048
```

This completes the setup guide. Follow these steps carefully, and you'll have a fully functional crypto trading bot ready for operation.

