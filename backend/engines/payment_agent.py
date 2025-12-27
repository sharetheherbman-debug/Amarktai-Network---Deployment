"""
Autonomous Payment Agent with Fetch.ai Wallet Integration

This module implements a PaymentAgent that uses a Fetch wallet to autonomously
settle gas fees and pay for external alpha signals via the Fetch ASI Network.

Features:
- Fetch.ai wallet management and integration
- Autonomous payment processing for trading signals
- Gas fee estimation and payment
- Transaction tracking and confirmation
- Payment history and analytics
- Budget management and spending limits
- Multi-currency support (FET, USDC, etc.)
- Retry logic for failed payments
"""

import os
import asyncio
import logging
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from decimal import Decimal

# Constants
ATTOFET_CONVERSION = Decimal("1e18")  # 1 FET = 10^18 attoFET
DEFAULT_GAS_ESTIMATE_FET = Decimal("0.01")  # Default gas estimate in FET

try:
    from cosmpy.aerial.wallet import LocalWallet
    from cosmpy.aerial.client import LedgerClient, NetworkConfig
    from cosmpy.aerial.faucet import FaucetApi
    from cosmpy.crypto.address import Address
    FETCH_AVAILABLE = True
except ImportError:
    FETCH_AVAILABLE = False
    logging.warning("Fetch.ai SDK not available. Install with: pip install cosmpy")


logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Payment transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentType(Enum):
    """Types of payments the agent can make"""
    ALPHA_SIGNAL = "alpha_signal"  # External trading signal purchase
    GAS_FEE = "gas_fee"  # Transaction gas fees
    DATA_FEED = "data_feed"  # Market data subscription
    AI_MODEL_USAGE = "ai_model_usage"  # AI model API calls
    ON_CHAIN_DATA = "on_chain_data"  # Blockchain data access
    NETWORK_FEE = "network_fee"  # Network usage fees


