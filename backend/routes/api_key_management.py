"""
API Key Management Router
Handles encrypted storage, validation, and testing of exchange/AI API keys
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Literal
import logging
import os
from cryptography.fernet import Fernet
import base64
import hashlib

from auth import get_current_user
import database as db
from models import APIKeyCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


def get_encryption_key() -> bytes:
    """Get or create encryption key for API keys
    
    Returns:
        Fernet encryption key
    """
    # In production, store this securely (e.g., AWS Secrets Manager, HashiCorp Vault)
    key_env = os.getenv("API_KEY_ENCRYPTION_KEY")
    
    if key_env:
        return base64.urlsafe_b64decode(key_env.encode())
    
    # Generate a deterministic key from JWT secret (NOT recommended for production)
    jwt_secret = os.getenv("JWT_SECRET", "default-dev-secret-change-in-production")
    key_material = hashlib.sha256(jwt_secret.encode()).digest()
    return base64.urlsafe_b64encode(key_material)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key (base64 encoded)
    """
    try:
        fernet = Fernet(get_encryption_key())
        encrypted = fernet.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise HTTPException(status_code=500, detail="Failed to encrypt API key")


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage
    
    Args:
        encrypted_key: Encrypted API key (base64 encoded)
        
    Returns:
        Plain text API key
    """
    try:
        fernet = Fernet(get_encryption_key())
        decoded = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt API key")


@router.post("/test")
async def test_api_key(
    data: Dict,
    user_id: str = Depends(get_current_user)
):
    """Test an API key before saving
    
    Makes a test API call to verify the key works
    
    Args:
        data: Contains provider, api_key, api_secret, exchange info
        user_id: Current user ID from auth
        
    Returns:
        Test result with success/error details
    """
    try:
        provider = data.get("provider")
        api_key = data.get("api_key")
        api_secret = data.get("api_secret")
        exchange = data.get("exchange")
        
        if not provider or not api_key:
            raise HTTPException(status_code=400, detail="Provider and API key required")
        
        # Test based on provider type
        if provider in ["binance", "luno", "kucoin", "kraken", "valr"]:
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
                # Test with a simple API call (fetch balance)
                balance = await exchange_instance.fetch_balance()
                await exchange_instance.close()
                
                # Get total balance
                total_usd = 0.0
                if 'total' in balance:
                    for currency, amount in balance['total'].items():
                        if amount > 0:
                            total_usd += amount  # Simplified - should convert to USD
                
                return {
                    "success": True,
                    "message": f"✅ {provider.upper()} API key validated successfully",
                    "provider": provider,
                    "test_data": {
                        "balance_available": True,
                        "currencies_found": len([c for c, amt in balance.get('total', {}).items() if amt > 0]),
                        "approximate_total": round(total_usd, 2)
                    }
                }
            except Exception as e:
                await exchange_instance.close()
                error_msg = str(e)
                if "Invalid API-key" in error_msg or "authentication" in error_msg.lower():
                    return {
                        "success": False,
                        "message": f"❌ Invalid API credentials for {provider.upper()}",
                        "error": "Authentication failed - check API key and secret"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ API test failed for {provider.upper()}",
                        "error": error_msg
                    }
        
        elif provider == "openai":
            # Test OpenAI API key
            import openai
            openai.api_key = api_key
            
            try:
                # Simple test call
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                
                return {
                    "success": True,
                    "message": "✅ OpenAI API key validated successfully",
                    "provider": provider,
                    "test_data": {
                        "model_accessible": True,
                        "models": ["gpt-3.5-turbo", "gpt-4"]
                    }
                }
            except Exception as e:
                error_msg = str(e)
                if "Invalid" in error_msg or "Incorrect" in error_msg:
                    return {
                        "success": False,
                        "message": "❌ Invalid OpenAI API key",
                        "error": "Authentication failed"
                    }
                else:
                    return {
                        "success": False,
                        "message": "❌ OpenAI API test failed",
                        "error": error_msg
                    }
        
        else:
            raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_api_key(
    data: Dict,
    user_id: str = Depends(get_current_user)
):
    """Save an API key with encryption
    
    Args:
        data: Contains provider, api_key, api_secret, exchange info
        user_id: Current user ID from auth
        
    Returns:
        Saved key info (without exposing actual keys)
    """
    try:
        provider = data.get("provider")
        api_key = data.get("api_key")
        api_secret = data.get("api_secret")
        exchange = data.get("exchange")
        
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
        
        from datetime import datetime, timezone
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
            "key_info": {
                "provider": provider,
                "exchange": exchange,
                "masked_key": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****",
                "saved_at": key_data.get("updated_at") or key_data.get("created_at")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save API key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_api_keys(user_id: str = Depends(get_current_user)):
    """List all saved API keys for user (without exposing actual keys)
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        List of saved keys with masked values
    """
    try:
        keys_cursor = db.api_keys_collection.find(
            {"user_id": user_id},
            {"_id": 0, "api_key_encrypted": 0, "api_secret_encrypted": 0}
        )
        keys = await keys_cursor.to_list(100)
        
        return {
            "success": True,
            "keys": keys,
            "total": len(keys)
        }
        
    except Exception as e:
        logger.error(f"List API keys error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{provider}")
async def delete_api_key(
    provider: str,
    user_id: str = Depends(get_current_user)
):
    """Delete an API key
    
    Args:
        provider: Provider name (e.g., 'binance', 'openai')
        user_id: Current user ID from auth
        
    Returns:
        Deletion confirmation
    """
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


async def get_decrypted_key(user_id: str, provider: str) -> Optional[Dict]:
    """Helper function to get and decrypt API keys
    
    Used internally by other services
    
    Args:
        user_id: User ID
        provider: Provider name
        
    Returns:
        Dict with decrypted api_key and api_secret, or None
    """
    try:
        key_doc = await db.api_keys_collection.find_one({
            "user_id": user_id,
            "provider": provider
        })
        
        if not key_doc:
            return None
        
        return {
            "api_key": decrypt_api_key(key_doc["api_key_encrypted"]),
            "api_secret": decrypt_api_key(key_doc["api_secret_encrypted"]) if key_doc.get("api_secret_encrypted") else None,
            "provider": provider,
            "exchange": key_doc.get("exchange")
        }
    except Exception as e:
        logger.error(f"Get decrypted key error: {e}")
        return None
