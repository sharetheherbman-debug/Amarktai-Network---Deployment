import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { API_BASE } from '../../lib/api.js';

const API = API_BASE;

export const CreateBotSection = ({ token, onBotCreated }) => {
  const [botName, setBotName] = useState('');
  const [botExchange, setBotExchange] = useState('luno');
  const [botCapital, setBotCapital] = useState('1000');
  const [botRisk, setBotRisk] = useState('safe');
  const [creating, setCreating] = useState(false);

  const axiosConfig = { headers: { Authorization: `Bearer ${token}` } };

  const handleCreateBot = async (e) => {
    e.preventDefault();
    
    if (!botName.trim()) {
      toast.error('Please enter a bot name');
      return;
    }

    if (parseFloat(botCapital) < 100) {
      toast.error('Minimum capital is R100');
      return;
    }

    setCreating(true);
    try {
      await axios.post(`${API}/bots`, {
        name: botName,
        initial_capital: parseFloat(botCapital),
        risk_mode: botRisk,
        exchange: botExchange
      }, axiosConfig);
      
      toast.success(`Bot "${botName}" created successfully!`);
      setBotName('');
      setBotCapital('1000');
      onBotCreated();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create bot';
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="create-bot-section">
      <h2 className="section-title">🤖 Create New Bot</h2>
      <form onSubmit={handleCreateBot} className="create-bot-form">
        <div className="form-row">
          <div className="form-group">
            <label>Bot Name</label>
            <input
              type="text"
              value={botName}
              onChange={(e) => setBotName(e.target.value)}
              placeholder="e.g., Zeus"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Exchange</label>
            <select value={botExchange} onChange={(e) => setBotExchange(e.target.value)}>
              <option value="luno">🇿🇦 Luno (Max 5 bots)</option>
              <option value="binance">🟡 Binance (Max 10 bots)</option>
              <option value="kucoin">🟢 KuCoin (Max 10 bots)</option>
              <option value="ovex">🟠 OVEX (Max 10 bots)</option>
              <option value="valr">🔵 VALR (Max 10 bots)</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Initial Capital (ZAR)</label>
            <input
              type="number"
              value={botCapital}
              onChange={(e) => setBotCapital(e.target.value)}
              min="100"
              step="100"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Risk Mode</label>
            <select value={botRisk} onChange={(e) => setBotRisk(e.target.value)}>
              <option value="safe">Safe (Conservative)</option>
              <option value="balanced">Balanced (Moderate)</option>
              <option value="aggressive">Aggressive (High Risk)</option>
            </select>
          </div>
        </div>

        <button type="submit" className="btn-primary" disabled={creating}>
          {creating ? '⏳ Creating...' : '✅ Create Bot'}
        </button>
      </form>
    </div>
  );
};
