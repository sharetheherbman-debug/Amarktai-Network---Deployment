/**
 * LiveTradesView Component
 * 
 * Displays live trades with 50/50 split:
 * - Left: Live trades feed
 * - Right: Platform selector + performance comparison
 */

import { useState } from 'react';
import { SUPPORTED_PLATFORMS, getPlatformIcon, getPlatformDisplayName } from '../constants/platforms';
import LiveTradesPanel from './LiveTradesPanel';
import './LiveTradesView.css';

export default function LiveTradesView() {
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [platformStats, setPlatformStats] = useState({});

  // Mock platform stats - in real implementation, this would come from API
  const getPlatformComparisonData = () => {
    return SUPPORTED_PLATFORMS.map(platformId => {
      const stats = platformStats[platformId] || {
        totalPnL: 0,
        tradeCount: 0,
        winCount: 0,
        lossCount: 0
      };
      
      const winRate = stats.tradeCount > 0 
        ? (stats.winCount / stats.tradeCount) * 100 
        : 0;

      return {
        id: platformId,
        name: getPlatformDisplayName(platformId),
        icon: getPlatformIcon(platformId),
        pnl: stats.totalPnL,
        tradeCount: stats.tradeCount,
        winRate: winRate.toFixed(1),
        wins: stats.winCount,
        losses: stats.lossCount
      };
    });
  };

  const comparisonData = getPlatformComparisonData();

  const formatMoney = (amount) => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR',
      minimumFractionDigits: 2
    }).format(amount);
  };

  return (
    <div className="live-trades-view">
      <div className="live-trades-container">
        {/* LEFT PANEL - Live Trades Feed */}
        <div className="live-trades-left">
          <LiveTradesPanel platformFilter={selectedPlatform} />
        </div>

        {/* RIGHT PANEL - Platform Selector + Comparison */}
        <div className="live-trades-right">
          <div className="platform-comparison-panel">
            <div className="panel-header">
              <h3 className="panel-title">Platform Performance</h3>
              <p className="panel-subtitle">Compare trading performance across platforms</p>
            </div>

            {/* Platform Selector */}
            <div className="platform-selector-section">
              <label htmlFor="platform-select" className="selector-label">
                Filter by Platform
              </label>
              <select
                id="platform-select"
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value)}
                className="platform-select"
              >
                <option value="all">All Platforms</option>
                {SUPPORTED_PLATFORMS.map(platformId => (
                  <option key={platformId} value={platformId}>
                    {getPlatformIcon(platformId)} {getPlatformDisplayName(platformId)}
                  </option>
                ))}
              </select>
            </div>

            {/* Platform Comparison Table */}
            <div className="comparison-table-container">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Platform</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map(platform => (
                    <tr
                      key={platform.id}
                      className={selectedPlatform === platform.id ? 'selected-row' : ''}
                      onClick={() => setSelectedPlatform(platform.id)}
                    >
                      <td>
                        <div className="platform-cell">
                          <span className="platform-icon">{platform.icon}</span>
                          <span className="platform-name">{platform.name}</span>
                        </div>
                      </td>
                      <td className="text-center">
                        <div className="trade-count">{platform.tradeCount}</div>
                        <div className="trade-breakdown">
                          <span className="wins">{platform.wins}W</span>
                          <span className="losses">{platform.losses}L</span>
                        </div>
                      </td>
                      <td className="text-center">
                        <div className={`win-rate ${parseFloat(platform.winRate) >= 50 ? 'positive' : 'negative'}`}>
                          {platform.winRate}%
                        </div>
                      </td>
                      <td className="text-right">
                        <div className={`pnl ${platform.pnl >= 0 ? 'profit' : 'loss'}`}>
                          {platform.pnl >= 0 ? '+' : ''}{formatMoney(platform.pnl)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {comparisonData.every(p => p.tradeCount === 0) && (
                <div className="empty-state">
                  <p>No trading data available yet</p>
                  <p className="empty-state-subtitle">Start trading to see platform comparisons</p>
                </div>
              )}
            </div>

            {/* Best Platform Highlight */}
            {comparisonData.some(p => p.tradeCount > 0) && (
              <div className="best-platform-highlight">
                <h4 className="highlight-title">🏆 Best Performing Platform</h4>
                {(() => {
                  const best = comparisonData
                    .filter(p => p.tradeCount > 0)
                    .sort((a, b) => b.pnl - a.pnl)[0];
                  
                  if (!best) return null;

                  return (
                    <div className="best-platform-card">
                      <div className="best-platform-header">
                        <span className="best-platform-icon">{best.icon}</span>
                        <span className="best-platform-name">{best.name}</span>
                      </div>
                      <div className="best-platform-stats">
                        <div className="stat">
                          <span className="stat-label">P&L</span>
                          <span className="stat-value profit">{formatMoney(best.pnl)}</span>
                        </div>
                        <div className="stat">
                          <span className="stat-label">Win Rate</span>
                          <span className="stat-value">{best.winRate}%</span>
                        </div>
                        <div className="stat">
                          <span className="stat-label">Trades</span>
                          <span className="stat-value">{best.tradeCount}</span>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
