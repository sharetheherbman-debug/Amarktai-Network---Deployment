/**
 * Public Market Data Fallback
 * 
 * Provides fallback market data from public APIs when user keys are not available
 * or backend fails. NO API KEYS required.
 * 
 * Supported exchanges: Binance, KuCoin, Luno, OVEX, VALR
 * Supported pairs: BTC, ETH, XRP (to ZAR or USD)
 */

class MarketDataFallback {
  constructor() {
    this.cache = {};
    this.cacheExpiry = 5000; // 5 seconds
    this.isActive = false;
    this.lastError = null;
  }

  /**
   * Fetch BTC price from Binance (BTCUSDT)
   */
  async fetchBinanceBTC() {
    try {
      const response = await fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) throw new Error('Binance API error');
      
      const data = await response.json();
      return parseFloat(data.price);
    } catch (error) {
      console.error('Binance fetch error:', error);
      return null;
    }
  }

  /**
   * Fetch BTC price from KuCoin (BTC-USDT)
   */
  async fetchKuCoinBTC() {
    try {
      const response = await fetch('https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) throw new Error('KuCoin API error');
      
      const data = await response.json();
      if (data.code === '200000' && data.data?.price) {
        return parseFloat(data.data.price);
      }
      return null;
    } catch (error) {
      console.error('KuCoin fetch error:', error);
      return null;
    }
  }

  /**
   * Fetch BTC price from Luno (XBTZAR)
   */
  async fetchLunoBTC() {
    try {
      const response = await fetch('https://api.luno.com/api/1/ticker?pair=XBTZAR', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) throw new Error('Luno API error');
      
      const data = await response.json();
      if (data.last_trade) {
        return parseFloat(data.last_trade);
      }
      return null;
    } catch (error) {
      console.error('Luno fetch error:', error);
      return null;
    }
  }

  /**
   * Fetch BTC price from VALR (BTCZAR)
   */
  async fetchVALRBTC() {
    try {
      const response = await fetch('https://api.valr.com/v1/public/BTCZAR/marketsummary', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) throw new Error('VALR API error');
      
      const data = await response.json();
      if (data.lastTradedPrice) {
        return parseFloat(data.lastTradedPrice);
      }
      return null;
    } catch (error) {
      console.error('VALR fetch error:', error);
      return null;
    }
  }

  /**
   * Fetch BTC price from OVEX (BTCZAR) - South African exchange
   */
  async fetchOVEXBTC() {
    try {
      const response = await fetch('https://www.ovex.io/api/v2/markets/btczar/ticker', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) throw new Error('OVEX API error');
      
      const data = await response.json();
      if (data.ticker && data.ticker.last) {
        return parseFloat(data.ticker.last);
      }
      return null;
    } catch (error) {
      console.error('OVEX fetch error:', error);
      return null;
    }
  }

  /**
   * Get cached or fetch fresh prices
   */
  async getPrices() {
    const now = Date.now();
    
    // Return cached data if still valid
    if (this.cache.data && this.cache.timestamp && (now - this.cache.timestamp) < this.cacheExpiry) {
      return this.cache.data;
    }

    // Fetch fresh data from multiple sources in parallel
    const [binanceBTC, kucoinBTC, lunoBTC, valrBTC, ovexBTC] = await Promise.all([
      this.fetchBinanceBTC(),
      this.fetchKuCoinBTC(),
      this.fetchLunoBTC(),
      this.fetchVALRBTC(),
      this.fetchOVEXBTC()
    ]);

    // Use USD/ZAR conversion rate (approximate, you might want a real API for this)
    const usdToZar = 18.5; // Approximate ZAR per USD

    // Build price map
    const prices = {
      'BTC/ZAR': {
        price: lunoBTC || valrBTC || ovexBTC || (binanceBTC ? binanceBTC * usdToZar : 0),
        change: 0, // We don't have 24h change from public APIs easily
        source: lunoBTC ? 'Luno' : valrBTC ? 'VALR' : ovexBTC ? 'OVEX' : 'Binance (USD→ZAR)',
        currency: 'ZAR',
        isFallback: true
      },
      'BTC/USD': {
        price: binanceBTC || kucoinBTC || 0,
        change: 0,
        source: binanceBTC ? 'Binance' : kucoinBTC ? 'KuCoin' : 'N/A',
        currency: 'USD',
        isFallback: true
      },
      'ETH/ZAR': {
        price: 0, // Placeholder - could add ETH support similarly
        change: 0,
        source: 'Not available',
        currency: 'ZAR',
        isFallback: true
      },
      'ETH/USD': {
        price: 0,
        change: 0,
        source: 'Not available',
        currency: 'USD',
        isFallback: true
      },
      'XRP/ZAR': {
        price: 0, // Placeholder
        change: 0,
        source: 'Not available',
        currency: 'ZAR',
        isFallback: true
      },
      'XRP/USD': {
        price: 0,
        change: 0,
        source: 'Not available',
        currency: 'USD',
        isFallback: true
      }
    };

    // Cache the results
    this.cache = {
      data: prices,
      timestamp: now
    };

    return prices;
  }

  /**
   * Start automatic polling
   */
  startPolling(callback, interval = 5000) {
    if (this.isActive) return;
    
    this.isActive = true;
    console.log('📊 Starting public market data fallback...');

    const poll = async () => {
      try {
        const prices = await this.getPrices();
        if (callback) callback(prices);
        this.lastError = null;
      } catch (error) {
        console.error('Market data fallback error:', error);
        this.lastError = error.message;
      }
    };

    // Initial fetch
    poll();

    // Set up interval
    this.pollInterval = setInterval(poll, interval);
  }

  /**
   * Stop polling
   */
  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isActive = false;
    console.log('📊 Stopped public market data fallback');
  }

  /**
   * Get single price (no polling)
   */
  async getPrice(pair) {
    const prices = await this.getPrices();
    return prices[pair] || null;
  }
}

// Singleton instance
const marketDataFallback = new MarketDataFallback();

export default marketDataFallback;
