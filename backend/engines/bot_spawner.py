"""
Autonomous Bot Spawner
- Auto-spawns bots until 45 total
- Distributes across exchanges
- AI-controlled allocation
- Uses wallet_manager for funding
"""

import asyncio
from typing import Dict, List
from datetime import datetime, timezone
from uuid import uuid4
import logging

import database as db
from engines.wallet_manager import wallet_manager
from config import *

logger = logging.getLogger(__name__)

class BotSpawner:
    def __init__(self):
        self.max_bots = 45
        self.exchange_distribution = {
            'luno': 5,      # 5 bots on Luno
            'binance': 10,  # 10 bots on Binance
            'kucoin': 10,   # 10 bots on KuCoin
            'kraken': 10,   # 10 bots on Kraken
            'valr': 10      # 10 bots on VALR
        }
        
        self.risk_distribution = {
            'safe': 0.3,        # 30% safe bots
            'balanced': 0.4,    # 40% balanced
            'risky': 0.2,       # 20% risky
            'aggressive': 0.1   # 10% aggressive
        }
    
    async def get_bot_count(self, user_id: str) -> Dict:
        """Get current bot count per exchange"""
        try:
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0, "exchange": 1, "status": 1}
            ).to_list(1000)
            
            by_exchange = {}
            for exchange in self.exchange_distribution.keys():
                exchange_bots = [b for b in bots if b.get('exchange', '').lower() == exchange]
                by_exchange[exchange] = {
                    "total": len(exchange_bots),
                    "active": len([b for b in exchange_bots if b.get('status') == 'active'])
                }
            
            return {
                "total_bots": len(bots),
                "by_exchange": by_exchange,
                "remaining_slots": self.max_bots - len(bots)
            }
            
        except Exception as e:
            logger.error(f"Get bot count error: {e}")
            return {"error": str(e)}
    
    async def determine_next_bot_config(self, user_id: str) -> Dict:
        """Determine config for next bot to spawn"""
        try:
            bot_count = await self.get_bot_count(user_id)
            
            if bot_count['total_bots'] >= self.max_bots:
                return {"error": "Maximum bot count reached"}
            
            # Find exchange with most remaining slots
            by_exchange = bot_count['by_exchange']
            target_exchange = None
            max_remaining = 0
            
            for exchange, target_count in self.exchange_distribution.items():
                current = by_exchange.get(exchange, {}).get('total', 0)
                remaining = target_count - current
                
                if remaining > max_remaining:
                    max_remaining = remaining
                    target_exchange = exchange
            
            if not target_exchange:
                return {"error": "No available exchange slots"}
            
            # Determine risk mode based on distribution
            import random
            rand = random.random()
            if rand < self.risk_distribution['safe']:
                risk_mode = 'safe'
            elif rand < self.risk_distribution['safe'] + self.risk_distribution['balanced']:
                risk_mode = 'balanced'
            elif rand < 0.9:  # 90% cumulative
                risk_mode = 'risky'
            else:
                risk_mode = 'aggressive'
            
            # Calculate capital allocation
            capital = await wallet_manager.calculate_allocation_per_bot(user_id, self.max_bots)
            
            return {
                "exchange": target_exchange,
                "risk_mode": risk_mode,
                "capital": capital,
                "name": f"Bot-{bot_count['total_bots'] + 1:02d}"
            }
            
        except Exception as e:
            logger.error(f"Next bot config error: {e}")
            return {"error": str(e)}
    
    async def spawn_bot(self, user_id: str, config: Dict) -> Dict:
        """Spawn a single bot"""
        try:
            bot_id = str(uuid4())
            
            # Allocate funds from master wallet
            allocation = await wallet_manager.allocate_funds_for_bot(
                user_id,
                bot_id,
                config['exchange'],
                config['capital']
            )
            
            if not allocation.get('success'):
                return {"success": False, "error": "Fund allocation failed"}
            
            # Create bot document
            bot_doc = {
                "id": bot_id,
                "user_id": user_id,
                "name": config['name'],
                "exchange": config['exchange'],
                "risk_mode": config['risk_mode'],
                "initial_capital": config['capital'],
                "current_capital": config['capital'],
                "total_profit": 0,
                "trades_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "mode": "paper",  # Always start in paper mode
                "paper_start_date": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "daily_trade_count": 0,
                "last_trade_time": None,
                "auto_spawned": True  # Mark as auto-spawned
            }
            
            await db.bots_collection.insert_one(bot_doc)
            
            logger.info(f"🤖 Spawned {config['name']} on {config['exchange']} with R{config['capital']:.2f}")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "bot": bot_doc
            }
            
        except Exception as e:
            logger.error(f"Bot spawn error: {e}")
            return {"success": False, "error": str(e)}
    
    async def auto_spawn_to_target(self, user_id: str) -> Dict:
        """Auto-spawn bots until target reached"""
        try:
            bot_count = await self.get_bot_count(user_id)
            total_bots = bot_count['total_bots']
            
            spawned = []
            
            while total_bots < self.max_bots:
                # Determine config for next bot
                config = await self.determine_next_bot_config(user_id)
                
                if "error" in config:
                    break
                
                # Spawn the bot
                result = await self.spawn_bot(user_id, config)
                
                if result.get('success'):
                    spawned.append(result['bot'])
                    total_bots += 1
                else:
                    logger.error(f"Failed to spawn bot: {result.get('error')}")
                    break
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "spawned_count": len(spawned),
                "total_bots": total_bots,
                "target": self.max_bots,
                "bots": spawned
            }
            
        except Exception as e:
            logger.error(f"Auto-spawn error: {e}")
            return {"success": False, "error": str(e)}
    
    async def spawn_single_bot_smart(self, user_id: str) -> Dict:
        """Spawn a single bot with AI-determined optimal config"""
        try:
            config = await self.determine_next_bot_config(user_id)
            
            if "error" in config:
                return {"success": False, "error": config["error"]}
            
            return await self.spawn_bot(user_id, config)
            
        except Exception as e:
            logger.error(f"Smart spawn error: {e}")
            return {"success": False, "error": str(e)}

# Global instance
bot_spawner = BotSpawner()
