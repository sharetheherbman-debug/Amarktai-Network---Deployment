"""
Chandelier Exits - ATR-Based Dynamic Stop Losses
Implements volatility-adjusted stops using Average True Range (ATR)
Formula: StopLoss_Long = HighestHigh_period - (ATR × multiplier)
         StopLoss_Short = LowestLow_period + (ATR × multiplier)
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class ChandelierExits:
    """
    Dynamic stop losses based on ATR (Average True Range)
    Adapts to market volatility automatically
    """
    
    def __init__(
        self,
        atr_period: int = 14,
        atr_multiplier: float = 3.0,
        lookback_period: int = 20
    ):
        """
        Initialize Chandelier Exits calculator
        
        Args:
            atr_period: Period for ATR calculation (default: 14)
            atr_multiplier: Multiplier for ATR distance (default: 3.0)
            lookback_period: Period for highest high/lowest low (default: 20)
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.lookback_period = lookback_period
        
        # Store price history per symbol
        self.price_history: Dict[str, deque] = {}
        
        logger.info(
            f"Chandelier Exits initialized: ATR({atr_period}) × {atr_multiplier}, "
            f"lookback {lookback_period}"
        )
    
    def add_price_data(
        self,
        symbol: str,
        high: float,
        low: float,
        close: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Add price data for ATR calculation
        
        Args:
            symbol: Trading pair
            high: Period high price
            low: Period low price
            close: Period close price
            timestamp: Data timestamp
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=max(self.atr_period, self.lookback_period) + 1)
        
        self.price_history[symbol].append({
            'high': high,
            'low': low,
            'close': close,
            'timestamp': timestamp or datetime.now(timezone.utc)
        })
    
    def calculate_atr(self, symbol: str) -> Optional[float]:
        """
        Calculate Average True Range for symbol
        
        Args:
            symbol: Trading pair
            
        Returns:
            ATR value or None if insufficient data
        """
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        
        if len(history) < self.atr_period + 1:
            logger.debug(f"Insufficient data for ATR: {len(history)} < {self.atr_period + 1}")
            return None
        
        # Calculate True Range for each period
        true_ranges = []
        
        for i in range(1, len(history)):
            current = history[i]
            previous = history[i-1]
            
            # True Range = max(high-low, |high-prevClose|, |low-prevClose|)
            tr = max(
                current['high'] - current['low'],
                abs(current['high'] - previous['close']),
                abs(current['low'] - previous['close'])
            )
            
            true_ranges.append(tr)
        
        # Average True Range = average of last N true ranges
        if len(true_ranges) < self.atr_period:
            return None
        
        atr = np.mean(true_ranges[-self.atr_period:])
        
        return atr
    
    def calculate_stop_loss(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        custom_multiplier: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Calculate Chandelier Exit stop loss level
        
        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            entry_price: Entry price for the position
            custom_multiplier: Override default ATR multiplier
            
        Returns:
            Dictionary with stop loss details or None
        """
        if symbol not in self.price_history:
            logger.warning(f"No price history for {symbol}")
            return None
        
        history = list(self.price_history[symbol])
        
        if len(history) < self.lookback_period:
            logger.debug(f"Insufficient data for Chandelier: {len(history)} < {self.lookback_period}")
            return None
        
        # Calculate ATR
        atr = self.calculate_atr(symbol)
        
        if atr is None:
            return None
        
        multiplier = custom_multiplier or self.atr_multiplier
        
        # Get recent high/low
        recent_candles = history[-self.lookback_period:]
        
        if side.lower() == 'long':
            # Long position: Stop = Highest High - (ATR × multiplier)
            highest_high = max(c['high'] for c in recent_candles)
            stop_loss = highest_high - (atr * multiplier)
            
            # Ensure stop is below entry
            if stop_loss >= entry_price:
                # Fallback: use entry - ATR
                stop_loss = entry_price - (atr * multiplier)
                logger.warning(
                    f"Chandelier stop above entry for long, using fallback: "
                    f"${stop_loss:.2f}"
                )
            
            reference_level = highest_high
            
        elif side.lower() == 'short':
            # Short position: Stop = Lowest Low + (ATR × multiplier)
            lowest_low = min(c['low'] for c in recent_candles)
            stop_loss = lowest_low + (atr * multiplier)
            
            # Ensure stop is above entry
            if stop_loss <= entry_price:
                # Fallback: use entry + ATR
                stop_loss = entry_price + (atr * multiplier)
                logger.warning(
                    f"Chandelier stop below entry for short, using fallback: "
                    f"${stop_loss:.2f}"
                )
            
            reference_level = lowest_low
            
        else:
            logger.error(f"Invalid side: {side}")
            return None
        
        # Calculate stop distance
        stop_distance = abs(entry_price - stop_loss)
        stop_distance_pct = (stop_distance / entry_price) * 100
        
        result = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'stop_distance': stop_distance,
            'stop_distance_pct': stop_distance_pct,
            'atr': atr,
            'atr_multiplier': multiplier,
            'reference_level': reference_level,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"Chandelier stop for {side} {symbol}: "
            f"${stop_loss:.2f} ({stop_distance_pct:.2f}% from entry), "
            f"ATR: ${atr:.2f}"
        )
        
        return result
    
    def calculate_trailing_stop(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        current_price: float,
        previous_stop: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Calculate trailing Chandelier Exit that moves with price
        
        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            entry_price: Original entry price
            current_price: Current market price
            previous_stop: Previous stop loss level
            
        Returns:
            Dictionary with trailing stop details
        """
        # Calculate new stop based on current price levels
        stop_data = self.calculate_stop_loss(symbol, side, entry_price)
        
        if stop_data is None:
            return None
        
        new_stop = stop_data['stop_loss']
        
        # Apply trailing logic
        if previous_stop is not None:
            if side.lower() == 'long':
                # For long: stop can only move up, never down
                trailing_stop = max(new_stop, previous_stop)
                moved = trailing_stop > previous_stop
            else:
                # For short: stop can only move down, never up
                trailing_stop = min(new_stop, previous_stop)
                moved = trailing_stop < previous_stop
        else:
            trailing_stop = new_stop
            moved = False
        
        # Check if stop was hit
        if side.lower() == 'long':
            stop_hit = current_price <= trailing_stop
        else:
            stop_hit = current_price >= trailing_stop
        
        result = {
            **stop_data,
            'current_price': current_price,
            'trailing_stop': trailing_stop,
            'previous_stop': previous_stop,
            'stop_moved': moved,
            'stop_hit': stop_hit,
            'unrealized_pnl': current_price - entry_price if side.lower() == 'long' else entry_price - current_price,
            'unrealized_pnl_pct': ((current_price / entry_price) - 1) * 100 if side.lower() == 'long' else ((entry_price / current_price) - 1) * 100
        }
        
        if stop_hit:
            logger.warning(
                f"STOP HIT for {side} {symbol}: "
                f"Price ${current_price:.2f} crossed stop ${trailing_stop:.2f}"
            )
        
        if moved:
            logger.info(
                f"Trailing stop moved for {side} {symbol}: "
                f"${previous_stop:.2f} → ${trailing_stop:.2f}"
            )
        
        return result
    
    def get_atr_stats(self, symbol: str) -> Optional[Dict]:
        """
        Get ATR statistics for a symbol
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with ATR stats
        """
        atr = self.calculate_atr(symbol)
        
        if atr is None:
            return None
        
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        
        if not history:
            return None
        
        current_price = history[-1]['close']
        atr_pct = (atr / current_price) * 100
        
        # Calculate ATR over different periods for comparison
        recent_highs = [c['high'] for c in history[-self.lookback_period:]]
        recent_lows = [c['low'] for c in history[-self.lookback_period:]]
        
        return {
            'symbol': symbol,
            'atr': atr,
            'atr_pct': atr_pct,
            'current_price': current_price,
            'period': self.atr_period,
            'highest_high': max(recent_highs) if recent_highs else None,
            'lowest_low': min(recent_lows) if recent_lows else None,
            'data_points': len(history),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global instance
chandelier_exits = ChandelierExits()
