/**
 * Platform Constants - Single Source of Truth
 * Defines the 5 supported platforms for the entire system
 */

// Supported platforms (in display order)
export const SUPPORTED_PLATFORMS = ['luno', 'binance', 'kucoin', 'ovex', 'valr'];

// Platform display configuration
export const PLATFORM_CONFIG = {
  luno: {
    id: 'luno',
    name: 'Luno',
    displayName: 'Luno',
    icon: '🇿🇦',
    color: '#3861FB',
    maxBots: 5,
    region: 'ZA',
    requiresPassphrase: false,
    enabled: true
  },
  binance: {
    id: 'binance',
    name: 'Binance',
    displayName: 'Binance',
    icon: '🟡',
    color: '#F3BA2F',
    maxBots: 10,
    region: 'Global',
    requiresPassphrase: false,
    enabled: true
  },
  kucoin: {
    id: 'kucoin',
    name: 'KuCoin',
    displayName: 'KuCoin',
    icon: '🟢',
    color: '#23AF91',
    maxBots: 10,
    region: 'Global',
    requiresPassphrase: true,  // KuCoin requires passphrase
    enabled: true
  },
  ovex: {
    id: 'ovex',
    name: 'OVEX',
    displayName: 'OVEX',
    icon: '🟠',
    color: '#FF8C00',
    maxBots: 10,
    region: 'ZA',
    requiresPassphrase: false,
    enabled: true
  },
  valr: {
    id: 'valr',
    name: 'VALR',
    displayName: 'VALR',
    icon: '🔵',
    color: '#00B8D4',
    maxBots: 10,
    region: 'ZA',
    requiresPassphrase: false,
    enabled: true
  }
};

// Total bot capacity
export const TOTAL_BOT_CAPACITY = Object.values(PLATFORM_CONFIG).reduce((sum, p) => sum + p.maxBots, 0);  // 45

/**
 * Get configuration for a specific platform
 */
export function getPlatformConfig(platformId) {
  return PLATFORM_CONFIG[platformId?.toLowerCase()] || null;
}

/**
 * Check if platform ID is valid
 */
export function isValidPlatform(platformId) {
  return SUPPORTED_PLATFORMS.includes(platformId?.toLowerCase());
}

/**
 * Get list of enabled platforms
 */
export function getEnabledPlatforms() {
  return SUPPORTED_PLATFORMS.filter(p => PLATFORM_CONFIG[p].enabled);
}

/**
 * Get display name for platform
 */
export function getPlatformDisplayName(platformId) {
  const config = getPlatformConfig(platformId);
  return config?.displayName || platformId?.toUpperCase() || 'Unknown';
}

/**
 * Get max bots allowed for platform
 */
export function getMaxBots(platformId) {
  const config = getPlatformConfig(platformId);
  return config?.maxBots || 0;
}

/**
 * Get platform icon
 */
export function getPlatformIcon(platformId) {
  const config = getPlatformConfig(platformId);
  return config?.icon || '🔷';
}

/**
 * Get platform color
 */
export function getPlatformColor(platformId) {
  const config = getPlatformConfig(platformId);
  return config?.color || '#999999';
}

/**
 * Get platform options for dropdowns
 */
export function getPlatformOptions() {
  return SUPPORTED_PLATFORMS.map(id => {
    const config = PLATFORM_CONFIG[id];
    return {
      value: id,
      label: `${config.icon} ${config.displayName} (Max ${config.maxBots} bots)`,
      ...config
    };
  });
}

export default {
  SUPPORTED_PLATFORMS,
  PLATFORM_CONFIG,
  TOTAL_BOT_CAPACITY,
  getPlatformConfig,
  isValidPlatform,
  getEnabledPlatforms,
  getPlatformDisplayName,
  getMaxBots,
  getPlatformIcon,
  getPlatformColor,
  getPlatformOptions
};
