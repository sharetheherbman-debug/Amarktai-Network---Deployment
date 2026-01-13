"""Real‑time streaming endpoints.

This router defines a simple Server‑Sent Events (SSE) endpoint to
demonstrate how real‑time data can be streamed to the frontend.  The
endpoint is designed to be self‑contained and not depend on the trading
engine or AI subsystems.  If the SSE feature is disabled via
`ENABLE_REALTIME=false` in the environment, this router can simply be
omitted from the server's include list.
"""

import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from auth import get_current_user

router = APIRouter(prefix="/api/realtime", tags=["RealTime"])


async def _event_generator(user_id: str):
    """Yield periodic server‑sent events with various event types."""
    heartbeat_counter = 0
    
    while True:
        try:
            # Heartbeat event every 5 seconds
            heartbeat_counter += 1
            yield f"event: heartbeat\ndata: {{\"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\", \"counter\": {heartbeat_counter}}}\n\n"
            
            # Every 15 seconds, send overview update
            if heartbeat_counter % 3 == 0:
                yield f"event: overview_update\ndata: {{\"type\": \"overview\", \"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\"}}\n\n"
            
            # Every 20 seconds, send performance update  
            if heartbeat_counter % 4 == 0:
                yield f"event: performance_update\ndata: {{\"type\": \"performance\", \"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\"}}\n\n"
            
            # Every 30 seconds, send whale update
            if heartbeat_counter % 6 == 0:
                yield f"event: whale_update\ndata: {{\"type\": \"whale\", \"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\"}}\n\n"
            
            # Every 10 seconds, send bot update
            if heartbeat_counter % 2 == 0:
                yield f"event: bot_update\ndata: {{\"type\": \"bot\", \"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\"}}\n\n"
            
            await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            # Clean shutdown on client disconnect
            break
        except Exception as e:
            # Log error but keep connection alive
            import logging
            logging.error(f"SSE generator error: {e}")
            await asyncio.sleep(5)


@router.get("/events")
async def realtime_events(user_id: str = Depends(get_current_user)) -> StreamingResponse:
    """Server‑Sent Events endpoint for real‑time updates.
    
    Emits events:
    - heartbeat: Every 5s with counter
    - overview_update: Dashboard overview data
    - performance_update: Performance metrics
    - whale_update: Whale flow activity
    - decision_update: AI decision traces
    - wallet_update: Wallet balance changes
    - bot_update: Bot status changes
    """
    return StreamingResponse(
        _event_generator(user_id), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )