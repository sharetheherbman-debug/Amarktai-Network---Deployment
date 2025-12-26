"""
Dashboard Endpoints Router
Provides real-time math and analytics for dashboard frontend
All data sourced from MongoDB - single source of truth
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
import logging
from decimal import Decimal

from auth import get_current_user
from database import bots_collection, trades_collection, users_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/profits")
async def get_profits(
    period: Literal["daily", "weekly", "monthly", "all"] = Query("daily"),
    user_id: str = Depends(get_current_user)
):
    """Get profit breakdown by period
    
    Args:
        period: Time period for profit calculation
        user_id: Current user ID from auth
        
    Returns:
        Profit data with realized/unrealized breakdown
    """
    try:
        # Calculate period start date
        now = datetime.now(timezone.utc)
        if period == "daily":
            start_date = now - timedelta(days=1)
        elif period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        else:  # all
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        # Get all trades for period
        trades_cursor = trades_collection.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date.isoformat()}
        })
        trades = await trades_cursor.to_list(10000)
        
        # Calculate realized profits (closed trades)
        realized_profit = 0.0
        total_trades = len(trades)
        winning_trades = 0
        losing_trades = 0
        total_fees = 0.0
        
        for trade in trades:
            if trade.get("status") == "closed":
                profit = trade.get("realized_profit", 0.0)
                realized_profit += profit
                
                if profit > 0:
                    winning_trades += 1
                elif profit < 0:
                    losing_trades += 1
                
                # Sum fees
                total_fees += trade.get("fees", 0.0)
        
        # Get unrealized profit (open positions)
        open_trades = [t for t in trades if t.get("status") == "open"]
        unrealized_profit = sum(t.get("unrealized_profit", 0.0) for t in open_trades)
        
        # Calculate win rate
        closed_trades = winning_trades + losing_trades
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0
        
        # Get user's starting capital for period
        user = await users_collection.find_one({"id": user_id}, {"_id": 0})
        initial_capital = user.get("initial_capital", 1000.0) if user else 1000.0
        
        # Calculate ROI
        roi = (realized_profit / initial_capital * 100) if initial_capital > 0 else 0.0
        
        return {
            "success": True,
            "period": period,
            "period_start": start_date.isoformat(),
            "period_end": now.isoformat(),
            "data": {
                "realized_profit": round(realized_profit, 2),
                "unrealized_profit": round(unrealized_profit, 2),
                "total_profit": round(realized_profit + unrealized_profit, 2),
                "total_fees": round(total_fees, 2),
                "net_profit": round(realized_profit - total_fees, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "open_trades": len(open_trades),
                "win_rate": round(win_rate, 2),
                "roi": round(roi, 2),
                "initial_capital": round(initial_capital, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Get profits error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/countdown/status")
async def get_countdown_status(user_id: str = Depends(get_current_user)):
    """Get countdown to million status based on actual equity
    
    Uses real math: current capital, daily average profit, projected days to goal
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        Countdown status with projections
    """
    try:
        # Get user data
        user = await users_collection.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get current capital (sum of all bot capitals + wallet balance)
        bots_cursor = bots_collection.find({"user_id": user_id, "status": {"$ne": "deleted"}})
        bots = await bots_cursor.to_list(1000)
        
        total_capital = 0.0
        for bot in bots:
            total_capital += bot.get("current_capital", bot.get("initial_capital", 0.0))
        
        # Add wallet balance if available
        wallet_balance = user.get("wallet_balance", 0.0)
        total_capital += wallet_balance
        
        # Get trades for last 30 days to calculate average daily profit
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        trades_cursor = trades_collection.find({
            "user_id": user_id,
            "status": "closed",
            "created_at": {"$gte": thirty_days_ago.isoformat()}
        })
        trades = await trades_cursor.to_list(10000)
        
        # Calculate total profit over 30 days
        total_profit_30d = sum(t.get("realized_profit", 0.0) for t in trades)
        avg_daily_profit = total_profit_30d / 30 if trades else 0.0
        
        # Calculate projection to R1 million
        goal = 1_000_000.0
        remaining = goal - total_capital
        
        if avg_daily_profit > 0:
            # Simple linear projection
            days_to_goal = remaining / avg_daily_profit
            projected_date = datetime.now(timezone.utc) + timedelta(days=days_to_goal)
            
            # Calculate with compound interest (more realistic)
            # Formula: days = log(goal/capital) / log(1 + daily_rate)
            daily_rate = avg_daily_profit / total_capital if total_capital > 0 else 0
            if daily_rate > 0:
                import math
                days_compound = math.log(goal / total_capital) / math.log(1 + daily_rate)
                projected_date_compound = datetime.now(timezone.utc) + timedelta(days=days_compound)
            else:
                days_compound = days_to_goal
                projected_date_compound = projected_date
        else:
            days_to_goal = 0
            days_compound = 0
            projected_date = None
            projected_date_compound = None
        
        # Calculate percentage complete
        progress_percent = (total_capital / goal * 100) if goal > 0 else 0.0
        
        return {
            "success": True,
            "data": {
                "current_capital": round(total_capital, 2),
                "goal": round(goal, 2),
                "remaining": round(remaining, 2),
                "progress_percent": round(progress_percent, 2),
                "avg_daily_profit_30d": round(avg_daily_profit, 2),
                "projection": {
                    "linear": {
                        "days_to_goal": round(days_to_goal, 1),
                        "projected_date": projected_date.isoformat() if projected_date else None
                    },
                    "compound": {
                        "days_to_goal": round(days_compound, 1),
                        "projected_date": projected_date_compound.isoformat() if projected_date_compound else None
                    }
                },
                "active_bots": len([b for b in bots if b.get("status") == "active"]),
                "total_bots": len(bots)
            }
        }
        
    except Exception as e:
        logger.error(f"Get countdown status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/summary")
async def get_portfolio_summary(user_id: str = Depends(get_current_user)):
    """Get comprehensive portfolio summary
    
    Includes equity, PnL, fees, drawdown, bot distribution
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        Complete portfolio summary
    """
    try:
        # Get all user bots
        bots_cursor = bots_collection.find({"user_id": user_id, "status": {"$ne": "deleted"}})
        bots = await bots_cursor.to_list(1000)
        
        # Calculate total equity
        total_equity = 0.0
        total_initial = 0.0
        bots_by_status = {"active": 0, "paused": 0, "stopped": 0}
        bots_by_exchange = {}
        
        for bot in bots:
            current_capital = bot.get("current_capital", bot.get("initial_capital", 0.0))
            initial_capital = bot.get("initial_capital", 0.0)
            
            total_equity += current_capital
            total_initial += initial_capital
            
            # Count by status
            status = bot.get("status", "active")
            if status in bots_by_status:
                bots_by_status[status] += 1
            
            # Count by exchange
            exchange = bot.get("exchange", "unknown")
            bots_by_exchange[exchange] = bots_by_exchange.get(exchange, 0) + 1
        
        # Get all trades
        trades_cursor = trades_collection.find({"user_id": user_id})
        trades = await trades_cursor.to_list(10000)
        
        # Calculate realized and unrealized PnL
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        total_fees = 0.0
        
        for trade in trades:
            if trade.get("status") == "closed":
                realized_pnl += trade.get("realized_profit", 0.0)
                total_fees += trade.get("fees", 0.0)
            elif trade.get("status") == "open":
                unrealized_pnl += trade.get("unrealized_profit", 0.0)
        
        # Calculate total PnL
        total_pnl = realized_pnl + unrealized_pnl
        
        # Calculate max drawdown (simplified - peak to trough)
        # In production, this would track daily equity snapshots
        equity_change = total_equity - total_initial
        max_drawdown_percent = 0.0
        if total_initial > 0 and equity_change < 0:
            max_drawdown_percent = abs(equity_change / total_initial * 100)
        
        # Get user info
        user = await users_collection.find_one({"id": user_id}, {"_id": 0})
        funded_capital = user.get("funded_capital", total_initial) if user else total_initial
        
        # Calculate returns
        roi_percent = (total_pnl / funded_capital * 100) if funded_capital > 0 else 0.0
        
        return {
            "success": True,
            "data": {
                "equity": {
                    "total": round(total_equity, 2),
                    "funded_capital": round(funded_capital, 2),
                    "change": round(equity_change, 2),
                    "change_percent": round((equity_change / funded_capital * 100) if funded_capital > 0 else 0.0, 2)
                },
                "pnl": {
                    "realized": round(realized_pnl, 2),
                    "unrealized": round(unrealized_pnl, 2),
                    "total": round(total_pnl, 2),
                    "fees": round(total_fees, 2),
                    "net": round(total_pnl - total_fees, 2)
                },
                "performance": {
                    "roi_percent": round(roi_percent, 2),
                    "max_drawdown_percent": round(max_drawdown_percent, 2)
                },
                "bots": {
                    "total": len(bots),
                    "by_status": bots_by_status,
                    "by_exchange": bots_by_exchange
                },
                "trades": {
                    "total": len(trades),
                    "open": len([t for t in trades if t.get("status") == "open"]),
                    "closed": len([t for t in trades if t.get("status") == "closed"])
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Get portfolio summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
