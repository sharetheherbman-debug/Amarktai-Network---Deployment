import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { API_BASE } from '../../lib/api.js';
import { SUPPORTED_PLATFORMS, PLATFORM_CONFIG } from '../../constants/platforms.js';

const API = API_BASE;

export const APISetupSection = ({ apiKeys, token, onKeysUpdate }) => {
  const [showForm, setShowForm] = useState(null);
  const [formData, setFormData] = useState({});
  const axiosConfig = { headers: { Authorization: `Bearer ${token}` } };

  const providers = [
    { id: 'openai', name: 'OpenAI', fields: ['api_key'] },
    ...SUPPORTED_PLATFORMS.map(platformId => {
      const config = PLATFORM_CONFIG[platformId];
      const fields = ['api_key', 'api_secret'];
      if (config.requiresPassphrase) {
        fields.push('passphrase');
      }
      return {
        id: platformId,
        name: config.displayName,
        fields
      };
    }),
    { id: 'fetchai', name: 'Fetch.ai', fields: ['api_key'] },
    { id: 'flokx', name: 'Flokx', fields: ['api_key'] }
  ];

  const handleSaveKey = async (provider) => {
    try {
      await axios.post(`${API}/api-keys`, {
        provider: provider.id,
        ...formData
      }, axiosConfig);
      
      toast.success(`${provider.name} API key saved!`);
      setShowForm(null);
      setFormData({});
      onKeysUpdate();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to save API key';
      console.error(`Failed to save ${provider.name} key:`, err);
      toast.error(`Failed to save ${provider.name} key: ${errorMsg}`);
    }
  };

  const handleTestConnection = async (providerId) => {
    try {
      const res = await axios.get(`${API}/api-keys/${providerId}/test`, axiosConfig);
      if (res.data.connected) {
        toast.success(`${providerId} connection successful!`);
      } else {
        toast.error(`${providerId} connection failed`);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Connection test failed';
      console.error('Connection test error:', err);
      toast.error(`Connection test failed: ${errorMsg}`);
    }
  };

  return (
    <div className="api-setup-section">
      <h2 className="section-title">🔑 API Keys Setup</h2>
      
      <div className="api-providers-grid">
        {providers.map(provider => {
          const keyData = apiKeys[provider.id];
          const isConnected = keyData?.status === 'connected';
          
          return (
            <div key={provider.id} className="api-provider-card">
              <div className="provider-header">
                <h3>{provider.name}</h3>
                <span className={`status-badge ${isConnected ? 'connected' : 'not-connected'}`}>
                  {isConnected ? '✅ Connected' : '⚠️ Not Connected'}
                </span>
              </div>
              
              {showForm === provider.id ? (
                <div className="api-form">
                  {provider.fields.map(field => (
                    <input
                      key={field}
                      type="password"
                      placeholder={field.replace('_', ' ').toUpperCase()}
                      value={formData[field] || ''}
                      onChange={(e) => setFormData({...formData, [field]: e.target.value})}
                    />
                  ))}
                  <div className="form-actions">
                    <button className="btn-primary" onClick={() => handleSaveKey(provider)}>
                      Save
                    </button>
                    <button className="btn-secondary" onClick={() => setShowForm(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="provider-actions">
                  <button 
                    className="btn-secondary"
                    onClick={() => setShowForm(provider.id)}
                  >
                    {isConnected ? 'Update' : 'Add'} Key
                  </button>
                  {isConnected && (
                    <button 
                      className="btn-outline"
                      onClick={() => handleTestConnection(provider.id)}
                    >
                      Test
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
