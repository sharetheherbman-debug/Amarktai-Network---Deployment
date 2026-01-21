import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { API_BASE } from '../../lib/api.js';

const API = API_BASE;

export const BotManagementSection = ({ bots, token, onBotsUpdate }) => {
  const [expandedBots, setExpandedBots] = useState({});
  const [editingBotId, setEditingBotId] = useState(null);
  const [editingBotName, setEditingBotName] = useState('');
  const axiosConfig = { headers: { Authorization: `Bearer ${token}` } };

  const toggleBotExpand = (botId) => {
    setExpandedBots(prev => ({ ...prev, [botId]: !prev[botId] }));
  };

  const handlePauseBot = async (botId) => {
    try {
      await axios.put(`${API}/bots/${botId}/pause`, {}, axiosConfig);
      toast.success('Bot paused');
      onBotsUpdate();
    } catch (err) {
      toast.error('Failed to pause bot');
    }
  };

  const handleResumeBot = async (botId) => {
    try {
      await axios.put(`${API}/bots/${botId}/resume`, {}, axiosConfig);
      toast.success('Bot resumed');
      onBotsUpdate();
    } catch (err) {
      toast.error('Failed to resume bot');
    }
  };

  const handleDeleteBot = async (botId) => {
    if (!window.confirm('Are you sure you want to delete this bot?')) return;
    
    try {
      await axios.delete(`${API}/bots/${botId}`, axiosConfig);
      toast.success('Bot deleted');
      onBotsUpdate();
    } catch (err) {
      toast.error('Failed to delete bot');
    }
  };

  const startEditingBotName = (bot) => {
    setEditingBotId(bot.id);
    setEditingBotName(bot.name);
  };

  const saveEditedBotName = async (botId) => {
    try {
      await axios.put(`${API}/bots/${botId}`, { name: editingBotName }, axiosConfig);
      toast.success('Bot name updated');
      setEditingBotId(null);
      onBotsUpdate();
    } catch (err) {
      toast.error('Failed to update bot name');
    }
  };

  const getRiskColor = (riskMode) => {
    if (riskMode === 'safe') return '#4ade80';
    if (riskMode === 'balanced') return '#fbbf24';
    return '#ef4444';
  };

  const getStatusColor = (status) => {
    return status === 'active' ? '#10b981' : '#6b7280';
  };

  const calculateTimeRemaining = (retrainingUntil) => {
    const now = new Date();
    const until = new Date(retrainingUntil);
    const diff = Math.max(0, Math.floor((until - now) / 1000));
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    
    return `${hours}h ${minutes}m remaining`;
  };

  return (
    <div className="bots-list">
      {bots.length === 0 ? (
        <div className="empty-state">
          <p>No bots yet. Create your first bot to start trading!</p>
        </div>
      ) : (
        bots.map(bot => (
          <div key={bot.id} className="bot-card">
            <div className="bot-header" onClick={() => toggleBotExpand(bot.id)}>
              <div className="bot-main-info">
                {editingBotId === bot.id ? (
                  <input
                    type="text"
                    value={editingBotName}
                    onChange={(e) => setEditingBotName(e.target.value)}
                    onBlur={() => saveEditedBotName(bot.id)}
                    onKeyPress={(e) => e.key === 'Enter' && saveEditedBotName(bot.id)}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <h3 onClick={(e) => { e.stopPropagation(); startEditingBotName(bot); }}>
                    {bot.name}
                  </h3>
                )}
                <div className="bot-tags">
                  <span 
                    className="bot-tag" 
                    style={{ backgroundColor: getRiskColor(bot.risk_mode) }}
                  >
                    {bot.risk_mode}
                  </span>
                  <span 
                    className="bot-tag"
                    style={{ backgroundColor: getStatusColor(bot.status) }}
                  >
                    {bot.status}
                  </span>
                  <span className="bot-tag">{bot.exchange}</span>
                </div>
                
                {/* Quarantine Status */}
                {bot.status === 'quarantined' && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    backgroundColor: 'rgba(245, 158, 11, 0.15)',
                    borderRadius: '4px',
                    border: '1px solid rgba(245, 158, 11, 0.5)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '0.75rem',
                      color: '#fbbf24'
                    }}>
                      <span>
                        🔒 In Quarantine (Attempt #{bot.quarantine_count})
                      </span>
                      {bot.retraining_until && (
                        <span style={{ fontFamily: 'monospace' }}>
                          {calculateTimeRemaining(bot.retraining_until)}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Pause Status */}
                {bot.status === 'paused' && bot.pause_reason && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    borderRadius: '4px',
                    border: '1px solid rgba(239, 68, 68, 0.5)'
                  }}>
                    <span style={{
                      fontSize: '0.75rem',
                      color: '#fca5a5'
                    }}>
                      ⏸️ Paused: {bot.pause_reason}
                    </span>
                  </div>
                )}
              </div>
              
              <div className="bot-metrics">
                <div className="metric">
                  <span className="label">Capital:</span>
                  <span className="value">R{bot.current_capital?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="metric">
                  <span className="label">Profit:</span>
                  <span className={`value ${(bot.total_profit || 0) >= 0 ? 'positive' : 'negative'}`}>
                    R{bot.total_profit?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
            </div>

            {expandedBots[bot.id] && (
              <div className="bot-details">
                <div className="details-grid">
                  <div className="detail-item">
                    <span className="detail-label">Trading Mode:</span>
                    <span className="detail-value">{bot.trading_mode}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Trades:</span>
                    <span className="detail-value">{bot.trades_count || 0}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Wins:</span>
                    <span className="detail-value">{bot.win_count || 0}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Losses:</span>
                    <span className="detail-value">{bot.loss_count || 0}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Win Rate:</span>
                    <span className="detail-value">
                      {bot.trades_count > 0 
                        ? ((bot.win_count / bot.trades_count) * 100).toFixed(1)
                        : 0}%
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Pair:</span>
                    <span className="detail-value">{bot.pair || 'BTC/ZAR'}</span>
                  </div>
                </div>

                <div className="bot-actions">
                  {bot.status === 'active' ? (
                    <button 
                      className="btn-secondary"
                      onClick={() => handlePauseBot(bot.id)}
                    >
                      ⏸️ Pause
                    </button>
                  ) : (
                    <button 
                      className="btn-primary"
                      onClick={() => handleResumeBot(bot.id)}
                    >
                      ▶️ Resume
                    </button>
                  )}
                  <button 
                    className="btn-danger"
                    onClick={() => handleDeleteBot(bot.id)}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
};
