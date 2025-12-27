"""
Fractional Kelly Position Sizing
Implements optimal capital allocation using Kelly Criterion with fractional sizing for stability
Formula: f* = (bp - q) / b where p = win probability, q = loss probability, b = reward/risk ratio
Uses Fractional Kelly (0.25 × f*) to reduce variance and drawdown
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
import numpy as np

logger = logging.getLogger(__name__)


class FractionalKellyCalculator:
    """
    Calculates optimal position size using Fractional Kelly Criterion
    Caps exposure at 25% of full Kelly for stability
    """
    
    def __init__(
        self,
        kelly_fraction: float = 0.25,
        min_position_size: float = 0.01,
        max_position_size: float = 0.25
    ):
        """
        Initialize Kelly calculator
        
        Args:
            kelly_fraction: Fraction of full Kelly to use (default: 0.25 = 25%)
            min_position_size: Minimum position as fraction of capital (default: 1%)
            max_position_size: Maximum position as fraction of capital (default: 25%)
        """
        self.kelly_fraction = kelly_fraction
        self.min_position_size = min_position_size
        self.max_position_size = max_position_size
        
        logger.info(
            f"Fractional Kelly initialized: {kelly_fraction*100:.0f}% Kelly, "
            f"range {min_position_size*100:.1f}%-{max_position_size*100:.1f}%"
        )
    
    def calculate_position_size(
        self,
        capital: float,
        win_rate: float,
        reward_risk_ratio: float,
        confidence: float = 1.0
    ) -> Tuple[float, Dict]:
        """
        Calculate optimal position size using Fractional Kelly
        
        Args:
            capital: Available trading capital
            win_rate: Historical win rate (0.0 to 1.0)
            reward_risk_ratio: Expected reward/risk ratio (e.g., 2.0 = 2:1)
            confidence: Signal confidence multiplier (0.0 to 1.0)
            
        Returns:
            (position_size, metrics) where:
            - position_size: Dollar amount to risk
            - metrics: Dictionary with Kelly calculations
        """
        # Input validation
        if capital <= 0:
            logger.error("Capital must be positive")
            return 0.0, {'error': 'Invalid capital'}
        
        if not 0 <= win_rate <= 1:
            logger.error(f"Invalid win rate: {win_rate}")
            return 0.0, {'error': 'Invalid win rate'}
        
        if reward_risk_ratio <= 0:
            logger.error(f"Invalid reward/risk ratio: {reward_risk_ratio}")
            return 0.0, {'error': 'Invalid reward/risk ratio'}
        
        # Calculate Kelly fraction
        # f* = (bp - q) / b
        # where:
        # b = reward/risk ratio
        # p = win probability
        # q = loss probability = 1 - p
        
        p = win_rate  # Win probability
        q = 1 - p     # Loss probability
        b = reward_risk_ratio
        
        # Full Kelly formula
        full_kelly = (b * p - q) / b
        
        # Apply Kelly fraction for safety
        fractional_kelly = full_kelly * self.kelly_fraction
        
        # Apply confidence multiplier
        adjusted_kelly = fractional_kelly * confidence
        
        # Clamp to min/max bounds
        position_fraction = max(
            self.min_position_size,
            min(self.max_position_size, adjusted_kelly)
        )
        
        # Calculate position size in dollars
        position_size = capital * position_fraction
        
        # Build metrics
        metrics = {
            'full_kelly': full_kelly,
            'fractional_kelly': fractional_kelly,
            'adjusted_kelly': adjusted_kelly,
            'position_fraction': position_fraction,
            'position_size': position_size,
            'capital': capital,
            'win_rate': win_rate,
            'reward_risk_ratio': reward_risk_ratio,
            'confidence': confidence,
            'kelly_fraction_used': self.kelly_fraction,
            'clamped': adjusted_kelly != position_fraction
        }
        
        # Log if we're betting too aggressively
        if full_kelly > 0.5:
            logger.warning(
                f"Full Kelly very high: {full_kelly:.2%} "
                f"(using {position_fraction:.2%} after fraction & clamp)"
            )
        
        # Don't trade if Kelly is negative (negative edge)
        if full_kelly <= 0:
            logger.warning(
                f"Negative Kelly edge detected: {full_kelly:.2%} "
                f"(win rate: {win_rate:.2%}, R:R: {reward_risk_ratio:.2f})"
            )
            return 0.0, {**metrics, 'recommendation': 'no_trade', 'reason': 'negative_edge'}
        
        logger.debug(
            f"Kelly position: ${position_size:,.2f} ({position_fraction:.2%} of ${capital:,.2f})"
        )
        
        return position_size, metrics
    
    def calculate_from_bot_history(
        self,
        bot_stats: Dict,
        capital: float,
        confidence: float = 1.0
    ) -> Tuple[float, Dict]:
        """
        Calculate position size from bot's historical performance
        
        Args:
            bot_stats: Bot statistics with win_rate, avg_profit, avg_loss
            capital: Available capital
            confidence: Signal confidence
            
        Returns:
            (position_size, metrics)
        """
        # Extract stats
        win_rate = bot_stats.get('win_rate', 0.5)
        avg_profit = bot_stats.get('avg_profit', 0)
        avg_loss = bot_stats.get('avg_loss', 0)
        
        # Calculate reward/risk ratio
        if avg_loss == 0:
            reward_risk_ratio = 2.0  # Default if no loss history
        else:
            reward_risk_ratio = abs(avg_profit / avg_loss)
        
        # Ensure minimum viable stats
        min_trades = 20
        total_trades = bot_stats.get('total_trades', 0)
        
        if total_trades < min_trades:
            # Reduce confidence for insufficient data
            data_confidence = total_trades / min_trades
            confidence = confidence * data_confidence
            logger.info(
                f"Insufficient trade history ({total_trades}/{min_trades}), "
                f"reducing confidence to {confidence:.2%}"
            )
        
        return self.calculate_position_size(
            capital=capital,
            win_rate=win_rate,
            reward_risk_ratio=reward_risk_ratio,
            confidence=confidence
        )
    
    def adjust_for_market_conditions(
        self,
        position_size: float,
        regime_volatility: float,
        market_stress: float = 0.0
    ) -> Tuple[float, str]:
        """
        Adjust position size based on market conditions
        
        Args:
            position_size: Base position size
            regime_volatility: Current market volatility (0-1 scale)
            market_stress: Market stress indicator (0-1 scale)
            
        Returns:
            (adjusted_position_size, reason)
        """
        adjustment_factor = 1.0
        reasons = []
        
        # Reduce size in high volatility
        if regime_volatility > 0.05:  # 5% threshold
            vol_reduction = 1.0 - min(0.5, regime_volatility * 5)
            adjustment_factor *= vol_reduction
            reasons.append(f"volatility: {vol_reduction:.2%}")
        
        # Reduce size in market stress
        if market_stress > 0.3:  # 30% threshold
            stress_reduction = 1.0 - (market_stress * 0.5)
            adjustment_factor *= stress_reduction
            reasons.append(f"stress: {stress_reduction:.2%}")
        
        adjusted_size = position_size * adjustment_factor
        
        if reasons:
            reason = f"Adjusted by {adjustment_factor:.2%} due to {', '.join(reasons)}"
            logger.info(reason)
        else:
            reason = "No adjustment needed"
        
        return adjusted_size, reason
    
    def get_kelly_edge(self, win_rate: float, reward_risk_ratio: float) -> float:
        """
        Calculate Kelly edge (expected value per unit risked)
        
        Args:
            win_rate: Win probability
            reward_risk_ratio: Reward/risk ratio
            
        Returns:
            Kelly edge (positive = edge, negative = no edge)
        """
        p = win_rate
        q = 1 - p
        b = reward_risk_ratio
        
        return (b * p - q) / b
    
    def get_min_win_rate(self, reward_risk_ratio: float) -> float:
        """
        Calculate minimum win rate needed for positive edge
        
        Args:
            reward_risk_ratio: Reward/risk ratio
            
        Returns:
            Minimum win rate (0-1) needed for Kelly > 0
        """
        # From Kelly formula: (bp - q) / b > 0
        # Solving for p: p > q / b = (1-p) / b
        # p * b > 1 - p
        # p * (b + 1) > 1
        # p > 1 / (b + 1)
        
        return 1.0 / (reward_risk_ratio + 1)


# Global instance
kelly_calculator = FractionalKellyCalculator()
