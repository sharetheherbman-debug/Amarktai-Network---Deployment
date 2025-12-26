"""
Alerts Router - User alert management
"""
from fastapi import APIRouter, Depends, HTTPException
from database import alerts_collection
from auth import get_current_user
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

@router.get("/alerts")
async def get_alerts(limit: int = 200, user_id: str = Depends(get_current_user)):
    """Get user alerts"""
    try:
        alerts = await alerts_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Normalize MongoDB _id to id string if present
        for alert in alerts:
            if '_id' in alert:
                alert['id'] = str(alert.pop('_id'))
        
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/ack/{alert_id}")
async def acknowledge_alert(alert_id: str, user_id: str = Depends(get_current_user)):
    """Acknowledge/dismiss an alert"""
    try:
        result = await alerts_collection.update_one(
            {"user_id": user_id, "id": alert_id},
            {"$set": {"dismissed": True, "dismissed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"message": "Alert acknowledged", "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Acknowledge alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/alerts/clear")
async def clear_alerts(user_id: str = Depends(get_current_user)):
    """Clear all user alerts"""
    try:
        result = await alerts_collection.delete_many({"user_id": user_id})
        
        return {
            "message": f"Cleared {result.deleted_count} alerts",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        logger.error(f"Clear alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
