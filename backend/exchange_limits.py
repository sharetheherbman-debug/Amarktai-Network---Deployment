"""Exchange rate limits and caps for safe trading"""

"""
Exchange Rate Limits - Based on Official Documentation & Research

SAFE PRODUCTION LIMITS (Per Exchange, 10 bots):
- Per Bot: 50 trades/day MAX
- Per Exchange: 500 trades/day MAX (10 bots × 50)
- Burst Protection: 10 orders per 10 seconds MAX

HARD EXCHANGE LIMITS (What they actually allow):
LUNO: 300 API calls/min (~100 trades/min theoretical)
BINANCE: 100 orders/10s, 200,000 orders/24h
KUCOIN: 45 orders/3s (~15 orders/second)

OUR USAGE: Hundreds of times below limits = ULTRA SAFE
"""

# GLOBAL LIMIT: 45 bots total across all exchanges
MAX_BOTS_GLOBAL = 45

# Bot allocation per exchange
BOT_ALLOCATION = {
    "luno": 5,
    "binance": 10,
    "kucoin": 10,
    "ovex": 10,
    "valr": 10
}

EXCHANGE_LIMITS = {
    "luno": {
        "max_bots": 5,
        "max_orders_per_day": 250,  # 5 bots × 50 trades
        "max_orders_per_minute": 60,
        "max_orders_per_10_seconds": 10,
        "max_orders_per_bot_per_day": 50,
        "fee_maker": 0.002,  # 0.2%
        "fee_taker": 0.0025,  # 0.25%
    },
    "binance": {
        "max_bots": 10,
        "max_orders_per_day": 500,  # 10 bots × 50 trades
        "max_orders_per_minute": 60,
        "max_orders_per_10_seconds": 10,
        "max_orders_per_bot_per_day": 50,
        "fee_maker": 0.001,  # 0.1%
        "fee_taker": 0.001,  # 0.1%
    },
    "kucoin": {
        "max_bots": 10,
        "max_orders_per_day": 500,  # 10 bots × 50 trades
        "max_orders_per_minute": 60,
        "max_orders_per_10_seconds": 10,
        "max_orders_per_bot_per_day": 50,
        "fee_maker": 0.001,  # 0.1%
        "fee_taker": 0.001,  # 0.1%
    },
    "ovex": {
        "max_bots": 10,
        "max_orders_per_day": 500,  # 10 bots × 50 trades
        "max_orders_per_minute": 60,
        "max_orders_per_10_seconds": 10,
        "max_orders_per_bot_per_day": 50,
        "fee_maker": 0.001,  # 0.1%
        "fee_taker": 0.0015,  # 0.15%
    },
    "valr": {
        "max_bots": 10,
        "max_orders_per_day": 500,  # 10 bots × 50 trades
        "max_orders_per_minute": 60,
        "max_orders_per_10_seconds": 10,
        "max_orders_per_bot_per_day": 50,
        "fee_maker": 0.0007,  # 0.07%
        "fee_taker": 0.00075,  # 0.075%
    },
}

def get_exchange_limits(exchange: str) -> dict:
    """Get limits for an exchange"""
    return EXCHANGE_LIMITS.get(exchange.lower(), EXCHANGE_LIMITS["luno"])

def get_fee_rate(exchange: str, order_type: str = "taker") -> float:
    """Get fee rate for exchange"""
    limits = get_exchange_limits(exchange)
    return limits.get(f"fee_{order_type}", 0.0025)
