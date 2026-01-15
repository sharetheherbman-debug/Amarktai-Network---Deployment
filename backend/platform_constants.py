"""
Platform Constants - Single Source of Truth
Defines the 5 supported platforms for the entire system
"""

# Supported platforms (in display order)
SUPPORTED_PLATFORMS = ['luno', 'binance', 'kucoin', 'ovex', 'valr']

# Platform display configuration
PLATFORM_CONFIG = {
    'luno': {
        'id': 'luno',
        'name': 'Luno',
        'display_name': 'Luno',
        'icon': '🇿🇦',
        'color': '#3861FB',
        'max_bots': 5,
        'region': 'ZA',
        'requires_passphrase': False,
        'enabled': True
    },
    'binance': {
        'id': 'binance',
        'name': 'Binance',
        'display_name': 'Binance',
        'icon': '🟡',
        'color': '#F3BA2F',
        'max_bots': 10,
        'region': 'Global',
        'requires_passphrase': False,
        'enabled': True
    },
    'kucoin': {
        'id': 'kucoin',
        'name': 'KuCoin',
        'display_name': 'KuCoin',
        'icon': '🟢',
        'color': '#23AF91',
        'max_bots': 10,
        'region': 'Global',
        'requires_passphrase': True,  # KuCoin requires passphrase
        'enabled': True
    },
    'ovex': {
        'id': 'ovex',
        'name': 'OVEX',
        'display_name': 'OVEX',
        'icon': '🟠',
        'color': '#FF8C00',
        'max_bots': 10,
        'region': 'ZA',
        'requires_passphrase': False,
        'enabled': True
    },
    'valr': {
        'id': 'valr',
        'name': 'VALR',
        'display_name': 'VALR',
        'icon': '🔵',
        'color': '#00B8D4',
        'max_bots': 10,
        'region': 'ZA',
        'requires_passphrase': False,
        'enabled': True
    }
}

# Total bot capacity
TOTAL_BOT_CAPACITY = sum(p['max_bots'] for p in PLATFORM_CONFIG.values())  # 45

def get_platform_config(platform_id: str) -> dict:
    """Get configuration for a specific platform"""
    return PLATFORM_CONFIG.get(platform_id.lower(), {})

def is_valid_platform(platform_id: str) -> bool:
    """Check if platform ID is valid"""
    return platform_id.lower() in SUPPORTED_PLATFORMS

def get_enabled_platforms() -> list:
    """Get list of enabled platforms"""
    return [p for p in SUPPORTED_PLATFORMS if PLATFORM_CONFIG[p]['enabled']]

def get_platform_display_name(platform_id: str) -> str:
    """Get display name for platform"""
    config = get_platform_config(platform_id)
    return config.get('display_name', platform_id.upper())

def get_max_bots(platform_id: str) -> int:
    """Get max bots allowed for platform"""
    config = get_platform_config(platform_id)
    return config.get('max_bots', 0)
