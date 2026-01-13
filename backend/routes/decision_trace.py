"""
Decision Trace Endpoints
Provides AI trading decision history and reasoning for dashboard
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

from auth import get_current_user
import database as db
from json_utils import serialize_list, serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/decisions", tags=["Decision Trace"])


@router.get("/trace")
async def get_decision_trace(
    limit: int = 50,
    symbol: Optional[str] = None,
    bot_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get recent AI trading decisions with reasoning
    
    Shows decision trace for bot actions, trade signals, and reasoning
    """
    try:
        # Build query
        query = {"user_id": user_id}
        if symbol:
            query["symbol"] = symbol
        if bot_id:
            query["bot_id"] = bot_id
        
        # Check if decisions collection exists
        if not hasattr(db, 'decisions_collection') or db.decisions_collection is None:
            # Return mock/example data structure if collection doesn't exist yet
            return {
                "decisions": [],
                "total": 0,
                "message": "Decision tracking not yet configured",
                "example_structure": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "symbol": "BTC/ZAR",
                    "exchange": "luno",
                    "decision": "buy",
                    "confidence": 0.75,
                    "reasoning": ["Market regime bullish", "OFI shows buying pressure"],
                    "bot_id": "bot-123",
                    "execution": "pending"
                }
            }
        
        # Get decisions from collection
        decisions = await db.decisions_collection.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Serialize
        serialized = serialize_list(decisions, exclude_fields=['_id'])
        
        return {
            "decisions": serialized,
            "total": len(serialized),
            "filters": {
                "symbol": symbol,
                "bot_id": bot_id,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Get decision trace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_decisions(
    count: int = 10,
    user_id: str = Depends(get_current_user)
):
    """Get latest decisions across all bots for user"""
    try:
        # If collection doesn't exist, return empty with structure
        if not hasattr(db, 'decisions_collection') or db.decisions_collection is None:
            return {
                "decisions": [],
                "count": 0,
                "message": "Decision tracking not yet configured"
            }
        
        decisions = await db.decisions_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(count).to_list(count)
        
        serialized = serialize_list(decisions, exclude_fields=['_id'])
        
        return {
            "decisions": serialized,
            "count": len(serialized)
        }
        
    except Exception as e:
        logger.error(f"Get latest decisions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log")
async def log_decision(
    decision_data: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """
    Log a trading decision (called by bots/trading engine)
    
    Expected fields:
    - symbol: str
    - exchange: str
    - decision: str (buy/sell/hold)
    - confidence: float
    - reasoning: List[str]
    - bot_id: str
    """
    try:
        # Add metadata
        decision_data['user_id'] = user_id
        decision_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Store decision if collection exists
        if hasattr(db, 'decisions_collection') and db.decisions_collection is not None:
            await db.decisions_collection.insert_one(decision_data)
            return {"success": True, "message": "Decision logged"}
        else:
            return {"success": False, "message": "Decision collection not configured"}
            
    except Exception as e:
        logger.error(f"Log decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
