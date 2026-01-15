import React, { useState, useEffect } from 'react';
import { useRealtimeEvent, useLastUpdate } from '../hooks/useRealtime';
import { get, post } from '../lib/apiClient';

const WalletHub = ({ platformFilter = 'all' }) => {
  const [balances, setBalances] = useState(null);
  const [requirements, setRequirements] = useState(null);
  const [fundingPlans, setFundingPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastUpdate = useLastUpdate('wallet');

  useEffect(() => {
    loadWalletData();
  }, [platformFilter]);

  const loadWalletData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load balances, requirements, and funding plans in parallel with safe defaults
      const [balancesData, requirementsData, plansData] = await Promise.all([
        get('/wallet/balances').catch(err => {
          console.error('Balance fetch error:', err);
          return { master_wallet: {}, last_updated: null }; // Safe default
        }),
        get('/wallet/requirements').catch(err => {
          console.error('Requirements fetch error:', err);
          return { requirements: {} }; // Safe default
        }),
        get('/wallet/funding-plans?status=awaiting_deposit').catch(err => {
          console.error('Funding plans fetch error:', err);
          return { plans: [] }; // Safe default
        })
      ]);

      setBalances(balancesData || {});
      setRequirements(requirementsData || {});
      setFundingPlans(plansData.plans || []);
      setLoading(false);
    } catch (err) {
      console.error('Wallet data load error:', err);
      const statusCode = err.status || err.response?.status || '';
      setError(`Failed to load wallet data${statusCode ? ` (${statusCode})` : ''}: ${err.message || 'Unknown error'}`);
      setLoading(false);
      
      // Initialize to safe defaults even on error
      setBalances({});
      setRequirements({});
      setFundingPlans([]);
    }
  };

  // Subscribe to real-time wallet updates
  useRealtimeEvent('wallet', (data) => {
    if (data.event === 'balance_update') {
      loadWalletData();
    }
  }, []);

  // Subscribe to real-time balance updates
  useRealtimeEvent('balances', (data) => {
    setBalances(prevBalances => ({
      ...prevBalances,
      ...data
    }));
  }, []);

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
      await post(`/wallet/funding-plans/${planId}/cancel`, {});
      loadWalletData();
    } catch (err) {
      alert('Failed to cancel funding plan: ' + (err.message || 'Unknown error'));
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
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', marginBottom: '20px', color: '#e74c3c' }}>⚠️</div>
        <p style={{ color: '#e74c3c', fontWeight: '600', marginBottom: '12px' }}>Backend Error Fetching Balances</p>
        <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '16px' }}>{error}</p>
        <div style={{
          padding: '12px',
          background: 'var(--glass)',
          borderRadius: '6px',
          marginBottom: '16px',
          textAlign: 'left',
          fontSize: '0.85rem',
          color: 'var(--muted)',
          maxWidth: '500px',
          margin: '0 auto 16px'
        }}>
          <p><strong>Possible causes:</strong></p>
          <ul style={{paddingLeft: '20px', marginTop: '8px'}}>
            <li>No exchange API keys configured yet</li>
            <li>Backend wallet service not responding</li>
            <li>Database connection issue</li>
          </ul>
        </div>
        <button onClick={loadWalletData} style={{ 
          marginTop: '20px', 
          padding: '12px 24px',
          background: 'linear-gradient(135deg, #4a90e2 0%, #357abd 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          fontWeight: '600',
          cursor: 'pointer'
        }}>
          🔄 Retry
        </button>
      </div>
    );
  }

  // Check if user has any keys saved
  const masterWallet = balances?.master_wallet || {};
  const exchanges = requirements?.requirements || {};
  const hasAnyKeys = Object.keys(exchanges).length > 0;

  if (!hasAnyKeys && !loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🔑</div>
        <h3 style={{ marginBottom: '12px', color: 'var(--text)' }}>Add Exchange Keys to See Wallet Balances</h3>
        <p style={{ color: 'var(--muted)', marginBottom: '20px', fontSize: '0.95rem' }}>
          Configure your exchange API keys to view your wallet balances and start trading.
        </p>
        <button 
          onClick={() => window.location.hash = '#api'}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          ➕ Add Exchange Keys
        </button>
      </div>
    );
  }

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
