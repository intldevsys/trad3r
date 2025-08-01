import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
import argparse
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages deployment of the crypto trading bot."""
    
    def __init__(self, environment='production'):
        self.environment = environment
        self.project_root = Path(__file__).parent
        self.deployment_dir = self.project_root / 'deployment'
        self.config_dir = self.project_root / 'config'
        
        # Create deployment directory
        self.deployment_dir.mkdir(exist_ok=True)
        
        logger.info(f"Deployment Manager initialized for {environment} environment")
    
    def validate_environment(self):
        """Validate the deployment environment."""
        logger.info("Validating deployment environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or python_version.minor < 8:
            raise RuntimeError("Python 3.8+ is required")
        
        # Check required directories
        required_dirs = ['src', 'config', 'logs', 'data']
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                logger.warning(f"Creating missing directory: {dir_name}")
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # Check configuration files
        config_file = self.config_dir / 'main_config.yaml'
        if not config_file.exists():
            raise RuntimeError(f"Configuration file not found: {config_file}")
        
        logger.info("Environment validation completed")
    
    def install_dependencies(self):
        """Install required dependencies."""
        logger.info("Installing dependencies...")
        
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            raise RuntimeError("requirements.txt not found")
        
        # Install dependencies
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
        ], check=True)
        
        logger.info("Dependencies installed successfully")
    
    def setup_security(self):
        """Setup security configurations."""
        logger.info("Setting up security configurations...")
        
        # Create security configuration
        security_config = {
            'api_security': {
                'rate_limiting': {
                    'enabled': True,
                    'requests_per_minute': 60,
                    'burst_limit': 10
                },
                'authentication': {
                    'enabled': True,
                    'token_expiry_hours': 24
                },
                'cors': {
                    'enabled': True,
                    'allowed_origins': ['*'] if self.environment == 'development' else []
                }
            },
            'trading_security': {
                'max_position_size_pct': 5.0,
                'daily_loss_limit_pct': 10.0,
                'emergency_stop_enabled': True,
                'whitelist_enabled': True,
                'allowed_tokens': ['BTC', 'ETH', 'USDC', 'LINK', 'UNI']
            },
            'system_security': {
                'log_level': 'INFO',
                'log_retention_days': 30,
                'backup_enabled': True,
                'backup_interval_hours': 6
            }
        }
        
        security_file = self.deployment_dir / 'security_config.json'
        with open(security_file, 'w') as f:
            json.dump(security_config, f, indent=2)
        
        logger.info(f"Security configuration saved to {security_file}")
    
    def create_systemd_service(self):
        """Create systemd service file for production deployment."""
        if self.environment != 'production':
            return
        
        logger.info("Creating systemd service file...")
        
        service_content = f"""[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory={self.project_root}
Environment=PYTHONPATH={self.project_root}
ExecStart={sys.executable} -m src.main_bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        service_file = self.deployment_dir / 'crypto-trading-bot.service'
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        logger.info(f"Systemd service file created: {service_file}")
        logger.info("To install the service, run:")
        logger.info(f"sudo cp {service_file} /etc/systemd/system/")
        logger.info("sudo systemctl daemon-reload")
        logger.info("sudo systemctl enable crypto-trading-bot")
        logger.info("sudo systemctl start crypto-trading-bot")
    
    def create_nginx_config(self):
        """Create nginx configuration for the API."""
        logger.info("Creating nginx configuration...")
        
        nginx_config = f"""server {{
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name your-domain.com;  # Replace with your domain
    
    # SSL configuration (replace with your certificates)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;
    
    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=5 nodelay;
    }}
    
    # Static files
    location /static/ {{
        alias {self.project_root}/trading_bot_api/src/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
        
        nginx_file = self.deployment_dir / 'nginx.conf'
        with open(nginx_file, 'w') as f:
            f.write(nginx_config)
        
        logger.info(f"Nginx configuration created: {nginx_file}")
    
    def create_docker_config(self):
        """Create Docker configuration files."""
        logger.info("Creating Docker configuration...")
        
        # Dockerfile
        dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/performance data/alerts backtesting_results

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=trading_bot_api/src/main.py

# Expose ports
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/api/bot/health || exit 1

# Run the application
CMD ["python", "-m", "src.main_bot"]
"""
        
        dockerfile = self.deployment_dir / 'Dockerfile'
        with open(dockerfile, 'w') as f:
            f.write(dockerfile_content)
        
        # Docker Compose
        compose_content = f"""version: '3.8'

services:
  trading-bot:
    build: .
    container_name: crypto-trading-bot
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - ENVIRONMENT=production
      - PYTHONPATH=/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/bot/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: crypto-trading-bot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deployment/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl  # Mount SSL certificates
    depends_on:
      - trading-bot

volumes:
  logs:
  data:
"""
        
        compose_file = self.deployment_dir / 'docker-compose.yml'
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        logger.info("Docker configuration files created")
    
    def create_backup_script(self):
        """Create backup script for data and configuration."""
        logger.info("Creating backup script...")
        
        backup_script = f"""#!/bin/bash

# Crypto Trading Bot Backup Script
# Run this script regularly to backup important data

BACKUP_DIR="/backup/crypto-trading-bot"
PROJECT_DIR="{self.project_root}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="crypto_trading_bot_backup_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup archive
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \\
    -C "$PROJECT_DIR" \\
    config/ \\
    data/ \\
    logs/ \\
    --exclude="*.pyc" \\
    --exclude="__pycache__"

# Keep only last 30 backups
cd "$BACKUP_DIR"
ls -t *.tar.gz | tail -n +31 | xargs -r rm

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Optional: Upload to cloud storage
# aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" s3://your-backup-bucket/
"""
        
        backup_file = self.deployment_dir / 'backup.sh'
        with open(backup_file, 'w') as f:
            f.write(backup_script)
        
        # Make executable
        os.chmod(backup_file, 0o755)
        
        logger.info(f"Backup script created: {backup_file}")
    
    def create_monitoring_script(self):
        """Create monitoring and health check script."""
        logger.info("Creating monitoring script...")
        
        monitoring_script = f"""#!/bin/bash

# Crypto Trading Bot Monitoring Script
# Checks system health and sends alerts if needed

PROJECT_DIR="{self.project_root}"
LOG_FILE="$PROJECT_DIR/logs/monitoring.log"
API_URL="http://localhost:5000/api/bot/health"

# Function to log messages
log_message() {{
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}}

# Check if the bot is running
check_bot_health() {{
    response=$(curl -s -o /dev/null -w "%{{http_code}}" "$API_URL" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        log_message "Bot health check: OK"
        return 0
    else
        log_message "Bot health check: FAILED (HTTP $response)"
        return 1
    fi
}}

# Check disk space
check_disk_space() {{
    usage=$(df "$PROJECT_DIR" | awk 'NR==2 {{print $5}}' | sed 's/%//')
    
    if [ "$usage" -gt 90 ]; then
        log_message "Disk space warning: $usage% used"
        return 1
    else
        log_message "Disk space check: OK ($usage% used)"
        return 0
    fi
}}

# Check log file size
check_log_size() {{
    log_size=$(du -m "$PROJECT_DIR/logs/trading_bot.log" 2>/dev/null | cut -f1)
    
    if [ "$log_size" -gt 100 ]; then
        log_message "Log file size warning: ${{log_size}}MB"
        # Rotate log file
        mv "$PROJECT_DIR/logs/trading_bot.log" "$PROJECT_DIR/logs/trading_bot.log.old"
        touch "$PROJECT_DIR/logs/trading_bot.log"
        log_message "Log file rotated"
    fi
}}

# Main monitoring function
main() {{
    log_message "Starting health check"
    
    health_ok=true
    
    if ! check_bot_health; then
        health_ok=false
    fi
    
    if ! check_disk_space; then
        health_ok=false
    fi
    
    check_log_size
    
    if [ "$health_ok" = false ]; then
        log_message "Health check FAILED - sending alert"
        # Send alert (implement your preferred method)
        # curl -X POST "your-webhook-url" -d "Bot health check failed"
    else
        log_message "Health check completed successfully"
    fi
}}

main "$@"
"""
        
        monitoring_file = self.deployment_dir / 'monitor.sh'
        with open(monitoring_file, 'w') as f:
            f.write(monitoring_script)
        
        # Make executable
        os.chmod(monitoring_file, 0o755)
        
        logger.info(f"Monitoring script created: {monitoring_file}")
    
    def create_deployment_guide(self):
        """Create deployment guide documentation."""
        logger.info("Creating deployment guide...")
        
        guide_content = f"""# Crypto Trading Bot Deployment Guide

## Prerequisites

1. **System Requirements:**
   - Ubuntu 20.04+ or similar Linux distribution
   - Python 3.8+
   - 4GB+ RAM
   - 20GB+ disk space
   - Stable internet connection

2. **Required Services:**
   - PostgreSQL or SQLite for data storage
   - Redis for caching (optional)
   - Nginx for reverse proxy (production)

## Deployment Steps

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd crypto_trading_bot

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs data/performance data/alerts backtesting_results
```

### 2. Configuration

1. Copy `config/main_config.yaml.example` to `config/main_config.yaml`
2. Update configuration values:
   - API keys and secrets
   - Trading parameters
   - Risk management settings
   - Alert configurations

### 3. Security Setup

1. Review and update `deployment/security_config.json`
2. Set up SSL certificates for HTTPS
3. Configure firewall rules
4. Set up monitoring and alerting

### 4. Production Deployment Options

#### Option A: Systemd Service

```bash
# Copy service file
sudo cp deployment/crypto-trading-bot.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable crypto-trading-bot
sudo systemctl start crypto-trading-bot

# Check status
sudo systemctl status crypto-trading-bot
```

#### Option B: Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f deployment/docker-compose.yml up -d

# Check logs
docker-compose logs -f trading-bot
```

### 5. Web Dashboard Setup

The web dashboard is available at `http://localhost:5000` after starting the API server.

For production, set up Nginx reverse proxy:

```bash
# Copy nginx configuration
sudo cp deployment/nginx.conf /etc/nginx/sites-available/crypto-trading-bot
sudo ln -s /etc/nginx/sites-available/crypto-trading-bot /etc/nginx/sites-enabled/

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Monitoring and Maintenance

1. **Health Monitoring:**
   ```bash
   # Run health check
   ./deployment/monitor.sh
   
   # Set up cron job for regular monitoring
   echo "*/5 * * * * /path/to/crypto_trading_bot/deployment/monitor.sh" | crontab -
   ```

2. **Backup Setup:**
   ```bash
   # Run backup
   ./deployment/backup.sh
   
   # Set up daily backup cron job
   echo "0 2 * * * /path/to/crypto_trading_bot/deployment/backup.sh" | crontab -
   ```

3. **Log Management:**
   - Logs are stored in `logs/` directory
   - Set up log rotation to prevent disk space issues
   - Monitor log files for errors and warnings

## Security Considerations

1. **API Security:**
   - Use HTTPS in production
   - Implement rate limiting
   - Use strong authentication tokens
   - Regularly rotate API keys

2. **Trading Security:**
   - Set conservative position size limits
   - Implement emergency stop mechanisms
   - Use whitelist for allowed tokens
   - Monitor for unusual trading patterns

3. **System Security:**
   - Keep system and dependencies updated
   - Use firewall to restrict access
   - Regular security audits
   - Backup encryption

## Troubleshooting

### Common Issues

1. **Bot not starting:**
   - Check configuration file syntax
   - Verify API keys and permissions
   - Check log files for error messages

2. **Trading not working:**
   - Verify exchange connectivity
   - Check account balances
   - Review risk management settings

3. **Performance issues:**
   - Monitor system resources
   - Check database performance
   - Review strategy parameters

### Log Locations

- Main bot logs: `logs/trading_bot.log`
- API logs: `logs/api.log`
- Monitoring logs: `logs/monitoring.log`

### Support

For support and updates, refer to the project documentation and community forums.

## Environment Variables

Set the following environment variables for production:

```bash
export ENVIRONMENT=production
export PYTHONPATH=/path/to/crypto_trading_bot
export FLASK_APP=trading_bot_api/src/main.py
```

## Performance Tuning

1. **Database Optimization:**
   - Use connection pooling
   - Implement proper indexing
   - Regular database maintenance

2. **Memory Management:**
   - Monitor memory usage
   - Implement data cleanup routines
   - Use efficient data structures

3. **Network Optimization:**
   - Use connection keep-alive
   - Implement request caching
   - Optimize API call frequency

## Scaling Considerations

For high-frequency trading or large portfolios:

1. Use multiple bot instances
2. Implement load balancing
3. Use distributed caching
4. Consider microservices architecture
"""
        
        guide_file = self.deployment_dir / 'DEPLOYMENT_GUIDE.md'
        with open(guide_file, 'w') as f:
            f.write(guide_content)
        
        logger.info(f"Deployment guide created: {guide_file}")
    
    def run_security_audit(self):
        """Run basic security audit checks."""
        logger.info("Running security audit...")
        
        audit_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': [],
            'warnings': [],
            'errors': []
        }
        
        # Check file permissions
        sensitive_files = [
            'config/main_config.yaml',
            'deployment/security_config.json'
        ]
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                stat = full_path.stat()
                mode = oct(stat.st_mode)[-3:]
                if mode != '600':
                    audit_results['warnings'].append(
                        f"File {file_path} has permissions {mode}, should be 600"
                    )
                else:
                    audit_results['checks'].append(f"File permissions OK: {file_path}")
        
        # Check for hardcoded secrets
        code_files = list(self.project_root.glob('src/**/*.py'))
        secret_patterns = ['password', 'secret', 'key', 'token']
        
        for file_path in code_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read().lower()
                    for pattern in secret_patterns:
                        if f'{pattern} = ' in content and 'your_' not in content:
                            audit_results['warnings'].append(
                                f"Potential hardcoded secret in {file_path}"
                            )
            except Exception:
                continue
        
        # Check configuration
        config_file = self.config_dir / 'main_config.yaml'
        if config_file.exists():
            audit_results['checks'].append("Configuration file exists")
        else:
            audit_results['errors'].append("Configuration file missing")
        
        # Save audit results
        audit_file = self.deployment_dir / 'security_audit.json'
        with open(audit_file, 'w') as f:
            json.dump(audit_results, f, indent=2)
        
        # Print summary
        logger.info(f"Security audit completed:")
        logger.info(f"  Checks passed: {len(audit_results['checks'])}")
        logger.info(f"  Warnings: {len(audit_results['warnings'])}")
        logger.info(f"  Errors: {len(audit_results['errors'])}")
        
        if audit_results['warnings']:
            logger.warning("Security warnings found:")
            for warning in audit_results['warnings']:
                logger.warning(f"  - {warning}")
        
        if audit_results['errors']:
            logger.error("Security errors found:")
            for error in audit_results['errors']:
                logger.error(f"  - {error}")
        
        return len(audit_results['errors']) == 0
    
    def deploy(self, skip_tests=False):
        """Run complete deployment process."""
        logger.info(f"Starting deployment for {self.environment} environment")
        
        try:
            # Validation
            self.validate_environment()
            
            # Dependencies
            self.install_dependencies()
            
            # Security
            self.setup_security()
            
            # Configuration files
            self.create_systemd_service()
            self.create_nginx_config()
            self.create_docker_config()
            
            # Scripts
            self.create_backup_script()
            self.create_monitoring_script()
            
            # Documentation
            self.create_deployment_guide()
            
            # Security audit
            if not self.run_security_audit():
                if self.environment == 'production':
                    raise RuntimeError("Security audit failed - deployment aborted")
                else:
                    logger.warning("Security audit failed - continuing with development deployment")
            
            logger.info("Deployment completed successfully!")
            logger.info(f"Deployment files created in: {self.deployment_dir}")
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            raise


def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(description='Deploy Crypto Trading Bot')
    parser.add_argument(
        '--environment',
        choices=['development', 'staging', 'production'],
        default='production',
        help='Deployment environment'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test execution'
    )
    
    args = parser.parse_args()
    
    # Create deployment manager
    deployment_manager = DeploymentManager(args.environment)
    
    # Run deployment
    deployment_manager.deploy(skip_tests=args.skip_tests)


if __name__ == '__main__':
    main()

