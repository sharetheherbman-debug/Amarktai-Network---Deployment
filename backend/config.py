"""
Production Configuration
All system limits and settings
Reads from environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# ENVIRONMENT VARIABLES (from .env)
# ============================================================================

# Database
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'amarktai_trading')

# Security
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')

# AI / OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Email (SMTP)
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER)
FROM_NAME = os.getenv('FROM_NAME', 'Amarktai Network')

# Optional Integrations
FETCHAI_API_KEY = os.getenv('FETCHAI_API_KEY', '')
FLOKX_API_KEY = os.getenv('FLOKX_API_KEY', '')

# ============================================================================
# FEATURE FLAGS (Safe defaults for production)
# ============================================================================

# Trading Feature Flags
ENABLE_TRADING = os.getenv('ENABLE_TRADING', 'false').lower() == 'true'
ENABLE_AUTOPILOT = os.getenv('ENABLE_AUTOPILOT', 'false').lower() == 'true'
ENABLE_CCXT = os.getenv('ENABLE_CCXT', 'true').lower() == 'true'  # Safe for price data
ENABLE_UAGENTS = os.getenv('ENABLE_UAGENTS', 'false').lower() == 'true'
PAYMENT_AGENT_ENABLED = os.getenv('PAYMENT_AGENT_ENABLED', 'false').lower() == 'true'

# Safe mode: All trading disabled by default
# Enable gradually:
# 1. ENABLE_CCXT=true (price data only)
# 2. ENABLE_TRADING=true + paper mode only
# 3. ENABLE_AUTOPILOT=true for autonomous management
# 4. Configure API keys and enable live trading

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

# Exchange bot limits (researched and safe)
EXCHANGE_BOT_LIMITS = {
    'luno': 5,
    'binance': 10,
    'kucoin': 10,
    'kraken': 10,
    'valr': 10
}

# Trading limits - Per exchange (configurable)
EXCHANGE_TRADE_LIMITS = {
    'luno': {
        'max_trades_per_bot_per_day': 75,
        'min_cooldown_minutes': 15,
        'max_api_calls_per_minute': 60
    },
    'binance': {
        'max_trades_per_bot_per_day': 150,
        'min_cooldown_minutes': 10,
        'max_api_calls_per_minute': 1200
    },
    'kucoin': {
        'max_trades_per_bot_per_day': 150,
        'min_cooldown_minutes': 10,
        'max_api_calls_per_minute': 600
    },
    'kraken': {
        'max_trades_per_bot_per_day': 100,
        'min_cooldown_minutes': 12,
        'max_api_calls_per_minute': 120
    },
    'valr': {
        'max_trades_per_bot_per_day': 100,
        'min_cooldown_minutes': 12,
        'max_api_calls_per_minute': 100
    }
}

# Global limits
MAX_TRADES_PER_USER_PER_DAY = 3000  # Total across all bots
MIN_TRADE_PROFIT_THRESHOLD_ZAR = 2.0  # Minimum net profit target (ignore 30c wins)

# Paper → Live promotion criteria
PAPER_TRAINING_DAYS = 7
MIN_WIN_RATE = 0.52  # 52%
MIN_PROFIT_PERCENT = 0.03  # 3%
MIN_TRADES_FOR_PROMOTION = 25

# Autopilot settings
REINVEST_THRESHOLD_ZAR = 500  # Reinvest every R500
NEW_BOT_CAPITAL = 1000  # R1000 minimum per bot
MAX_TOTAL_BOTS = 30
TOP_PERFORMERS_COUNT = 5

# AI Models
AI_MODELS = {
    'system_brain': 'gpt-5.1',  # Autopilot, risk, learning
    'trade_decision': 'gpt-4o',  # Per-bot decisions
    'reporting': 'gpt-4',  # Summaries, emails
    'chatops': 'gpt-4o'  # Dashboard chat
}

# Risk settings
STOP_LOSS_SAFE = 0.05  # 5%
STOP_LOSS_BALANCED = 0.10  # 10%
STOP_LOSS_AGGRESSIVE = 0.15  # 15%

# Rogue bot detection
MAX_HOURLY_LOSS_PERCENT = 0.15  # 15% in 1 hour
MAX_DRAWDOWN_PERCENT = 0.20  # 20%
