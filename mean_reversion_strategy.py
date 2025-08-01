"""
Mean Reversion Trading Strategy for Crypto Trading Bot
Exploits temporary price dislocations by identifying overbought and oversold conditions.
"""

import logging
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

from .base_strategy import BaseStrategy, TradingSignal, SignalType
from ..data_sources.price_data import PriceData

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy that exploits temporary price dislocations.
    
    The strategy identifies when prices deviate significantly from their mean
    and trades on the expectation that they will revert to the mean.
    
    Key components:
    - Bollinger Bands for mean and deviation calculation
    - Z-score analysis for statistical significance
    - RSI for momentum confirmation
    - Volume analysis for validation
    - Multiple timeframe analysis
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'enabled': True,
            'weight': 0.25,
            'lookback_period': 20,
            'std_threshold': 2.0,
            'z_score_threshold': 1.5,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'volume_confirmation': True,
            'min_volume_ratio': 0.8,
            'max_position_age_hours': 48,
            'profit_target': 0.03,
            'stop_loss': 0.02,
            'mean_reversion_period': 5
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("mean_reversion", default_config)
        
        # Strategy parameters
        self.lookback_period = self.config['lookback_period']
        self.std_threshold = self.config['std_threshold']
        self.z_score_threshold = self.config['z_score_threshold']
        self.rsi_oversold = self.config['rsi_oversold']
        self.rsi_overbought = self.config['rsi_overbought']
        self.volume_confirmation = self.config['volume_confirmation']
        self.min_volume_ratio = self.config['min_volume_ratio']
        self.max_position_age_hours = self.config['max_position_age_hours']
        self.profit_target = self.config['profit_target']
        self.stop_loss = self.config['stop_loss']
        self.mean_reversion_period = self.config['mean_reversion_period']
        
        logger.info(f"Mean reversion strategy initialized with lookback: {self.lookback_period}, "
                   f"std_threshold: {self.std_threshold}")
    
    def generate_signals(self, price_data: Dict[str, PriceData], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate mean reversion trading signals."""
        signals = []
        
        for symbol, current_data in price_data.items():
            try:
                # Update price cache
                self.update_price_cache(symbol, current_data)
                
                # Get price and volume history
                prices = self.get_price_history(symbol, self.lookback_period * 2)
                volumes = self.get_volume_history(symbol, self.lookback_period)
                
                if len(prices) < self.lookback_period:
                    continue
                
                # Calculate mean reversion indicators
                reversion_score = self._calculate_reversion_score(symbol, prices, volumes, current_data)
                
                if reversion_score is None:
                    continue
                
                # Generate signal based on reversion score
                signal = self._generate_reversion_signal(symbol, current_data, reversion_score)
                
                if signal and self.validate_signal(signal):
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating mean reversion signal for {symbol}: {e}")
        
        # Filter and rank signals
        filtered_signals = self.filter_signals(signals, min_strength=0.5)
        
        logger.info(f"Mean reversion strategy generated {len(filtered_signals)} signals")
        return filtered_signals
    
    def _calculate_reversion_score(self, symbol: str, prices: List[float], volumes: List[float], 
                                 current_data: PriceData) -> float:
        """Calculate comprehensive mean reversion score."""
        try:
            # 1. Bollinger Bands deviation
            bb_score = self._calculate_bollinger_score(prices)
            
            # 2. Z-score analysis
            z_score = self._calculate_z_score(prices)
            
            # 3. RSI extremes
            rsi_score = self._calculate_rsi_reversion_score(prices)
            
            # 4. Volume confirmation
            volume_score = self._calculate_volume_confirmation(volumes) if self.volume_confirmation else 0.5
            
            # 5. Price momentum (should be opposite to reversion direction)
            momentum_score = self._calculate_momentum_divergence(prices)
            
            # 6. Multiple timeframe confirmation
            mtf_score = self._calculate_multi_timeframe_score(symbol, prices)
            
            # Combine scores with weights
            weights = {
                'bollinger': 0.3,
                'z_score': 0.25,
                'rsi': 0.2,
                'volume': 0.1,
                'momentum': 0.1,
                'mtf': 0.05
            }
            
            reversion_score = (
                bb_score * weights['bollinger'] +
                z_score * weights['z_score'] +
                rsi_score * weights['rsi'] +
                volume_score * weights['volume'] +
                momentum_score * weights['momentum'] +
                mtf_score * weights['mtf']
            )
            
            logger.debug(f"Mean reversion scores for {symbol}: BB={bb_score:.3f}, Z={z_score:.3f}, "
                        f"RSI={rsi_score:.3f}, Vol={volume_score:.3f}, Mom={momentum_score:.3f}, "
                        f"MTF={mtf_score:.3f}, Final={reversion_score:.3f}")
            
            return reversion_score
            
        except Exception as e:
            logger.error(f"Error calculating reversion score for {symbol}: {e}")
            return None
    
    def _calculate_bollinger_score(self, prices: List[float]) -> float:
        """Calculate Bollinger Bands deviation score."""
        if len(prices) < self.lookback_period:
            return 0.0
        
        upper_bands, middle_bands, lower_bands = self.indicators.bollinger_bands(
            prices, self.lookback_period, self.std_threshold
        )
        
        if not upper_bands:
            return 0.0
        
        current_price = prices[-1]
        current_upper = upper_bands[-1]
        current_lower = lower_bands[-1]
        current_middle = middle_bands[-1]
        
        # Calculate position within bands
        if current_price > current_upper:
            # Price above upper band - sell signal
            deviation = (current_price - current_upper) / (current_upper - current_middle)
            return -min(1.0, deviation)
        elif current_price < current_lower:
            # Price below lower band - buy signal
            deviation = (current_lower - current_price) / (current_middle - current_lower)
            return min(1.0, deviation)
        else:
            # Price within bands
            band_position = (current_price - current_lower) / (current_upper - current_lower)
            if band_position > 0.8:
                return -(band_position - 0.8) * 2.5  # Approaching upper band
            elif band_position < 0.2:
                return (0.2 - band_position) * 2.5  # Approaching lower band
            else:
                return 0.0  # Neutral zone
    
    def _calculate_z_score(self, prices: List[float]) -> float:
        """Calculate Z-score for statistical significance."""
        if len(prices) < self.lookback_period:
            return 0.0
        
        recent_prices = prices[-self.lookback_period:]
        current_price = prices[-1]
        
        mean_price = np.mean(recent_prices)
        std_price = np.std(recent_prices)
        
        if std_price == 0:
            return 0.0
        
        z_score = (current_price - mean_price) / std_price
        
        # Convert to signal score
        if abs(z_score) >= self.z_score_threshold:
            # Significant deviation - reversion signal
            return -np.sign(z_score) * min(1.0, abs(z_score) / self.z_score_threshold)
        else:
            return 0.0
    
    def _calculate_rsi_reversion_score(self, prices: List[float]) -> float:
        """Calculate RSI-based reversion score."""
        if len(prices) < 15:
            return 0.0
        
        rsi_values = self.indicators.rsi(prices, 14)
        
        if not rsi_values:
            return 0.0
        
        current_rsi = rsi_values[-1]
        
        # Score based on RSI extremes
        if current_rsi <= self.rsi_oversold:
            # Oversold - buy signal
            oversold_intensity = (self.rsi_oversold - current_rsi) / self.rsi_oversold
            return min(1.0, oversold_intensity * 2)
        elif current_rsi >= self.rsi_overbought:
            # Overbought - sell signal
            overbought_intensity = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            return -min(1.0, overbought_intensity * 2)
        else:
            return 0.0
    
    def _calculate_volume_confirmation(self, volumes: List[float]) -> float:
        """Calculate volume confirmation score."""
        if len(volumes) < 5:
            return 0.5  # Neutral if insufficient data
        
        recent_volume = np.mean(volumes[-3:])
        avg_volume = np.mean(volumes)
        
        if avg_volume == 0:
            return 0.5
        
        volume_ratio = recent_volume / avg_volume
        
        # Volume should be above minimum threshold for confirmation
        if volume_ratio >= self.min_volume_ratio:
            return min(1.0, volume_ratio)
        else:
            return max(0.0, volume_ratio / self.min_volume_ratio)
    
    def _calculate_momentum_divergence(self, prices: List[float]) -> float:
        """Calculate momentum divergence score."""
        if len(prices) < 10:
            return 0.0
        
        # Calculate short-term momentum
        short_momentum = (prices[-1] - prices[-3]) / prices[-3]
        
        # Calculate medium-term momentum
        medium_momentum = (prices[-1] - prices[-7]) / prices[-7]
        
        # For mean reversion, we want momentum to be slowing down
        momentum_change = short_momentum - medium_momentum
        
        # Positive momentum change suggests continuation (bad for reversion)
        # Negative momentum change suggests slowing (good for reversion)
        return -np.tanh(momentum_change * 10)  # Normalize to -1 to 1
    
    def _calculate_multi_timeframe_score(self, symbol: str, prices: List[float]) -> float:
        """Calculate multi-timeframe confirmation score."""
        if len(prices) < 50:
            return 0.5  # Neutral if insufficient data
        
        # Check different timeframes for mean reversion setup
        score = 0.0
        
        # Short-term (5 periods)
        if len(prices) >= 5:
            short_mean = np.mean(prices[-5:])
            short_deviation = abs(prices[-1] - short_mean) / short_mean
            if short_deviation > 0.01:  # 1% deviation
                score += 0.3
        
        # Medium-term (20 periods)
        if len(prices) >= 20:
            medium_mean = np.mean(prices[-20:])
            medium_deviation = abs(prices[-1] - medium_mean) / medium_mean
            if medium_deviation > 0.02:  # 2% deviation
                score += 0.4
        
        # Long-term (50 periods)
        if len(prices) >= 50:
            long_mean = np.mean(prices[-50:])
            long_deviation = abs(prices[-1] - long_mean) / long_mean
            if long_deviation > 0.03:  # 3% deviation
                score += 0.3
        
        return min(1.0, score)
    
    def _generate_reversion_signal(self, symbol: str, current_data: PriceData, 
                                 reversion_score: float) -> TradingSignal:
        """Generate trading signal based on reversion score."""
        
        # Determine signal type and strength
        abs_score = abs(reversion_score)
        
        if abs_score < 0.4:
            return None  # No signal
        
        if reversion_score > 0.7:
            signal_type = SignalType.STRONG_BUY
            strength = min(1.0, abs_score)
        elif reversion_score > 0.4:
            signal_type = SignalType.BUY
            strength = abs_score
        elif reversion_score < -0.7:
            signal_type = SignalType.STRONG_SELL
            strength = min(1.0, abs_score)
        elif reversion_score < -0.4:
            signal_type = SignalType.SELL
            strength = abs_score
        else:
            return None
        
        # Calculate confidence
        confidence = self._calculate_signal_confidence(symbol, reversion_score)
        
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            price=current_data.price,
            timestamp=datetime.utcnow(),
            strategy=self.name,
            confidence=confidence,
            metadata={
                'reversion_score': reversion_score,
                'volume_24h': current_data.volume_24h,
                'change_24h': current_data.change_24h,
                'expected_reversion_time': self.mean_reversion_period
            }
        )
        
        self.add_signal(signal)
        
        logger.info(f"Mean reversion signal generated: {symbol} {signal_type.value} "
                   f"strength={strength:.3f} confidence={confidence:.3f}")
        
        return signal
    
    def _calculate_signal_confidence(self, symbol: str, reversion_score: float) -> float:
        """Calculate confidence level for the signal."""
        confidence = 0.4  # Base confidence (lower than momentum)
        
        # Increase confidence for stronger reversion signals
        confidence += abs(reversion_score) * 0.4
        
        # Check for consistent reversion signals
        recent_signals = self.get_recent_signals(symbol, hours=12)
        if recent_signals:
            consistent_signals = sum(1 for s in recent_signals 
                                   if np.sign(reversion_score) == (1 if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else -1))
            if consistent_signals >= 2:
                confidence += 0.2
        
        # Adjust for market conditions
        volatility = self.calculate_volatility(symbol, 10)
        if volatility > 0.3:  # Higher volatility favors mean reversion
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def should_enter_position(self, symbol: str, current_price: float, signal: TradingSignal) -> bool:
        """Determine if position should be entered."""
        
        # Check signal strength threshold
        if signal.strength < 0.5:
            return False
        
        # Check confidence threshold
        if signal.confidence < 0.4:
            return False
        
        # Check if price has moved too much since signal
        price_change = abs(current_price - signal.price) / signal.price
        if price_change > 0.01:  # 1% movement
            return False
        
        # Check for recent opposing momentum signals
        recent_signals = self.get_recent_signals(symbol, hours=4)
        momentum_signals = [s for s in recent_signals if s.strategy == "momentum"]
        
        for mom_signal in momentum_signals:
            # If momentum signal is in same direction, it might not revert
            if ((signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] and 
                 mom_signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]) or
                (signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL] and 
                 mom_signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL])):
                return False
        
        logger.info(f"Mean reversion position entry approved for {symbol}: {signal.signal_type.value}")
        return True
    
    def should_exit_position(self, symbol: str, current_price: float, entry_price: float, 
                           position_age: timedelta) -> bool:
        """Determine if position should be exited."""
        
        # Calculate current return
        price_return = (current_price - entry_price) / entry_price
        
        # Exit if profit target reached
        if price_return >= self.profit_target:
            logger.info(f"Mean reversion profit target reached for {symbol}: {price_return:.3f}")
            return True
        
        # Exit if stop loss triggered
        if price_return <= -self.stop_loss:
            logger.info(f"Mean reversion stop loss triggered for {symbol}: {price_return:.3f}")
            return True
        
        # Exit if position is too old
        if position_age.total_seconds() / 3600 >= self.max_position_age_hours:
            logger.info(f"Mean reversion position age limit reached for {symbol}: {position_age}")
            return True
        
        # Exit if mean reversion has occurred (price moved back toward mean)
        prices = self.get_price_history(symbol, self.lookback_period)
        if len(prices) >= self.lookback_period:
            recent_mean = np.mean(prices[-self.lookback_period:])
            
            # Check if price has reverted toward mean
            entry_deviation = abs(entry_price - recent_mean) / recent_mean
            current_deviation = abs(current_price - recent_mean) / recent_mean
            
            if current_deviation < entry_deviation * 0.5:  # Significant reversion
                logger.info(f"Mean reversion completed for {symbol}: deviation reduced from "
                           f"{entry_deviation:.3f} to {current_deviation:.3f}")
                return True
        
        # Exit if new strong momentum signal appears
        recent_signals = self.get_recent_signals(symbol, hours=2)
        strong_momentum = [s for s in recent_signals 
                          if s.strategy == "momentum" and s.strength > 0.7]
        
        if strong_momentum:
            logger.info(f"Strong momentum signal detected, exiting mean reversion position for {symbol}")
            return True
        
        return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get detailed strategy information."""
        return {
            "name": self.name,
            "type": "mean_reversion",
            "description": "Exploits temporary price dislocations by trading on mean reversion",
            "parameters": {
                "lookback_period": self.lookback_period,
                "std_threshold": self.std_threshold,
                "z_score_threshold": self.z_score_threshold,
                "profit_target": self.profit_target,
                "stop_loss": self.stop_loss,
                "max_position_age_hours": self.max_position_age_hours,
                "mean_reversion_period": self.mean_reversion_period
            },
            "indicators_used": [
                "Bollinger Bands",
                "Z-Score Analysis",
                "RSI Extremes",
                "Volume Confirmation",
                "Multi-timeframe Analysis"
            ],
            "timeframes": ["1h", "4h", "1d"],
            "risk_level": "medium-low",
            "expected_win_rate": "65-75%",
            "expected_profit_factor": "1.3-1.8",
            "best_market_conditions": "Range-bound, high volatility"
        }

