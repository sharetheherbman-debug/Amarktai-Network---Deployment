"""
Regime-Adaptive Intelligence Module
Uses Hidden Markov Models (HMM) and Gaussian Mixture Models (GMM) to detect market regimes
Identifies: Bullish/Calm, Bearish/Volatile, Squeeze states
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from hmmlearn import hmm
    from sklearn.mixture import GaussianMixture
    from scipy import stats
except ImportError:
    hmm = None
    GaussianMixture = None
    stats = None

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime states"""
    BULLISH_CALM = "bullish_calm"
    BEARISH_VOLATILE = "bearish_volatile"
    SQUEEZE = "squeeze"
    UNKNOWN = "unknown"


@dataclass
class RegimeState:
    """Current market regime state"""
    regime: MarketRegime
    confidence: float
    volatility: float
    trend_strength: float
    timestamp: datetime
    features: Dict[str, float]


class RegimeDetector:
    """
    Detects market regimes using statistical models (HMM, GMM)
    Adapts trading strategies based on detected market conditions
    """
    
    def __init__(self, n_regimes: int = 3, lookback_periods: int = 100):
        """
        Initialize regime detector
        
        Args:
            n_regimes: Number of market regimes to detect (default: 3)
            lookback_periods: Historical periods for training (default: 100)
        """
        self.n_regimes = n_regimes
        self.lookback_periods = lookback_periods
        self.price_history: Dict[str, List[Dict]] = {}
        self.current_regimes: Dict[str, RegimeState] = {}
        
        # Initialize models if libraries available
        if hmm is not None:
            self.hmm_model = hmm.GaussianHMM(
                n_components=n_regimes,
                covariance_type="full",
                n_iter=100,
                random_state=42
            )
        else:
            self.hmm_model = None
            logger.warning("hmmlearn not available, HMM features disabled")
        
        if GaussianMixture is not None:
            self.gmm_model = GaussianMixture(
                n_components=n_regimes,
                covariance_type='full',
                random_state=42
            )
        else:
            self.gmm_model = None
            logger.warning("sklearn not available, GMM features disabled")
    
    async def update_price_data(self, symbol: str, price: float, volume: float = 0) -> None:
        """
        Update price history for a symbol
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            volume: Current volume (optional)
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            'price': price,
            'volume': volume,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Keep only recent history
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self.price_history[symbol] = [
            p for p in self.price_history[symbol]
            if p['timestamp'] > cutoff
        ]
    
    def _extract_features(self, prices: np.ndarray) -> np.ndarray:
        """
        Extract features from price data for regime detection
        
        Features:
        1. Log returns
        2. Volatility (rolling std)
        3. Momentum (rate of change)
        4. Price z-score
        
        Args:
            prices: Array of prices
            
        Returns:
            Feature matrix (n_samples, n_features)
        """
        if len(prices) < 10:
            return np.array([])
        
        # Calculate log returns
        log_returns = np.diff(np.log(prices))
        
        # Calculate rolling volatility (std of returns)
        window = min(20, len(log_returns) // 2)
        volatility = np.array([
            np.std(log_returns[max(0, i-window):i+1])
            for i in range(len(log_returns))
        ])
        
        # Calculate momentum (rate of change)
        momentum = np.array([
            (prices[i] - prices[max(0, i-window)]) / prices[max(0, i-window)]
            if prices[max(0, i-window)] != 0 else 0
            for i in range(1, len(prices))
        ])
        
        # Calculate z-score of prices
        price_mean = np.mean(prices[:-1])
        price_std = np.std(prices[:-1])
        z_scores = (prices[1:] - price_mean) / (price_std if price_std != 0 else 1)
        
        # Combine features
        n_samples = min(len(log_returns), len(volatility), len(momentum), len(z_scores))
        features = np.column_stack([
            log_returns[-n_samples:],
            volatility[-n_samples:],
            momentum[-n_samples:],
            z_scores[-n_samples:]
        ])
        
        return features
    
    def _detect_with_hmm(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Detect regime using Hidden Markov Model
        
        Args:
            features: Feature matrix
            
        Returns:
            (regime_id, confidence)
        """
        if self.hmm_model is None or len(features) < 10:
            return -1, 0.0
        
        try:
            # Train or update HMM
            self.hmm_model.fit(features)
            
            # Predict current state
            hidden_states = self.hmm_model.predict(features)
            current_state = hidden_states[-1]
            
            # Calculate confidence from state probabilities
            state_probs = self.hmm_model.predict_proba(features)
            confidence = state_probs[-1, current_state]
            
            return int(current_state), float(confidence)
            
        except Exception as e:
            logger.error(f"HMM detection error: {e}")
            return -1, 0.0
    
    def _detect_with_gmm(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Detect regime using Gaussian Mixture Model
        
        Args:
            features: Feature matrix
            
        Returns:
            (regime_id, confidence)
        """
        if self.gmm_model is None or len(features) < 10:
            return -1, 0.0
        
        try:
            # Train GMM
            self.gmm_model.fit(features)
            
            # Predict current cluster
            current_cluster = self.gmm_model.predict(features[-1:])
            
            # Calculate confidence from posterior probabilities
            probs = self.gmm_model.predict_proba(features[-1:])
            confidence = probs[0, current_cluster[0]]
            
            return int(current_cluster[0]), float(confidence)
            
        except Exception as e:
            logger.error(f"GMM detection error: {e}")
            return -1, 0.0
    
    def _map_regime_to_state(
        self,
        regime_id: int,
        features: np.ndarray
    ) -> MarketRegime:
        """
        Map numerical regime ID to semantic market state
        
        Args:
            regime_id: Detected regime cluster ID
            features: Feature matrix for analysis
            
        Returns:
            MarketRegime enum
        """
        if regime_id < 0 or len(features) == 0:
            return MarketRegime.UNKNOWN
        
        # Analyze recent features
        recent_features = features[-10:]
        
        # Calculate regime characteristics
        avg_return = np.mean(recent_features[:, 0])  # Log returns
        avg_volatility = np.mean(recent_features[:, 1])  # Volatility
        avg_momentum = np.mean(recent_features[:, 2])  # Momentum
        
        # Classification logic
        # Bullish/Calm: Positive returns, low volatility
        if avg_return > 0 and avg_volatility < np.median(features[:, 1]):
            return MarketRegime.BULLISH_CALM
        
        # Bearish/Volatile: Negative returns, high volatility
        elif avg_return < 0 and avg_volatility > np.median(features[:, 1]):
            return MarketRegime.BEARISH_VOLATILE
        
        # Squeeze: Low volatility with unclear direction
        elif avg_volatility < np.percentile(features[:, 1], 25):
            return MarketRegime.SQUEEZE
        
        # Default based on momentum
        elif avg_momentum > 0:
            return MarketRegime.BULLISH_CALM
        else:
            return MarketRegime.BEARISH_VOLATILE
    
    async def detect_regime(self, symbol: str) -> Optional[RegimeState]:
        """
        Detect current market regime for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            RegimeState with detected regime and confidence
        """
        if symbol not in self.price_history:
            logger.warning(f"No price history for {symbol}")
            return None
        
        history = self.price_history[symbol]
        
        if len(history) < 20:
            logger.debug(f"Insufficient data for {symbol}: {len(history)} points")
            return RegimeState(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                volatility=0.0,
                trend_strength=0.0,
                timestamp=datetime.now(timezone.utc),
                features={}
            )
        
        # Extract prices
        prices = np.array([h['price'] for h in history])
        
        # Extract features
        features = self._extract_features(prices)
        
        if len(features) < 10:
            return None
        
        # Detect with HMM (primary method)
        hmm_regime, hmm_confidence = self._detect_with_hmm(features)
        
        # Detect with GMM (validation method)
        gmm_regime, gmm_confidence = self._detect_with_gmm(features)
        
        # Use HMM result if available, otherwise GMM
        regime_id = hmm_regime if hmm_regime >= 0 else gmm_regime
        confidence = max(hmm_confidence, gmm_confidence)
        
        # Map to semantic regime
        regime = self._map_regime_to_state(regime_id, features)
        
        # Calculate additional metrics
        recent_features = features[-10:]
        volatility = float(np.mean(recent_features[:, 1]))
        trend_strength = float(np.abs(np.mean(recent_features[:, 2])))
        
        regime_state = RegimeState(
            regime=regime,
            confidence=confidence,
            volatility=volatility,
            trend_strength=trend_strength,
            timestamp=datetime.now(timezone.utc),
            features={
                'avg_return': float(np.mean(recent_features[:, 0])),
                'avg_volatility': volatility,
                'avg_momentum': float(np.mean(recent_features[:, 2])),
                'z_score': float(recent_features[-1, 3])
            }
        )
        
        # Cache result
        self.current_regimes[symbol] = regime_state
        
        logger.info(
            f"Regime detected for {symbol}: {regime.value} "
            f"(confidence: {confidence:.2%}, volatility: {volatility:.4f})"
        )
        
        return regime_state
    
    def get_trading_parameters(self, regime_state: RegimeState) -> Dict[str, float]:
        """
        Get adaptive trading parameters based on regime
        
        Args:
            regime_state: Current market regime
            
        Returns:
            Dictionary of trading parameters
        """
        if regime_state.regime == MarketRegime.BULLISH_CALM:
            return {
                'position_size_multiplier': 1.2,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 5.0,
                'max_trades_per_day': 10,
                'confidence_threshold': 0.6
            }
        
        elif regime_state.regime == MarketRegime.BEARISH_VOLATILE:
            return {
                'position_size_multiplier': 0.5,
                'stop_loss_pct': 3.0,
                'take_profit_pct': 3.0,
                'max_trades_per_day': 5,
                'confidence_threshold': 0.75
            }
        
        elif regime_state.regime == MarketRegime.SQUEEZE:
            return {
                'position_size_multiplier': 0.7,
                'stop_loss_pct': 1.5,
                'take_profit_pct': 2.5,
                'max_trades_per_day': 8,
                'confidence_threshold': 0.65
            }
        
        else:  # UNKNOWN
            return {
                'position_size_multiplier': 0.8,
                'stop_loss_pct': 2.5,
                'take_profit_pct': 4.0,
                'max_trades_per_day': 7,
                'confidence_threshold': 0.7
            }
    
    async def get_regime_summary(self) -> Dict[str, Dict]:
        """
        Get summary of all tracked regimes
        
        Returns:
            Dictionary of symbol -> regime info
        """
        summary = {}
        
        for symbol, regime_state in self.current_regimes.items():
            summary[symbol] = {
                'regime': regime_state.regime.value,
                'confidence': regime_state.confidence,
                'volatility': regime_state.volatility,
                'trend_strength': regime_state.trend_strength,
                'timestamp': regime_state.timestamp.isoformat(),
                'features': regime_state.features,
                'trading_params': self.get_trading_parameters(regime_state)
            }
        
        return summary


# Global instance
regime_detector = RegimeDetector()
