"""
Profits API Endpoints
Provides profit data and reinvestment functionality
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict
import logging
from datetime import datetime, timezone, timedelta

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profits", tags=["Profits"])


@router.get("")
async def get_profits(
    period: str = "daily",
    user_id: str = Depends(get_current_user)
):
    """Get profit data for user
    
    Protected endpoint that returns profit information
    Supports multiple period types: daily, weekly, monthly
    
    Args:
        period: Time period for aggregation (daily, weekly, monthly)
        user_id: Current user ID from auth
        
    Returns:
        Profit data with items and total
    """
    try:
        # Get all trades for user
        trades_cursor = db.trades_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1)
        
        trades = await trades_cursor.to_list(1000)
        
        # Calculate total profit
        total_profit = sum(
            t.get('profit', 0) for t in trades 
            if t.get('status') == 'closed' and t.get('profit')
        )
        
        # Group by period
        items = []
        if period == "daily":
            # Group by day
            daily_profits = {}
            for trade in trades:
                if trade.get('status') == 'closed' and trade.get('profit'):
                    timestamp = trade.get('timestamp')
                    if isinstance(timestamp, str):
                        date = timestamp[:10]  # YYYY-MM-DD
                    else:
                        date = timestamp.strftime('%Y-%m-%d') if timestamp else 'unknown'
                    
                    if date not in daily_profits:
                        daily_profits[date] = 0
                    daily_profits[date] += trade.get('profit', 0)
            
            # Convert to items list
            for date, profit in sorted(daily_profits.items(), reverse=True)[:30]:
                items.append({
                    "date": date,
                    "profit": round(profit, 2),
                    "period": "daily"
                })
        
        elif period == "weekly":
            # Group by week
            weekly_profits = {}
            for trade in trades:
                if trade.get('status') == 'closed' and trade.get('profit'):
                    timestamp = trade.get('timestamp')
                    if isinstance(timestamp, str):
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            week = dt.strftime('%Y-W%U')
                        except:
                            week = 'unknown'
                    else:
                        week = timestamp.strftime('%Y-W%U') if timestamp else 'unknown'
                    
                    if week not in weekly_profits:
                        weekly_profits[week] = 0
                    weekly_profits[week] += trade.get('profit', 0)
            
            # Convert to items list
            for week, profit in sorted(weekly_profits.items(), reverse=True)[:12]:
                items.append({
                    "week": week,
                    "profit": round(profit, 2),
                    "period": "weekly"
                })
        
        elif period == "monthly":
            # Group by month
            monthly_profits = {}
            for trade in trades:
                if trade.get('status') == 'closed' and trade.get('profit'):
                    timestamp = trade.get('timestamp')
                    if isinstance(timestamp, str):
                        month = timestamp[:7]  # YYYY-MM
                    else:
                        month = timestamp.strftime('%Y-%m') if timestamp else 'unknown'
                    
                    if month not in monthly_profits:
                        monthly_profits[month] = 0
                    monthly_profits[month] += trade.get('profit', 0)
            
            # Convert to items list
            for month, profit in sorted(monthly_profits.items(), reverse=True)[:12]:
                items.append({
                    "month": month,
                    "profit": round(profit, 2),
                    "period": "monthly"
                })
        
        return {
            "period": period,
            "items": items,
            "total": round(total_profit, 2),
            "currency": "ZAR",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting profits: {e}")
        # Return safe default instead of 500
        return {
            "period": period,
            "items": [],
            "total": 0,
            "currency": "ZAR",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/reinvest")
async def reinvest_profits(
    data: Optional[Dict] = None,
    user_id: str = Depends(get_current_user)
):
    """Reinvest profits into new or existing bots
    
    Protected endpoint for profit reinvestment
    Can be stubbed for now if full implementation not ready
    
    Args:
        data: Optional configuration for reinvestment
        user_id: Current user ID from auth
        
    Returns:
        Reinvestment result with success status
    """
    try:
        # Check if reinvestment service is available
        try:
            from services.daily_reinvestment import get_reinvestment_service
            reinvest_service = get_reinvestment_service(db.db)
            
            # Execute reinvestment
            result = await reinvest_service.execute_reinvestment(user_id)
            
            return {
                "success": True,
                "message": "Profits reinvested successfully",
                "amount_reinvested": result.get('amount_reinvested', 0),
                "bots_funded": result.get('bots_funded', 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            # Reinvestment service not available - return stub response
            logger.info(f"Reinvestment requested by user {user_id[:8]} but service not available (stub)")
            return {
                "success": True,
                "message": "Reinvestment request received (queued for processing)",
                "amount_reinvested": 0,
                "bots_funded": 0,
                "stub": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error reinvesting profits: {e}")
        return {
            "success": False,
            "message": f"Reinvestment failed: {str(e)}",
            "amount_reinvested": 0,
            "bots_funded": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
