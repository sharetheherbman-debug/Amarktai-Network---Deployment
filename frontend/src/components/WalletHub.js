import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../lib/api.js';

const WalletHub = () => {
  const [balances, setBalances] = useState(null);
  const [requirements, setRequirements] = useState(null);
  const [fundingPlans, setFundingPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const backendUrl = process.env.REACT_APP_API_BASE || '';

  useEffect(() => {
    loadWalletData();
    // Refresh every 30 seconds
    const interval = setInterval(loadWalletData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadWalletData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // Load balances, requirements, and funding plans in parallel
      const [balancesRes, requirementsRes, plansRes] = await Promise.all([
        axios.get(`${backendUrl}/api/wallet/balances`, { headers }),
        axios.get(`${backendUrl}/api/wallet/requirements`, { headers }),
        axios.get(`${backendUrl}/api/wallet/funding-plans?status=awaiting_deposit`, { headers })
      ]);

      setBalances(balancesRes.data);
      setRequirements(requirementsRes.data);
      setFundingPlans(plansRes.data.plans || []);
      setLoading(false);
    } catch (err) {
      console.error('Wallet data load error:', err);
      setError(err.response?.data?.detail || 'Failed to load wallet data');
      setLoading(false);
    }
  };

  const getHealthColor = (health) => {
    switch (health) {
      case 'healthy': return '#27ae60';
      case 'adequate': return '#3498db';
      case 'warning': return '#f39c12';
      case 'critical': return '#e74c3c';
      default: return '#95a5a6';
    }
  };

  const getHealthIcon = (health) => {
    switch (health) {
      case 'healthy': return '✅';
      case 'adequate': return '✔️';
      case 'warning': return '⚠️';
      case 'critical': return '🚨';
      default: return '❓';
    }
  };

  const cancelFundingPlan = async (planId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${backendUrl}/api/wallet/funding-plans/${planId}/cancel`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadWalletData();
    } catch (err) {
      alert('Failed to cancel funding plan: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', marginBottom: '20px' }}>💰</div>
        <p>Loading wallet data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#e74c3c' }}>
        <div style={{ fontSize: '2rem', marginBottom: '20px' }}>⚠️</div>
        <p>{error}</p>
        <button onClick={loadWalletData} style={{ marginTop: '20px', padding: '10px 20px' }}>
          Retry
        </button>
      </div>
    );
  }

  const masterWallet = balances?.master_wallet || {};
  const exchanges = requirements?.requirements || {};

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px', fontSize: '2rem', color: 'var(--text)' }}>
        💰 Wallet Hub
      </h1>

      {/* Master Luno Wallet */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '12px',
        padding: '30px',
        marginBottom: '30px',
        color: 'white',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
      }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.5rem' }}>🏦 Master Luno Wallet</h2>
        <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Total Balance (ZAR)</div>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
              R{(masterWallet.total_zar || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>BTC Balance</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              {(masterWallet.btc_balance || 0).toFixed(8)} BTC
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>ETH Balance</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              {(masterWallet.eth_balance || 0).toFixed(6)} ETH
            </div>
          </div>
        </div>
        <div style={{ marginTop: '20px', fontSize: '0.85rem', opacity: 0.8 }}>
          Last updated: {balances?.last_updated || 'Just now'}
        </div>
      </div>

      {/* Funding Plans (if any) */}
      {fundingPlans.length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ marginBottom: '15px', fontSize: '1.3rem', color: 'var(--text)' }}>
            📋 Active Funding Plans
          </h2>
          {fundingPlans.map(plan => (
            <div key={plan.plan_id} style={{
              background: '#fff3cd',
              border: '2px solid #ffc107',
              borderRadius: '8px',
              padding: '20px',
              marginBottom: '15px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '10px' }}>
                    💰 {plan.to_exchange?.toUpperCase()} - R{plan.amount_required?.toFixed(2)} needed
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', color: '#856404', marginBottom: '10px' }}>
                    {plan.ai_message}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#856404' }}>
                    Bot: {plan.bot_name || 'N/A'} | Created: {new Date(plan.created_at).toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => cancelFundingPlan(plan.plan_id)}
                  style={{
                    background: '#dc3545',
                    color: 'white',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.9rem'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Exchange Cards */}
      <h2 style={{ marginBottom: '15px', fontSize: '1.3rem', color: 'var(--text)' }}>
        🏢 Exchange Balances
      </h2>
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '20px'
      }}>
        {Object.entries(exchanges).map(([exchange, data]) => {
          const healthColor = getHealthColor(data.health);
          const healthIcon = getHealthIcon(data.health);
          const surplus = data.surplus_deficit || 0;

          return (
            <div key={exchange} style={{
              background: 'var(--panel)',
              border: `2px solid ${healthColor}`,
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              {/* Exchange Header */}
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '15px'
              }}>
                <h3 style={{ fontSize: '1.2rem', color: 'var(--text)', margin: 0 }}>
                  {exchange.toUpperCase()}
                </h3>
                <div style={{ fontSize: '1.5rem' }}>{healthIcon}</div>
              </div>

              {/* Balances */}
              <div style={{ marginBottom: '15px' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '5px' }}>
                  Required Capital
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text)' }}>
                  R{(data.required || 0).toLocaleString()}
                </div>
              </div>

              <div style={{ marginBottom: '15px' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '5px' }}>
                  Available Balance
                </div>
                <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text)' }}>
                  R{(data.available || 0).toLocaleString()}
                </div>
              </div>

              {/* Surplus/Deficit */}
              <div style={{
                padding: '10px',
                borderRadius: '6px',
                background: surplus >= 0 ? '#d4edda' : '#f8d7da',
                color: surplus >= 0 ? '#155724' : '#721c24',
                marginBottom: '15px'
              }}>
                <div style={{ fontSize: '0.85rem' }}>
                  {surplus >= 0 ? 'Surplus' : 'Deficit'}
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                  R{Math.abs(surplus).toLocaleString()}
                </div>
              </div>

              {/* Stats */}
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                padding: '10px 0',
                borderTop: '1px solid var(--border)',
                fontSize: '0.85rem',
                color: 'var(--muted)'
              }}>
                <div>Active Bots: {data.bots || 0}</div>
                <div>Health: {data.health || 'unknown'}</div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                <button style={{
                  flex: 1,
                  padding: '10px',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}>
                  Top Up
                </button>
                <button style={{
                  flex: 1,
                  padding: '10px',
                  background: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}>
                  Withdraw
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* No exchanges with bots */}
      {Object.keys(exchanges).length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '40px',
          color: 'var(--muted)',
          background: 'var(--panel)',
          borderRadius: '8px'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '10px' }}>🤖</div>
          <p>No active bots yet. Create your first bot to see exchange requirements.</p>
        </div>
      )}
    </div>
  );
};

export default WalletHub;
