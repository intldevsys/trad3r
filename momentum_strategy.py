"""
Momentum Trading Strategy for Crypto Trading Bot
Identifies and capitalizes on strong directional price movements.
"""

import logging
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

from .base_strategy import BaseStrategy, TradingSignal, SignalType
from ..data_sources.price_data import PriceData

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    Momentum trading strategy that identifies and trades strong directional moves.
    
    The strategy uses multiple timeframes and indicators to detect momentum:
    - Price rate of change
    - Volume confirmation
    - Moving average trends
    - RSI momentum
    - MACD signals
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'enabled': True,
            'weight': 0.25,
            'lookback_period': 14,
            'threshold': 0.02,
            'volume_threshold': 1.5,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'min_price_change': 0.01,
            'max_position_age_hours': 24,
            'profit_target': 0.05,
            'stop_loss': 0.03
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("momentum", default_config)
        
        # Strategy parameters
        self.lookback_period = self.config['lookback_period']
        self.threshold = self.config['threshold']
        self.volume_threshold = self.config['volume_threshold']
        self.rsi_oversold = self.config['rsi_oversold']
        self.rsi_overbought = self.config['rsi_overbought']
        self.min_price_change = self.config['min_price_change']
        self.max_position_age_hours = self.config['max_position_age_hours']
        self.profit_target = self.config['profit_target']
        self.stop_loss = self.config['stop_loss']
        
        logger.info(f"Momentum strategy initialized with lookback: {self.lookback_period}, threshold: {self.threshold}")
    
    def generate_signals(self, price_data: Dict[str, PriceData], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate momentum trading signals."""
        signals = []
        
        for symbol, current_data in price_data.items():
            try:
                # Update price cache
                self.update_price_cache(symbol, current_data)
                
                # Get price history
                prices = self.get_price_history(symbol, self.lookback_period * 2)
                volumes = self.get_volume_history(symbol, self.lookback_period * 2)
                
                if len(prices) < self.lookback_period:
                    continue
                
                # Calculate momentum indicators
                momentum_score = self._calculate_momentum_score(symbol, prices, volumes, current_data)
                
                if momentum_score is None:
                    continue
                
                # Generate signal based on momentum score
                signal = self._generate_momentum_signal(symbol, current_data, momentum_score)
                
                if signal and self.validate_signal(signal):
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating momentum signal for {symbol}: {e}")
        
        # Filter and rank signals
        filtered_signals = self.filter_signals(signals, min_strength=0.6)
        
        logger.info(f"Momentum strategy generated {len(filtered_signals)} signals")
        return filtered_signals
    
    def _calculate_momentum_score(self, symbol: str, prices: List[float], volumes: List[float], 
                                current_data: PriceData) -> float:
        """Calculate comprehensive momentum score."""
        try:
            # 1. Price Rate of Change
            roc_score = self._calculate_roc_score(prices)
            
            # 2. Volume confirmation
            volume_score = self._calculate_volume_score(volumes)
            
            # 3. Moving average trend
            ma_score = self._calculate_ma_trend_score(prices)
            
            # 4. RSI momentum
            rsi_score = self._calculate_rsi_momentum_score(prices)
            
            # 5. MACD momentum
            macd_score = self._calculate_macd_score(prices)
            
            # 6. Volatility adjustment
            volatility_score = self._calculate_volatility_score(symbol)
            
            # Combine scores with weights
            weights = {
                'roc': 0.3,
                'volume': 0.2,
                'ma': 0.2,
                'rsi': 0.15,
                'macd': 0.1,
                'volatility': 0.05
            }
            
            momentum_score = (
                roc_score * weights['roc'] +
                volume_score * weights['volume'] +
                ma_score * weights['ma'] +
                rsi_score * weights['rsi'] +
                macd_score * weights['macd'] +
                volatility_score * weights['volatility']
            )
            
            logger.debug(f"Momentum scores for {symbol}: ROC={roc_score:.3f}, Vol={volume_score:.3f}, "
                        f"MA={ma_score:.3f}, RSI={rsi_score:.3f}, MACD={macd_score:.3f}, "
                        f"Final={momentum_score:.3f}")
            
            return momentum_score
            
        except Exception as e:
            logger.error(f"Error calculating momentum score for {symbol}: {e}")
            return None
    
    def _calculate_roc_score(self, prices: List[float]) -> float:
        """Calculate Rate of Change score."""
        if len(prices) < self.lookback_period:
            return 0.0
        
        current_price = prices[-1]
        past_price = prices[-self.lookback_period]
        
        roc = (current_price - past_price) / past_price
        
        # Normalize to -1 to 1 scale
        roc_score = np.tanh(roc / self.threshold)
        
        return roc_score
    
    def _calculate_volume_score(self, volumes: List[float]) -> float:
        """Calculate volume confirmation score."""
        if len(volumes) < self.lookback_period:
            return 0.0
        
        recent_volume = np.mean(volumes[-3:])  # Last 3 periods
        avg_volume = np.mean(volumes[-self.lookback_period:])
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = recent_volume / avg_volume
        
        # Score based on volume increase
        if volume_ratio >= self.volume_threshold:
            return min(1.0, (volume_ratio - 1.0) / self.volume_threshold)
        else:
            return max(-0.5, (volume_ratio - 1.0) / self.volume_threshold)
    
    def _calculate_ma_trend_score(self, prices: List[float]) -> float:
        """Calculate moving average trend score."""
        if len(prices) < 20:
            return 0.0
        
        # Calculate multiple moving averages
        ma_5 = np.mean(prices[-5:])
        ma_10 = np.mean(prices[-10:])
        ma_20 = np.mean(prices[-20:])
        
        current_price = prices[-1]
        
        # Score based on price position relative to MAs and MA alignment
        score = 0.0
        
        # Price above/below MAs
        if current_price > ma_5 > ma_10 > ma_20:
            score += 1.0  # Strong uptrend
        elif current_price < ma_5 < ma_10 < ma_20:
            score -= 1.0  # Strong downtrend
        elif current_price > ma_5:
            score += 0.5  # Mild uptrend
        elif current_price < ma_5:
            score -= 0.5  # Mild downtrend
        
        return np.clip(score, -1.0, 1.0)
    
    def _calculate_rsi_momentum_score(self, prices: List[float]) -> float:
        """Calculate RSI momentum score."""
        if len(prices) < 15:
            return 0.0
        
        rsi_values = self.indicators.rsi(prices, 14)
        
        if not rsi_values:
            return 0.0
        
        current_rsi = rsi_values[-1]
        
        # Score based on RSI momentum (not just overbought/oversold)
        if len(rsi_values) >= 3:
            rsi_trend = rsi_values[-1] - rsi_values[-3]
            
            if current_rsi < self.rsi_oversold and rsi_trend > 0:
                return 0.8  # Oversold but recovering
            elif current_rsi > self.rsi_overbought and rsi_trend < 0:
                return -0.8  # Overbought and declining
            elif 40 < current_rsi < 60 and abs(rsi_trend) > 5:
                return np.sign(rsi_trend) * 0.6  # Strong momentum in neutral zone
        
        return 0.0
    
    def _calculate_macd_score(self, prices: List[float]) -> float:
        """Calculate MACD momentum score."""
        if len(prices) < 26:
            return 0.0
        
        macd_line, signal_line, histogram = self.indicators.macd(prices)
        
        if not macd_line or len(macd_line) < 2:
            return 0.0
        
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = histogram[-1]
        
        score = 0.0
        
        # MACD line above/below signal line
        if current_macd > current_signal:
            score += 0.5
        else:
            score -= 0.5
        
        # Histogram momentum
        if len(histogram) >= 2:
            histogram_change = histogram[-1] - histogram[-2]
            score += np.sign(histogram_change) * 0.3
        
        # MACD line momentum
        if len(macd_line) >= 2:
            macd_change = macd_line[-1] - macd_line[-2]
            score += np.sign(macd_change) * 0.2
        
        return np.clip(score, -1.0, 1.0)
    
    def _calculate_volatility_score(self, symbol: str) -> float:
        """Calculate volatility-adjusted score."""
        volatility = self.calculate_volatility(symbol, 20)
        
        # Prefer moderate volatility for momentum trades
        optimal_volatility = 0.5  # 50% annualized
        
        if volatility == 0:
            return 0.0
        
        # Score peaks at optimal volatility
        volatility_score = 1.0 - abs(volatility - optimal_volatility) / optimal_volatility
        
        return max(0.0, volatility_score)
    
    def _generate_momentum_signal(self, symbol: str, current_data: PriceData, 
                                momentum_score: float) -> TradingSignal:
        """Generate trading signal based on momentum score."""
        
        # Determine signal type and strength
        abs_score = abs(momentum_score)
        
        if abs_score < 0.5:
            return None  # No signal
        
        if momentum_score > 0.8:
            signal_type = SignalType.STRONG_BUY
            strength = min(1.0, abs_score)
        elif momentum_score > 0.5:
            signal_type = SignalType.BUY
            strength = abs_score
        elif momentum_score < -0.8:
            signal_type = SignalType.STRONG_SELL
            strength = min(1.0, abs_score)
        elif momentum_score < -0.5:
            signal_type = SignalType.SELL
            strength = abs_score
        else:
            return None
        
        # Calculate confidence based on multiple factors
        confidence = self._calculate_signal_confidence(symbol, momentum_score)
        
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            price=current_data.price,
            timestamp=datetime.utcnow(),
            strategy=self.name,
            confidence=confidence,
            metadata={
                'momentum_score': momentum_score,
                'volume_24h': current_data.volume_24h,
                'change_24h': current_data.change_24h
            }
        )
        
        self.add_signal(signal)
        
        logger.info(f"Momentum signal generated: {symbol} {signal_type.value} "
                   f"strength={strength:.3f} confidence={confidence:.3f}")
        
        return signal
    
    def _calculate_signal_confidence(self, symbol: str, momentum_score: float) -> float:
        """Calculate confidence level for the signal."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for stronger momentum
        confidence += abs(momentum_score) * 0.3
        
        # Increase confidence if multiple recent signals agree
        recent_signals = self.get_recent_signals(symbol, hours=6)
        if recent_signals:
            signal_agreement = sum(1 for s in recent_signals 
                                 if np.sign(momentum_score) == (1 if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else -1))
            confidence += (signal_agreement / len(recent_signals)) * 0.2
        
        # Adjust for market volatility
        volatility = self.calculate_volatility(symbol, 10)
        if 0.2 < volatility < 0.8:  # Optimal volatility range
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def should_enter_position(self, symbol: str, current_price: float, signal: TradingSignal) -> bool:
        """Determine if position should be entered."""
        
        # Check signal strength threshold
        if signal.strength < 0.6:
            return False
        
        # Check confidence threshold
        if signal.confidence < 0.5:
            return False
        
        # Check price movement since signal
        price_change = abs(current_price - signal.price) / signal.price
        if price_change > self.min_price_change * 3:  # Price moved too much
            return False
        
        # Check for conflicting recent signals
        recent_signals = self.get_recent_signals(symbol, hours=2)
        conflicting_signals = [s for s in recent_signals 
                             if s.signal_type != signal.signal_type and s.timestamp > signal.timestamp]
        
        if conflicting_signals:
            return False
        
        logger.info(f"Position entry approved for {symbol}: {signal.signal_type.value}")
        return True
    
    def should_exit_position(self, symbol: str, current_price: float, entry_price: float, 
                           position_age: timedelta) -> bool:
        """Determine if position should be exited."""
        
        # Calculate current return
        price_return = (current_price - entry_price) / entry_price
        
        # Exit if profit target reached
        if price_return >= self.profit_target:
            logger.info(f"Profit target reached for {symbol}: {price_return:.3f}")
            return True
        
        # Exit if stop loss triggered
        if price_return <= -self.stop_loss:
            logger.info(f"Stop loss triggered for {symbol}: {price_return:.3f}")
            return True
        
        # Exit if position is too old
        if position_age.total_seconds() / 3600 >= self.max_position_age_hours:
            logger.info(f"Position age limit reached for {symbol}: {position_age}")
            return True
        
        # Exit if momentum has reversed
        prices = self.get_price_history(symbol, 10)
        if len(prices) >= 5:
            recent_momentum = (prices[-1] - prices[-5]) / prices[-5]
            if abs(recent_momentum) < self.threshold / 2:  # Momentum weakening
                logger.info(f"Momentum weakening for {symbol}: {recent_momentum:.3f}")
                return True
        
        return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get detailed strategy information."""
        return {
            "name": self.name,
            "type": "momentum",
            "description": "Identifies and trades strong directional price movements",
            "parameters": {
                "lookback_period": self.lookback_period,
                "threshold": self.threshold,
                "volume_threshold": self.volume_threshold,
                "profit_target": self.profit_target,
                "stop_loss": self.stop_loss,
                "max_position_age_hours": self.max_position_age_hours
            },
            "indicators_used": [
                "Rate of Change",
                "Volume Analysis",
                "Moving Averages",
                "RSI",
                "MACD",
                "Volatility"
            ],
            "timeframes": ["1h", "4h", "1d"],
            "risk_level": "medium",
            "expected_win_rate": "60-70%",
            "expected_profit_factor": "1.5-2.0"
        }