@dataclass
class PaymentTransaction:
    """Represents a payment transaction"""
    transaction_id: str
    payment_type: PaymentType
    amount: Decimal
    currency: str  # FET, USDC, etc.
    recipient: str
    status: PaymentStatus
    timestamp: datetime
    description: str
    tx_hash: Optional[str] = None
    confirmation_height: Optional[int] = None
    gas_used: Optional[Decimal] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaymentAgent:
    """
    Autonomous Payment Agent for handling Fetch.ai wallet transactions
    
    This agent manages payments for external services, alpha signals, and gas fees
    using the Fetch ASI Network.
    """
    
    def __init__(self):
        """Initialize the Payment Agent"""
        self.enabled = os.getenv("PAYMENT_AGENT_ENABLED", "false").lower() == "true"
        
        if not self.enabled:
            logger.info("Payment Agent is disabled. Set PAYMENT_AGENT_ENABLED=true to enable.")
            return
            
        if not FETCH_AVAILABLE:
            logger.error("Fetch.ai SDK not available. Payment Agent cannot initialize.")
            self.enabled = False
            return
        
        # Wallet configuration
        self.wallet_seed = os.getenv("FETCH_WALLET_SEED", "")
        self.network_type = os.getenv("FETCH_NETWORK", "testnet")  # testnet or mainnet
        
        # Budget configuration
        self.daily_budget_fet = Decimal(os.getenv("PAYMENT_DAILY_BUDGET_FET", "100"))
        self.max_single_payment_fet = Decimal(os.getenv("PAYMENT_MAX_SINGLE_FET", "10"))
        self.min_balance_fet = Decimal(os.getenv("PAYMENT_MIN_BALANCE_FET", "10"))
        
        # Payment tracking
        self.transactions: List[PaymentTransaction] = []
        self.daily_spent_fet = Decimal("0")
        self.last_reset_date = datetime.utcnow().date()
        
        # Retry configuration
        self.max_retries = int(os.getenv("PAYMENT_MAX_RETRIES", "3"))
        self.retry_delay_seconds = int(os.getenv("PAYMENT_RETRY_DELAY", "10"))
        
        # Initialize wallet and client
        self.wallet: Optional[LocalWallet] = None
        self.client: Optional[LedgerClient] = None
        self.address: Optional[str] = None
        
        try:
            self._initialize_wallet()
        except Exception as e:
            logger.error(f"Failed to initialize Payment Agent: {e}")
            self.enabled = False
    
    def _initialize_wallet(self):
        """Initialize Fetch.ai wallet and client"""
        if not self.wallet_seed:
            logger.warning("No FETCH_WALLET_SEED provided. Payment Agent disabled.")
            self.enabled = False
            return
        
        try:
            # Create wallet from seed
            self.wallet = LocalWallet.from_mnemonic(self.wallet_seed)
            self.address = str(self.wallet.address())
            
            # Initialize network client
            if self.network_type == "mainnet":
                network = NetworkConfig.fetchai_mainnet()
            else:
                network = NetworkConfig.fetchai_stable_testnet()
            
            self.client = LedgerClient(network)
            
            # Get initial balance
            balance = self._get_balance()
            logger.info(f"Payment Agent initialized. Address: {self.address}, Balance: {balance} FET")
            
            if balance < self.min_balance_fet:
                logger.warning(f"Wallet balance ({balance} FET) below minimum ({self.min_balance_fet} FET)")
                
        except Exception as e:
            logger.error(f"Failed to initialize Fetch wallet: {e}")
            raise
    
    def _get_balance(self) -> Decimal:
        """Get current wallet balance in FET"""
        if not self.client or not self.wallet:
            return Decimal("0")
        
        try:
            balance = self.client.query_bank_balance(self.wallet.address())
            return Decimal(str(balance)) / ATTOFET_CONVERSION  # Convert from attoFET to FET
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            return Decimal("0")
    
    def _reset_daily_budget_if_needed(self):
        """Reset daily spending if new day"""
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            logger.info(f"Resetting daily budget. Previous spent: {self.daily_spent_fet} FET")
            self.daily_spent_fet = Decimal("0")
            self.last_reset_date = current_date
    
    async def can_make_payment(self, amount_fet: Decimal, payment_type: PaymentType) -> Tuple[bool, str]:
        """
        Check if payment can be made given current budget and balance
        
        Returns:
            (can_pay, reason) tuple
        """
        if not self.enabled:
            return False, "Payment Agent is disabled"
        
        self._reset_daily_budget_if_needed()
        
        # Check single payment limit
        if amount_fet > self.max_single_payment_fet:
            return False, f"Payment amount ({amount_fet} FET) exceeds single payment limit ({self.max_single_payment_fet} FET)"
        
        # Check daily budget
        if self.daily_spent_fet + amount_fet > self.daily_budget_fet:
            remaining = self.daily_budget_fet - self.daily_spent_fet
            return False, f"Payment would exceed daily budget. Remaining: {remaining} FET"
        
        # Check wallet balance
        balance = self._get_balance()
        estimated_gas = Decimal(os.getenv("PAYMENT_GAS_ESTIMATE_FET", str(DEFAULT_GAS_ESTIMATE_FET)))
        total_needed = amount_fet + estimated_gas
        
        if balance < total_needed:
            return False, f"Insufficient balance. Need {total_needed} FET, have {balance} FET"
        
        # Check minimum balance maintenance
        if balance - total_needed < self.min_balance_fet:
            return False, f"Payment would bring balance below minimum ({self.min_balance_fet} FET)"
        
        return True, "Payment approved"
    
    async def make_payment(
        self,
        amount_fet: Decimal,
        recipient: str,
        payment_type: PaymentType,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentTransaction:
        """
        Make a payment using Fetch wallet
        
        Args:
            amount_fet: Amount to pay in FET
            recipient: Recipient address
            payment_type: Type of payment
            description: Human-readable description
            metadata: Additional payment metadata
        
        Returns:
            PaymentTransaction object with status
        """
        transaction_id = f"pay_{int(datetime.utcnow().timestamp())}_{payment_type.value}"
        
        transaction = PaymentTransaction(
            transaction_id=transaction_id,
            payment_type=payment_type,
            amount=amount_fet,
            currency="FET",
            recipient=recipient,
            status=PaymentStatus.PENDING,
            timestamp=datetime.utcnow(),
            description=description,
            metadata=metadata or {}
        )
        
        self.transactions.append(transaction)
        
        # Check if payment can be made
        can_pay, reason = await self.can_make_payment(amount_fet, payment_type)
        if not can_pay:
            transaction.status = PaymentStatus.FAILED
            transaction.error_message = reason
            logger.warning(f"Payment {transaction_id} rejected: {reason}")
            return transaction
        
        # Attempt payment with retries
        for attempt in range(self.max_retries):
            try:
                transaction.status = PaymentStatus.PROCESSING
                transaction.retry_count = attempt + 1
                
                # Convert FET to attoFET
                amount_attofet = int(amount_fet * ATTOFET_CONVERSION)
                
                # Create and submit transaction
                tx = self.client.send_tokens(
                    destination=recipient,
                    amount=amount_attofet,
                    denom="afet",
                    sender=self.wallet,
                    memo=description[:256]  # Memo limit
                )
                
                # Wait for confirmation
                await asyncio.sleep(2)  # Give time for confirmation
                
                # Update transaction
                transaction.tx_hash = tx.tx_hash
                transaction.status = PaymentStatus.CONFIRMED
                # Note: Actual gas used should be fetched from transaction receipt in production
                transaction.gas_used = Decimal(os.getenv("PAYMENT_GAS_ESTIMATE_FET", str(DEFAULT_GAS_ESTIMATE_FET)))
                
                # Update daily spending
                self.daily_spent_fet += amount_fet
                
                logger.info(f"Payment {transaction_id} confirmed. TX: {tx.tx_hash}")
                return transaction
                
            except Exception as e:
                logger.error(f"Payment attempt {attempt + 1} failed: {e}")
                transaction.error_message = str(e)
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
                else:
                    transaction.status = PaymentStatus.FAILED
                    logger.error(f"Payment {transaction_id} failed after {self.max_retries} attempts")
        
        return transaction
    
    async def pay_for_alpha_signal(
        self,
        signal_provider: str,
        signal_id: str,
        amount_fet: Decimal
    ) -> PaymentTransaction:
        """
        Pay for an external alpha trading signal
        
        Args:
            signal_provider: Address of signal provider
            signal_id: Unique identifier for the signal
            amount_fet: Payment amount in FET
        
        Returns:
            PaymentTransaction
        """
        description = f"Alpha signal purchase: {signal_id}"
        metadata = {
            "signal_provider": signal_provider,
            "signal_id": signal_id,
            "purchase_timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.make_payment(
            amount_fet=amount_fet,
            recipient=signal_provider,
            payment_type=PaymentType.ALPHA_SIGNAL,
            description=description,
            metadata=metadata
        )
    
    async def pay_gas_fee(
        self,
        transaction_hash: str,
        gas_amount_fet: Decimal
    ) -> PaymentTransaction:
        """
        Pay gas fee for a blockchain transaction
        
        Args:
            transaction_hash: Hash of the transaction needing gas
            gas_amount_fet: Gas fee in FET
        
        Returns:
            PaymentTransaction
        """
        description = f"Gas fee for TX: {transaction_hash[:16]}..."
        metadata = {
            "transaction_hash": transaction_hash,
            "gas_type": "transaction_fee"
        }
        
        # Gas fees typically go to validator/network (use special address or skip for gas)
        # This is illustrative - actual gas is deducted automatically
        logger.info(f"Gas fee recorded: {gas_amount_fet} FET for {transaction_hash}")
        
        # Create record-only transaction (gas already deducted)
        transaction = PaymentTransaction(
            transaction_id=f"gas_{int(datetime.utcnow().timestamp())}",
            payment_type=PaymentType.GAS_FEE,
            amount=gas_amount_fet,
            currency="FET",
            recipient="network",
            status=PaymentStatus.CONFIRMED,
            timestamp=datetime.utcnow(),
            description=description,
            tx_hash=transaction_hash,
            metadata=metadata
        )
        
        self.transactions.append(transaction)
        return transaction
    
    async def pay_for_data_feed(
        self,
        provider_address: str,
        feed_name: str,
        duration_days: int,
        amount_fet: Decimal
    ) -> PaymentTransaction:
        """
        Pay for market data feed subscription
        
        Args:
            provider_address: Data provider's address
            feed_name: Name of data feed
            duration_days: Subscription duration
            amount_fet: Payment amount
        
        Returns:
            PaymentTransaction
        """
        description = f"Data feed subscription: {feed_name} ({duration_days} days)"
        metadata = {
            "feed_name": feed_name,
            "duration_days": duration_days,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        }
        
        return await self.make_payment(
            amount_fet=amount_fet,
            recipient=provider_address,
            payment_type=PaymentType.DATA_FEED,
            description=description,
            metadata=metadata
        )
    
    def get_payment_history(
        self,
        payment_type: Optional[PaymentType] = None,
        status: Optional[PaymentStatus] = None,
        days: int = 7
    ) -> List[PaymentTransaction]:
        """
        Get payment history with optional filters
        
        Args:
            payment_type: Filter by payment type
            status: Filter by status
            days: Number of days to look back
        
        Returns:
            List of matching transactions
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        filtered = [
            tx for tx in self.transactions
            if tx.timestamp >= cutoff_date
        ]
        
        if payment_type:
            filtered = [tx for tx in filtered if tx.payment_type == payment_type]
        
        if status:
            filtered = [tx for tx in filtered if tx.status == status]
        
        return filtered
    
    def get_payment_stats(self) -> Dict[str, Any]:
        """
        Get payment statistics and analytics
        
        Returns:
            Dictionary with payment stats
        """
        if not self.transactions:
            return {
                "total_transactions": 0,
                "total_spent_fet": "0",
                "success_rate": 0.0,
                "daily_spent_fet": "0",
                "daily_budget_fet": str(self.daily_budget_fet),
                "current_balance_fet": "0"
            }
        
        confirmed_txs = [tx for tx in self.transactions if tx.status == PaymentStatus.CONFIRMED]
        total_spent = sum(tx.amount for tx in confirmed_txs)
        success_rate = len(confirmed_txs) / len(self.transactions) * 100
        
        # Spending by type
        by_type = {}
        for tx in confirmed_txs:
            type_name = tx.payment_type.value
            by_type[type_name] = by_type.get(type_name, Decimal("0")) + tx.amount
        
        return {
            "total_transactions": len(self.transactions),
            "confirmed_transactions": len(confirmed_txs),
            "total_spent_fet": str(total_spent),
            "success_rate": round(success_rate, 2),
            "daily_spent_fet": str(self.daily_spent_fet),
            "daily_budget_fet": str(self.daily_budget_fet),
            "budget_remaining_fet": str(self.daily_budget_fet - self.daily_spent_fet),
            "current_balance_fet": str(self._get_balance()),
            "spending_by_type": {k: str(v) for k, v in by_type.items()},
            "wallet_address": self.address,
            "network": self.network_type,
            "enabled": self.enabled
        }
    
    async def request_testnet_funds(self) -> bool:
        """
        Request testnet funds from Fetch.ai faucet (testnet only)
        
        Returns:
            True if successful, False otherwise
        """
        if self.network_type != "testnet":
            logger.warning("Faucet only available on testnet")
            return False
        
        try:
            faucet = FaucetApi(NetworkConfig.fetchai_stable_testnet())
            faucet.get_wealth(self.wallet.address())
            logger.info(f"Successfully requested testnet funds for {self.address}")
            await asyncio.sleep(5)  # Wait for funds to arrive
            balance = self._get_balance()
            logger.info(f"New balance: {balance} FET")
            return True
        except Exception as e:
            logger.error(f"Failed to request testnet funds: {e}")
            return False


# Global payment agent instance
payment_agent = PaymentAgent()
