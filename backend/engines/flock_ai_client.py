"""
FLock.io API Integration
Replaces generic GPT calls with vertical-specific trading intelligence
Uses flock-trading-specialist-v1 model for domain-specific insights
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging
import os

logger = logging.getLogger(__name__)


class FlockAIClient:
    """
    FLock.io API client for trading-specific intelligence
    Vertical model: flock-trading-specialist-v1
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FLock.io API client
        
        Args:
            api_key: FLock.io API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("FLOCK_API_KEY")
        self.base_url = "https://api.flock.io/v1"
        self.model = "flock-trading-specialist-v1"
        self.timeout = 30
        
        if not self.api_key:
            logger.warning("FLock.io API key not configured - using fallback")
    
    async def get_trading_decision(
        self,
        market_data: Dict,
        regime_state: Optional[Dict] = None,
        ofi_signal: Optional[Dict] = None,
        whale_signal: Optional[Dict] = None,
        sentiment: Optional[Dict] = None
    ) -> Dict:
        """
        Get trading decision from FLock.io trading specialist
        
        Args:
            market_data: Current market conditions
            regime_state: Market regime from HMM/GMM
            ofi_signal: Order flow imbalance signal
            whale_signal: Whale activity signal
            sentiment: Market sentiment data
            
        Returns:
            Trading decision with reasoning
        """
        if not self.api_key:
            return self._fallback_decision(market_data)
        
        try:
            # Construct prompt with all available signals
            prompt = self._build_trading_prompt(
                market_data, regime_state, ofi_signal, whale_signal, sentiment
            )
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional cryptocurrency trading advisor with expertise in technical analysis, market microstructure, and risk management. Provide concise, actionable trading decisions based on multi-modal market signals."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        logger.error(f"FLock.io API error: {response.status}")
                        return self._fallback_decision(market_data)
                        
        except asyncio.TimeoutError:
            logger.error("FLock.io API timeout")
            return self._fallback_decision(market_data)
        except Exception as e:
            logger.error(f"FLock.io API error: {e}")
            return self._fallback_decision(market_data)
    
    def _build_trading_prompt(
        self,
        market_data: Dict,
        regime_state: Optional[Dict],
        ofi_signal: Optional[Dict],
        whale_signal: Optional[Dict],
        sentiment: Optional[Dict]
    ) -> str:
        """Build comprehensive trading prompt from all signals"""
        
        prompt_parts = [
            f"Symbol: {market_data.get('symbol', 'BTC/USDT')}",
            f"Current Price: ${market_data.get('price', 0):,.2f}",
            f"24h Volume: ${market_data.get('volume_24h', 0):,.0f}"
        ]
        
        # Add regime state if available
        if regime_state:
            prompt_parts.append(
                f"\nMarket Regime: {regime_state.get('regime', 'unknown')} "
                f"(confidence: {regime_state.get('confidence', 0):.0%})"
            )
            if 'volatility' in regime_state:
                prompt_parts.append(f"Volatility: {regime_state['volatility']:.4f}")
        
        # Add OFI signal if available
        if ofi_signal:
            prompt_parts.append(
                f"\nOrder Flow: {ofi_signal.get('recommendation', 'neutral')} "
                f"(strength: {ofi_signal.get('signal_strength', 0):+.2f})"
            )
        
        # Add whale signal if available
        if whale_signal:
            prompt_parts.append(
                f"\nWhale Activity: {whale_signal.get('signal', 'neutral')} "
                f"- {whale_signal.get('reason', 'No significant activity')}"
            )
        
        # Add sentiment if available
        if sentiment:
            prompt_parts.append(
                f"\nMarket Sentiment: {sentiment.get('sentiment', 'neutral')} "
                f"(confidence: {sentiment.get('confidence', 0):.0%})"
            )
            if 'key_topics' in sentiment:
                topics = ', '.join(sentiment['key_topics'][:3])
                prompt_parts.append(f"Key Topics: {topics}")
        
        prompt_parts.append(
            "\nBased on these signals, provide a trading recommendation (buy/sell/hold) "
            "with specific entry price, stop loss, and take profit levels. "
            "Include brief reasoning (max 2-3 sentences)."
        )
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: Dict) -> Dict:
        """Parse FLock.io API response into structured decision"""
        try:
            content = response['choices'][0]['message']['content']
            
            # Extract decision (buy/sell/hold)
            decision = 'hold'
            if 'buy' in content.lower() and 'don\'t buy' not in content.lower():
                decision = 'buy'
            elif 'sell' in content.lower() and 'don\'t sell' not in content.lower():
                decision = 'sell'
            
            return {
                'decision': decision,
                'reasoning': content,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'flock-trading-specialist-v1',
                'confidence': 0.75  # FLock.io provides high-quality vertical-specific advice
            }
            
        except Exception as e:
            logger.error(f"Error parsing FLock.io response: {e}")
            return {
                'decision': 'hold',
                'reasoning': 'Error parsing AI response',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'flock-fallback',
                'confidence': 0.0
            }
    
    def _fallback_decision(self, market_data: Dict) -> Dict:
        """Fallback decision when FLock.io is unavailable"""
        return {
            'decision': 'hold',
            'reasoning': 'FLock.io API unavailable - defaulting to hold',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'fallback',
            'confidence': 0.3
        }
    
    async def test_connection(self) -> bool:
        """Test FLock.io API connection"""
        if not self.api_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Test with minimal request
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "Test connection"}
                    ],
                    "max_tokens": 10
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"FLock.io connection test failed: {e}")
            return False


# Global instance
flock_client = FlockAIClient()
