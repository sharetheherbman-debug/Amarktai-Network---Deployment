"""
Admin Dashboard Endpoints
User management, system monitoring, and administrative actions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
import logging
from datetime import datetime, timezone
import bcrypt
import os
import secrets

from auth import get_current_user
import database as db
from engines.audit_logger import audit_logger
from json_utils import serialize_doc, serialize_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

@router.post("/unlock")
async def unlock_admin_panel(
    request: dict,
    current_user_id: str = Depends(get_current_user)
):
    """
    Verify admin password and generate unlock token
    Case-insensitive and whitespace-tolerant password check
    
    SECURITY: Requires ADMIN_PASSWORD environment variable to be set.
    Token is returned but not stored (stateless approach).
    In production, implement Redis-based token validation for added security.
    """
    try:
        # Get password from request
        password = request.get('password', '').strip()
        
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        # Get admin password from environment (REQUIRED - no fallback for security)
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if not admin_password or not admin_password.strip():
            logger.error("ADMIN_PASSWORD environment variable not set or empty")
            raise HTTPException(
                status_code=500, 
                detail="Server configuration error: Admin password not configured"
            )
        
        admin_password = admin_password.strip()
        
        # Case-insensitive and whitespace-tolerant comparison
        if password.lower() != admin_password.lower():
            # Log failed attempt
            await audit_logger.log_event(
                event_type="admin_unlock_failed",
                user_id=current_user_id,
                details={"reason": "Invalid password"},
                severity="warning"
            )
            raise HTTPException(status_code=403, detail="Invalid admin password")
        
        # Generate unlock token (valid for 1 hour)
        # NOTE: Token is not stored server-side (stateless approach)
        # For production, consider implementing Redis-based token storage
        unlock_token = secrets.token_urlsafe(32)
        
        # Log successful unlock
        await audit_logger.log_event(
            event_type="admin_panel_unlocked",
            user_id=current_user_id,
            details={"timestamp": datetime.now(timezone.utc).isoformat()},
            severity="info"
        )
        
        logger.info(f"Admin panel unlocked by user {current_user_id}")
        
        return {
            "success": True,
            "message": "Admin panel unlocked",
            "unlock_token": unlock_token,
            "expires_in": 3600  # 1 hour in seconds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin unlock error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def verify_admin(current_user_id: str = Depends(get_current_user)):
    """Verify user is admin - fixed to use user_id string from get_current_user"""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Query user by id field first
    user = await db.users_collection.find_one({"id": current_user_id}, {"_id": 0})
    
    # Fallback to ObjectId if not found and format is valid (24 hex characters)
    if not user and len(current_user_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in current_user_id):
        try:
            user = await db.users_collection.find_one({"_id": ObjectId(current_user_id)})
        except InvalidId:
            pass  # Invalid ObjectId despite format check
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is admin
    is_admin = user.get('is_admin', False) or user.get('role') == 'admin'
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_user_id  # Return user_id string for consistency

@router.get("/users")
async def get_all_users(admin_user_id: str = Depends(verify_admin)):
    """Get all users with stats - properly serialized"""
    try:
        users = await db.users_collection.find({}, {"password_hash": 0}).to_list(1000)
        
        # Serialize and enrich with stats
        serialized_users = []
        for user in users:
            # Serialize the user document
            user_data = serialize_doc(user)
            user_id = user_data.get('id') or str(user.get('_id'))
            user_data['id'] = user_id  # Ensure id field exists
            
            # Remove _id if present
            user_data.pop('_id', None)
            
            # Count bots
            bot_count = await db.bots_collection.count_documents({"user_id": user_id})
            active_bots = await db.bots_collection.count_documents({
                "user_id": user_id,
                "status": "active"
            })
            
            # Count trades
            trade_count = await db.trades_collection.count_documents({"user_id": user_id})
            
            # Get total profit
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0, "total_profit": 1}
            ).to_list(1000)
            total_profit = sum(b.get('total_profit', 0) for b in bots)
            
            user_data['stats'] = {
                "total_bots": bot_count,
                "active_bots": active_bots,
                "total_trades": trade_count,
                "total_profit": round(total_profit, 2)
            }
            
            serialized_users.append(user_data)
        
        return {
            "users": serialized_users,
            "total_count": len(serialized_users)
        }
        
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_details(user_id: str, admin_user_id: str = Depends(verify_admin)):
    """Get detailed user information"""
    try:
        user = await db.users_collection.find_one({"id": user_id}, {"_id": 0, "password": 0})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get bots
        bots = await db.bots_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Get recent trades
        recent_trades = await db.trades_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50).to_list(50)
        
        # Get audit logs
        audit_logs = await audit_logger.get_user_audit_trail(user_id, days=30)
        
        return {
            "user": user,
            "bots": bots,
            "recent_trades": recent_trades[:10],  # Last 10 trades
            "audit_logs": audit_logs[:20],  # Last 20 audit events
            "stats": {
                "total_bots": len(bots),
                "total_trades": len(recent_trades),
                "total_profit": sum(b.get('total_profit', 0) for b in bots)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/block")
async def block_user(
    user_id: str,
    reason: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Block a user"""
    try:
        # Update user status
        result = await db.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "status": "blocked",
                    "blocked_at": datetime.now(timezone.utc).isoformat(),
                    "blocked_by": admin_user['id'],
                    "blocked_reason": reason
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Pause all user's bots
        await db.bots_collection.update_many(
            {"user_id": user_id},
            {"$set": {"status": "paused"}}
        )
        
        # Log action
        await audit_logger.log_event(
            event_type="user_blocked",
            user_id=admin_user['id'],
            details={
                "target_user_id": user_id,
                "reason": reason
            },
            severity="critical"
        )
        
        return {
            "success": True,
            "message": f"User {user_id} blocked",
            "blocked_by": admin_user['email']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Block user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: str, admin_user_id: str = Depends(verify_admin)):
    """Unblock a user"""
    try:
        result = await db.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "status": "active",
                    "unblocked_at": datetime.now(timezone.utc).isoformat(),
                    "unblocked_by": admin_user['id']
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log action
        await audit_logger.log_event(
            event_type="user_unblocked",
            user_id=admin_user['id'],
            details={"target_user_id": user_id},
            severity="warning"
        )
        
        return {
            "success": True,
            "message": f"User {user_id} unblocked"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unblock user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    new_password: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Reset user password (admin action)"""
    try:
        # Hash new password
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        result = await db.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "password": hashed.decode('utf-8'),
                    "password_reset_by_admin": True,
                    "password_reset_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log action
        await audit_logger.log_event(
            event_type="password_reset_by_admin",
            user_id=admin_user['id'],
            details={
                "target_user_id": user_id,
                "reset_by": admin_user['email']
            },
            severity="critical"
        )
        
        return {
            "success": True,
            "message": "Password reset successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    confirm: bool,
    admin_user_id: str = Depends(verify_admin)
):
    """Delete user and all their data (dangerous!)"""
    try:
        if not confirm:
            return {
                "success": False,
                "message": "Confirmation required. Set confirm=true to proceed."
            }
        
        # Delete all user's bots
        bots_result = await db.bots_collection.delete_many({"user_id": user_id})
        
        # Delete all user's trades
        trades_result = await db.trades_collection.delete_many({"user_id": user_id})
        
        # Delete user
        user_result = await db.users_collection.delete_one({"id": user_id})
        
        if user_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log action
        await audit_logger.log_event(
            event_type="user_deleted",
            user_id=admin_user['id'],
            details={
                "target_user_id": user_id,
                "bots_deleted": bots_result.deleted_count,
                "trades_deleted": trades_result.deleted_count,
                "deleted_by": admin_user['email']
            },
            severity="critical"
        )
        
        return {
            "success": True,
            "message": f"User deleted",
            "bots_deleted": bots_result.deleted_count,
            "trades_deleted": trades_result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_system_stats(admin_user_id: str = Depends(verify_admin)):
    """Get overall system statistics"""
    try:
        total_users = await db.users_collection.count_documents({})
        active_users = await db.users_collection.count_documents({"status": "active"})
        blocked_users = await db.users_collection.count_documents({"status": "blocked"})
        
        total_bots = await db.bots_collection.count_documents({})
        active_bots = await db.bots_collection.count_documents({"status": "active"})
        live_bots = await db.bots_collection.count_documents({"mode": "live"})
        
        total_trades = await db.trades_collection.count_documents({})
        live_trades = await db.trades_collection.count_documents({"is_paper": False})
        
        # Calculate total profit across all users
        all_bots = await db.bots_collection.find(
            {},
            {"_id": 0, "total_profit": 1}
        ).to_list(10000)
        total_profit = sum(b.get('total_profit', 0) for b in all_bots)
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "blocked": blocked_users
            },
            "bots": {
                "total": total_bots,
                "active": active_bots,
                "live": live_bots,
                "paper": total_bots - live_bots
            },
            "trades": {
                "total": total_trades,
                "live": live_trades,
                "paper": total_trades - live_trades
            },
            "profit": {
                "total": round(total_profit, 2)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get system stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/events")
async def get_audit_events(
    limit: int = 100,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    admin_user_id: str = Depends(verify_admin)
):
    """Get audit trail events for admin monitoring"""
    try:
        # Build query
        query = {}
        if user_id:
            query["user_id"] = user_id
        if event_type:
            query["event_type"] = event_type
        
        # Get events from audit logs collection
        events = await db.audit_logs_collection.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Serialize events
        serialized_events = serialize_list(events, exclude_fields=['_id'])
        
        return {
            "events": serialized_events,
            "total": len(serialized_events),
            "filters": {
                "user_id": user_id,
                "event_type": event_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Get audit events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
