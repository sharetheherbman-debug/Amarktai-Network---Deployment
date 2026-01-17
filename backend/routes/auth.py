from fastapi import HTTPException, Depends, APIRouter, Request
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging
from uuid import uuid4

from models import User, UserLogin, UserRegister, Bot, BotCreate, APIKey, APIKeyCreate, Trade, SystemMode, Alert, ChatMessage, BotRiskMode
import database as db
from auth import create_access_token, get_current_user, get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/auth/register")
async def register(request: Request, user: UserRegister):
    # Check invite code from header or body
    expected = (os.getenv("INVITE_CODE") or "").strip()
    provided_header = (request.headers.get("X-Invite-Code") or "").strip()
    provided_body = (user.invite_code or "").strip()
    provided = provided_header or provided_body
    
    if expected and provided != expected:
        raise HTTPException(status_code=403, detail="Invalid invite code")
    
    # Validate password: exactly one of password or password_hash must be provided
    if not user.password and not user.password_hash:
        raise HTTPException(status_code=400, detail="Either password or password_hash is required")
    if user.password and user.password_hash:
        raise HTTPException(status_code=400, detail="Provide either password or password_hash, not both")
    
    # Get plain password (prefer password field, treat password_hash as plain password for legacy)
    plain_password = user.password if user.password else user.password_hash

    # Normalize email to lowercase for consistency
    normalized_email = user.email.lower().strip()
    
    existing = await db.users_collection.find_one({"email": normalized_email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user dict
    user_id = str(uuid4())
    user_dict = {
        "id": user_id,
        "first_name": user.first_name,
        "email": normalized_email,
        "password_hash": get_password_hash(plain_password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "currency": "ZAR",
        "system_mode": "testing",
        "autopilot_enabled": True,
        "bodyguard_enabled": True,
        "learning_enabled": True,
        "emergency_stop": False,
        "blocked": False,
        "two_factor_enabled": False
    }

    res = await db.users_collection.insert_one(user_dict)
    user_dict.pop("_id", None)

    # Create token
    access_token = create_access_token({"user_id": user_id})
    
    # Return with both new and legacy fields
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "token": access_token,  # Legacy field for backward compatibility
        "user": {k: v for k, v in user_dict.items() if k != "password_hash"}
    }




@router.post("/auth/login")
async def login(credentials: UserLogin):
    # Normalize email to lowercase for consistency
    normalized_email = credentials.email.lower().strip()
    
    user = await db.users_collection.find_one({"email": normalized_email}, {"_id": 0})
    
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"user_id": user['id']})
    
    # Return with both new and legacy fields
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "token": access_token,  # Legacy field for backward compatibility
        "user": {k: v for k, v in user.items() if k != 'password_hash'}
    }


@router.get("/auth/me")
async def get_current_user_profile(user_id: str = Depends(get_current_user)):
    """Get current user profile - tries both 'id' field and MongoDB '_id' ObjectId"""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # First try with string id field (preferred)
    user = await db.users_collection.find_one({"id": user_id}, {"_id": 0})
    
    # If not found, try with ObjectId (fallback for older users)
    if not user:
        # Validate ObjectId format before querying (24 hex characters)
        if len(user_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in user_id):
            try:
                user = await db.users_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    # Remove _id and use id field going forward
                    user.pop("_id", None)
                    # Ensure id field exists for future queries
                    if "id" not in user:
                        user["id"] = user_id
            except InvalidId:
                pass  # Invalid ObjectId despite format check
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {k: v for k, v in user.items() if k != 'password_hash'}


@router.put("/auth/profile")
async def update_profile(update: dict, user_id: str = Depends(get_current_user)):
    """Update user profile - FIXED"""
    try:
        update_data = {k: v for k, v in update.items() if v is not None}
        
        if update_data:
            await db.users_collection.update_one(
                {"id": user_id},
                {"$set": update_data}
            )
        
        # Clear AI chat cache to use new name
        if 'first_name' in update_data and user_id in ai_service.chats:
            del ai_service.chats[user_id]
            logger.info(f"Cleared AI chat cache for user {user_id} after name update")
        
        user = await db.users_collection.find_one({"id": user_id}, {"_id": 0})
        return {"message": "Profile updated", "user": {k: v for k, v in user.items() if k != 'password_hash'}}
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


