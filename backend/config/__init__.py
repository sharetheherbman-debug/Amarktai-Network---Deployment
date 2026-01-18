"""
Config package
Re-exports constants from ../config.py for backward compatibility with imports like:
    from config import PAPER_TRAINING_DAYS
"""

# These constants are duplicated here to avoid circular import issues
# The canonical source is ../config.py
# When backend/config.py is updated, these should be kept in sync

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use environment variables directly

# Paper -> Live promotion criteria (most commonly imported)
PAPER_TRAINING_DAYS = 7
MIN_WIN_RATE = 0.52  # 52%
MIN_PROFIT_PERCENT = 0.03  # 3%
MIN_TRADES_FOR_PROMOTION = 25

# Exchange limits
EXCHANGE_BOT_LIMITS = {
    'luno': 5,
    'binance': 10,
    'kucoin': 10,
    'ovex': 10,
    'valr': 10
}

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
    'ovex': {
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
MAX_TRADES_PER_USER_PER_DAY = 3000
MIN_TRADE_PROFIT_THRESHOLD_ZAR = 2.0

# Autopilot settings
REINVEST_THRESHOLD_ZAR = 500
NEW_BOT_CAPITAL = 1000
MAX_TOTAL_BOTS = 30
TOP_PERFORMERS_COUNT = 5

# Risk settings
STOP_LOSS_SAFE = 0.05
STOP_LOSS_BALANCED = 0.10
STOP_LOSS_AGGRESSIVE = 0.15

MAX_HOURLY_LOSS_PERCENT = 0.15
MAX_DRAWDOWN_PERCENT = 0.20

# AI Models
AI_MODELS = {
    'system_brain': 'gpt-5.1',
    'trade_decision': 'gpt-4o',
    'reporting': 'gpt-4',
    'chatops': 'gpt-4o'
}

# Feature flags
ENABLE_TRADING = os.getenv('ENABLE_TRADING', 'false').lower() == 'true'
ENABLE_LIVE_TRADING = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
ENABLE_AUTOPILOT = os.getenv('ENABLE_AUTOPILOT', 'false').lower() == 'true'
ENABLE_SELF_LEARNING = os.getenv('ENABLE_SELF_LEARNING', 'true').lower() == 'true'
ENABLE_SELF_HEALING = os.getenv('ENABLE_SELF_HEALING', 'true').lower() == 'true'
ENABLE_CCXT = os.getenv('ENABLE_CCXT', 'true').lower() == 'true'
ENABLE_UAGENTS = os.getenv('ENABLE_UAGENTS', 'false').lower() == 'true'
PAYMENT_AGENT_ENABLED = os.getenv('PAYMENT_AGENT_ENABLED', 'false').lower() == 'true'

__all__ = [
    'PAPER_TRAINING_DAYS', 'MIN_WIN_RATE', 'MIN_PROFIT_PERCENT', 'MIN_TRADES_FOR_PROMOTION',
    'EXCHANGE_BOT_LIMITS', 'EXCHANGE_TRADE_LIMITS',
    'MAX_TRADES_PER_USER_PER_DAY', 'MIN_TRADE_PROFIT_THRESHOLD_ZAR',
    'REINVEST_THRESHOLD_ZAR', 'NEW_BOT_CAPITAL', 'MAX_TOTAL_BOTS', 'TOP_PERFORMERS_COUNT',
    'AI_MODELS',
    'STOP_LOSS_SAFE', 'STOP_LOSS_BALANCED', 'STOP_LOSS_AGGRESSIVE',
    'MAX_HOURLY_LOSS_PERCENT', 'MAX_DRAWDOWN_PERCENT',
    'ENABLE_TRADING', 'ENABLE_LIVE_TRADING', 'ENABLE_AUTOPILOT',
    'ENABLE_SELF_LEARNING', 'ENABLE_SELF_HEALING', 'ENABLE_CCXT',
    'ENABLE_UAGENTS', 'PAYMENT_AGENT_ENABLED'
]
