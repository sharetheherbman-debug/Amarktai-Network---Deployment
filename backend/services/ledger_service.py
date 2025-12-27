"""
Ledger Service - Immutable accounting for fills and events

This service provides the single source of truth for:
- Fills (immutable trade executions)
- Ledger events (funding, transfers, allocations)
- Derived metrics (equity, PnL, drawdown, fees)

Phase 1: Read-only + parallel write (opt-in via feature flag)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class LedgerService:
    """
    Immutable ledger-based accounting service
    
    Collections:
    - fills_ledger: Immutable fill records
    - ledger_events: Funding, transfer, allocation events
    """
    
    def __init__(self, db):
        self.db = db
        self.fills_ledger = db["fills_ledger"]
        self.ledger_events = db["ledger_events"]
        
        # Create indexes for performance
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            # Fills ledger indexes
            self.fills_ledger.create_index([("user_id", 1), ("timestamp", -1)])
            self.fills_ledger.create_index([("bot_id", 1), ("timestamp", -1)])
            self.fills_ledger.create_index([("client_order_id", 1)], unique=True, sparse=True)
            self.fills_ledger.create_index([("exchange_trade_id", 1)])
            self.fills_ledger.create_index([("timestamp", -1)])
            
            # Ledger events indexes
            self.ledger_events.create_index([("user_id", 1), ("timestamp", -1)])
            self.ledger_events.create_index([("event_type", 1), ("timestamp", -1)])
        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")
    
    async def append_fill(
        self,
        user_id: str,
        bot_id: str,
        exchange: str,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        qty: float,
        price: float,
        fee: float,
        fee_currency: str,
        timestamp: datetime,
        order_id: str,
        client_order_id: Optional[str] = None,
        exchange_trade_id: Optional[str] = None,
        is_paper: bool = True,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Append an immutable fill to the ledger
        
        Returns: fill_id
        """
        fill_doc = {
            "user_id": user_id,
            "bot_id": bot_id,
            "exchange": exchange,
            "symbol": symbol,
            "side": side.lower(),
            "qty": float(qty),
            "price": float(price),
            "fee": float(fee),
            "fee_currency": fee_currency,
            "timestamp": timestamp,
            "order_id": order_id,
            "client_order_id": client_order_id,
            "exchange_trade_id": exchange_trade_id,
            "is_paper": is_paper,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        try:
            result = await self.fills_ledger.insert_one(fill_doc)
            fill_id = str(result.inserted_id)
            logger.info(f"Appended fill {fill_id} for bot {bot_id}: {side} {qty} {symbol} @ {price}")
            return fill_id
        except Exception as e:
            logger.error(f"Failed to append fill: {e}")
            raise
    
    async def append_event(
        self,
        user_id: str,
        event_type: str,  # 'funding', 'transfer', 'allocation', 'circuit_breaker'
        amount: float,
        currency: str,
        timestamp: datetime,
        bot_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Append a ledger event (funding, transfers, etc.)
        
        Returns: event_id
        """
        event_doc = {
            "user_id": user_id,
            "bot_id": bot_id,
            "event_type": event_type,
            "amount": float(amount),
            "currency": currency,
            "timestamp": timestamp,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        try:
            result = await self.ledger_events.insert_one(event_doc)
            event_id = str(result.inserted_id)
            logger.info(f"Appended event {event_id}: {event_type} {amount} {currency}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            raise
    
    async def get_fills(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get fills with optional filters"""
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        if bot_id:
            query["bot_id"] = bot_id
        if since or until:
            query["timestamp"] = {}
            if since:
                query["timestamp"]["$gte"] = since
            if until:
                query["timestamp"]["$lte"] = until
        
        cursor = self.fills_ledger.find(query).sort("timestamp", -1).limit(limit)
        fills = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for fill in fills:
            fill["_id"] = str(fill["_id"])
        
        return fills
    
    async def compute_equity(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        currency: str = "USDT",
        include_unrealized: bool = True
    ) -> float:
        """
        Compute total equity from fills and events
        
        Equity = Starting Capital + Realized PnL + Unrealized PnL - Fees
        
        Can compute for user_id or bot_id
        """
        # Determine the query target
        target_id = user_id or bot_id
        target_field = "user_id" if user_id else "bot_id"
        
        if not target_id:
            raise ValueError("Must provide either user_id or bot_id")
        
        # Get funding events
        funding_query = {
            target_field: target_id,
            "event_type": "funding",
            "currency": currency
        }
        funding_cursor = self.ledger_events.find(funding_query)
        funding_events = await funding_cursor.to_list(length=1000)
        
        starting_capital = sum(event.get("amount", 0) for event in funding_events)
        
        # Get realized PnL from closed fills
        realized_pnl = await self.compute_realized_pnl(user_id=user_id, bot_id=bot_id, currency=currency)
        
        # Get unrealized PnL from open positions
        unrealized_pnl = 0
        if include_unrealized:
            unrealized_pnl = await self.compute_unrealized_pnl(user_id=user_id, bot_id=bot_id, currency=currency)
        
        # Get total fees paid
        fees_paid = await self.compute_fees_paid(user_id=user_id, bot_id=bot_id, currency=currency)
        
        equity = starting_capital + realized_pnl + unrealized_pnl - fees_paid
        
        logger.debug(f"Equity calculation for {target_field}={target_id}: starting={starting_capital}, realized={realized_pnl}, unrealized={unrealized_pnl}, fees={fees_paid}, total={equity}")
        
        return equity
    
    async def compute_realized_pnl(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        currency: str = "USDT"
    ) -> float:
        """
        Compute realized PnL from closed positions
        
        Method: Match buys and sells using FIFO
        
        Can compute for user_id or bot_id
        """
        # Determine the query target
        target_id = user_id or bot_id
        target_field = "user_id" if user_id else "bot_id"
        
        if not target_id:
            raise ValueError("Must provide either user_id or bot_id")
        
        query = {target_field: target_id}
        if since or until:
            query["timestamp"] = {}
            if since:
                query["timestamp"]["$gte"] = since
            if until:
                query["timestamp"]["$lte"] = until
        
        cursor = self.fills_ledger.find(query).sort("timestamp", 1)
        fills = await cursor.to_list(length=10000)
        
        # Group by symbol
        positions_by_symbol = {}
        realized_pnl = 0.0
        
        for fill in fills:
            symbol = fill["symbol"]
            side = fill["side"]
            qty = fill["qty"]
            price = fill["price"]
            
            if symbol not in positions_by_symbol:
                positions_by_symbol[symbol] = []
            
            if side == "buy":
                # Add to position
                positions_by_symbol[symbol].append({
                    "qty": qty,
                    "price": price
                })
            elif side == "sell":
                # Close position using FIFO
                remaining_qty = qty
                sell_price = price
                
                while remaining_qty > 0 and positions_by_symbol[symbol]:
                    buy = positions_by_symbol[symbol][0]
                    
                    if buy["qty"] <= remaining_qty:
                        # Close entire buy
                        closed_qty = buy["qty"]
                        pnl = closed_qty * (sell_price - buy["price"])
                        realized_pnl += pnl
                        remaining_qty -= closed_qty
                        positions_by_symbol[symbol].pop(0)
                    else:
                        # Partially close buy
                        closed_qty = remaining_qty
                        pnl = closed_qty * (sell_price - buy["price"])
                        realized_pnl += pnl
                        buy["qty"] -= closed_qty
                        remaining_qty = 0
        
        return realized_pnl
    
    async def compute_unrealized_pnl(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        currency: str = "USDT"
    ) -> float:
        """
        Compute unrealized PnL from open positions
        
        Note: Requires current market prices (not implemented in Phase 1)
        Returns 0 for now as this requires price feed integration
        
        Can compute for user_id or bot_id
        """
        # TODO: Implement with price feed in Phase 2
        logger.debug(f"Unrealized PnL calculation not implemented yet (requires price feed)")
        return 0.0
    
    async def compute_fees_paid(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        currency: str = "USDT"
    ) -> float:
        """
        Compute total fees paid from fills
        
        Can compute for user_id or bot_id
        """
        # Determine the query target
        target_id = user_id or bot_id
        target_field = "user_id" if user_id else "bot_id"
        
        if not target_id:
            raise ValueError("Must provide either user_id or bot_id")
        
        query = {target_field: target_id}
        if since or until:
            query["timestamp"] = {}
            if since:
                query["timestamp"]["$gte"] = since
            if until:
                query["timestamp"]["$lte"] = until
        
        # Aggregate fees
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "total_fees": {"$sum": "$fee"}
            }}
        ]
        
        result = await self.fills_ledger.aggregate(pipeline).to_list(length=1)
        
        if result:
            return result[0].get("total_fees", 0.0)
        return 0.0
    
    async def compute_drawdown(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        currency: str = "USDT"
    ) -> Tuple[float, float]:
        """
        Compute current drawdown and max drawdown
        
        Returns: (current_drawdown_pct, max_drawdown_pct)
        
        Can compute for user_id or bot_id
        """
        # Determine the query target
        target_id = user_id or bot_id
        target_field = "user_id" if user_id else "bot_id"
        
        if not target_id:
            raise ValueError("Must provide either user_id or bot_id")
        
        # Get equity time series
        fills = await self.get_fills(**{target_field: target_id}, limit=10000)
        
        if not fills:
            return 0.0, 0.0
        
        # Calculate equity at each point
        equity_series = []
        running_equity = 0.0
        
        # Get starting capital
        funding_query = {
            target_field: target_id,
            "event_type": "funding",
            "currency": currency
        }
        funding_cursor = self.ledger_events.find(funding_query)
        funding_events = await funding_cursor.to_list(length=1000)
        starting_capital = sum(event.get("amount", 0) for event in funding_events)
        
        running_equity = starting_capital
        equity_series.append(running_equity)
        
        # Simple approximation: add/subtract trade value and fees
        for fill in reversed(fills):  # Reverse to go chronological
            side = fill["side"]
            qty = fill["qty"]
            price = fill["price"]
            fee = fill["fee"]
            
            trade_value = qty * price
            
            if side == "buy":
                running_equity -= trade_value
            else:  # sell
                running_equity += trade_value
            
            running_equity -= fee
            equity_series.append(running_equity)
        
        if not equity_series or max(equity_series) == 0:
            return 0.0, 0.0
        
        # Calculate drawdowns
        peak = equity_series[0]
        max_dd = 0.0
        current_dd = 0.0
        
        for equity in equity_series:
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        # Current drawdown
        current_equity = equity_series[-1]
        current_dd = (peak - current_equity) / peak if peak > 0 else 0
        
        return current_dd, max_dd
    
    async def profit_series(
        self,
        user_id: str,
        period: str = "daily",  # 'daily', 'weekly', 'monthly'
        limit: int = 30
    ) -> List[Dict]:
        """
        Get profit time series aggregated by period
        
        Returns: [{"date": "2025-01-01", "realized_pnl": 100, "fees": 5, "net_profit": 95}, ...]
        """
        # Determine time bucket size
        if period == "daily":
            delta = timedelta(days=1)
            date_format = "%Y-%m-%d"
        elif period == "weekly":
            delta = timedelta(weeks=1)
            date_format = "%Y-W%W"
        elif period == "monthly":
            delta = timedelta(days=30)
            date_format = "%Y-%m"
        else:
            raise ValueError(f"Invalid period: {period}")
        
        # Get fills for the period
        since = datetime.utcnow() - (delta * limit)
        fills = await self.get_fills(user_id=user_id, since=since, limit=10000)
        
        # Group by period
        periods_data = {}
        
        for fill in reversed(fills):  # Chronological order
            timestamp = fill["timestamp"]
            date_key = timestamp.strftime(date_format)
            
            if date_key not in periods_data:
                periods_data[date_key] = {
                    "date": date_key,
                    "trades": 0,
                    "fees": 0.0,
                    "volume": 0.0
                }
            
            periods_data[date_key]["trades"] += 1
            periods_data[date_key]["fees"] += fill.get("fee", 0)
            periods_data[date_key]["volume"] += fill["qty"] * fill["price"]
        
        # Calculate realized PnL per period (simplified - actual would need position tracking)
        # For Phase 1, we'll use a simpler approximation
        series = []
        for date_key in sorted(periods_data.keys()):
            data = periods_data[date_key]
            # TODO: Calculate actual realized PnL per period
            data["realized_pnl"] = 0  # Placeholder - needs proper calculation
            data["net_profit"] = data["realized_pnl"] - data["fees"]
            series.append(data)
        
        return series[-limit:]
    
    async def get_stats(self, user_id: str, bot_id: Optional[str] = None) -> Dict:
        """
        Get comprehensive statistics
        
        Returns: {
            "total_fills": int,
            "total_volume": float,
            "total_fees": float,
            "win_rate": float,  # if calculable
            "avg_fill_size": float
        }
        """
        query = {"user_id": user_id}
        if bot_id:
            query["bot_id"] = bot_id
        
        # Aggregate stats
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "total_fills": {"$sum": 1},
                "total_volume": {"$sum": {"$multiply": ["$qty", "$price"]}},
                "total_fees": {"$sum": "$fee"},
                "avg_qty": {"$avg": "$qty"}
            }}
        ]
        
        result = await self.fills_ledger.aggregate(pipeline).to_list(length=1)
        
        if result:
            stats = result[0]
            del stats["_id"]
            return stats
        
        return {
            "total_fills": 0,
            "total_volume": 0.0,
            "total_fees": 0.0,
            "avg_qty": 0.0
        }
    
    async def get_trade_count(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> int:
        """
        Count trades for a bot/user in a time period
        
        Used by order pipeline for trade limiting
        """
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        if bot_id:
            query["bot_id"] = bot_id
        if since or until:
            query["timestamp"] = {}
            if since:
                query["timestamp"]["$gte"] = since
            if until:
                query["timestamp"]["$lte"] = until
        
        count = await self.fills_ledger.count_documents(query)
        return count
    
    async def compute_daily_pnl(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        currency: str = "USDT"
    ) -> float:
        """
        Calculate PnL for today
        
        Used by circuit breaker to detect daily loss triggers
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate realized PnL for today
        realized_pnl = await self.compute_realized_pnl(
            user_id=user_id,
            bot_id=bot_id,
            since=today_start,
            currency=currency
        )
        
        # Subtract today's fees
        fees = await self.compute_fees_paid(
            user_id=user_id,
            bot_id=bot_id,
            since=today_start,
            currency=currency
        )
        
        return realized_pnl - fees
    
    async def get_consecutive_losses(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        limit: int = 100
    ) -> int:
        """
        Track consecutive losing trades
        
        Used by circuit breaker to detect loss streaks
        """
        query = {}
        if user_id:
            query["user_id"] = user_id
        if bot_id:
            query["bot_id"] = bot_id
        
        # Get recent fills sorted by timestamp descending
        cursor = self.fills_ledger.find(query).sort("timestamp", -1).limit(limit)
        fills = await cursor.to_list(length=limit)
        
        if not fills:
            return 0
        
        # Group fills by symbol to track positions
        # Simplified: Check if recent trades resulted in losses
        # This is a simplified heuristic - proper implementation would need full position tracking
        consecutive = 0
        positions = {}
        
        for fill in reversed(fills):  # Process chronologically
            symbol = fill["symbol"]
            side = fill["side"]
            qty = fill["qty"]
            price = fill["price"]
            
            if symbol not in positions:
                positions[symbol] = []
            
            if side == "buy":
                positions[symbol].append({"qty": qty, "price": price})
            elif side == "sell" and positions[symbol]:
                # Close position
                remaining_qty = qty
                trade_pnl = 0
                
                while remaining_qty > 0 and positions[symbol]:
                    buy = positions[symbol][0]
                    
                    if buy["qty"] <= remaining_qty:
                        closed_qty = buy["qty"]
                        trade_pnl += closed_qty * (price - buy["price"])
                        remaining_qty -= closed_qty
                        positions[symbol].pop(0)
                    else:
                        closed_qty = remaining_qty
                        trade_pnl += closed_qty * (price - buy["price"])
                        buy["qty"] -= closed_qty
                        remaining_qty = 0
                
                # Check if this was a loss
                if trade_pnl < 0:
                    consecutive += 1
                else:
                    # Reset counter on a win
                    consecutive = 0
        
        return consecutive
    
    async def get_error_rate(
        self,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        hours: int = 1
    ) -> int:
        """
        Track errors per hour for circuit breaker
        
        Looks for error events in ledger_events
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = {
            "event_type": "error",
            "timestamp": {"$gte": since}
        }
        
        if user_id:
            query["user_id"] = user_id
        if bot_id:
            query["bot_id"] = bot_id
        
        count = await self.ledger_events.count_documents(query)
        return count


# Singleton instance
_ledger_service_instance = None


def get_ledger_service(db):
    """Get or create ledger service instance"""
    global _ledger_service_instance
    if _ledger_service_instance is None:
        _ledger_service_instance = LedgerService(db)
    return _ledger_service_instance
