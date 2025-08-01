"""
Configuration Manager for Crypto Trading Bot
Handles loading and managing configuration from YAML files and environment variables.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class APIConfig(BaseModel):
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = 60
    timeout: int = 30


class TradingConfig(BaseModel):
    initial_capital: float
    max_position_size_pct: float = 5.0
    min_position_size_pct: float = 0.5
    max_daily_loss_pct: float = 10.0
    max_weekly_loss_pct: float = 20.0
    max_drawdown_pct: float = 15.0
    dex_platforms: list = Field(default_factory=list)
    networks: list = Field(default_factory=list)


class RiskManagementConfig(BaseModel):
    kelly_fraction: float = 0.25
    volatility_lookback: int = 30
    correlation_threshold: float = 0.7
    stop_loss: Dict[str, float] = Field(default_factory=dict)
    position_sizing: Dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    enabled: bool = True
    weight: float = 0.2
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MonitoringConfig(BaseModel):
    prometheus: Dict[str, Any] = Field(default_factory=dict)
    alerts: Dict[str, Any] = Field(default_factory=dict)
    performance_targets: Dict[str, float] = Field(default_factory=dict)


class SecurityConfig(BaseModel):
    private_key_encrypted: bool = True
    use_hardware_wallet: bool = False
    multi_sig_enabled: bool = False
    encryption: Dict[str, Any] = Field(default_factory=dict)


class ExecutionConfig(BaseModel):
    gas_strategy: str = "fast"
    max_gas_price_gwei: int = 100
    slippage_tolerance_pct: float = 1.0
    deadline_minutes: int = 20
    order_routing: Dict[str, Any] = Field(default_factory=dict)


class DataConfig(BaseModel):
    price_update_interval: int = 1
    sentiment_update_interval: int = 300
    on_chain_update_interval: int = 60
    storage: Dict[str, Any] = Field(default_factory=dict)


class BacktestingConfig(BaseModel):
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    commission_pct: float = 0.1
    slippage_pct: float = 0.05


class SystemConfig(BaseModel):
    environment: str = "development"
    log_level: str = "INFO"
    max_workers: int = 4
    timezone: str = "UTC"


class Config(BaseModel):
    system: SystemConfig
    database: DatabaseConfig
    redis: RedisConfig
    api: Dict[str, APIConfig]
    trading: TradingConfig
    risk_management: RiskManagementConfig
    strategies: Dict[str, StrategyConfig]
    monitoring: MonitoringConfig
    security: SecurityConfig
    execution: ExecutionConfig
    data: DataConfig
    backtesting: BacktestingConfig


class ConfigManager:
    """Manages configuration loading and access for the trading bot."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default path.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Config] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "config" / "main_config.yaml")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            # Replace environment variable placeholders
            config_data = self._replace_env_vars(config_data)
            
            # Validate and create config object
            self._config = Config(**config_data)
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _replace_env_vars(self, data: Any) -> Any:
        """Recursively replace environment variable placeholders in configuration data."""
        if isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        else:
            return data
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        logger.info("Configuration reloaded")
    
    @property
    def config(self) -> Config:
        """Get the current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        return self._config
    
    def get_api_config(self, api_name: str) -> APIConfig:
        """Get configuration for a specific API."""
        if api_name not in self.config.api:
            raise ValueError(f"API configuration not found: {api_name}")
        return self.config.api[api_name]
    
    def get_strategy_config(self, strategy_name: str) -> StrategyConfig:
        """Get configuration for a specific strategy."""
        if strategy_name not in self.config.strategies:
            raise ValueError(f"Strategy configuration not found: {strategy_name}")
        return self.config.strategies[strategy_name]
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """Update a configuration value."""
        if not hasattr(self.config, section):
            raise ValueError(f"Configuration section not found: {section}")
        
        section_config = getattr(self.config, section)
        if not hasattr(section_config, key):
            raise ValueError(f"Configuration key not found: {section}.{key}")
        
        setattr(section_config, key, value)
        logger.info(f"Configuration updated: {section}.{key} = {value}")
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.config.database.url
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration as dictionary."""
        return {
            "host": self.config.redis.host,
            "port": self.config.redis.port,
            "db": self.config.redis.db,
            "password": self.config.redis.password,
        }
    
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """Check if a strategy is enabled."""
        try:
            strategy_config = self.get_strategy_config(strategy_name)
            return strategy_config.enabled
        except ValueError:
            return False
    
    def get_risk_limits(self) -> Dict[str, float]:
        """Get risk management limits."""
        return {
            "max_position_size_pct": self.config.trading.max_position_size_pct,
            "max_daily_loss_pct": self.config.trading.max_daily_loss_pct,
            "max_weekly_loss_pct": self.config.trading.max_weekly_loss_pct,
            "max_drawdown_pct": self.config.trading.max_drawdown_pct,
            "correlation_threshold": self.config.risk_management.correlation_threshold,
        }
    
    def get_execution_params(self) -> Dict[str, Any]:
        """Get execution parameters."""
        return {
            "gas_strategy": self.config.execution.gas_strategy,
            "max_gas_price_gwei": self.config.execution.max_gas_price_gwei,
            "slippage_tolerance_pct": self.config.execution.slippage_tolerance_pct,
            "deadline_minutes": self.config.execution.deadline_minutes,
        }


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.config


def get_api_config(api_name: str) -> APIConfig:
    """Get API configuration."""
    return config_manager.get_api_config(api_name)


def get_strategy_config(strategy_name: str) -> StrategyConfig:
    """Get strategy configuration."""
    return config_manager.get_strategy_config(strategy_name)

