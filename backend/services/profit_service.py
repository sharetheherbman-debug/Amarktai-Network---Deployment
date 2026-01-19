"""
Profit Service - Single source of truth for all profit calculations
Consolidates profit logic from multiple sources into one canonical service
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import logging

import database as db

logger = logging.getLogger(__name__)


class ProfitService:
    """Canonical profit calculation service"""
    
    @staticmethod
    async def calculate_total_profit(
        user_id: str,
        trading_mode: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """Calculate total realized profit from closed trades
        
        Args:
            user_id: User ID
            trading_mode: Filter by 'paper' or 'live' (None = both)
            start_date: Start date filter (None = all time)
            end_date: End date filter (None = now)
            
        Returns:
            Total realized profit (sum of profit_loss for closed trades)
        """
        try:
            # Build query
            query = {
                "user_id": user_id,
                "status": "closed"
            }
            
            if trading_mode:
                query["trading_mode"] = trading_mode
            
            # Add date filters if provided
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date.isoformat()
                if end_date:
                    query["timestamp"]["$lte"] = end_date.isoformat()
            
            # Get trades
            trades_cursor = db.trades_collection.find(query, {"_id": 0, "profit_loss": 1})
            trades = await trades_cursor.to_list(10000)
            
            # Calculate total
            total_profit = sum(t.get("profit_loss", 0) for t in trades)
            
            return round(total_profit, 2)
            
        except Exception as e:
            logger.error(f"Calculate total profit error: {e}")
            return 0.0
    
    @staticmethod
    async def calculate_profit_today(
        user_id: str,
        trading_mode: Optional[str] = None
    ) -> float:
        """Calculate profit for today (since midnight UTC)"""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        return await ProfitService.calculate_total_profit(
            user_id,
            trading_mode,
            start_date=today_start
        )
    
    @staticmethod
    async def calculate_profit_yesterday(
        user_id: str,
        trading_mode: Optional[str] = None
    ) -> float:
        """Calculate profit for yesterday"""
        now = datetime.now(timezone.utc)
        yesterday_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        
        return await ProfitService.calculate_total_profit(
            user_id,
            trading_mode,
            start_date=yesterday_start,
            end_date=yesterday_end
        )
    
    @staticmethod
    async def get_daily_profit_series(
        user_id: str,
        days: int = 7,
        trading_mode: Optional[str] = None
    ) -> List[Dict]:
        """Get daily profit series for chart
        
        Args:
            user_id: User ID
            days: Number of days to include
            trading_mode: Filter by mode
            
        Returns:
            List of dicts with date and profit
        """
        try:
            # Calculate start date
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=days)
            
            # Build query
            query = {
                "user_id": user_id,
                "status": "closed",
                "timestamp": {"$gte": start_date.isoformat()}
            }
            
            if trading_mode:
                query["trading_mode"] = trading_mode
            
            # Get trades
            trades_cursor = db.trades_collection.find(
                query,
                {"_id": 0, "profit_loss": 1, "timestamp": 1}
            )
            trades = await trades_cursor.to_list(10000)
            
            # Group by date
            daily_profits = defaultdict(float)
            
            for trade in trades:
                timestamp = trade.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                        daily_profits[date_str] += trade.get("profit_loss", 0)
                    except:
                        pass
            
            # Build result list
            result = []
            for i in range(days):
                date = (now - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
                result.append({
                    "date": date,
                    "profit": round(daily_profits.get(date, 0), 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Get daily profit series error: {e}")
            return []
    
    @staticmethod
    async def get_profit_summary(
        user_id: str,
        trading_mode: Optional[str] = None
    ) -> Dict:
        """Get comprehensive profit summary
        
        Returns:
            Dict with total_profit, profit_today, profit_yesterday,
            daily_series_7, daily_series_30, best_day, avg_daily, last_calculated_at
        """
        try:
            # Calculate all metrics
            total_profit = await ProfitService.calculate_total_profit(user_id, trading_mode)
            profit_today = await ProfitService.calculate_profit_today(user_id, trading_mode)
            profit_yesterday = await ProfitService.calculate_profit_yesterday(user_id, trading_mode)
            
            daily_series_7 = await ProfitService.get_daily_profit_series(user_id, 7, trading_mode)
            daily_series_30 = await ProfitService.get_daily_profit_series(user_id, 30, trading_mode)
            
            # Calculate best day and average
            all_profits = [d["profit"] for d in daily_series_30]
            best_day = max(all_profits) if all_profits else 0
            avg_daily = sum(all_profits) / len(all_profits) if all_profits else 0
            
            return {
                "total_profit": total_profit,
                "profit_today": profit_today,
                "profit_yesterday": profit_yesterday,
                "daily_series_7": daily_series_7,
                "daily_series_30": daily_series_30,
                "best_day": round(best_day, 2),
                "avg_daily": round(avg_daily, 2),
                "last_calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Get profit summary error: {e}")
            return {
                "total_profit": 0,
                "profit_today": 0,
                "profit_yesterday": 0,
                "daily_series_7": [],
                "daily_series_30": [],
                "best_day": 0,
                "avg_daily": 0,
                "last_calculated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    @staticmethod
    async def calculate_unrealized_profit(
        user_id: str,
        trading_mode: Optional[str] = None
    ) -> float:
        """Calculate unrealized profit from open positions
        
        Note: This requires current market prices which may not be available.
        If market data is not available, returns 0.
        
        Args:
            user_id: User ID
            trading_mode: Filter by mode
            
        Returns:
            Unrealized profit (estimated)
        """
        try:
            # Build query for open positions
            query = {
                "user_id": user_id,
                "status": "open"
            }
            
            if trading_mode:
                query["trading_mode"] = trading_mode
            
            # Get open positions
            positions_cursor = db.trades_collection.find(query, {"_id": 0})
            positions = await positions_cursor.to_list(1000)
            
            # Sum unrealized profit if available
            # Note: unrealized_profit should be updated by trading engine
            unrealized_profit = sum(
                p.get("unrealized_profit", 0) for p in positions
            )
            
            return round(unrealized_profit, 2)
            
        except Exception as e:
            logger.error(f"Calculate unrealized profit error: {e}")
            return 0.0
    
    @staticmethod
    async def get_trade_stats(
        user_id: str,
        trading_mode: Optional[str] = None
    ) -> Dict:
        """Get trading statistics
        
        Returns:
            Dict with total_trades, winning_trades, losing_trades, win_rate, total_fees
        """
        try:
            # Build query
            query = {
                "user_id": user_id,
                "status": "closed"
            }
            
            if trading_mode:
                query["trading_mode"] = trading_mode
            
            # Get trades
            trades_cursor = db.trades_collection.find(query, {"_id": 0})
            trades = await trades_cursor.to_list(10000)
            
            # Calculate stats
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get("profit_loss", 0) > 0)
            losing_trades = sum(1 for t in trades if t.get("profit_loss", 0) < 0)
            total_fees = sum(t.get("fees", 0) for t in trades)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "total_fees": round(total_fees, 2)
            }
            
        except Exception as e:
            logger.error(f"Get trade stats error: {e}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_fees": 0
            }


# Global instance
profit_service = ProfitService()
