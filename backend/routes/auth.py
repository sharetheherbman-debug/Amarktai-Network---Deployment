from fastapi import HTTPException, Depends, APIRouter
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging

from models import User, UserLogin, Bot, BotCreate, APIKey, APIKeyCreate, Trade, SystemMode, Alert, ChatMessage, BotRiskMode
import database as db
from auth import create_access_token, get_current_user, get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/auth/register")
async def register(user: User):
    existing = await db.users_collection.find_one({"email": user.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user.model_dump()
    user_dict['password_hash'] = get_password_hash(user_dict['password_hash'])
    user_dict['created_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.users_collection.insert_one(user_dict)
    
    token = create_access_token({"user_id": user.id})
    return {"token": token, "user": {k: v for k, v in user_dict.items() if k != 'password_hash'}}


@router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users_collection.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"user_id": user['id']})
    return {"token": token, "user": {k: v for k, v in user.items() if k != 'password_hash'}}


@router.get("/auth/me")
async def get_current_user_profile(user_id: str = Depends(get_current_user)):
    user = await db.users_collection.find_one({"id": user_id}, {"_id": 0})
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
        return {"message": "Profile updated", "user": {k: v for k, v in user.items() if k != 'password'}}
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


