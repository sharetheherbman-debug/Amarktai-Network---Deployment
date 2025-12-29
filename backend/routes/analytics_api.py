"""
Analytics API - Single Source of Truth for PnL and Performance Data
All graphs and dashboards must read from these endpoints only
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import logging

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/pnl_timeseries")
async def get_pnl_timeseries(
    range: str = Query("7d", regex="^(1d|7d|30d|90d|1y|all)$"),
    interval: str = Query("1h", regex="^(5m|15m|1h|4h|1d)$"),
    user_id: str = Depends(get_current_user)
):
    """Get PnL timeseries data - SINGLE SOURCE OF TRUTH for all profit graphs
    
    Args:
        range: Time range (1d, 7d, 30d, 90d, 1y, all)
        interval: Data point interval (5m, 15m, 1h, 4h, 1d)
        user_id: Current user ID
        
    Returns:
        Timeseries data with timestamps and cumulative PnL
    """
    try:
        # Calculate time range
        now = datetime.now(timezone.utc)
        
        range_map = {
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365),
            "all": timedelta(days=3650)  # 10 years
        }
        
        start_time = now - range_map.get(range, timedelta(days=7))
        
        # Get all trades in range
        trades = await db.trades_collection.find(
            {
                "user_id": user_id,
                "timestamp": {"$gte": start_time.isoformat()}
            },
            {"_id": 0, "timestamp": 1, "profit_loss": 1, "bot_id": 1}
        ).sort("timestamp", 1).to_list(10000)
        
        if not trades:
            return {
                "range": range,
                "interval": interval,
                "datapoints": [],
                "summary": {
                    "total_pnl": 0,
                    "trade_count": 0,
                    "start_time": start_time.isoformat(),
                    "end_time": now.isoformat()
                }
            }
        
        # Group trades by interval
        interval_map = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1)
        }
        
        interval_delta = interval_map.get(interval, timedelta(hours=1))
        
        # Create time buckets
        datapoints = []
        cumulative_pnl = 0
        current_bucket_start = start_time
        bucket_trades = []
        
        for trade in trades:
            trade_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
            
            # Check if trade belongs to current bucket
            while trade_time >= current_bucket_start + interval_delta:
                # Close current bucket
                if bucket_trades:
                    bucket_pnl = sum(t.get('profit_loss', 0) for t in bucket_trades)
                    cumulative_pnl += bucket_pnl
                    
                    datapoints.append({
                        "timestamp": current_bucket_start.isoformat(),
                        "cumulative_pnl": round(cumulative_pnl, 2),
                        "period_pnl": round(bucket_pnl, 2),
                        "trade_count": len(bucket_trades)
                    })
                
                # Move to next bucket
                current_bucket_start += interval_delta
                bucket_trades = []
            
            # Add trade to current bucket
            bucket_trades.append(trade)
        
        # Close final bucket
        if bucket_trades:
            bucket_pnl = sum(t.get('profit_loss', 0) for t in bucket_trades)
            cumulative_pnl += bucket_pnl
            
            datapoints.append({
                "timestamp": current_bucket_start.isoformat(),
                "cumulative_pnl": round(cumulative_pnl, 2),
                "period_pnl": round(bucket_pnl, 2),
                "trade_count": len(bucket_trades)
            })
        
        return {
            "range": range,
            "interval": interval,
            "datapoints": datapoints,
            "summary": {
                "total_pnl": round(cumulative_pnl, 2),
                "trade_count": len(trades),
                "start_time": start_time.isoformat(),
                "end_time": now.isoformat(),
                "total_datapoints": len(datapoints)
            }
        }
        
    except Exception as e:
        logger.error(f"Get PnL timeseries error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capital_breakdown")
async def get_capital_breakdown(user_id: str = Depends(get_current_user)):
    """Get detailed capital breakdown - distinguishes funded vs unrealized vs realized
    
    Returns:
        - funded_capital: Total capital deposited/allocated
        - current_capital: Current total capital (funded + realized)
        - unrealized_pnl: Profit/loss from open positions (if any)
        - realized_pnl: Profit/loss from closed trades
    """
    try:
        # Get all user bots
        bots = await db.bots_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        if not bots:
            return {
                "funded_capital": 0,
                "current_capital": 0,
                "unrealized_pnl": 0,
                "realized_pnl": 0,
                "total_bots": 0
            }
        
        # Calculate totals
        funded_capital = sum(bot.get('initial_capital', 0) for bot in bots)
        current_capital = sum(bot.get('current_capital', 0) for bot in bots)
        realized_pnl = sum(bot.get('total_profit', 0) for bot in bots)
        
        # Unrealized PnL from open positions (paper trading doesn't have open positions)
        unrealized_pnl = 0  # Will be calculated from open positions in live trading
        
        return {
            "funded_capital": round(funded_capital, 2),
            "current_capital": round(current_capital, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_bots": len(bots),
            "breakdown_by_bot": [
                {
                    "bot_id": bot['id'],
                    "bot_name": bot.get('name'),
                    "funded": bot.get('initial_capital', 0),
                    "current": bot.get('current_capital', 0),
                    "realized_pnl": bot.get('total_profit', 0)
                }
                for bot in bots
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get capital breakdown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance_summary")
async def get_performance_summary(
    period: str = Query("all", regex="^(today|7d|30d|all)$"),
    user_id: str = Depends(get_current_user)
):
    """Get comprehensive performance summary
    
    Args:
        period: Time period for summary (today, 7d, 30d, all)
    """
    try:
        # Calculate time range
        now = datetime.now(timezone.utc)
        
        if period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "7d":
            start_time = now - timedelta(days=7)
        elif period == "30d":
            start_time = now - timedelta(days=30)
        else:  # all
            start_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        # Get trades in period
        trades = await db.trades_collection.find(
            {
                "user_id": user_id,
                "timestamp": {"$gte": start_time.isoformat()}
            },
            {"_id": 0}
        ).to_list(10000)
        
        # Calculate statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('profit_loss', 0) > 0])
        losing_trades = len([t for t in trades if t.get('profit_loss', 0) < 0])
        
        total_pnl = sum(t.get('profit_loss', 0) for t in trades)
        gross_profit = sum(t.get('profit_loss', 0) for t in trades if t.get('profit_loss', 0) > 0)
        gross_loss = abs(sum(t.get('profit_loss', 0) for t in trades if t.get('profit_loss', 0) < 0))
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        # Average trade metrics
        avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0
        
        return {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "trades": {
                "total": total_trades,
                "winning": winning_trades,
                "losing": losing_trades,
                "win_rate_pct": round(win_rate, 2)
            },
            "pnl": {
                "total": round(total_pnl, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "profit_factor": round(profit_factor, 2)
            },
            "averages": {
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "avg_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            },
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get performance summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
