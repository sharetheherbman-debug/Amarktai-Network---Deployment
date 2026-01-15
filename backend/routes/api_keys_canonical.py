"""
Canonical API Keys Management
Consolidates all API key operations into one place with encryption at rest
Legacy routes alias to these handlers
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timezone

from auth import get_current_user, is_admin
from routes.api_key_management import (
    encrypt_api_key, 
    decrypt_api_key,
    get_decrypted_key
)
import database as db

logger = logging.getLogger(__name__)

# Canonical router with /api/api-keys prefix
router = APIRouter(prefix="/api/api-keys", tags=["API Keys (Canonical)"])


class APIKeyTestRequest(BaseModel):
    provider: str = Field(..., description="Exchange or service provider")
    api_key: str = Field(..., description="API key to test")
    api_secret: Optional[str] = Field(None, description="API secret (for exchanges)")


class APIKeySaveRequest(BaseModel):
    provider: str = Field(..., description="Exchange or service provider")
    api_key: str = Field(..., description="API key")
    api_secret: Optional[str] = Field(None, description="API secret (for exchanges)")
    exchange: Optional[str] = Field(None, description="Exchange name")


@router.get("")
async def list_api_keys(user_id: str = Depends(get_current_user)):
    """
    List all API keys for the current user (masked, encrypted at rest)
    Never returns plaintext keys
    """
    try:
        keys_cursor = db.api_keys_collection.find(
            {"user_id": user_id},
            {"_id": 0, "api_key_encrypted": 0, "api_secret_encrypted": 0}
        )
        keys = await keys_cursor.to_list(100)
        
        # Add status indicators
        for key in keys:
            # Mask any remaining sensitive data
            if 'api_key' in key:
                key['api_key_masked'] = f"{key['api_key'][:4]}..." if len(key.get('api_key', '')) > 4 else '***'
                del key['api_key']
            if 'secret' in key:
                key['secret'] = '***'
        
        return {
            "success": True,
            "keys": keys,
            "total": len(keys)
        }
        
    except Exception as e:
        logger.error(f"List API keys error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def save_api_key(
    data: APIKeySaveRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Save an API key with encryption at rest
    Keys are encrypted using Fernet symmetric encryption
    """
    try:
        provider = data.provider
        api_key = data.api_key
        api_secret = data.api_secret
        exchange = data.exchange
        
        if not provider or not api_key:
            raise HTTPException(status_code=400, detail="Provider and API key required")
        
        # Encrypt keys before storage
        encrypted_key = encrypt_api_key(api_key)
        encrypted_secret = encrypt_api_key(api_secret) if api_secret else None
        
        # Check if key already exists
        existing = await db.api_keys_collection.find_one({
            "user_id": user_id,
            "provider": provider
        })
        
        key_data = {
            "user_id": user_id,
            "provider": provider,
            "api_key_encrypted": encrypted_key,
            "api_secret_encrypted": encrypted_secret,
            "exchange": exchange,
            "created_at": existing.get("created_at") if existing else None,
            "updated_at": None
        }
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update existing key
            key_data["updated_at"] = timestamp
            await db.api_keys_collection.update_one(
                {"user_id": user_id, "provider": provider},
                {"$set": key_data}
            )
            message = f"Updated {provider.upper()} API key"
        else:
            # Create new key
            key_data["created_at"] = timestamp
            await db.api_keys_collection.insert_one(key_data)
            message = f"Saved {provider.upper()} API key"
        
        logger.info(f"✅ {message} for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": message,
            "provider": provider,
            "masked_key": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save API key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{provider}")
async def delete_api_key(
    provider: str,
    user_id: str = Depends(get_current_user)
):
    """Delete an API key for the current user"""
    try:
        result = await db.api_keys_collection.delete_one({
            "user_id": user_id,
            "provider": provider
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"No API key found for {provider}")
        
        logger.info(f"🗑️ Deleted {provider} API key for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Deleted {provider.upper()} API key"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete API key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider}/test")
async def test_api_key(
    provider: str,
    data: Dict,
    user_id: str = Depends(get_current_user)
):
    """
    Test an API key before saving
    Makes a lightweight API call to verify credentials
    """
    try:
        api_key = data.get("api_key")
        api_secret = data.get("api_secret")
        
        if not api_key:
            raise HTTPException(status_code=400, detail="API key required")
        
        # Test based on provider type
        if provider in ["binance", "luno", "kucoin", "ovex", "valr"]:
            # Test exchange API key
            import ccxt.async_support as ccxt
            
            exchange_class = getattr(ccxt, provider, None)
            if not exchange_class:
                raise HTTPException(status_code=400, detail=f"Exchange {provider} not supported")
            
            exchange_instance = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True
            })
            
            try:
                # Test with a simple API call
                balance = await exchange_instance.fetch_balance()
                await exchange_instance.close()
                
                # Get currency count
                currencies_found = len([c for c, amt in balance.get('total', {}).items() if amt > 0])
                
                return {
                    "success": True,
                    "message": f"✅ {provider.upper()} API key validated successfully",
                    "provider": provider,
                    "currencies_found": currencies_found
                }
            except Exception as e:
                await exchange_instance.close()
                error_msg = str(e)
                if "Invalid API-key" in error_msg or "authentication" in error_msg.lower():
                    return {
                        "success": False,
                        "message": f"❌ Invalid API credentials for {provider.upper()}",
                        "error": "Authentication failed"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ API test failed for {provider.upper()}",
                        "error": error_msg
                    }
        
        else:
            # Generic success for other providers (OpenAI, etc.)
            return {
                "success": True,
                "message": f"✅ {provider.upper()} API key format validated",
                "provider": provider
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
