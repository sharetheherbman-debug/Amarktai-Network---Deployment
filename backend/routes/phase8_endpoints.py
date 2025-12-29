"""
Phase 8 API Endpoints - Logging, Monitoring, Audit, Email
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone, timedelta

from auth import get_current_user
from engines.audit_logger import audit_logger
from engines.email_reporter import email_reporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phase8", tags=["Phase 8 - Logging & Monitoring"])

# ============================================================================
# AUDIT LOGGER ENDPOINTS
# ============================================================================

@router.get("/audit/trail")
async def get_audit_trail(
    days: int = Query(7, ge=1, le=90),
    event_types: Optional[List[str]] = Query(None),
    current_user: Dict = Depends(get_current_user)
):
    """Get audit trail for user"""
    try:
        logs = await audit_logger.get_user_audit_trail(
            current_user['id'],
            days=days,
            event_types=event_types
        )
        
        return {
            "user_id": current_user['id'],
            "days": days,
            "total_events": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Get audit trail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit/critical")
async def get_critical_events(
    days: int = Query(30, ge=1, le=90),
    current_user: Dict = Depends(get_current_user)
):
    """Get critical audit events"""
    try:
        events = await audit_logger.get_critical_events(current_user['id'], days=days)
        
        return {
            "user_id": current_user['id'],
            "days": days,
            "critical_events": events
        }
    except Exception as e:
        logger.error(f"Get critical events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit/compliance-report")
async def get_compliance_report(
    start_date: str,
    end_date: str,
    current_user: Dict = Depends(get_current_user)
):
    """Generate compliance report for date range"""
    try:
        report = await audit_logger.generate_compliance_report(
            current_user['id'],
            start_date,
            end_date
        )
        
        return report
    except Exception as e:
        logger.error(f"Compliance report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit/statistics")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=90),
    current_user: Dict = Depends(get_current_user)
):
    """Get audit log statistics"""
    try:
        stats = await audit_logger.get_statistics(current_user['id'], days=days)
        return stats
    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# EMAIL REPORTER ENDPOINTS
# ============================================================================

@router.post("/email/send-daily-report")
async def send_daily_report(current_user: Dict = Depends(get_current_user)):
    """Send daily performance report to user's email"""
    try:
        # Get user email
        import database as db
        user = await db.users_collection.find_one({"id": current_user['id']}, {"_id": 0})
        
        if not user or not user.get('email'):
            raise HTTPException(status_code=404, detail="User email not found")
        
        result = await email_reporter.send_daily_report(current_user['id'], user['email'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send daily report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/email/test")
async def test_email(current_user: Dict = Depends(get_current_user)):
    """Test email configuration"""
    try:
        import database as db
        user = await db.users_collection.find_one({"id": current_user['id']}, {"_id": 0})
        
        if not user or not user.get('email'):
            raise HTTPException(status_code=404, detail="User email not found")
        
        # Send test email
        html = "<h1>Test Email</h1><p>Your email configuration is working correctly!</p>"
        sent = await email_reporter.send_email(user['email'], "Amarktai Test Email", html)
        
        return {
            "success": sent,
            "email": user['email'],
            "smtp_enabled": email_reporter.smtp_enabled
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/email/report-preview")
async def preview_daily_report(current_user: Dict = Depends(get_current_user)):
    """Preview daily report without sending email"""
    try:
        import database as db
        user = await db.users_collection.find_one({"id": current_user['id']}, {"_id": 0})
        
        if not user or not user.get('email'):
            raise HTTPException(status_code=404, detail="User email not found")
        
        # Generate report (don't send)
        report = await email_reporter.generate_daily_report(current_user['id'], user['email'])
        
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
