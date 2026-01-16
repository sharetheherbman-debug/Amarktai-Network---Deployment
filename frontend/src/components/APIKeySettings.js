import React, { useState, useEffect } from 'react';
import './APIKeySettings.css';

const APIKeySettings = () => {
  const [apiKeys, setApiKeys] = useState({
    openai: '',
    flock: '',
    fetch_wallet: ''
  });
  
  const [keyStatus, setKeyStatus] = useState({
    openai: { configured: false, status: 'none' },
    flock: { configured: false, status: 'none' },
    fetch_wallet: { configured: false, status: 'none' }
  });
  
  const [paymentConfig, setPaymentConfig] = useState({
    enabled: false,
    wallet_seed: '',
    daily_budget_fet: 100,
    network: 'testnet',
    max_single_transaction_fet: 50,
    has_wallet: false
  });
  
  const [showSeeds, setShowSeeds] = useState({
    fetch_wallet: false
  });
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const token = localStorage.getItem('token');
  
  useEffect(() => {
    fetchKeyStatus();
    fetchPaymentConfig();
  }, []);
  
  const fetchKeyStatus = async () => {
    try {
      const services = ['openai', 'flock', 'fetch_wallet'];
      for (const service of services) {
        const response = await fetch(`/api/user/api-keys/${service}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setKeyStatus(prev => ({
            ...prev,
            [service]: {
              configured: data.user_configured,
              status: data.status
            }
          }));
        }
      }
    } catch (error) {
      console.error('Error fetching key status:', error);
    }
  };
  
  const fetchPaymentConfig = async () => {
    try {
      const response = await fetch('/api/user/payment-config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPaymentConfig(data);
      }
    } catch (error) {
      console.error('Error fetching payment config:', error);
    }
  };
  
  const saveApiKey = async (service) => {
    const key = apiKeys[service];
    if (!key || key.trim() === '') {
      showMessage('error', 'API key cannot be empty');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch('/api/user/api-keys', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ service, key })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        showMessage('success', data.message);
        setApiKeys(prev => ({ ...prev, [service]: '' }));
        fetchKeyStatus();
      } else {
        showMessage('error', data.detail || 'Failed to save API key');
      }
    } catch (error) {
      showMessage('error', 'Error saving API key: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const deleteApiKey = async (service) => {
    if (!window.confirm(`Delete your ${service} API key? System default will be used if available.`)) {
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`/api/user/api-keys/${service}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        showMessage('success', data.message);
        fetchKeyStatus();
      } else {
        showMessage('error', data.message || 'Failed to delete API key');
      }
    } catch (error) {
      showMessage('error', 'Error deleting API key: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const generateWallet = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/user/generate-wallet', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setApiKeys(prev => ({ ...prev, fetch_wallet: data.mnemonic }));
        setPaymentConfig(prev => ({ ...prev, wallet_seed: data.mnemonic }));
        showMessage('success', `Wallet generated: ${data.address}`);
        alert(`IMPORTANT: Save your mnemonic securely!\n\n${data.mnemonic}\n\n${data.warning}`);
      } else {
        showMessage('error', 'Failed to generate wallet');
      }
    } catch (error) {
      showMessage('error', 'Error generating wallet: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const savePaymentConfig = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/user/payment-config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(paymentConfig)
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        showMessage('success', data.message);
        fetchPaymentConfig();
      } else {
        showMessage('error', data.detail || 'Failed to save payment configuration');
      }
    } catch (error) {
      showMessage('error', 'Error saving payment config: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };
  
  const getStatusBadge = (status) => {
    if (status === 'user') {
      return <span className="badge badge-user">Your Key</span>;
    } else if (status === 'system') {
      return <span className="badge badge-system">System Default</span>;
    } else {
      return <span className="badge badge-none">Not Configured</span>;
    }
  };
  
  return (
    <div className="api-key-settings">
      <h2>API Key Configuration</h2>
      <p className="subtitle">Configure your own API keys or use system defaults</p>
      
      {message.text && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}
      
      {/* OpenAI API Key */}
      <div className="api-key-section">
        <div className="section-header">
          <h3>OpenAI API Key</h3>
          {getStatusBadge(keyStatus.openai.status)}
        </div>
        <p className="description">
          For AI-powered sentiment analysis and decision-making. Optional - uses system key if not provided.
        </p>
        <div className="input-group">
          <input
            type="password"
            autoComplete="new-password"
            placeholder="sk-..."
            value={apiKeys.openai}
            onChange={(e) => setApiKeys(prev => ({ ...prev, openai: e.target.value }))}
            disabled={loading}
          />
          <button 
            onClick={() => saveApiKey('openai')}
            disabled={loading || !apiKeys.openai}
            className="btn btn-primary"
          >
            Save
          </button>
          {keyStatus.openai.configured && (
            <button 
              onClick={() => deleteApiKey('openai')}
              disabled={loading}
              className="btn btn-danger"
            >
              Delete
            </button>
          )}
        </div>
      </div>
      
      {/* FLock.io API Key */}
      <div className="api-key-section">
        <div className="section-header">
          <h3>FLock.io API Key</h3>
          {getStatusBadge(keyStatus.flock.status)}
        </div>
        <p className="description">
          For vertical-specific trading intelligence. Optional - uses system key if not provided.
        </p>
        <div className="input-group">
          <input
            type="password"
            autoComplete="new-password"
            placeholder="flock_..."
            value={apiKeys.flock}
            onChange={(e) => setApiKeys(prev => ({ ...prev, flock: e.target.value }))}
            disabled={loading}
          />
          <button 
            onClick={() => saveApiKey('flock')}
            disabled={loading || !apiKeys.flock}
            className="btn btn-primary"
          >
            Save
          </button>
          {keyStatus.flock.configured && (
            <button 
              onClick={() => deleteApiKey('flock')}
              disabled={loading}
              className="btn btn-danger"
            >
              Delete
            </button>
          )}
        </div>
      </div>
      
      {/* Fetch.ai Wallet */}
      <div className="api-key-section wallet-section">
        <div className="section-header">
          <h3>Fetch.ai Payment Wallet</h3>
          {getStatusBadge(keyStatus.fetch_wallet.status)}
        </div>
        <p className="description">
          For autonomous payments (alpha signals, gas fees, data feeds). Configure your own wallet or use system default.
        </p>
        
        <div className="wallet-controls">
          <button 
            onClick={generateWallet}
            disabled={loading}
            className="btn btn-secondary"
          >
            🔑 Generate New Wallet
          </button>
          
          {paymentConfig.has_wallet && (
            <span className="wallet-status">
              ✅ Wallet Configured
            </span>
          )}
        </div>
        
        {apiKeys.fetch_wallet && (
          <div className="wallet-seed-section">
            <label>Wallet Seed (24 words)</label>
            <div className="input-group">
              <textarea
                rows="3"
                placeholder="word1 word2 word3 ..."
                value={showSeeds.fetch_wallet ? apiKeys.fetch_wallet : '••••••••••••••••••••'}
                onChange={(e) => setApiKeys(prev => ({ ...prev, fetch_wallet: e.target.value }))}
                disabled={loading}
              />
              <button 
                onClick={() => setShowSeeds(prev => ({ ...prev, fetch_wallet: !prev.fetch_wallet }))}
                className="btn btn-secondary btn-small"
              >
                {showSeeds.fetch_wallet ? '👁️ Hide' : '👁️ Show'}
              </button>
            </div>
            <button 
              onClick={() => {
                setPaymentConfig(prev => ({ ...prev, wallet_seed: apiKeys.fetch_wallet }));
                saveApiKey('fetch_wallet');
              }}
              disabled={loading || !apiKeys.fetch_wallet}
              className="btn btn-primary"
            >
              Save Wallet Seed
            </button>
          </div>
        )}
        
        {/* Payment Configuration */}
        <div className="payment-config">
          <h4>Payment Agent Settings</h4>
          
          <div className="config-row">
            <label>
              <input
                type="checkbox"
                checked={paymentConfig.enabled}
                onChange={(e) => setPaymentConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                disabled={loading}
              />
              Enable Autonomous Payments
            </label>
          </div>
          
          <div className="config-row">
            <label>Network</label>
            <select
              value={paymentConfig.network}
              onChange={(e) => setPaymentConfig(prev => ({ ...prev, network: e.target.value }))}
              disabled={loading}
            >
              <option value="testnet">Testnet</option>
              <option value="mainnet">Mainnet</option>
            </select>
          </div>
          
          <div className="config-row">
            <label>Daily Budget (FET)</label>
            <input
              type="number"
              min="10"
              max="10000"
              value={paymentConfig.daily_budget_fet}
              onChange={(e) => setPaymentConfig(prev => ({ ...prev, daily_budget_fet: parseFloat(e.target.value) }))}
              disabled={loading}
            />
          </div>
          
          <div className="config-row">
            <label>Max Single Transaction (FET)</label>
            <input
              type="number"
              min="1"
              max="1000"
              value={paymentConfig.max_single_transaction_fet}
              onChange={(e) => setPaymentConfig(prev => ({ ...prev, max_single_transaction_fet: parseFloat(e.target.value) }))}
              disabled={loading}
            />
          </div>
          
          <button 
            onClick={savePaymentConfig}
            disabled={loading}
            className="btn btn-primary"
          >
            Save Payment Configuration
          </button>
        </div>
      </div>
      
      {/* System Keys Info */}
      <div className="info-section">
        <h3>ℹ️ About API Keys</h3>
        <ul>
          <li><strong>Your Keys:</strong> Encrypted and stored securely. Only you can access them.</li>
          <li><strong>System Defaults:</strong> Shared keys provided by the platform (if configured).</li>
          <li><strong>Fallback:</strong> If you don't provide a key, system default is used automatically.</li>
          <li><strong>Privacy:</strong> Your keys are never shared with other users.</li>
          <li><strong>Costs:</strong> Using your own keys means you pay for your own API usage.</li>
        </ul>
      </div>
    </div>
  );
};

export default APIKeySettings;
