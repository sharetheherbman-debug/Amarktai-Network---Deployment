"""
Cross-Exchange Wallet Manager
- Luno as master wallet
- Auto-transfer funds to other exchanges
- Track balances across all platforms
- AI-controlled allocation
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
import logging

import database as db
from ccxt_service import CCXTService

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(self):
        self.ccxt_service = CCXTService()
        self.master_exchange = 'luno'  # Luno is the master wallet
        self.supported_exchanges = ['luno', 'binance', 'kucoin', 'kraken', 'valr']
        
        # Track allocated funds per exchange
        self.exchange_allocations = {
            'luno': {'allocated': 0, 'available': 0},
            'binance': {'allocated': 0, 'available': 0},
            'kucoin': {'allocated': 0, 'available': 0},
            'kraken': {'allocated': 0, 'available': 0},
            'valr': {'allocated': 0, 'available': 0}
        }
    
    async def get_master_balance(self, user_id: str) -> Dict:
        """Get balance from Luno (master wallet)"""
        try:
            # Get Luno API keys
            luno_key = await db.api_keys_collection.find_one({
                "user_id": user_id,
                "exchange": "luno"
            }, {"_id": 0})
            
            if not luno_key:
                return {"error": "Luno API keys not configured"}
            
            # Initialize Luno exchange
            exchange = self.ccxt_service.init_exchange(
                'luno',
                luno_key['api_key'],
                luno_key['api_secret']
            )
            
            # Fetch balances
            balance = await asyncio.to_thread(exchange.fetch_balance)
            
            # Get ZAR and crypto balances
            zar_balance = balance.get('ZAR', {}).get('free', 0)
            btc_balance = balance.get('BTC', {}).get('free', 0)
            eth_balance = balance.get('ETH', {}).get('free', 0)
            xrp_balance = balance.get('XRP', {}).get('free', 0)
            
            # Calculate total in ZAR (simplified)
            btc_price = await self.get_btc_price_zar(exchange)
            total_zar = zar_balance + (btc_balance * btc_price) if btc_price else zar_balance
            
            return {
                "exchange": "luno",
                "zar": zar_balance,
                "btc": btc_balance,
                "eth": eth_balance,
                "xrp": xrp_balance,
                "total_zar": total_zar,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get Luno balance: {e}")
            return {"error": str(e)}
    
    async def get_btc_price_zar(self, exchange) -> Optional[float]:
        """Get BTC/ZAR price"""
        try:
            ticker = await asyncio.to_thread(exchange.fetch_ticker, 'XBTZAR')
            return ticker.get('last', 0)
        except:
            return None
    
    async def get_all_balances(self, user_id: str) -> Dict:
        """Get balances from all configured exchanges"""
        balances = {}
        
        api_keys = await db.api_keys_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(100)
        
        for key_doc in api_keys:
            exchange_name = key_doc['exchange'].lower()
            try:
                exchange = self.ccxt_service.init_exchange(
                    exchange_name,
                    key_doc['api_key'],
                    key_doc['api_secret'],
                    passphrase=key_doc.get('passphrase')
                )
                
                balance = await asyncio.to_thread(exchange.fetch_balance)
                
                # Extract key currencies
                balances[exchange_name] = {
                    "zar": balance.get('ZAR', {}).get('free', 0),
                    "usdt": balance.get('USDT', {}).get('free', 0),
                    "btc": balance.get('BTC', {}).get('free', 0),
                    "eth": balance.get('ETH', {}).get('free', 0)
                }
                
            except Exception as e:
                logger.error(f"Failed to get balance for {exchange_name}: {e}")
                balances[exchange_name] = {"error": str(e)}
        
        return balances
    
    async def calculate_allocation_per_bot(self, user_id: str, total_bots: int = 45) -> float:
        """Calculate how much capital to allocate per bot"""
        try:
            master_balance = await self.get_master_balance(user_id)
            
            if "error" in master_balance:
                return 0
            
            total_capital = master_balance.get('total_zar', 0)
            
            # Allocate 80% of total capital across bots (keep 20% reserve)
            allocatable = total_capital * 0.8
            
            # Divide by target number of bots
            per_bot = allocatable / total_bots
            
            return per_bot
            
        except Exception as e:
            logger.error(f"Allocation calculation error: {e}")
            return 0
    
    async def allocate_funds_for_bot(self, user_id: str, bot_id: str, 
                                    exchange: str, amount: float) -> Dict:
        """Allocate funds from master wallet to specific exchange for a bot"""
        try:
            # Record allocation
            self.exchange_allocations[exchange]['allocated'] += amount
            
            # In production, this would:
            # 1. Check if target exchange has sufficient balance
            # 2. If not, transfer from Luno to target exchange
            # 3. Update allocation tracking
            
            logger.info(f"💰 Allocated R{amount:.2f} to {exchange} for bot {bot_id[:8]}")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "exchange": exchange,
                "amount": amount,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fund allocation error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_allocation_status(self, user_id: str) -> Dict:
        """Get current allocation status across all exchanges"""
        try:
            # Get bots per exchange
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0, "exchange": 1, "current_capital": 1}
            ).to_list(1000)
            
            allocation_summary = {}
            
            for exchange in self.supported_exchanges:
                exchange_bots = [b for b in bots if b.get('exchange', '').lower() == exchange]
                total_allocated = sum(b.get('current_capital', 0) for b in exchange_bots)
                
                allocation_summary[exchange] = {
                    "bot_count": len(exchange_bots),
                    "allocated_capital": total_allocated
                }
            
            return {
                "allocations": allocation_summary,
                "total_bots": len(bots),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Allocation status error: {e}")
            return {"error": str(e)}
    
    async def rebalance_funds(self, user_id: str, top_performers: List[str]) -> Dict:
        """Rebalance funds to top 5 performing bots"""
        try:
            # Get all bots
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0}
            ).to_list(1000)
            
            # Calculate total profit available for reinvestment
            total_profit = sum(b.get('total_profit', 0) for b in bots if b.get('total_profit', 0) > 0)
            
            if total_profit < 500:  # Minimum R500 to rebalance
                return {
                    "success": False,
                    "message": f"Insufficient profit for rebalancing (R{total_profit:.2f} < R500)"
                }
            
            # Distribute profit to top 5 performers
            per_bot_allocation = total_profit / 5
            
            for bot_id in top_performers[:5]:
                await db.bots_collection.update_one(
                    {"id": bot_id},
                    {"$inc": {"current_capital": per_bot_allocation}}
                )
            
            logger.info(f"💰 Rebalanced R{total_profit:.2f} to top 5 bots (R{per_bot_allocation:.2f} each)")
            
            return {
                "success": True,
                "total_profit": total_profit,
                "per_bot": per_bot_allocation,
                "recipients": top_performers[:5]
            }
            
        except Exception as e:
            logger.error(f"Rebalancing error: {e}")
            return {"success": False, "error": str(e)}

# Global instance
wallet_manager = WalletManager()
