"""
Wallet Transfer System - Virtual Transfer Ledger
Handles fund transfers between providers/accounts for autopilot capital allocation
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import uuid

from auth import get_current_user
import database as db
from config.platforms import SUPPORTED_PLATFORMS, get_platform_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallet", tags=["Wallet"])


@router.get("/transfers")
async def get_transfers(
    user_id: str = Depends(get_current_user),
    limit: int = 100,
    status: Optional[str] = None
) -> dict:
    """
    Get transfer history for user
    
    Returns all fund transfers between providers
    Supports filtering by status
    """
    try:
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status
        
        transfers = await db.wallet_transfers_collection.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return {
            "success": True,
            "transfers": transfers,
            "count": len(transfers),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Get transfers error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transfers: {str(e)}")


@router.post("/transfer")
async def create_transfer(
    payload: Dict = Body(...),
    user_id: str = Depends(get_current_user)
) -> dict:
    """
    Create a fund transfer between providers
    
    Records transfer in virtual ledger. If real exchange transfer isn't possible via API,
    status is set to 'manual_required' with instructions for user.
    
    Body:
        {
            "from_provider": "luno",
            "to_provider": "binance",
            "amount": 1000.0,
            "currency": "ZAR",
            "reason": "autopilot_rebalance" | "manual_allocation" | "bot_funding"
        }
    """
    try:
        from_provider = payload.get("from_provider")
        to_provider = payload.get("to_provider")
        amount = payload.get("amount")
        currency = payload.get("currency", "ZAR")
        reason = payload.get("reason", "manual_allocation")
        
        # Validation
        if not from_provider or not to_provider:
            raise HTTPException(
                status_code=400,
                detail="Both from_provider and to_provider are required"
            )
        
        if from_provider == to_provider:
            raise HTTPException(
                status_code=400,
                detail="Cannot transfer to the same provider"
            )
        
        if not amount or amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Amount must be greater than 0"
            )
        
        # Validate providers exist
        if from_provider not in SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid from_provider: {from_provider}"
            )
        
        if to_provider not in SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid to_provider: {to_provider}"
            )
        
        # Check if user has API keys for both providers
        from_keys = await db.api_keys_collection.find_one({
            "user_id": user_id,
            "provider": from_provider
        })
        
        to_keys = await db.api_keys_collection.find_one({
            "user_id": user_id,
            "provider": to_provider
        })
        
        if not from_keys:
            raise HTTPException(
                status_code=400,
                detail=f"No API keys configured for {from_provider}"
            )
        
        if not to_keys:
            raise HTTPException(
                status_code=400,
                detail=f"No API keys configured for {to_provider}"
            )
        
        # Create transfer record
        transfer_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        
        # Most exchanges don't support direct transfers via API
        # So we create a ledger entry with status indicating manual action needed
        transfer_doc = {
            "id": transfer_id,
            "user_id": user_id,
            "from_provider": from_provider,
            "to_provider": to_provider,
            "amount": amount,
            "currency": currency,
            "status": "manual_required",  # Options: pending, manual_required, completed, failed
            "reason": reason,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "notes": f"Transfer of {amount} {currency} from {from_provider} to {to_provider}. Manual action required: Withdraw from {from_provider} and deposit to {to_provider}.",
            "instructions": [
                f"1. Log into {from_provider} exchange",
                f"2. Withdraw {amount} {currency} to your wallet",
                f"3. Log into {to_provider} exchange",
                f"4. Deposit {amount} {currency} from your wallet",
                f"5. Update transfer status to 'completed' when done"
            ]
        }
        
        result = await db.wallet_transfers_collection.insert_one(transfer_doc)
        
        logger.info(f"Transfer created: {transfer_id} - {from_provider} → {to_provider}, {amount} {currency}")
        
        return {
            "success": True,
            "transfer": {
                "id": transfer_id,
                "status": "manual_required",
                "message": "Transfer recorded. Manual action required for real exchange transfer.",
                "from_provider": from_provider,
                "to_provider": to_provider,
                "amount": amount,
                "currency": currency,
                "instructions": transfer_doc["instructions"]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create transfer error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create transfer: {str(e)}")


@router.patch("/transfer/{transfer_id}/status")
async def update_transfer_status(
    transfer_id: str,
    payload: Dict = Body(...),
    user_id: str = Depends(get_current_user)
) -> dict:
    """
    Update transfer status
    
    Allows user to mark transfer as completed, failed, etc.
    
    Body:
        {
            "status": "completed" | "failed" | "cancelled",
            "notes": "Optional notes"
        }
    """
    try:
        new_status = payload.get("status")
        notes = payload.get("notes", "")
        
        if new_status not in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be: completed, failed, or cancelled"
            )
        
        # Find transfer
        transfer = await db.wallet_transfers_collection.find_one({
            "id": transfer_id,
            "user_id": user_id
        })
        
        if not transfer:
            raise HTTPException(
                status_code=404,
                detail="Transfer not found"
            )
        
        # Update status
        update_doc = {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        if notes:
            update_doc["$set"]["user_notes"] = notes
        
        result = await db.wallet_transfers_collection.update_one(
            {"id": transfer_id, "user_id": user_id},
            update_doc
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to update transfer status"
            )
        
        logger.info(f"Transfer {transfer_id} status updated to: {new_status}")
        
        return {
            "success": True,
            "transfer_id": transfer_id,
            "status": new_status,
            "message": f"Transfer status updated to {new_status}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update transfer status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update transfer: {str(e)}")


@router.get("/balance/summary")
async def get_balance_summary(user_id: str = Depends(get_current_user)) -> dict:
    """
    Get wallet balance summary across all providers
    
    Returns aggregated balances from all configured exchanges
    """
    try:
        # Get all user's bots grouped by exchange
        bots = await db.bots_collection.find(
            {"user_id": user_id},
            {"_id": 0, "exchange": 1, "current_capital": 1, "status": 1}
        ).to_list(1000)
        
        # Aggregate capital by exchange
        balances_by_provider = {}
        
        for bot in bots:
            exchange = bot.get("exchange")
            capital = bot.get("current_capital", 0)
            
            if exchange not in balances_by_provider:
                balances_by_provider[exchange] = {
                    "total_capital": 0,
                    "bots_count": 0,
                    "active_bots": 0
                }
            
            balances_by_provider[exchange]["total_capital"] += capital
            balances_by_provider[exchange]["bots_count"] += 1
            
            if bot.get("status") == "active":
                balances_by_provider[exchange]["active_bots"] += 1
        
        # Calculate totals
        total_capital = sum(p["total_capital"] for p in balances_by_provider.values())
        total_bots = sum(p["bots_count"] for p in balances_by_provider.values())
        
        return {
            "success": True,
            "balances": balances_by_provider,
            "summary": {
                "total_capital": round(total_capital, 2),
                "total_bots": total_bots,
                "providers_count": len(balances_by_provider)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Get balance summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get balance summary: {str(e)}")
