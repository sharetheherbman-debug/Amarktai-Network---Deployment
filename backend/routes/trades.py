"""
Trades API - Canonical trade history and metrics
Frontend calls GET /api/trades/recent?limit=50
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional, List
import logging

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("/ping")
async def trades_ping() -> dict:
    """Return a simple heartbeat response for trades checks."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/recent")
async def get_recent_trades(
    limit: int = Query(50, ge=1, le=500),
    user_id: str = Depends(get_current_user)
):
    """
    Get recent trades with date+time metrics
    Frontend calls this endpoint to display trade history
    
    Args:
        limit: Maximum number of trades to return (1-500)
        user_id: Current authenticated user
        
    Returns:
        List of trades with full timestamps and metrics
    """
    try:
        # Fetch recent trades sorted by timestamp descending
        trades = await db.trades_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Ensure all trades have proper date+time fields
        for trade in trades:
            # Ensure timestamp exists
            if 'timestamp' not in trade or not trade['timestamp']:
                trade['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Parse timestamp to ensure it's ISO format
            try:
                if isinstance(trade['timestamp'], str):
                    dt = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
                elif isinstance(trade['timestamp'], datetime):
                    dt = trade['timestamp']
                else:
                    dt = datetime.now(timezone.utc)
                
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                # Set formatted fields
                trade['timestamp'] = dt.isoformat()
                trade['date'] = dt.strftime('%Y-%m-%d')
                trade['time'] = dt.strftime('%H:%M:%S')
                
            except Exception as parse_error:
                logger.warning(f"Trade timestamp parse error: {parse_error}")
                now = datetime.now(timezone.utc)
                trade['timestamp'] = now.isoformat()
                trade['date'] = now.strftime('%Y-%m-%d')
                trade['time'] = now.strftime('%H:%M:%S')
        
        return {
            "trades": trades,
            "count": len(trades),
            "limit": limit,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get recent trades error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_trade_stats(
    user_id: str = Depends(get_current_user)
):
    """
    Get trade statistics summary
    
    Returns:
        Summary statistics for all user trades
    """
    try:
        # Get all trades
        trades = await db.trades_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(10000)
        
        if not trades:
            return {
                "total_trades": 0,
                "total_volume": 0,
                "total_pnl": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate statistics
        total_trades = len(trades)
        total_volume = sum(abs(t.get('amount', 0) * t.get('price', 0)) for t in trades)
        total_pnl = sum(t.get('profit_loss', 0) for t in trades)
        winning_trades = len([t for t in trades if t.get('profit_loss', 0) > 0])
        losing_trades = len([t for t in trades if t.get('profit_loss', 0) < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "total_volume": round(total_volume, 2),
            "total_pnl": round(total_pnl, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get trade stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
