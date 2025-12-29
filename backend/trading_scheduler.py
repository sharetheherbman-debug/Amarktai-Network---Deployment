"""
Trading Scheduler - CONTINUOUS STAGGERED TRADING
Uses trade_staggerer for 24/7 distributed execution
Actually uses live_trading_engine for live bots
"""

import asyncio
import logging
from datetime import datetime, timezone
from paper_trading_engine import paper_engine
from engines.trading_engine_live import live_trading_engine
from engines.trade_staggerer import trade_staggerer
import database as db
from websocket_manager import manager

logger = logging.getLogger(__name__)

class TradingScheduler:
    """CONTINUOUS STAGGERED TRADING - Uses trade_staggerer for 24/7 execution"""
    
    def __init__(self):
        self.is_running = False
        self.task = None
        self.check_interval = 10  # Check every 10 seconds for ready trades
        
    async def execute_bot_trades(self):
        """Execute trades using staggered queue - CONTINUOUS OPERATION"""
        try:
            # Get all active bots
            active_bots = await db.bots_collection.find(
                {"status": "active"},
                {"_id": 0}
            ).to_list(1000)
            
            if not active_bots:
                return
            
            # Check each user's System Mode settings
            users_with_trading = {}
            for bot in active_bots:
                user_id = bot['user_id']
                if user_id not in users_with_trading:
                    modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
                    
                    # Trading enabled if autopilot is ON
                    if modes and modes.get('autopilot'):
                        # Check emergency stop
                        if not modes.get('emergencyStop', False):
                            users_with_trading[user_id] = True
                        else:
                            users_with_trading[user_id] = False
                    else:
                        users_with_trading[user_id] = False
            
            # Filter bots with trading enabled
            active_bots = [bot for bot in active_bots if users_with_trading.get(bot['user_id'], False)]
            
            if not active_bots:
                return
            
            # Process ready trades from queue
            for _ in range(5):  # Process up to 5 trades per cycle
                trade_request = await trade_staggerer.get_next_trade()
                
                if not trade_request:
                    break
                
                bot_id = trade_request['bot_id']
                bot = next((b for b in active_bots if b['id'] == bot_id), None)
                
                if not bot:
                    continue
                
                # Execute trade based on mode
                try:
                    # Check both 'mode' and 'trading_mode' for backwards compatibility
                    mode = bot.get('mode') or bot.get('trading_mode', 'paper')
                    is_paper_mode = mode == 'paper'
                    
                    # Register trade start
                    await trade_staggerer.register_trade_start(bot_id, bot.get('exchange'))
                    
                    if is_paper_mode:
                        # Paper trading
                        result = await paper_engine.run_trading_cycle(
                            bot['id'],
                            bot,
                            {'bots': db.bots_collection, 'trades': db.trades_collection}
                        )
                    else:
                        # LIVE TRADING - Use live_trading_engine
                        logger.info(f"🔴 LIVE TRADING: {bot['name']} on {bot.get('exchange')}")
                        
                        # Execute live trade
                        result = await self.execute_live_trade(bot)
                    
                    # Register trade complete
                    await trade_staggerer.register_trade_complete(bot_id, bot.get('exchange'))
                    
                    # Send WebSocket update
                    if result and isinstance(result, dict):
                        await manager.send_message(bot['user_id'], {
                            "type": "trade_executed",
                            "bot_id": result['bot_id'],
                            "bot_name": bot['name'],
                            "new_capital": result.get('new_capital', 0),
                            "total_profit": result.get('total_profit', 0),
                            "trade": result.get('trade', {})
                        })
                    
                except Exception as e:
                    logger.error(f"Trade execution error for {bot['name']}: {e}")
                    await trade_staggerer.register_trade_complete(bot_id, bot.get('exchange'))
            
            # Add new trades to queue
            for bot in active_bots:
                bot_id = bot['id']
                exchange = bot.get('exchange', 'binance')
                
                # Check if bot can trade
                can_execute, reason = await trade_staggerer.can_execute_now(bot_id, exchange)
                
                if can_execute:
                    # Add to queue
                    await trade_staggerer.add_to_queue(bot_id, exchange, priority=0)
        
        except Exception as e:
            logger.error(f"Trading cycle error: {e}")
    
    async def execute_live_trade(self, bot: dict) -> dict:
        """Execute a live trade using live_trading_engine"""
        try:
            # Get bot's trading pair
            pair = bot.get('pair', 'BTC/ZAR')
            exchange = bot.get('exchange', 'binance')
            
            # Determine trade size based on risk mode
            risk_multipliers = {
                'safe': 0.25,
                'balanced': 0.35,
                'risky': 0.45,
                'aggressive': 0.60
            }
            
            risk_mode = bot.get('risk_mode', 'safe')
            multiplier = risk_multipliers.get(risk_mode, 0.25)
            
            capital = bot.get('current_capital', 1000)
            trade_size = capital * multiplier
            
            # Determine trade side (buy or sell)
            import random
            side = 'buy' if random.random() > 0.5 else 'sell'
            
            # Calculate amount
            # For live trading, we need to get real price first
            import database as db
            
            # Check if user has API keys for this exchange
            api_key_doc = await db.api_keys_collection.find_one({
                "user_id": bot['user_id'],
                "exchange": exchange
            }, {"_id": 0})
            
            if not api_key_doc:
                logger.warning(f"No API keys for {exchange} - falling back to paper mode")
                return await paper_engine.run_trading_cycle(
                    bot['id'],
                    bot,
                    {'bots': db.bots_collection, 'trades': db.trades_collection}
                )
            
            # Execute trade via live engine
            trade_result = await live_trading_engine.execute_trade(
                bot_id=bot['id'],
                bot_data=bot,
                symbol=pair,
                side=side,
                amount=0.001,  # Small amount for testing
                price=None,  # Market order
                paper_mode=False  # LIVE MODE
            )
            
            if not trade_result.get('success'):
                logger.error(f"Live trade failed: {trade_result.get('error')}")
                return None
            
            # Record trade in database
            from uuid import uuid4
            trade_doc = {
                "id": str(uuid4()),
                "bot_id": bot['id'],
                "user_id": bot['user_id'],
                "pair": pair,
                "side": side,
                "entry_price": trade_result.get('price', 0),
                "amount": trade_result.get('amount', 0),
                "profit_loss": trade_result.get('net_profit', 0),
                "is_paper": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "exchange": exchange
            }
            
            await db.trades_collection.insert_one(trade_doc)
            
            # Update bot stats
            new_capital = capital + trade_result.get('net_profit', 0)
            is_win = trade_result.get('net_profit', 0) > 0
            
            await db.bots_collection.update_one(
                {"id": bot['id']},
                {
                    "$set": {
                        "current_capital": new_capital,
                        "last_trade_time": datetime.now(timezone.utc).isoformat()
                    },
                    "$inc": {
                        "total_profit": trade_result.get('net_profit', 0),
                        "trades_count": 1,
                        "win_count": 1 if is_win else 0,
                        "loss_count": 0 if is_win else 1
                    }
                }
            )
            
            return {
                "bot_id": bot['id'],
                "new_capital": new_capital,
                "total_profit": bot.get('total_profit', 0) + trade_result.get('net_profit', 0),
                "trade": trade_doc
            }
            
        except Exception as e:
            logger.error(f"Execute live trade error: {e}")
            return None
    
    async def trading_loop(self):
        """Main trading loop - runs continuously"""
        logger.info("🚀 Continuous staggered trading started")
        
        while self.is_running:
            try:
                await self.execute_bot_trades()
                
                # Clean up stale trades periodically
                await trade_staggerer.clear_stale_trades()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def start(self):
        """Start the trading scheduler"""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.trading_loop())
            logger.info("✅ Trading scheduler started - continuous staggered execution")
    
    def stop(self):
        """Stop the trading scheduler"""
        self.is_running = False
        if self.task:
            self.task.cancel()
        logger.info("🔴 Trading scheduler stopped")

# Global instance
trading_scheduler = TradingScheduler()
