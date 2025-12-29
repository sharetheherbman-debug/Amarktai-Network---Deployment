"""
Admin Dashboard Endpoints
User management, system monitoring, and administrative actions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
import logging
from datetime import datetime, timezone
import bcrypt

from auth import get_current_user
import database as db
from engines.audit_logger import audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

async def verify_admin(current_user: Dict = Depends(get_current_user)):
    """Verify user is admin"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/users")
async def get_all_users(admin_user: Dict = Depends(verify_admin)):
    """Get all users with stats"""
    try:
        users = await db.users_collection.find({}, {"_id": 0, "password": 0}).to_list(1000)
        
        # Enrich with stats
        for user in users:
            user_id = user['id']
            
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
            
            user['stats'] = {
                "total_bots": bot_count,
                "active_bots": active_bots,
                "total_trades": trade_count,
                "total_profit": round(total_profit, 2)
            }
        
        return {
            "users": users,
            "total_count": len(users)
        }
        
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_details(user_id: str, admin_user: Dict = Depends(verify_admin)):
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
    admin_user: Dict = Depends(verify_admin)
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
async def unblock_user(user_id: str, admin_user: Dict = Depends(verify_admin)):
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
    admin_user: Dict = Depends(verify_admin)
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
    admin_user: Dict = Depends(verify_admin)
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
async def get_system_stats(admin_user: Dict = Depends(verify_admin)):
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
