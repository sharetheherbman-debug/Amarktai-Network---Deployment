"""
Bot Performance Ranking System
- Ranks bots by performance metrics
- Identifies top and bottom performers
- Calculates Sharpe ratio, win rate, profit factor
"""

import asyncio
from datetime import datetime, timezone, timedelta
import database as db
from logger_config import logger
import math


class PerformanceRanker:
    def __init__(self):
        self.ranking_cache = {}
        self.last_rank_time = None
    
    async def rank_bots(self, user_id: str) -> list:
        """Rank all user's bots by performance"""
        try:
            bots = await db.bots_collection.find(
                {"user_id": user_id, "status": "active"},
                {"_id": 0}
            ).to_list(1000)
            
            ranked_bots = []
            for bot in bots:
                score = await self._calculate_performance_score(bot)
                ranked_bots.append({
                    **bot,
                    "performance_score": score
                })
            
            # Sort by performance score (descending)
            ranked_bots.sort(key=lambda x: x['performance_score'], reverse=True)
            
            # Add rank
            for idx, bot in enumerate(ranked_bots):
                bot['rank'] = idx + 1
            
            # Cache rankings
            self.ranking_cache[user_id] = {
                "rankings": ranked_bots,
                "timestamp": datetime.now(timezone.utc)
            }
            
            logger.info(f"Ranked {len(ranked_bots)} bots for user {user_id}")
            return ranked_bots
            
        except Exception as e:
            logger.error(f"Bot ranking failed: {e}")
            return []
    
    async def _calculate_performance_score(self, bot: dict) -> float:
        """Calculate composite performance score"""
        try:
            # Get bot's trades
            trades = await db.trades_collection.find(
                {"bot_id": bot['id']},
                {"_id": 0}
            ).to_list(1000)
            
            if not trades:
                return 0.0
            
            # 1. Win Rate (0-100)
            winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
            win_rate = (winning_trades / len(trades)) * 100
            
            # 2. Profit Factor (ratio of wins to losses)
            total_wins = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
            total_losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
            profit_factor = total_wins / total_losses if total_losses > 0 else total_wins
            
            # 3. Average profit per trade
            avg_profit = sum(t.get('pnl', 0) for t in trades) / len(trades)
            
            # 4. Sharpe Ratio (simplified)
            returns = [t.get('pnl', 0) for t in trades]
            mean_return = sum(returns) / len(returns)
            std_dev = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns))
            sharpe = mean_return / std_dev if std_dev > 0 else 0
            
            # 5. Total profit
            total_profit = bot.get('total_profit', 0)
            
            # Composite score (weighted)
            score = (
                win_rate * 0.25 +           # 25% weight on win rate
                profit_factor * 10 * 0.20 + # 20% weight on profit factor
                sharpe * 20 * 0.15 +        # 15% weight on Sharpe
                total_profit * 0.30 +       # 30% weight on total profit
                avg_profit * 100 * 0.10     # 10% weight on avg profit
            )
            
            return round(score, 2)
            
        except Exception as e:
            logger.error(f"Performance score calculation failed: {e}")
            return 0.0
    
    async def get_top_performers(self, user_id: str, limit: int = 5) -> list:
        """Get top N performing bots"""
        ranked = await self.rank_bots(user_id)
        return ranked[:limit]
    
    async def get_bottom_performers(self, user_id: str, limit: int = 5) -> list:
        """Get bottom N performing bots"""
        ranked = await self.rank_bots(user_id)
        return ranked[-limit:] if len(ranked) > limit else ranked


# Global instance
performance_ranker = PerformanceRanker()
