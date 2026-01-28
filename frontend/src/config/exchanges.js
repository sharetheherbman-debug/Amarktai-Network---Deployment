/**
 * Exchange Configuration
 * 
 * Supported exchanges for the Amarktai trading system
 * Including bot caps and feature flags
 */

// Feature flags (can be overridden by environment variables)
export const FEATURE_FLAGS = {
  ENABLE_OVEX: process.env.REACT_APP_ENABLE_OVEX === 'true' || false, // OVEX is optional for South African users
};

// Supported exchanges
export const EXCHANGES = {
  LUNO: {
    id: 'luno',
    name: 'Luno',
    displayName: 'Luno',
    maxBots: 5,
    region: 'ZA', // South Africa
    icon: '🇿🇦',
    requiresSecret: true,
    requiresPassphrase: false,
    supported: true
  },
  BINANCE: {
    id: 'binance',
    name: 'Binance',
    displayName: 'Binance',
    maxBots: 10,
    region: 'Global',
    icon: '🟡',
    requiresSecret: true,
    requiresPassphrase: false,
    supported: true
  },
  KUCOIN: {
    id: 'kucoin',
    name: 'KuCoin',
    displayName: 'KuCoin',
    maxBots: 10,
    region: 'Global',
    icon: '🟢',
    requiresSecret: true,
    requiresPassphrase: true, // KuCoin requires passphrase
    supported: true
  },
  OVEX: {
    id: 'ovex',
    name: 'OVEX',
    displayName: 'OVEX',
    maxBots: 10,
    region: 'ZA', // South Africa
    icon: '🟠',
    requiresSecret: true,
    requiresPassphrase: false,
    supported: true
  },
  VALR: {
    id: 'valr',
    name: 'VALR',
    displayName: 'VALR',
    maxBots: 10,
    region: 'ZA', // South Africa
    icon: '🔵',
    requiresSecret: true,
    requiresPassphrase: false,
    supported: true
  }
};

// Get list of all exchanges
export const getAllExchanges = () => {
  return Object.values(EXCHANGES);
};

// Get list of active/supported exchanges
export const getActiveExchanges = () => {
  return Object.values(EXCHANGES).filter(ex => ex.supported);
};

// Get list of South African exchanges
export const getSouthAfricanExchanges = () => {
  return Object.values(EXCHANGES).filter(ex => ex.region === 'ZA' && ex.supported);
};

// Get exchange by ID
export const getExchangeById = (id) => {
  const exchange = Object.values(EXCHANGES).find(ex => ex.id === id?.toLowerCase());
  return exchange || null;
};

// Get total bot cap
export const getTotalBotCap = () => {
  return getActiveExchanges().reduce((sum, ex) => sum + ex.maxBots, 0);
};

// Check if exchange is supported
export const isExchangeSupported = (exchangeId) => {
  const exchange = getExchangeById(exchangeId);
  return exchange ? exchange.supported : false;
};

// Exchange list for dropdowns
export const getExchangeOptions = () => {
  return getAllExchanges().map(ex => ({
    value: ex.id,
    label: `${ex.icon} ${ex.displayName}`,
    disabled: false,
    exchange: ex
  }));
};

export default EXCHANGES;
