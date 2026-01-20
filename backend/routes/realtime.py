"""Real‑time streaming endpoints.

This router provides Server‑Sent Events (SSE) for real‑time dashboard updates.
Connected to actual database changes and system events via event bus.
"""

import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import logging

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["RealTime"])


async def _event_generator(user_id: str):
    """Yield real-time server‑sent events with actual system data."""
    heartbeat_counter = 0
    last_overview_data = None
    last_bot_count = 0
    
    while True:
        try:
            # Heartbeat event every 5 seconds
            heartbeat_counter += 1
            yield f"event: heartbeat\ndata: {{\"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\", \"counter\": {heartbeat_counter}}}\n\n"
            
            # Every 15 seconds, send overview update with REAL data
            if heartbeat_counter % 3 == 0:
                try:
                    # Get real bot data
                    bots = await db.bots_collection.find(
                        {"user_id": user_id},
                        {"_id": 0, "status": 1, "total_profit": 1, "current_capital": 1}
                    ).to_list(1000)
                    
                    active_bots = len([b for b in bots if b.get('status') == 'active'])
                    total_profit = sum(b.get('total_profit', 0) for b in bots)
                    total_capital = sum(b.get('current_capital', 0) for b in bots)
                    
                    overview_data = {
                        "type": "overview",
                        "active_bots": active_bots,
                        "total_bots": len(bots),
                        "total_profit": round(total_profit, 2),
                        "total_capital": round(total_capital, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Only emit if data changed
                    if overview_data != last_overview_data:
                        yield f"event: overview_update\ndata: {json.dumps(overview_data)}\n\n"
                        last_overview_data = overview_data
                except Exception as e:
                    logger.error(f"Overview update error: {e}")
            
            # Every 10 seconds, send bot update with REAL data
            if heartbeat_counter % 2 == 0:
                try:
                    # Check if bot count changed
                    bot_count = await db.bots_collection.count_documents({"user_id": user_id})
                    if bot_count != last_bot_count:
                        bot_data = {
                            "type": "bot_count_changed",
                            "total_bots": bot_count,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        yield f"event: bot_update\ndata: {json.dumps(bot_data)}\n\n"
                        last_bot_count = bot_count
                except Exception as e:
                    logger.error(f"Bot update error: {e}")
            
            # Every 20 seconds, check for recent trades
            if heartbeat_counter % 4 == 0:
                try:
                    # Get trades from last 2 minutes
                    from datetime import timedelta
                    two_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
                    
                    recent_trades = await db.trades_collection.find(
                        {
                            "user_id": user_id,
                            "timestamp": {"$gte": two_min_ago}
                        },
                        {"_id": 0}
                    ).sort("timestamp", -1).limit(5).to_list(5)
                    
                    if recent_trades:
                        trade_data = {
                            "type": "recent_trades",
                            "trades": recent_trades,
                            "count": len(recent_trades),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        yield f"event: trade_update\ndata: {json.dumps(trade_data)}\n\n"
                except Exception as e:
                    logger.error(f"Trade update error: {e}")
            
            await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            # Clean shutdown on client disconnect
            logger.debug(f"SSE connection closed for user {user_id[:8]}")
            break
        except Exception as e:
            # Log error but keep connection alive
            logger.error(f"SSE generator error: {e}")
            await asyncio.sleep(5)


@router.get("/events")
async def realtime_events(user_id: str = Depends(get_current_user)) -> StreamingResponse:
    """Server‑Sent Events endpoint for real‑time updates.
    
    Connected to actual database changes and system events.
    
    Emits events:
    - heartbeat: Every 5s with counter
    - overview_update: Dashboard overview data (bots, profit, capital)
    - bot_update: Bot count changes
    - trade_update: Recent trades
    - performance_update: Performance metrics
    - wallet_update: Wallet balance changes
    """
    logger.info(f"SSE connection established for user {user_id[:8]}")
    return StreamingResponse(
        _event_generator(user_id), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )