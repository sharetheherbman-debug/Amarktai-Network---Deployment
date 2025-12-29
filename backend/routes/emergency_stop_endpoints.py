"""
Emergency Stop System
Provides instant trading halt across all bots and exchanges
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging
from datetime import datetime, timezone

from auth import get_current_user
import database as db
from engines.audit_logger import audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["Emergency Stop"])

@router.post("/emergency-stop")
async def activate_emergency_stop(
    reason: str = "User initiated",
    current_user: Dict = Depends(get_current_user)
):
    """
    Activate emergency stop - immediately halt all trading
    """
    try:
        user_id = current_user['id']
        
        # Set emergency stop flag
        await db.system_modes_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "emergencyStop": True,
                    "emergency_stop_reason": reason,
                    "emergency_stop_at": datetime.now(timezone.utc).isoformat(),
                    "emergency_stop_by": user_id
                }
            },
            upsert=True
        )
        
        # Pause all active bots
        result = await db.bots_collection.update_many(
            {"user_id": user_id, "status": "active"},
            {"$set": {"status": "paused"}}
        )
        
        # Log the action
        await audit_logger.log_event(
            event_type="emergency_stop_activated",
            user_id=user_id,
            details={
                "reason": reason,
                "bots_paused": result.modified_count
            },
            severity="critical"
        )
        
        logger.critical(f"🚨 EMERGENCY STOP activated by user {user_id[:8]}: {reason}")
        
        return {
            "success": True,
            "message": "Emergency stop activated - all trading halted",
            "bots_paused": result.modified_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/emergency-stop/disable")
async def deactivate_emergency_stop(current_user: Dict = Depends(get_current_user)):
    """
    Deactivate emergency stop - resume normal operations
    """
    try:
        user_id = current_user['id']
        
        # Check if emergency stop is active
        modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
        
        if not modes or not modes.get('emergencyStop'):
            return {
                "success": False,
                "message": "Emergency stop is not active"
            }
        
        # Disable emergency stop
        await db.system_modes_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "emergencyStop": False,
                    "emergency_stop_disabled_at": datetime.now(timezone.utc).isoformat(),
                    "emergency_stop_disabled_by": user_id
                }
            }
        )
        
        # Resume paused bots (user can manually activate them)
        # Note: We don't auto-activate to give user control
        
        # Log the action
        await audit_logger.log_event(
            event_type="emergency_stop_deactivated",
            user_id=user_id,
            details={
                "reason": "User resumed operations"
            },
            severity="warning"
        )
        
        logger.info(f"✅ Emergency stop deactivated by user {user_id[:8]}")
        
        return {
            "success": True,
            "message": "Emergency stop deactivated - you can now resume trading",
            "note": "Bots remain paused. Activate them manually when ready.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Deactivate emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emergency-stop/status")
async def get_emergency_stop_status(current_user: Dict = Depends(get_current_user)):
    """
    Get current emergency stop status
    """
    try:
        user_id = current_user['id']
        
        modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
        
        if not modes:
            return {
                "active": False,
                "reason": None,
                "activated_at": None
            }
        
        return {
            "active": modes.get('emergencyStop', False),
            "reason": modes.get('emergency_stop_reason'),
            "activated_at": modes.get('emergency_stop_at'),
            "activated_by": modes.get('emergency_stop_by')
        }
        
    except Exception as e:
        logger.error(f"Get emergency stop status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
