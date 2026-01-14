import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../lib/api';

/**
 * Platform Selector Component
 * 
 * Fetches all enabled platforms from backend and allows filtering
 * Used across Bot Management, Trading, and other screens
 */
export default function PlatformSelector({ value, onChange, includeAll = true }) {
  const [platforms, setPlatforms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlatforms();
  }, []);

  const fetchPlatforms = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE}/system/platforms`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data && response.data.platforms) {
        setPlatforms(response.data.platforms);
      }
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch platforms:', error);
      // Fallback to default platforms if API fails
      setPlatforms([
        { name: 'luno', display_name: 'Luno', enabled: true },
        { name: 'binance', display_name: 'Binance', enabled: true },
        { name: 'kucoin', display_name: 'KuCoin', enabled: true },
        { name: 'kraken', display_name: 'Kraken', enabled: true },
        { name: 'valr', display_name: 'VALR', enabled: true }
      ]);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <select 
        className="platform-selector loading"
        disabled
        style={{
          padding: '8px 12px',
          borderRadius: '6px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          background: 'rgba(17, 24, 39, 0.8)',
          color: 'var(--text)',
          fontSize: '14px',
          cursor: 'not-allowed',
          minWidth: '150px'
        }}
      >
        <option>Loading...</option>
      </select>
    );
  }

  const enabledPlatforms = platforms.filter(p => p.enabled);

  return (
    <select
      value={value || 'all'}
      onChange={(e) => onChange(e.target.value)}
      className="platform-selector"
      style={{
        padding: '8px 12px',
        borderRadius: '6px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        background: 'rgba(17, 24, 39, 0.8)',
        color: 'var(--text)',
        fontSize: '14px',
        cursor: 'pointer',
        minWidth: '150px',
        transition: 'all 0.2s ease'
      }}
    >
      {includeAll && (
        <option value="all">
          🌐 All Platforms ({enabledPlatforms.length})
        </option>
      )}
      {enabledPlatforms.map(platform => (
        <option key={platform.name} value={platform.name}>
          {getPlatformIcon(platform.name)} {platform.display_name}
        </option>
      ))}
    </select>
  );
}

// Platform icons/emojis for better UX
function getPlatformIcon(platform) {
  const icons = {
    luno: '🌙',
    binance: '🔶',
    kucoin: '🔷',
    kraken: '🐙',
    valr: '💎'
  };
  return icons[platform] || '📊';
}
