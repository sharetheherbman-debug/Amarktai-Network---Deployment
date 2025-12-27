"""
Sentiment Analysis Module
Uses LLMs (DeepSeek/FinBERT) to extract sentiment from news and social media
Combines textual insights with quantitative signals
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class SentimentType(Enum):
    """Sentiment classification"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class NewsArticle:
    """News article data"""
    timestamp: datetime
    title: str
    content: str
    source: str
    url: str
    coins_mentioned: List[str]


@dataclass
class SentimentScore:
    """Sentiment analysis result"""
    timestamp: datetime
    text: str
    sentiment: SentimentType
    score: float  # -1.0 (very bearish) to 1.0 (very bullish)
    confidence: float
    keywords: List[str]
    source: str


@dataclass
class AggregatedSentiment:
    """Aggregated sentiment signal"""
    timestamp: datetime
    coin: str
    sentiment: SentimentType
    score: float
    confidence: float
    article_count: int
    key_topics: List[str]
    recommendation: str  # 'buy', 'sell', 'hold'


class SentimentAnalyzer:
    """
    Analyzes market sentiment from news and social media
    Provides trading signals based on textual sentiment
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize sentiment analyzer
        
        Args:
            openai_api_key: OpenAI API key for GPT-based analysis
        """
        self.openai_api_key = openai_api_key
        
        # Store analyzed content
        self.sentiment_history: Dict[str, List[SentimentScore]] = {}
        
        # News sources (simplified)
        self.news_sources = [
            'https://cryptonews.com',
            'https://cointelegraph.com',
            'https://decrypt.co'
        ]
        
        # Sentiment keywords
        self.bullish_keywords = [
            'bullish', 'surge', 'rally', 'breakout', 'moon', 'pump',
            'adoption', 'institutional', 'breakthrough', 'all-time high',
            'ATH', 'bull run', 'accumulation', 'upgrade', 'partnership'
        ]
        
        self.bearish_keywords = [
            'bearish', 'crash', 'dump', 'collapse', 'regulation',
            'ban', 'hack', 'scandal', 'investigation', 'fraud',
            'lawsuit', 'bankruptcy', 'bear market', 'correction'
        ]
    
    async def _call_openai(self, prompt: str) -> Optional[str]:
        """
        Call OpenAI API for sentiment analysis
        
        Args:
            prompt: Text to analyze
            
        Returns:
            AI response or None
        """
        if not self.openai_api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.openai_api_key}',
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a financial sentiment analyzer. Analyze the sentiment of crypto news and provide a score from -1 (very bearish) to 1 (very bullish).'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 100
                }
                
                async with session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
        
        return None
    
    def _keyword_based_sentiment(self, text: str) -> Tuple[float, List[str]]:
        """
        Calculate sentiment using keyword matching
        
        Args:
            text: Text to analyze
            
        Returns:
            (sentiment_score, matched_keywords)
        """
        text_lower = text.lower()
        
        # Count keyword matches
        bullish_matches = [kw for kw in self.bullish_keywords if kw in text_lower]
        bearish_matches = [kw for kw in self.bearish_keywords if kw in text_lower]
        
        # Calculate score
        bullish_count = len(bullish_matches)
        bearish_count = len(bearish_matches)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0, []
        
        score = (bullish_count - bearish_count) / total
        keywords = bullish_matches + bearish_matches
        
        return score, keywords
    
    async def analyze_text(
        self,
        text: str,
        source: str = "unknown",
        use_ai: bool = True
    ) -> SentimentScore:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            source: Source of text
            use_ai: Whether to use AI for analysis
            
        Returns:
            SentimentScore
        """
        # Keyword-based analysis (fallback)
        keyword_score, keywords = self._keyword_based_sentiment(text)
        
        # AI-based analysis (primary)
        ai_score = None
        if use_ai and self.openai_api_key:
            prompt = f"Analyze the sentiment of this crypto news (score from -1 to 1):\n\n{text[:500]}"
            ai_response = await self._call_openai(prompt)
            
            if ai_response:
                # Extract score from response
                try:
                    # Look for number between -1 and 1
                    numbers = re.findall(r'-?\d+\.?\d*', ai_response)
                    for num in numbers:
                        score_val = float(num)
                        if -1 <= score_val <= 1:
                            ai_score = score_val
                            break
                except:
                    pass
        
        # Use AI score if available, otherwise keyword score
        final_score = ai_score if ai_score is not None else keyword_score
        
        # Classify sentiment
        if final_score >= 0.6:
            sentiment = SentimentType.VERY_BULLISH
        elif final_score >= 0.2:
            sentiment = SentimentType.BULLISH
        elif final_score <= -0.6:
            sentiment = SentimentType.VERY_BEARISH
        elif final_score <= -0.2:
            sentiment = SentimentType.BEARISH
        else:
            sentiment = SentimentType.NEUTRAL
        
        # Confidence based on agreement between methods
        if ai_score is not None:
            agreement = 1.0 - abs(ai_score - keyword_score) / 2.0
            confidence = min(0.9, agreement)
        else:
            confidence = 0.5  # Lower confidence without AI
        
        result = SentimentScore(
            timestamp=datetime.now(timezone.utc),
            text=text[:200],
            sentiment=sentiment,
            score=final_score,
            confidence=confidence,
            keywords=keywords,
            source=source
        )
        
        return result
    
    async def fetch_news(self, coin: str = "BTC", limit: int = 10) -> List[NewsArticle]:
        """
        Fetch recent news articles (simulated for now)
        
        Args:
            coin: Cryptocurrency to fetch news for
            limit: Maximum number of articles
            
        Returns:
            List of NewsArticle
        """
        # In production, integrate with actual news APIs like:
        # - CryptoCompare News API
        # - NewsAPI
        # - CoinGecko News
        # - Twitter API for social sentiment
        
        # Simulated news for demonstration
        articles = []
        
        sample_news = [
            {
                'title': f'{coin} Price Surges on Institutional Adoption',
                'content': f'{coin} has seen significant institutional investment this week, with major funds announcing positions.',
                'source': 'CryptoNews'
            },
            {
                'title': f'Regulatory Concerns Impact {coin} Market',
                'content': f'New regulatory proposals have created uncertainty in the {coin} market, leading to volatility.',
                'source': 'CoinTelegraph'
            },
            {
                'title': f'{coin} Network Upgrade Completed Successfully',
                'content': f'The latest {coin} network upgrade has been implemented, improving scalability and efficiency.',
                'source': 'Decrypt'
            }
        ]
        
        for i, news in enumerate(sample_news[:limit]):
            article = NewsArticle(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                title=news['title'],
                content=news['content'],
                source=news['source'],
                url=f"https://example.com/article-{i}",
                coins_mentioned=[coin]
            )
            articles.append(article)
        
        return articles
    
    async def analyze_coin_sentiment(
        self,
        coin: str,
        hours: int = 24
    ) -> Optional[AggregatedSentiment]:
        """
        Analyze aggregated sentiment for a coin
        
        Args:
            coin: Cryptocurrency
            hours: Time window in hours
            
        Returns:
            AggregatedSentiment
        """
        # Fetch recent news
        articles = await self.fetch_news(coin, limit=20)
        
        if not articles:
            return None
        
        # Analyze each article
        sentiments = []
        for article in articles:
            text = f"{article.title}. {article.content}"
            sentiment = await self.analyze_text(text, source=article.source)
            sentiments.append(sentiment)
        
        # Store in history
        if coin not in self.sentiment_history:
            self.sentiment_history[coin] = []
        
        self.sentiment_history[coin].extend(sentiments)
        
        # Clean old history
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        self.sentiment_history[coin] = [
            s for s in self.sentiment_history[coin]
            if s.timestamp > cutoff
        ]
        
        # Aggregate sentiment
        recent = self.sentiment_history[coin]
        
        if not recent:
            return None
        
        avg_score = sum(s.score for s in recent) / len(recent)
        avg_confidence = sum(s.confidence for s in recent) / len(recent)
        
        # Classify aggregated sentiment
        if avg_score >= 0.5:
            agg_sentiment = SentimentType.VERY_BULLISH
            recommendation = 'buy'
        elif avg_score >= 0.2:
            agg_sentiment = SentimentType.BULLISH
            recommendation = 'buy'
        elif avg_score <= -0.5:
            agg_sentiment = SentimentType.VERY_BEARISH
            recommendation = 'sell'
        elif avg_score <= -0.2:
            agg_sentiment = SentimentType.BEARISH
            recommendation = 'sell'
        else:
            agg_sentiment = SentimentType.NEUTRAL
            recommendation = 'hold'
        
        # Extract key topics
        all_keywords = []
        for s in recent:
            all_keywords.extend(s.keywords)
        
        # Count keyword frequency
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        # Top 5 keywords
        key_topics = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        key_topics = [kw for kw, _ in key_topics]
        
        result = AggregatedSentiment(
            timestamp=datetime.now(timezone.utc),
            coin=coin,
            sentiment=agg_sentiment,
            score=avg_score,
            confidence=avg_confidence,
            article_count=len(recent),
            key_topics=key_topics,
            recommendation=recommendation
        )
        
        logger.info(
            f"Sentiment for {coin}: {agg_sentiment.value} "
            f"(score: {avg_score:.2f}, confidence: {avg_confidence:.2%}) "
            f"-> {recommendation}"
        )
        
        return result
    
    async def get_sentiment_summary(self) -> Dict[str, Dict]:
        """
        Get sentiment summary for all tracked coins
        
        Returns:
            Dictionary of coin -> sentiment summary
        """
        summary = {}
        
        for coin in ['BTC', 'ETH', 'USDT']:
            sentiment = await self.analyze_coin_sentiment(coin, hours=24)
            
            if sentiment:
                summary[coin] = {
                    'sentiment': sentiment.sentiment.value,
                    'score': sentiment.score,
                    'confidence': sentiment.confidence,
                    'article_count': sentiment.article_count,
                    'key_topics': sentiment.key_topics,
                    'recommendation': sentiment.recommendation,
                    'timestamp': sentiment.timestamp.isoformat()
                }
        
        return summary


# Global instance
sentiment_analyzer = SentimentAnalyzer()
