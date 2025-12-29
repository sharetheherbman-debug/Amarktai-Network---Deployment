from fastapi import HTTPException, Depends, APIRouter
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging

from models import User, UserLogin, Bot, BotCreate, APIKey, APIKeyCreate, Trade, SystemMode, Alert, ChatMessage, BotRiskMode
import database as db
from auth import create_access_token, get_current_user, get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()
from trading_scheduler import trading_scheduler


@router.get("/bots")
async def get_bots(user_id: str = Depends(get_current_user)):
    bots = await db.bots_collection.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    return bots


