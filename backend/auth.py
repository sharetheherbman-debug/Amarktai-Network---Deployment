from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id: str = payload.get("user_id")  # Changed from "sub" to "user_id"
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return user_id

async def verify_admin_password(password: str) -> bool:
    """Verify admin password"""
    admin_password = os.getenv("ADMIN_PASSWORD", "ashmor12@")
    return password == admin_password

async def is_admin(user_id: str) -> bool:
    """Check if user has admin privileges - never crashes"""
    try:
        import database as db
        user = await db.users_collection.find_one({"id": user_id}, {"_id": 0})
        if not user:
            return False
        # Check if user has is_admin field set to True or role == 'admin'
        return user.get('is_admin', False) or user.get('role', '') == 'admin'
    except Exception as e:
        # Log error but don't crash - default to non-admin
        import logging
        logging.getLogger(__name__).error(f"Error checking admin status: {e}")
        return False

async def require_admin(user_id: str = Depends(get_current_user)) -> str:
    """Require user to be admin, raises 403 if not"""
    if not await is_admin(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user_id
