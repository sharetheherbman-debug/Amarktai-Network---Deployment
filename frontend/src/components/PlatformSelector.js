import React, { useState, useEffect } from 'react';
import { fetchPlatforms, getPlatformIcon } from '../lib/platforms';

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
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      const token = localStorage.getItem('token');
      const platformsData = await fetchPlatforms(token);
      setPlatforms(platformsData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load platforms:', error);
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
        <option key={platform.id || platform.name} value={platform.id || platform.name}>
          {getPlatformIcon(platform.id || platform.name)} {platform.displayName || platform.display_name}
        </option>
      ))}
    </select>
  );
}
