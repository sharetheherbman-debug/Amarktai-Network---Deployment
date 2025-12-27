"""
API endpoints for Autonomous Payment Agent

Provides REST API endpoints for managing payments, viewing transaction history,
and monitoring payment agent status.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from engines.payment_agent import payment_agent, PaymentType, PaymentStatus

router = APIRouter(prefix="/api/payment", tags=["Payment Agent"])


# Helper Functions
def validate_payment_type(payment_type_str: str) -> PaymentType:
    """
    Validate and convert payment type string to enum
    
    Args:
        payment_type_str: Payment type as string
    
    Returns:
        PaymentType enum
    
    Raises:
        HTTPException: If payment type is invalid
    """
    try:
        return PaymentType[payment_type_str.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment_type: {payment_type_str}. Valid types: {', '.join([t.name.lower() for t in PaymentType])}"
        )


def validate_payment_status(status_str: str) -> PaymentStatus:
    """
    Validate and convert payment status string to enum
    
    Args:
        status_str: Payment status as string
    
    Returns:
        PaymentStatus enum
    
    Raises:
        HTTPException: If status is invalid
    """
    try:
        return PaymentStatus[status_str.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status_str}. Valid statuses: {', '.join([s.name.lower() for s in PaymentStatus])}"
        )


# Request/Response Models
class PaymentRequest(BaseModel):
    """Request model for making a payment"""
    amount_fet: float = Field(..., gt=0, description="Amount to pay in FET")
    recipient: str = Field(..., description="Recipient Fetch address")
    payment_type: str = Field(..., description="Type of payment (alpha_signal, gas_fee, data_feed, etc.)")
    description: str = Field(..., max_length=256, description="Payment description")
    metadata: Optional[dict] = Field(default=None, description="Additional payment metadata")


class AlphaSignalPaymentRequest(BaseModel):
    """Request model for paying for alpha signal"""
    signal_provider: str = Field(..., description="Signal provider address")
    signal_id: str = Field(..., description="Unique signal identifier")
    amount_fet: float = Field(..., gt=0, description="Payment amount in FET")


class DataFeedPaymentRequest(BaseModel):
    """Request model for data feed subscription payment"""
    provider_address: str = Field(..., description="Data provider address")
    feed_name: str = Field(..., description="Name of data feed")
    duration_days: int = Field(..., gt=0, le=365, description="Subscription duration in days")
    amount_fet: float = Field(..., gt=0, description="Payment amount in FET")


class PaymentHistoryRequest(BaseModel):
    """Request model for payment history query"""
    payment_type: Optional[str] = Field(default=None, description="Filter by payment type")
    status: Optional[str] = Field(default=None, description="Filter by status")
    days: int = Field(default=7, ge=1, le=365, description="Number of days to look back")


class PaymentResponse(BaseModel):
    """Response model for payment transactions"""
    transaction_id: str
    payment_type: str
    amount: str
    currency: str
    recipient: str
    status: str
    timestamp: datetime
    description: str
    tx_hash: Optional[str] = None
    confirmation_height: Optional[int] = None
    gas_used: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: dict = {}


# Endpoints

@router.get("/status")
async def get_payment_agent_status():
    """
    Get Payment Agent status and configuration
    
    Returns:
        - enabled: Whether Payment Agent is enabled
        - wallet_address: Fetch wallet address
        - network: Network type (testnet/mainnet)
        - balance_fet: Current wallet balance
        - daily_budget_fet: Daily spending budget
        - daily_spent_fet: Amount spent today
        - budget_remaining_fet: Remaining budget for today
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        stats = payment_agent.get_payment_stats()
        return {
            "enabled": stats["enabled"],
            "wallet_address": stats["wallet_address"],
            "network": stats["network"],
            "balance_fet": stats["current_balance_fet"],
            "daily_budget_fet": stats["daily_budget_fet"],
            "daily_spent_fet": stats["daily_spent_fet"],
            "budget_remaining_fet": stats["budget_remaining_fet"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment agent status: {str(e)}")


@router.get("/stats")
async def get_payment_statistics():
    """
    Get detailed payment statistics and analytics
    
    Returns:
        - total_transactions: Total number of transactions
        - confirmed_transactions: Number of confirmed transactions
        - total_spent_fet: Total amount spent
        - success_rate: Payment success rate percentage
        - spending_by_type: Breakdown of spending by payment type
        - current_balance_fet: Current wallet balance
        - And more...
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        return payment_agent.get_payment_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment statistics: {str(e)}")


@router.post("/make-payment", response_model=PaymentResponse)
async def make_payment(request: PaymentRequest):
    """
    Make a payment using the Payment Agent
    
    Args:
        request: Payment details including amount, recipient, type, and description
    
    Returns:
        PaymentResponse with transaction status
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        # Validate payment type
        payment_type = validate_payment_type(request.payment_type)
        
        # Make payment
        transaction = await payment_agent.make_payment(
            amount_fet=Decimal(str(request.amount_fet)),
            recipient=request.recipient,
            payment_type=payment_type,
            description=request.description,
            metadata=request.metadata
        )
        
        return PaymentResponse(
            transaction_id=transaction.transaction_id,
            payment_type=transaction.payment_type.value,
            amount=str(transaction.amount),
            currency=transaction.currency,
            recipient=transaction.recipient,
            status=transaction.status.value,
            timestamp=transaction.timestamp,
            description=transaction.description,
            tx_hash=transaction.tx_hash,
            confirmation_height=transaction.confirmation_height,
            gas_used=str(transaction.gas_used) if transaction.gas_used else None,
            error_message=transaction.error_message,
            retry_count=transaction.retry_count,
            metadata=transaction.metadata
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")


@router.post("/pay-alpha-signal", response_model=PaymentResponse)
async def pay_for_alpha_signal(request: AlphaSignalPaymentRequest):
    """
    Pay for an external alpha trading signal
    
    Args:
        request: Signal provider, signal ID, and payment amount
    
    Returns:
        PaymentResponse with transaction status
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        transaction = await payment_agent.pay_for_alpha_signal(
            signal_provider=request.signal_provider,
            signal_id=request.signal_id,
            amount_fet=Decimal(str(request.amount_fet))
        )
        
        return PaymentResponse(
            transaction_id=transaction.transaction_id,
            payment_type=transaction.payment_type.value,
            amount=str(transaction.amount),
            currency=transaction.currency,
            recipient=transaction.recipient,
            status=transaction.status.value,
            timestamp=transaction.timestamp,
            description=transaction.description,
            tx_hash=transaction.tx_hash,
            confirmation_height=transaction.confirmation_height,
            gas_used=str(transaction.gas_used) if transaction.gas_used else None,
            error_message=transaction.error_message,
            retry_count=transaction.retry_count,
            metadata=transaction.metadata
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alpha signal payment failed: {str(e)}")


@router.post("/pay-data-feed", response_model=PaymentResponse)
async def pay_for_data_feed(request: DataFeedPaymentRequest):
    """
    Pay for market data feed subscription
    
    Args:
        request: Provider address, feed name, duration, and amount
    
    Returns:
        PaymentResponse with transaction status
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        transaction = await payment_agent.pay_for_data_feed(
            provider_address=request.provider_address,
            feed_name=request.feed_name,
            duration_days=request.duration_days,
            amount_fet=Decimal(str(request.amount_fet))
        )
        
        return PaymentResponse(
            transaction_id=transaction.transaction_id,
            payment_type=transaction.payment_type.value,
            amount=str(transaction.amount),
            currency=transaction.currency,
            recipient=transaction.recipient,
            status=transaction.status.value,
            timestamp=transaction.timestamp,
            description=transaction.description,
            tx_hash=transaction.tx_hash,
            confirmation_height=transaction.confirmation_height,
            gas_used=str(transaction.gas_used) if transaction.gas_used else None,
            error_message=transaction.error_message,
            retry_count=transaction.retry_count,
            metadata=transaction.metadata
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data feed payment failed: {str(e)}")


@router.post("/history", response_model=List[PaymentResponse])
async def get_payment_history(request: PaymentHistoryRequest):
    """
    Get payment transaction history with optional filters
    
    Args:
        request: Filters for payment type, status, and time range
    
    Returns:
        List of PaymentResponse objects matching filters
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        # Convert string filters to enums
        payment_type = validate_payment_type(request.payment_type) if request.payment_type else None
        status = validate_payment_status(request.status) if request.status else None
        
        # Get history
        transactions = payment_agent.get_payment_history(
            payment_type=payment_type,
            status=status,
            days=request.days
        )
        
        return [
            PaymentResponse(
                transaction_id=tx.transaction_id,
                payment_type=tx.payment_type.value,
                amount=str(tx.amount),
                currency=tx.currency,
                recipient=tx.recipient,
                status=tx.status.value,
                timestamp=tx.timestamp,
                description=tx.description,
                tx_hash=tx.tx_hash,
                confirmation_height=tx.confirmation_height,
                gas_used=str(tx.gas_used) if tx.gas_used else None,
                error_message=tx.error_message,
                retry_count=tx.retry_count,
                metadata=tx.metadata
            )
            for tx in transactions
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment history: {str(e)}")


@router.post("/request-testnet-funds")
async def request_testnet_funds():
    """
    Request testnet funds from Fetch.ai faucet (testnet only)
    
    Returns:
        Success status and new balance
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    if payment_agent.network_type != "testnet":
        raise HTTPException(status_code=400, detail="Faucet only available on testnet")
    
    try:
        success = await payment_agent.request_testnet_funds()
        
        if success:
            balance = payment_agent._get_balance()
            return {
                "success": True,
                "message": "Testnet funds requested successfully",
                "new_balance_fet": str(balance),
                "wallet_address": payment_agent.address
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to request testnet funds")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Faucet request failed: {str(e)}")


@router.get("/can-pay/{amount_fet}")
async def check_can_make_payment(amount_fet: float, payment_type: str = "alpha_signal"):
    """
    Check if a payment can be made given current budget and balance
    
    Args:
        amount_fet: Amount to check in FET
        payment_type: Type of payment to check
    
    Returns:
        can_pay: Boolean indicating if payment is possible
        reason: Explanation of result
    """
    if not payment_agent.enabled:
        raise HTTPException(status_code=503, detail="Payment Agent is disabled")
    
    try:
        # Validate payment type
        ptype = validate_payment_type(payment_type)
        
        can_pay, reason = await payment_agent.can_make_payment(
            amount_fet=Decimal(str(amount_fet)),
            payment_type=ptype
        )
        
        return {
            "can_pay": can_pay,
            "reason": reason,
            "amount_fet": amount_fet,
            "payment_type": payment_type
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check payment eligibility: {str(e)}")
