"""
Self-Learning System - Adaptive Parameter Tuning
- Learns from winning/losing trades
- Adjusts bot parameters automatically
- Uses AI for pattern recognition
- Logs all adjustments for transparency
"""

import asyncio
from typing import Dict, List
from datetime import datetime, timezone, timedelta
import logging
from statistics import mean, stdev

import database as db
from engines.ai_model_router import ai_model_router

logger = logging.getLogger(__name__)

class SelfLearningEngine:
    def __init__(self):
        self.learning_enabled = True
        self.min_trades_for_learning = 10  # Need at least 10 trades to learn
        self.adjustment_threshold = 0.15    # 15% improvement needed to adjust
        
        # Parameter adjustment ranges
        self.param_ranges = {
            'trade_size_multiplier': (0.7, 1.3),    # Can adjust ±30%
            'cooldown_multiplier': (0.8, 1.5),      # Can adjust ±50%
            'stop_loss_pct': (0.01, 0.05),          # 1-5% stop loss
            'take_profit_pct': (0.02, 0.10)         # 2-10% take profit
        }
    
    async def analyze_bot_performance(self, bot_id: str) -> Dict:
        """Analyze bot's recent performance for learning"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            
            if not bot:
                return {"error": "Bot not found"}
            
            # Get recent trades (last 30 days or 50 trades, whichever is less)
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            recent_trades = await db.trades_collection.find(
                {
                    "bot_id": bot_id,
                    "timestamp": {"$gte": thirty_days_ago}
                },
                {"_id": 0}
            ).sort("timestamp", -1).limit(50).to_list(50)
            
            if len(recent_trades) < self.min_trades_for_learning:
                return {
                    "status": "insufficient_data",
                    "trades_count": len(recent_trades),
                    "min_required": self.min_trades_for_learning
                }
            
            # Calculate metrics
            wins = [t for t in recent_trades if t.get('profit_loss', 0) > 0]
            losses = [t for t in recent_trades if t.get('profit_loss', 0) < 0]
            
            win_rate = (len(wins) / len(recent_trades)) * 100 if recent_trades else 0
            
            avg_win = mean([t['profit_loss'] for t in wins]) if wins else 0
            avg_loss = mean([t['profit_loss'] for t in losses]) if losses else 0
            
            total_profit = sum(t.get('profit_loss', 0) for t in recent_trades)
            
            # Identify patterns
            patterns = await self.identify_patterns(recent_trades)
            
            return {
                "bot_id": bot_id,
                "bot_name": bot.get('name'),
                "trades_analyzed": len(recent_trades),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "total_profit": total_profit,
                "win_loss_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
                "patterns": patterns,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance analysis error: {e}")
            return {"error": str(e)}
    
    async def identify_patterns(self, trades: List[Dict]) -> Dict:
        """Identify patterns in winning/losing trades"""
        try:
            if not trades:
                return {}
            
            wins = [t for t in trades if t.get('profit_loss', 0) > 0]
            losses = [t for t in trades if t.get('profit_loss', 0) < 0]
            
            patterns = {}
            
            # Time-of-day pattern
            winning_hours = [datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')).hour for t in wins]
            losing_hours = [datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')).hour for t in losses]
            
            if winning_hours:
                patterns['best_trading_hours'] = max(set(winning_hours), key=winning_hours.count)
            if losing_hours:
                patterns['worst_trading_hours'] = max(set(losing_hours), key=losing_hours.count)
            
            # Trade size pattern
            winning_sizes = [t.get('entry_price', 0) * t.get('amount', 0) for t in wins]
            losing_sizes = [t.get('entry_price', 0) * t.get('amount', 0) for t in losses]
            
            if winning_sizes:
                patterns['avg_winning_trade_size'] = mean(winning_sizes)
            if losing_sizes:
                patterns['avg_losing_trade_size'] = mean(losing_sizes)
            
            # Pair performance
            pair_performance = {}
            for trade in trades:
                pair = trade.get('pair', 'UNKNOWN')
                if pair not in pair_performance:
                    pair_performance[pair] = {'wins': 0, 'losses': 0, 'profit': 0}
                
                if trade.get('profit_loss', 0) > 0:
                    pair_performance[pair]['wins'] += 1
                else:
                    pair_performance[pair]['losses'] += 1
                
                pair_performance[pair]['profit'] += trade.get('profit_loss', 0)
            
            patterns['pair_performance'] = pair_performance
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern identification error: {e}")
            return {}
    
    async def generate_adjustments(self, bot_id: str, analysis: Dict) -> Dict:
        """Generate parameter adjustments based on analysis"""
        try:
            if analysis.get('error') or analysis.get('status') == 'insufficient_data':
                return {
                    "adjustments": [],
                    "message": "Not enough data for adjustments"
                }
            
            adjustments = []
            
            # Win rate adjustments
            win_rate = analysis.get('win_rate', 0)
            
            if win_rate < 45:  # Poor performance
                adjustments.append({
                    "parameter": "risk_mode",
                    "current": "unknown",
                    "suggested": "safe",
                    "reason": f"Win rate too low ({win_rate:.1f}%). Reducing risk."
                })
                
                adjustments.append({
                    "parameter": "trade_size_multiplier",
                    "adjustment": 0.8,
                    "reason": "Reducing trade size due to poor performance"
                })
            
            elif win_rate > 60:  # Good performance
                adjustments.append({
                    "parameter": "trade_size_multiplier",
                    "adjustment": 1.2,
                    "reason": f"Increasing trade size due to strong performance ({win_rate:.1f}%)"
                })
            
            # Win/Loss ratio adjustments
            wl_ratio = analysis.get('win_loss_ratio', 0)
            
            if wl_ratio < 1.5:  # Wins not significantly bigger than losses
                adjustments.append({
                    "parameter": "take_profit_pct",
                    "adjustment": 1.3,
                    "reason": "Increasing take profit target to capture larger wins"
                })
            
            # Pattern-based adjustments
            patterns = analysis.get('patterns', {})
            
            if 'best_trading_hours' in patterns and 'worst_trading_hours' in patterns:
                adjustments.append({
                    "parameter": "trading_schedule",
                    "suggested": f"Focus on hour {patterns['best_trading_hours']}, avoid hour {patterns['worst_trading_hours']}",
                    "reason": "Time-based pattern detected"
                })
            
            # Use AI for deep analysis
            if len(adjustments) > 0:
                ai_recommendations = await ai_model_router.deep_strategy_analysis(
                    analysis,
                    []  # Would pass recent trades here
                )
                
                adjustments.append({
                    "parameter": "ai_insight",
                    "suggested": ai_recommendations.get('recommendations', 'No recommendations'),
                    "reason": "AI-generated strategic advice"
                })
            
            return {
                "bot_id": bot_id,
                "adjustments": adjustments,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Generate adjustments error: {e}")
            return {"error": str(e)}
    
    async def apply_adjustments(self, bot_id: str, adjustments: List[Dict]) -> Dict:
        """Apply approved adjustments to bot"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            
            if not bot:
                return {"error": "Bot not found"}
            
            updates = {}
            applied = []
            
            for adj in adjustments:
                param = adj.get('parameter')
                
                if param == 'risk_mode':
                    updates['risk_mode'] = adj.get('suggested')
                    applied.append(adj)
                
                elif param == 'trade_size_multiplier':
                    current_multiplier = bot.get('trade_size_multiplier', 1.0)
                    new_multiplier = current_multiplier * adj.get('adjustment', 1.0)
                    
                    # Clamp to safe range
                    new_multiplier = max(0.7, min(new_multiplier, 1.3))
                    updates['trade_size_multiplier'] = new_multiplier
                    applied.append(adj)
                
                elif param == 'take_profit_pct':
                    current_tp = bot.get('take_profit_pct', 0.03)
                    new_tp = current_tp * adj.get('adjustment', 1.0)
                    
                    # Clamp to safe range
                    new_tp = max(0.02, min(new_tp, 0.10))
                    updates['take_profit_pct'] = new_tp
                    applied.append(adj)
            
            if updates:
                # Apply updates to bot
                await db.bots_collection.update_one(
                    {"id": bot_id},
                    {"$set": updates}
                )
                
                # Log the learning action
                await db.learning_logs_collection.insert_one({
                    "user_id": bot.get('user_id'),
                    "bot_id": bot_id,
                    "bot_name": bot.get('name'),
                    "adjustments": applied,
                    "updates_applied": updates,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "self_learning_engine"
                })
                
                logger.info(f"🧠 Applied {len(applied)} adjustments to {bot.get('name')}")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "adjustments_applied": len(applied),
                "updates": updates
            }
            
        except Exception as e:
            logger.error(f"Apply adjustments error: {e}")
            return {"error": str(e)}
    
    async def run_learning_cycle(self, user_id: str) -> Dict:
        """Run full learning cycle for all user's bots"""
        try:
            # Get all active bots
            bots = await db.bots_collection.find(
                {"user_id": user_id, "status": "active"},
                {"_id": 0, "id": 1, "name": 1}
            ).to_list(1000)
            
            if not bots:
                return {
                    "success": False,
                    "message": "No active bots to learn from"
                }
            
            learning_results = []
            
            for bot in bots:
                bot_id = bot['id']
                
                # Analyze performance
                analysis = await self.analyze_bot_performance(bot_id)
                
                if analysis.get('error') or analysis.get('status') == 'insufficient_data':
                    continue
                
                # Generate adjustments
                adjustments_data = await self.generate_adjustments(bot_id, analysis)
                
                if adjustments_data.get('adjustments'):
                    # Apply adjustments (auto-apply for now, could require approval)
                    result = await self.apply_adjustments(bot_id, adjustments_data['adjustments'])
                    
                    learning_results.append({
                        "bot_id": bot_id,
                        "bot_name": bot['name'],
                        "result": result
                    })
            
            return {
                "success": True,
                "bots_analyzed": len(bots),
                "bots_adjusted": len(learning_results),
                "results": learning_results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Learning cycle error: {e}")
            return {"success": False, "error": str(e)}

# Global instance
self_learning_engine = SelfLearningEngine()
