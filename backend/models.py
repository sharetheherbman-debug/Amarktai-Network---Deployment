from pydantic import BaseModel, Field, ConfigDict, EmailStr, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"

class BotRiskMode(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

class SystemMode(str, Enum):
    TESTING = "testing"
    LIVE_TRADING = "live_trading"
    AUTOPILOT = "autopilot"

class BotStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"

# User Models
class UserCreate(BaseModel):
    first_name: str
    email: EmailStr
    password: str
    invite_code: str

class UserRegister(BaseModel):
    """Registration model with backward compatibility for password_hash and name->first_name"""
    first_name: Optional[str] = None
    name: Optional[str] = None  # Legacy field, mapped to first_name
    email: EmailStr
    password: Optional[str] = None
    password_hash: Optional[str] = None  # Legacy field, treated as plain password
    invite_code: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_name_fields(self):
        """Map name to first_name for backward compatibility and validate"""
        if self.name and not self.first_name:
            self.first_name = self.name
        if not self.first_name:
            raise ValueError("Either 'first_name' or 'name' field is required for registration")
        return self

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str
    email: EmailStr
    password_hash: str
    currency: str = "ZAR"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    system_mode: SystemMode = SystemMode.TESTING
    autopilot_enabled: bool = True
    bodyguard_enabled: bool = True
    learning_enabled: bool = True
    emergency_stop: bool = False
    blocked: bool = False
    is_admin: bool = False  # Admin flag (no roles, just boolean)
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None

# API Keys Models
class APIKeyCreate(BaseModel):
    provider: str  # openai, luno, binance, kucoin, fetchai, flokx
    api_key: str
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    testnet: bool = False  # Mainnet only

class APIKey(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: str
    api_key: str
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    testnet: bool = False  # Mainnet only
    connected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Bot Models
class BotCreate(BaseModel):
    name: str
    exchange: str  # luno, binance, kucoin
    risk_mode: BotRiskMode
    trading_mode: TradingMode = TradingMode.PAPER
    initial_capital: float = 0

class Bot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    exchange: str
    risk_mode: BotRiskMode
    trading_mode: TradingMode
    status: BotStatus = BotStatus.ACTIVE
    initial_capital: float
    current_capital: float
    total_profit: float = 0
    win_rate: float = 0
    trades_count: int = 0
    max_drawdown: float = 0
    stop_loss_percent: float = 15.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    paper_start_date: Optional[datetime] = None
    promoted_to_live: bool = False
    strategy: Dict[str, Any] = {}
    learned_insights: List[str] = []

# Trade Models
class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bot_id: str
    user_id: str
    exchange: str
    symbol: str
    side: str  # buy, sell
    amount: float
    price: float
    profit_loss: float = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trading_mode: TradingMode

# Learning Data Models
class LearningData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    insights: List[str] = []
    market_conditions: Dict[str, Any] = {}
    bot_performance: Dict[str, Any] = {}
    strategy_adjustments: List[str] = []
    daily_summary: str = ""

# Alerts Models
class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    bot_id: Optional[str] = None
    type: str  # bodyguard, system, user
    severity: str  # low, medium, high, critical
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dismissed: bool = False

# Audit Log Models
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    action: str
    details: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Chat Models
class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role: str  # user, assistant
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Profile Update
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    email: Optional[EmailStr] = None
    currency: Optional[str] = None
    password: Optional[str] = None
    new_password: Optional[str] = None

# System Metrics
class SystemMetrics(BaseModel):
    api_status: str
    sse_status: str
    websocket_status: str
    total_profit: float
    active_bots: int
    exposure: float
    risk_level: str
    ai_sentiment: str
    last_update: datetime
