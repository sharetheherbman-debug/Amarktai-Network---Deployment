import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import './DashboardV3.css';
import WalletHub from '../components/WalletHub';
import WalletOverview from '../components/WalletOverview';
import DecisionTrace from '../components/DecisionTrace';
import WhaleFlowHeatmap from '../components/WhaleFlowHeatmap';
import PrometheusMetrics from '../components/PrometheusMetrics';
import APIKeySettings from '../components/APIKeySettings';
import { API_BASE, wsUrl } from '../lib/api.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API = API_BASE;
const ADMIN_PASSWORD = 'ashmor12@';
const APP_VERSION = '1.0.6'; // Increment this to force cache clear

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [activeSection, setActiveSection] = useState('welcome');
  const [intelligenceTab, setIntelligenceTab] = useState('whale-flow'); // Tab state for Intelligence section
  // Admin panel state - Hidden by default, shown only after password
  const [showAdmin, setShowAdmin] = useState(() => {
    // Check sessionStorage only (more temporary)
    const sessionSaved = sessionStorage.getItem('adminPanelVisible');
    console.log('🔍 Initial showAdmin state from sessionStorage:', sessionSaved);
    return sessionSaved === 'true';
  });
  
  // Log whenever showAdmin changes
  useEffect(() => {
    console.log('🔄 showAdmin state changed to:', showAdmin);
  }, [showAdmin]);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [bots, setBots] = useState([]);
  const [apiKeys, setApiKeys] = useState({});
  const [metrics, setMetrics] = useState({
    totalProfit: 'R0.00',
    activeBots: '0 / 0',
    exposure: '0%',
    riskLevel: 'Unknown',
    aiSentiment: 'Neutral',
    lastUpdate: '—'
  });
  const [balances, setBalances] = useState({ zar: 0, btc: 0 });
  const [systemModes, setSystemModes] = useState({
    paperTrading: false,
    liveTrading: false,
    autopilot: false
  });
  const [awaitingPassword, setAwaitingPassword] = useState(false);
  const [adminAction, setAdminAction] = useState(null);
  const [isMobile, setIsMobile] = useState(false);
  const [expandedBots, setExpandedBots] = useState({});
  const [expandedApis, setExpandedApis] = useState({});
  const [activeBotTab, setActiveBotTab] = useState('exchange'); // Setup wizard removed - users create starting bots manually
  const [graphPeriod, setGraphPeriod] = useState('daily');
  const [profitData, setProfitData] = useState(null);
  const [projection, setProjection] = useState(null);
  const [depositAddress, setDepositAddress] = useState(null);
  const [profileData, setProfileData] = useState({});
  const [allUsers, setAllUsers] = useState([]);
  const [systemStats, setSystemStats] = useState(null);
  const [flokxAlerts, setFlokxAlerts] = useState([]);
  const [isFlokxActive, setIsFlokxActive] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({
    api: 'Disconnected',
    sse: 'Disconnected',
    ws: 'Disconnected'
  });
  const [wsRtt, setWsRtt] = useState('—');
  const [sseLastUpdate, setSseLastUpdate] = useState(null); // Track SSE last update time
  const [platformFilter, setPlatformFilter] = useState('all');
  const [editingBotId, setEditingBotId] = useState(null);
  const [editingBotName, setEditingBotName] = useState('');
  const [metricsExpanded, setMetricsExpanded] = useState(false); // State for metrics submenu
  const [botSetup, setBotSetup] = useState({
    count: 10,
    capital_per_bot: 1000,
    safe_count: 6,
    risky_count: 2,
    aggressive_count: 2,
    exchange: 'luno'
  });
  const [livePrices, setLivePrices] = useState({
    'BTC/ZAR': { price: 0, change: 0 },
    'ETH/ZAR': { price: 0, change: 0 },
    'XRP/ZAR': { price: 0, change: 0 }
  });
  const [systemHealth, setSystemHealth] = useState({
    status: 'Unknown',
    errors: 0,
    uptime: '—',
    lastCheck: '—'
  });
  const [recentTrades, setRecentTrades] = useState([]);
  const [bodyguardStatus, setBodyguardStatus] = useState(null);
  const [storageData, setStorageData] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [aiTaskLoading, setAiTaskLoading] = useState(null); // Track which AI task is running
  const [showAITools, setShowAITools] = useState(false); // Toggle AI tools submenu
  const [eligibleBots, setEligibleBots] = useState([]);
  const [showPromotionModal, setShowPromotionModal] = useState(false);
  
  const chatEndRef = useRef(null);
  const wsRef = useRef(null);
  const sseRef = useRef(null);
  
  const token = localStorage.getItem('token');
  const axiosConfig = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    loadUser();
    loadBots();
    loadMetrics();
    loadSystemModes();
    loadApiStatuses();
    loadRecentTrades();
    loadCountdown();
    
    // Setup real-time connections
    setupRealTimeConnections();
    
    // Handle responsive
    const handleResize = () => setIsMobile(window.innerWidth <= 900);
    handleResize();
    window.addEventListener('resize', handleResize);
    
    // Add personalized welcome message
    setChatMessages([{
      role: 'assist',
      content: `Hello ${user?.first_name || 'there'}! Welcome to Amarktai Network. I'm your AI assistant with full control over your trading system. Try commands like 'create a bot', 'show performance', 'enable autopilot', or ask me anything about your trading!`
    }]);
    
    return () => {
      window.removeEventListener('resize', handleResize);
      if (wsRef.current) wsRef.current.close();
      if (sseRef.current) sseRef.current.close();
    };
  }, []);
  useEffect(() => {
    if (token && user) {
      loadBots();
      loadApiStatuses();
      loadSystemStats();
      loadProfitData();
      loadLivePrices();
      setupRealTimeConnections();
      
      // Update live prices every 5 seconds
      const priceInterval = setInterval(() => {
        loadLivePrices();
      }, 5000);
      
      return () => {
        clearInterval(priceInterval);
        if (wsRef.current) wsRef.current.close();
        if (sseRef.current) sseRef.current.close();
      };
    }
  }, [token, user]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Load profit data when period changes
  useEffect(() => {
    if (connectionStatus.sse === 'Connected' || connectionStatus.api === 'Connected') {
      loadProfitData();
    }
  }, [graphPeriod, connectionStatus]);

  // Load projection for countdown
  useEffect(() => {
    calculateProjection();
    const interval = setInterval(calculateProjection, 60000);
    return () => clearInterval(interval);
  }, [balances, metrics]);

  // Load deposit address
  useEffect(() => {
    loadDepositAddress();
  }, []);

  // Set profile data when user loads
  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || '',
        email: user.email || '',
        currency: user.currency || 'ZAR',
        new_password: ''
      });
    }
  }, [user]);

  // Check for eligible bots every 5 minutes
  useEffect(() => {
    checkEligibleBots();
    const interval = setInterval(checkEligibleBots, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);

  // Load admin data when admin panel is shown
  useEffect(() => {
    if (showAdmin) {
      loadAllUsers();
      loadSystemStats();
      loadStorageData();
    }
  }, [showAdmin]);

  // Check Flokx status
  useEffect(() => {
    if (apiKeys.flokx?.connected) {
      setIsFlokxActive(true);
      loadFlokxAlerts();
      const interval = setInterval(loadFlokxAlerts, 30000);
      return () => clearInterval(interval);
    }
  }, [apiKeys.flokx]);

  const setupRealTimeConnections = () => {
    console.log('✅ Initializing WebSocket connection...');
    
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    
    const connectWebSocket = () => {
      try {
        // Use shared helper to build same-origin WS URL (wss:// on HTTPS)
        const wsEndpoint = `${wsUrl()}?token=${token}`;
        wsRef.current = new WebSocket(wsEndpoint);
        
        wsRef.current.onopen = () => {
          reconnectAttempts = 0; // Reset on successful connection
          setConnectionStatus(prev => ({ ...prev, ws: 'Connected', sse: 'Connected' }));
          console.log('✅ WebSocket connected');
          
          const pingInterval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              const startTime = Date.now();
              wsRef.current.send(JSON.stringify({ 
                type: 'ping', 
                timestamp: startTime 
              }));
            }
          }, 5000);
          
          wsRef.current.pingInterval = pingInterval;
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'pong') {
              const rtt = Date.now() - data.timestamp;
              setWsRtt(`${rtt}ms`);
            } else {
              handleRealTimeUpdate(data);
            }
          } catch (err) {
            console.error('WebSocket message parse error:', err);
          }
        };
        
        wsRef.current.onclose = () => {
          setConnectionStatus(prev => ({ ...prev, ws: 'Disconnected', sse: 'Disconnected' }));
          setWsRtt('—');
          
          // Only reconnect if under max attempts
          if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            setTimeout(() => {
              console.log(`Reconnecting... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
              connectWebSocket();
            }, 5000);
          } else {
            console.log('❌ Max reconnect attempts reached');
          }
        };
        
        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setConnectionStatus(prev => ({ ...prev, ws: 'Error', sse: 'Error' }));
        };
      } catch (err) {
        console.error('WebSocket connection error:', err);
        setConnectionStatus(prev => ({ ...prev, ws: 'Error', sse: 'Error' }));
      }
    };
    
    // Only use WebSocket (SSE disabled due to auth issues)
    try {
      connectWebSocket();
    } catch (err) {
      console.error('Failed to initialize WebSocket:', err);
      setConnectionStatus({ ws: 'Error', sse: 'Error', api: 'Connected' });
    }
  };

  const handleRealTimeUpdate = (data) => {
    switch (data.type) {
      case 'metrics':
        setMetrics(prev => ({ ...prev, ...data.payload }));
        break;
      case 'bot_status':
        setBots(prev => prev.map(bot => 
          bot.id === data.payload.bot_id 
            ? { ...bot, ...data.payload.updates }
            : bot
        ));
        break;
      case 'balance':
        setBalances(prev => ({ ...prev, ...data.payload }));
        break;
      case 'notification':
        showNotification(data.payload.message, data.payload.type || 'info');
        break;
      case 'chat_response':
        setChatMessages(prev => [...prev, { 
          role: 'assist', 
          content: data.payload.message 
        }]);
        break;
      case 'trade_executed':
        // Real-time trade feed update - only update state, don't reload
        setRecentTrades(prev => {
          // Prevent duplicates by checking if trade already exists
          const tradeExists = prev.some(t => t.id === data.trade?.id);
          if (tradeExists) return prev;
          
          return [{
            ...data.trade,
            bot_name: data.bot_name,
            timestamp: new Date().toISOString()
          }, ...prev.slice(0, 49)]; // Keep last 50 trades
        });
        
        // Update bot data
        setBots(prev => prev.map(bot => 
          bot.id === data.bot_id 
            ? { 
                ...bot, 
                current_capital: data.new_capital,
                total_profit: data.total_profit,
                name: bot.name || data.bot_name // Preserve bot name
              }
            : bot
        ));
        
        // Refresh metrics to show new profit
        loadMetrics();
        break;
      
      case 'profit_update':
        // Real-time profit update in overview
        setMetrics(prev => ({
          ...prev,
          totalProfit: `R${data.total_profit.toFixed(2)}`
        }));
        // Update countdown when profit changes
        loadCountdown();
        break;
      
      case 'system_mode_update':
        // System mode changed
        setSystemModes(data.modes);
        toast.success('System modes updated');
        break;
      
      case 'bot_created':
        // Reload bots and metrics immediately
        loadBots();
        loadMetrics();
        if (data.message) toast.success(data.message);
        break;
      
      case 'bot_updated':
        // Update specific bot
        setBots(prev => prev.map(bot => 
          bot.id === data.bot_id ? { ...bot, ...data.changes } : bot
        ));
        break;
      
      case 'bot_deleted':
        // Reload bots list
        loadBots();
        loadMetrics();
        if (data.message) toast.success(data.message);
        break;
      
      case 'bot_promoted':
        // Bot promoted to live
        loadBots();
        if (data.message) toast.success(data.message);
        break;
      
      case 'api_key_update':
        // API key connected/updated
        loadApiStatuses();
        if (data.message) toast.success(data.message);
        break;
      
      case 'autopilot_action':
        // Autopilot did something
        loadBots();
        loadMetrics();
        if (data.message) toast.info(data.message);
        break;
      
      case 'self_healing':
        // Self-healing paused a bot
        loadBots();
        if (data.message) toast.warning(data.message);
        break;
      
      case 'countdown_update':
        // Countdown changed
        loadCountdown();
        break;
      
      // REMOVED: Duplicate trade_executed handler
      // Now handled above with state updates only (no full reload)
      
      case 'profit_updated':
        // Profit changed - update all profit displays
        loadMetrics();
        loadCountdown();
        loadProfitData(graphPeriod);
        break;
      
      case 'ai_evolution':
        // AI learning/evolution happened
        if (data.message) toast.info(data.message);
        loadBots(); // May have new bots
        break;
      
      case 'system_update':
        // General system update from AI
        loadBots();
        loadSystemModes();
        loadMetrics();
        if (data.success) {
          toast.success('System updated successfully');
        }
        break;
      
      case 'force_refresh':
        // FORCE IMMEDIATE REFRESH from AI action - COMPLETE STATE RESET
        console.log('🔄 FORCE REFRESH - Clearing ALL state');
        
        // Clear ALL state to zeros/empty first
        setProfitData({
          labels: [],
          values: [],
          total: 0,
          avg_daily: 0,
          best_day: 0,
          growth_rate: 0
        });
        setCountdown(null);
        setRecentTrades([]);
        setBots([]);
        setMetrics({
          total_profit: 0,
          total_trades: 0,
          win_rate: 0,
          active_bots: 0
        });
        
        // Clear browser cache for profit data
        sessionStorage.removeItem('profitData');
        sessionStorage.removeItem('recentTrades');
        
        // Wait a moment then reload everything
        setTimeout(() => {
          loadBots();
          loadSystemModes();
          loadMetrics();
          loadProfitData();
          loadCountdown();
          loadRecentTrades();
          loadBalances();
        }, 100);
        
        if (data.message) {
          toast.success(data.message + ' - All data cleared!');
        }
        break;
      
      default:
        console.log('Unknown real-time update:', data);
    }
  };

  const showNotification = (message, type = 'success') => {
    toast[type](message);
  };

  // Helper to extract error message from backend response
  const extractErrorMessage = (err, defaultMsg = 'An error occurred') => {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'object' && detail !== null) {
      return detail.message || detail.error || JSON.stringify(detail);
    }
    return detail || err.message || defaultMsg;
  };

  const loadUser = async () => {
    try {
      const res = await axios.get(`${API}/auth/me`, axiosConfig);
      setUser(res.data);
      setConnectionStatus(prev => ({ ...prev, api: 'Connected' }));
    } catch (err) {
      console.error('User fetch error:', err);
      setConnectionStatus(prev => ({ ...prev, api: 'Disconnected' }));
      if (err.response?.status === 401) navigate('/login');
    }
  };

  const loadBots = async () => {
    try {
      const res = await axios.get(`${API}/bots`, axiosConfig);
      setBots(res.data || []);
    } catch (err) {
      console.error('Bots fetch error:', err);
    }
  };

  const loadRecentTrades = async () => {
    try {
      const res = await axios.get(`${API}/trades/recent?limit=50`, axiosConfig);
      setRecentTrades(res.data.trades || []);
    } catch (err) {
      console.error('Recent trades fetch error:', err);
    }
  };

  const loadMetrics = async () => {
    try {
      const res = await axios.get(`${API}/portfolio/summary`, axiosConfig);
      setMetrics({
        totalProfit: `R${res.data.net_pnl?.toFixed(2) || '0.00'}`,
        activeBots: `${res.data.active_bots || 0} / ${res.data.total_bots || 0}`,
        exposure: `${res.data.exposure?.toFixed(1) || 0}%`,
        riskLevel: res.data.risk_level || 'Unknown',
        aiSentiment: res.data.ai_sentiment || 'Neutral',
        lastUpdate: new Date().toLocaleTimeString() || '—'
      });
    } catch (err) {
      console.error('Metrics fetch error:', err);
    }
  };

  const loadSystemModes = async () => {
    try {
      const res = await axios.get(`${API}/system/mode`, axiosConfig);
      setSystemModes({
        paperTrading: res.data.paperTrading || false,
        liveTrading: res.data.liveTrading || false,
        autopilot: res.data.autopilot || false
      });
    } catch (err) {
      console.error('System modes fetch error:', err);
    }
  };

  const loadApiStatuses = async () => {
    try {
      const res = await axios.get(`${API}/api-keys`, axiosConfig);
      const statuses = {};
      (res.data || []).forEach(key => {
        statuses[key.provider.toLowerCase()] = {
          status: key.connected ? 'verified' : 'saved',
          connected: key.connected
        };
      });
      setApiKeys(statuses);
    } catch (err) {
      console.error('API keys fetch error:', err);
    }
  };

  const loadCountdown = async () => {
    try {
      const res = await axios.get(`${API}/analytics/countdown-to-million`, axiosConfig);
      setCountdown(res.data);
    } catch (err) {
      console.error('Countdown fetch error:', err);
    }
  };

  const loadStorageData = async () => {
    try {
      const res = await axios.get(`${API}/admin/storage`, axiosConfig);
      setStorageData(res.data);
    } catch (err) {
      console.error('Storage data fetch error:', err);
    }
  };

  const checkEligibleBots = async () => {
    try {
      const res = await axios.get(`${API}/bots/eligible-for-promotion`, axiosConfig);
      if (res.data.count > 0) {
        setEligibleBots(res.data.eligible_bots);
        setShowPromotionModal(true);
      }
    } catch (err) {
      console.error('Eligible bots check error:', err);
    }
  };

  const confirmLiveSwitch = async (lunoFunded, usePaperBots) => {
    try {
      const res = await axios.post(`${API}/bots/confirm-live-switch`, {
        luno_funded: lunoFunded,
        use_paper_bots: usePaperBots
      }, axiosConfig);
      toast.success(res.data.message || 'Bots switched to live trading!');
      setShowPromotionModal(false);
      loadBots();
      loadSystemModes();
    } catch (err) {
      console.error('Live switch error:', err);
      toast.error(extractErrorMessage(err, 'Failed to switch to live trading'));
    }
  };


  const loadBalances = async () => {
    try {
      const res = await axios.get(`${API}/wallet/balances`, axiosConfig);
      setBalances({
        zar: res.data.zar || 0,
        btc: res.data.btc || 0
      });
    } catch (err) {
      console.error('Balances fetch error:', err);
    }
  };

  const loadProfitData = async () => {
    try {
      const res = await axios.get(`${API}/profits?period=${graphPeriod}`, axiosConfig);
      setProfitData(res.data);
    } catch (err) {
      console.error('Profit data error:', err);
    }
  };

  const loadLivePrices = async () => {
    try {
      const res = await axios.get(`${API}/prices/live`, axiosConfig);
      // Backend returns prices directly, not wrapped
      setLivePrices(res.data || {});
    } catch (err) {
      console.error('Live prices fetch error:', err);
    }
  };

  const calculateProjection = async () => {
    // This function now fetches from countdown endpoint
    // Note: loadCountdown() is already called, so we just ensure projection state matches countdown
    if (countdown) {
      setProjection({
        days_to_million: countdown.days_remaining < 9999 ? countdown.days_remaining : '∞',
        current_balance: countdown.current_capital,
        daily_growth_rate: countdown.metrics?.daily_roi_pct?.toFixed(3) || '0.000',
        progress_percentage: countdown.progress_pct?.toFixed(1) || '0.0',
        projected_annual: (countdown.metrics?.avg_daily_profit * 365)?.toFixed(2) || '0.00',
        compound_effect: countdown.projections?.using === 'compound' ? 100 : 0
      });
    }
  };

  const loadDepositAddress = async () => {
    try {
      const res = await axios.get(`${API}/wallet/deposit-address`, axiosConfig);
      setDepositAddress(res.data);
    } catch (err) {
      console.error('Deposit address error:', err);
    }
  };

  const loadAllUsers = async () => {
    try {
      const res = await axios.get(`${API}/admin/users`, axiosConfig);
      setAllUsers(res.data.users || []);
    } catch (err) {
      console.error('Admin users error:', err);
      setAllUsers([]);
    }
  };

  const loadSystemStats = async () => {
    try {
      const res = await axios.get(`${API}/admin/system-stats`, axiosConfig);
      setSystemStats(res.data);
    } catch (err) {
      console.error('System stats error:', err);
    }
  };

  const loadFlokxAlerts = async () => {
    try {
      const res = await axios.get(`${API}/flokx/alerts`, axiosConfig);
      setFlokxAlerts(res.data?.alerts || []);
    } catch (err) {
      console.error('Flokx alerts error:', err);
      setFlokxAlerts([]);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    const msgLower = chatInput.toLowerCase();
    const originalInput = chatInput;
    setChatInput('');

    // Handle admin commands - COMPLETELY FRONTEND ONLY
    if (awaitingPassword) {
      if (originalInput === ADMIN_PASSWORD) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: '✅ Password correct!' }]);
        
        if (adminAction === 'show') {
          console.log('🔓 SHOWING ADMIN - Setting state to TRUE');
          setShowAdmin(true);
          sessionStorage.setItem('adminPanelVisible', 'true');
          // Force re-render by updating section
          setTimeout(() => {
            setActiveSection('admin');
            console.log('Admin section activated, showAdmin:', true);
          }, 100);
        } else if (adminAction === 'hide') {
          console.log('🔒 HIDING ADMIN - Setting state to FALSE');
          setShowAdmin(false);
          sessionStorage.setItem('adminPanelVisible', 'false');
          setActiveSection('welcome');
          console.log('Admin section deactivated, showAdmin:', false);
        }
        
        setAwaitingPassword(false);
        setAdminAction(null);
      } else {
        console.log('❌ WRONG PASSWORD:', originalInput);
        setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Wrong password. You entered: "${originalInput}". Correct password starts with "ash..."` }]);
        setAwaitingPassword(false);
        setAdminAction(null);
      }
      return;
    }

    // Handle show/hide admin commands (frontend only)
    if (msgLower === 'show admin' || msgLower === 'show admn') {
      setAwaitingPassword(true);
      setAdminAction('show');
      setChatMessages(prev => [...prev, { role: 'assistant', content: '🔐 Please enter the admin password:' }]);
      return; // STOP - do not send to backend
    }

    if (msgLower === 'hide admin') {
      setAwaitingPassword(true);
      setAdminAction('hide');
      setChatMessages(prev => [...prev, { role: 'assistant', content: '🔐 Please enter the admin password:' }]);
      return; // STOP - do not send to backend
    }

    // Send all other messages to AI backend
    try {
      const res = await axios.post(`${API}/chat`, { content: originalInput }, axiosConfig);
      // Backend returns plain string, not an object
      const reply = typeof res.data === 'string' ? res.data : (res.data.response || res.data.reply || res.data.message || 'No response');
      setChatMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      console.error('Chat error:', err);
      setChatMessages(prev => [...prev, { role: 'assistant', content: `AI error: ${err.message}` }]);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const showSection = (section) => {
    setActiveSection(section);
  };

  const toggleSystemMode = async (mode) => {
    const newValue = !systemModes[mode];
    
    // Paper and Live trading are mutually exclusive
    if (mode === 'paperTrading' && newValue) {
      setSystemModes(prev => ({ ...prev, paperTrading: true, liveTrading: false }));
      showNotification('Paper Trading activated. Live Trading disabled.');
    } else if (mode === 'liveTrading' && newValue) {
      if (!window.confirm('⚠️ WARNING: This will enable REAL trading with REAL money. Are you sure?')) {
        return;
      }
      setSystemModes(prev => ({ ...prev, liveTrading: true, paperTrading: false }));
      showNotification('Live Trading activated. Paper Trading disabled.');
    } else {
      setSystemModes(prev => ({ ...prev, [mode]: newValue }));
      showNotification(`${mode} ${newValue ? 'activated' : 'deactivated'}`);
    }
    
    try {
      await axios.put(`${API}/system/mode`, { mode, enabled: newValue }, axiosConfig);
    } catch (err) {
      console.error('Mode toggle error:', err);
      showNotification('Failed to update mode', 'error');
    }
  };

  const handleEmergencyStop = async () => {
    if (!window.confirm('🚨 EMERGENCY STOP: This will immediately stop ALL bots and trading activity. Continue?')) {
      return;
    }
    
    try {
      await axios.post(`${API}/system/emergency-stop`, {}, axiosConfig);
      showNotification('🚨 EMERGENCY STOP ACTIVATED - All systems halted', 'error');
      setSystemModes({ paperTrading: false, liveTrading: false, autopilot: false });
      loadBots();
    } catch (err) {
      console.error('Emergency stop error:', err);
      showNotification('Emergency stop failed', 'error');
    }
  };

  const toggleBotExpand = (botId) => {
    setExpandedBots(prev => ({ ...prev, [botId]: !prev[botId] }));
  };

  const toggleApiExpand = (provider) => {
    setExpandedApis(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleCreateBot = async (e) => {
    e.preventDefault();
    const name = e.target['bot-name'].value;
    const budget = parseInt(e.target['bot-budget'].value);
    const exchange = e.target['bot-exchange'].value;
    const riskMode = e.target['bot-risk'].value;
    
    if (!name) {
      showNotification('Please enter a bot name', 'error');
      return;
    }

    if (budget < 1000) {
      showNotification('Minimum budget is R1000', 'error');
      return;
    }

    try {
      // Prepare bot data - USER CREATED = 7 day learning period
      const botData = {
        name,
        exchange,
        trading_mode: 'paper', // Always start in paper for user bots
        risk_mode: riskMode,
        initial_capital: budget,
        created_by: 'user', // Track origin
        paper_start_date: new Date().toISOString(), // Start 7-day countdown
        learning_complete: false
      };
      
      await axios.post(`${API}/bots`, botData, axiosConfig);
      showNotification(`Bot "${name}" created! Starting 7-day learning period.`, 'success');
      loadBots();
      e.target.reset();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' ? detail.message || JSON.stringify(detail) : detail || 'Failed to create bot';
      showNotification(errorMsg, 'error');
      console.error('Bot creation error:', err);
    }
  };

  const handleCreateUAgent = async (e) => {
    e.preventDefault();
    const name = e.target['uagent-name'].value;
    const file = e.target['uagent-file'].files[0];
    const strategy = e.target['uagent-strategy'].value;
    
    if (!name || !file) {
      showNotification('Please provide name and file', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    formData.append('strategy', strategy);
    formData.append('type', 'uagent');

    try {
      await axios.post(`${API}/bots/uagent`, formData, {
        ...axiosConfig,
        headers: {
          ...axiosConfig.headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      showNotification(`uAgent "${name}" deployed successfully!`);
      loadBots();
      e.target.reset();
    } catch (err) {
      showNotification('Failed to deploy uAgent', 'error');
    }
  };

  const handleCreateFlokxBot = async (e) => {
    e.preventDefault();
    const name = e.target['flokx-name'].value;
    const signalType = e.target['flokx-signal'].value;
    const riskLevel = e.target['flokx-risk'].value;
    
    if (!name) {
      showNotification('Please enter a bot name', 'error');
      return;
    }

    try {
      await axios.post(`${API}/bots/flokx`, { 
        name, 
        signal_type: signalType, 
        risk_level: riskLevel,
        type: 'flokx'
      }, axiosConfig);
      showNotification(`Flokx bot "${name}" created successfully!`);
      loadBots();
      e.target.reset();
    } catch (err) {
      showNotification('Failed to create Flokx bot', 'error');
    }
  };

  const handleDeleteBot = async (botId) => {
    if (!window.confirm('Delete this bot? This cannot be undone.')) return;
    
    try {
      await axios.delete(`${API}/bots/${botId}`, axiosConfig);
      showNotification('Bot deleted');
      loadBots();
    } catch (err) {
      showNotification('Failed to delete bot', 'error');
    }
  };

  const handleSaveBotName = async (botId) => {
    try {
      await axios.put(`${API}/bots/${botId}`, { name: editingBotName }, axiosConfig);
      showNotification('Bot name updated');
      setEditingBotId(null);
      setEditingBotName('');
      loadBots();
    } catch (err) {
      showNotification('Failed to update bot name', 'error');
    }
  };

  const handleChangeRiskMode = async (botId, newRiskMode) => {
    try {
      await axios.put(`${API}/bots/${botId}`, { risk_mode: newRiskMode }, axiosConfig);
      showNotification(`Risk mode changed to ${newRiskMode.toUpperCase()}`);
      loadBots();
    } catch (err) {
      showNotification('Failed to change risk mode', 'error');
    }
  };

  const handleToggleBotMode = async (botId, currentMode) => {
    const newMode = currentMode === 'paper' ? 'live' : 'paper';
    
    if (newMode === 'live') {
      if (!window.confirm('⚠️ WARNING: Switch to LIVE trading with REAL money?\n\nThis bot will trade with actual funds. Are you sure?')) {
        return;
      }
    }
    
    try {
      await axios.put(`${API}/bots/${botId}`, { trading_mode: newMode }, axiosConfig);
      showNotification(`✅ Bot switched to ${newMode.toUpperCase()} mode`);
      loadBots();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to change bot mode';
      showNotification(`❌ ${errorMsg}`, 'error');
    }
  };

  const handleBotSetup = async () => {
    const { count, capital_per_bot, safe_count, risky_count, aggressive_count } = botSetup;
    
    // Validation
    if (count < 3 || count > 30) {
      showNotification('❌ Bot count must be between 3 and 30', 'error');
      return;
    }
    
    if (safe_count + risky_count + aggressive_count !== count) {
      showNotification('❌ Risk distribution must equal total bot count', 'error');
      return;
    }
    
    if (capital_per_bot < 1000) {
      showNotification('❌ Minimum capital per bot is R1000', 'error');
      return;
    }
    
    const total_capital = count * capital_per_bot;
    const confirm_msg = `🤖 Create ${count} bots with R${total_capital.toLocaleString()} total capital?\n\n` +
      `💰 R${capital_per_bot.toLocaleString()} per bot\n` +
      `🛡️ ${safe_count} Safe bots\n` +
      `⚡ ${risky_count} Risky bots\n` +
      `🚀 ${aggressive_count} Aggressive bots\n\n` +
      `All bots will start in PAPER mode with FAKE funds for 7 days.`;
    
    if (!window.confirm(confirm_msg)) return;
    
    try {
      const res = await axios.post(`${API}/bots/batch-create`, botSetup, axiosConfig);
      const createdCount = res.data.bots?.length || res.data.created || botSetup.count;
      showNotification(`✅ Created ${createdCount} bots successfully!`, 'success');
      loadBots();
      showSection('bots');
    } catch (err) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' ? detail.message || JSON.stringify(detail) : detail || 'Failed to create bots';
      showNotification(`❌ ${errorMsg}`, 'error');
    }
  };

  const handleSaveApiKey = async (provider) => {
    const formId = `form-${provider}`;
    const form = document.getElementById(formId);
    if (!form) return;

    const inputs = form.querySelectorAll('input');
    const data = { provider };
    let hasValidInput = false;
    
    inputs.forEach(input => {
      const value = input.value.trim();
      if (value) {
        // Map field names correctly
        if (input.name === 'api_token') {
          data['api_key'] = value;  // Flokx uses api_token in UI but api_key in backend
        } else {
          data[input.name] = value;
        }
        hasValidInput = true;
      }
    });

    // Validate that at least the primary API key is provided
    if (!hasValidInput || !data.api_key) {
      showNotification('Please enter a valid API key', 'error');
      return;
    }

    // Special validation for OpenAI
    if (provider === 'openai' && data.api_key && !data.api_key.startsWith('sk-')) {
      showNotification('Invalid OpenAI API key format (must start with sk-)', 'error');
      return;
    }

    // Validate exchange keys have secrets
    if (['luno', 'binance', 'kucoin'].includes(provider) && !data.api_secret) {
      showNotification(`${provider.toUpperCase()} requires both API key and secret`, 'error');
      return;
    }

    try {
      await axios.post(`${API}/keys/save`, data, axiosConfig);
      showNotification(`✅ ${provider.toUpperCase()} API key saved!`);
      loadApiStatuses();
      
      // Clear form inputs after successful save
      inputs.forEach(input => input.value = '');
    } catch (err) {
      showNotification(extractErrorMessage(err, 'Failed to save API key'), 'error');
      console.error('API key save error:', err);
    }
  };

  const handleTestApiKey = async (provider) => {
    try {
      await axios.post(`${API}/keys/test`, { provider }, axiosConfig);
      showNotification(`${provider} connection verified!`);
      loadApiStatuses();
    } catch (err) {
      showNotification(`${provider} connection failed`, 'error');
    }
  };

  const handleDeleteApiKey = async (provider) => {
    if (!window.confirm(`Remove ${provider} API keys?`)) return;
    
    try {
      await axios.delete(`${API}/api-keys/${provider}`, axiosConfig);
      
      // Immediately clear from state
      setApiKeys(prev => {
        const updated = { ...prev };
        delete updated[provider.toLowerCase()];
        return updated;
      });
      
      showNotification(`✅ ${provider} API removed`);
      
      // Reload to confirm
      setTimeout(() => loadApiStatuses(), 500);
    } catch (err) {
      showNotification('❌ Failed to remove API key', 'error');
    }
  };

  const getApiStatus = (provider) => {
    const key = apiKeys[provider.toLowerCase()];
    if (!key) return { badge: 'missing', text: 'Not configured', dot: 'err' };
    if (key.connected) return { badge: 'verified', text: 'Verified ✓', dot: 'ok' };
    return { badge: 'saved', text: 'Saved (untested)', dot: 'err' };
  };

  const handleProfileChange = (field, value) => {
    setProfileData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleProfileSave = async () => {
    try {
      const updateData = {
        first_name: profileData.first_name,
        email: profileData.email,
        currency: profileData.currency
      };
      
      if (profileData.new_password) {
        updateData.new_password = profileData.new_password;
      }

      // Use PUT method and correct endpoint: /api/auth/profile
      await axios.put(`${API}/auth/profile`, updateData, axiosConfig);
      showNotification('Profile updated successfully!');
      
      // Update local user state
      setUser(prev => ({
        ...prev,
        first_name: profileData.first_name,
        email: profileData.email
      }));
      
      // Clear password field
      setProfileData(prev => ({
        ...prev,
        new_password: ''
      }));
    } catch (err) {
      showNotification(extractErrorMessage(err, 'Failed to update profile'), 'error');
      console.error('Profile update error:', err);
    }
  };

  const copyAddress = async (address) => {
    if (!address || address === 'N/A') {
      showNotification('No address available', 'error');
      return;
    }
    
    try {
      await navigator.clipboard.writeText(address);
      showNotification('Address copied to clipboard!');
    } catch (err) {
      console.error('Copy failed:', err);
      showNotification('Failed to copy address', 'error');
    }
  };

  const getAlertColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'var(--error)';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return 'var(--success)';
      default:
        return 'var(--accent)';
    }
  };

  const handleTriggerBodyguard = async () => {
    try {
      setAiTaskLoading('bodyguard');
      showNotification('🛡️ AI Bodyguard scanning system...', 'info');
      setActiveSection('welcome'); // Switch to chat to see results
      
      const res = await axios.post(`${API}/autonomous/bodyguard/system-check`, {}, axiosConfig);
      const report = res.data;
      
      // Save status for display
      setBodyguardStatus(report);
      
      // Show detailed report in chat
      const message = `🛡️ AI Bodyguard System Scan Complete!\n\n` +
        `📊 Health Score: ${report.health_score}/100 (${report.health_status})\n` +
        `❌ Critical Issues: ${report.issues?.length || 0}\n` +
        `⚠️ Warnings: ${report.warnings?.length || 0}\n` +
        `✅ Passed Checks: ${report.passed_checks || 0}\n` +
        `⏱️ Scan Time: ${new Date().toLocaleTimeString()}\n\n` +
        (report.issues?.length > 0 ? `Issues Found:\n${report.issues.map(i => `• ${i}`).join('\n')}\n\n` : '') +
        (report.warnings?.length > 0 ? `Warnings:\n${report.warnings.map(w => `• ${w}`).join('\n')}\n\n` : '') +
        `💬 Ask me about any concerns or recommendations!`;
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: message 
      }]);
      
      showNotification(
        `🛡️ Health: ${report.health_score}/100`,
        report.health_score >= 80 ? 'success' : 'warning'
      );
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Bodyguard check failed';
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `❌ Bodyguard scan failed: ${errorMsg}` 
      }]);
      showNotification(`❌ ${errorMsg}`, 'error');
    } finally {
      setAiTaskLoading(null);
    }
  };

  const handleTriggerLearning = async () => {
    try {
      setAiTaskLoading('learning');
      showNotification('📚 AI Learning in progress...', 'info');
      setActiveSection('welcome'); // Switch to chat to see results
      
      const res = await axios.post(`${API}/autonomous/learning/trigger`, {}, axiosConfig);
      
      // Show detailed report in chat
      const report = res.data.report || {};
      const message = `📚 AI Learning Analysis Complete!\n\n` +
        `📊 Trades Analyzed: ${report.trades_analyzed || 0}\n` +
        `📈 Win Rate: ${report.win_rate || 0}%\n` +
        `💰 Avg Profit: R${report.avg_profit || 0}\n` +
        `🎯 Strategy Updates: ${report.updates || 'Optimized'}\n` +
        `⏱️ Completed: ${new Date().toLocaleTimeString()}\n\n` +
        `💬 Ask me any questions about this report!`;
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: message 
      }]);
      
      showNotification('✅ AI Learning complete!', 'success');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Learning failed';
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `❌ Learning failed: ${errorMsg}` 
      }]);
      showNotification(`❌ ${errorMsg}`, 'error');
    } finally {
      setAiTaskLoading(null);
    }
  };

  const handleEmailAllUsers = async () => {
    const subject = window.prompt('📧 Email Subject:');
    if (!subject) return;
    
    const message = window.prompt('📧 Email Message:');
    if (!message) return;
    
    if (!window.confirm(`Send to ALL users?\n\nSubject: ${subject}`)) return;
    
    try {
      const res = await axios.post(`${API}/admin/email-all-users`, { subject, message }, axiosConfig);
      showNotification(`✅ Sent to ${res.data.sent} users (${res.data.failed} failed)`, 'success');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to send emails';
      showNotification(`❌ ${errorMsg}`, 'error');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return;
    }

    try {
      await axios.delete(`${API}/admin/users/${userId}`, axiosConfig);
      showNotification('User deleted successfully');
      loadAllUsers();
      loadSystemStats(); // Update stats
    } catch (err) {
      showNotification('Failed to delete user', 'error');
      console.error('Delete user error:', err);
    }
  };

  const handleBlockUser = async (userId, isBlocked) => {
    const action = isBlocked ? 'unblock' : 'block';
    if (!window.confirm(`Are you sure you want to ${action} this user?`)) {
      return;
    }

    try {
      await axios.put(`${API}/admin/users/${userId}/block`, 
        { blocked: !isBlocked }, 
        axiosConfig
      );
      showNotification(`User ${action}ed successfully`);
      loadAllUsers();
      loadSystemStats(); // Update stats
    } catch (err) {
      showNotification(`Failed to ${action} user`, 'error');
      console.error(`${action} user error:`, err);
    }
  };

  const handleChangePassword = async (userId) => {
    const newPassword = window.prompt('Enter new password for this user (minimum 6 characters):');
    if (!newPassword) {
      return;
    }

    if (newPassword.length < 6) {
      showNotification('Password must be at least 6 characters', 'error');
      return;
    }

    try {
      await axios.put(`${API}/admin/users/${userId}/password`, 
        { new_password: newPassword }, 
        axiosConfig
      );
      showNotification('Password changed successfully');
      loadAllUsers(); // Refresh user list after password change
    } catch (err) {
      showNotification('Failed to change password', 'error');
      console.error('Password change error:', err);
    }
  };

  const renderWelcome = () => (
    <section className="section active">
      <div className="card welcome-container">
        <div className="welcome-header">
          <h2>Welcome, {user?.first_name || 'User'}</h2>
          <p>Control your AI trading system with natural language.</p>
        </div>
        
        {/* AI Tools Toggle Button */}
        <div style={{marginBottom: '16px'}}>
          <button 
            onClick={() => setShowAITools(!showAITools)}
            style={{
              width: '100%',
              padding: '12px 16px',
              background: showAITools ? 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' : 'var(--panel)',
              color: showAITools ? 'white' : 'var(--text)',
              border: '1px solid var(--success)',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <span>🧠 AI Tools & Analytics</span>
            <span>{showAITools ? '▼' : '▶'}</span>
          </button>
        </div>
        
        {/* AI Tools & Analytics - Collapsible */}
        {showAITools && (
        <div style={{marginBottom: '20px', padding: '16px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--success)'}}>
          <p style={{fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '12px'}}>
            ⚡ All reports appear in the chat below. Ask questions about results!
          </p>
          
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px'}}>
            <button 
              onClick={handleTriggerLearning}
              disabled={aiTaskLoading === 'learning'}
              style={{padding: '12px', background: aiTaskLoading === 'learning' ? '#666' : 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', color: 'white', border: 'none', borderRadius: '6px', cursor: aiTaskLoading === 'learning' ? 'wait' : 'pointer', fontWeight: 600, fontSize: '0.9rem', opacity: aiTaskLoading === 'learning' ? 0.7 : 1}}
            >
              {aiTaskLoading === 'learning' ? '⏳ Analyzing...' : '📚 AI Learning'}
            </button>
            
            <button 
              onClick={async () => {
                try {
                  showNotification('🧬 Evolving bots...', 'info');
                  const res = await axios.post(`${API}/bots/evolve`, {}, axiosConfig);
                  const msg = `🧬 Evolution Complete!\n\nEvolved ${res.data.evolved} bots (Generation ${res.data.generation})\n\nNew bots created with optimized DNA from top performers.`;
                  setChatMessages(prev => [...prev, { role: 'assistant', content: msg }]);
                  showNotification(`✅ Evolved ${res.data.evolved} bots!`, 'success');
                } catch (err) {
                  const errorMsg = err.response?.data?.detail || 'Evolution failed';
                  setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Evolution failed: ${errorMsg}` }]);
                  showNotification(errorMsg, 'error');
                }
              }}
              style={{padding: '12px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'}}
            >
              🧬 Evolve Bots
            </button>
            
            <button 
              onClick={async () => {
                try {
                  showNotification('💡 Generating insights...', 'info');
                  const res = await axios.get(`${API}/insights/daily`, axiosConfig);
                  const msg = `💡 AI Insights Report\n\n${res.data.insights}\n\nRecommendations:\n${res.data.recommendations.map((r, i) => `${i+1}. ${r}`).join('\n')}`;
                  setChatMessages(prev => [...prev, { role: 'assistant', content: msg }]);
                  showNotification('✅ Insights generated!', 'success');
                } catch (err) {
                  showNotification('Insights failed', 'error');
                }
              }}
              style={{padding: '12px', background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'}}
            >
              💡 AI Insights
            </button>
            
            <button 
              onClick={async () => {
                try {
                  const res = await axios.get(`${API}/ml/predict/BTC-ZAR?timeframe=1h`, axiosConfig);
                  const msg = `🔮 ML Price Prediction\n\nPair: BTC/ZAR\nDirection: ${res.data.direction.toUpperCase()}\nConfidence: ${(res.data.confidence*100).toFixed(1)}%\nTimeframe: 1 hour\n\nPredicted Change: ${res.data.predicted_change > 0 ? '+' : ''}${res.data.predicted_change.toFixed(2)}%`;
                  setChatMessages(prev => [...prev, { role: 'assistant', content: msg }]);
                  showNotification(`📈 BTC: ${res.data.direction} (${(res.data.confidence*100).toFixed(0)}%)`, 'info');
                } catch (err) {
                  showNotification('Prediction failed', 'error');
                }
              }}
              style={{padding: '12px', background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'}}
            >
              🔮 ML Predict
            </button>
            
            <button 
              onClick={async () => {
                try {
                  const res = await axios.post(`${API}/autonomous/reinvest-profits`, {}, axiosConfig);
                  const msg = `💰 Profit Reinvestment\n\nReinvested: R${res.data.reinvested.toFixed(2)}\nBots Funded: ${res.data.bots_funded}\n\n${res.data.message}`;
                  setChatMessages(prev => [...prev, { role: 'assistant', content: msg }]);
                  showNotification(`✅ Reinvested R${res.data.reinvested.toFixed(2)}`, 'success');
                } catch (err) {
                  showNotification('Reinvestment failed', 'error');
                }
              }}
              style={{padding: '12px', background: 'linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'}}
            >
              💰 Reinvest Profits
            </button>
          </div>
        </div>
        )}
        
        <div className="amk-chat">
          <div className="amk-chat-box">
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`msg ${msg.role}`}>
                <div className="bubble">{msg.content}</div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          <div className="amk-row">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type a message or ask about AI reports..."
            />
            <button className="send" onClick={handleSendMessage}>Send</button>
          </div>
        </div>
      </div>
    </section>
  );

  const renderOverview = () => (
    <section className="section active">
      <div className="card">
        <h2>System Overview</h2>
        <div className="overview-container">
          <div className="overview-image"></div>
          <div className="overview-metrics">
            <div className="status-list">
              <div className="status-item">
                <strong>Total Profit</strong>
                <div className="led-row"><span>{metrics.totalProfit}</span></div>
              </div>
              <div className="status-item">
                <strong>Active Bots</strong>
                <div className="led-row"><span>{metrics.activeBots}</span></div>
              </div>
              <div className="status-item">
                <strong>Exposure</strong>
                <div className="led-row"><span>{metrics.exposure}</span></div>
              </div>
              <div className="status-item">
                <strong>Risk Level</strong>
                <div className="led-row"><span>{metrics.riskLevel}</span></div>
              </div>
              <div className="status-item">
                <strong>AI Sentiment</strong>
                <div className="led-row"><span>{metrics.aiSentiment}</span></div>
              </div>
              <div className="status-item">
                <strong>Last Update</strong>
                <div className="led-row"><span>{metrics.lastUpdate}</span></div>
              </div>
              <div className="status-item">
                <strong>Round-Trip Time</strong>
                <div className="led-row"><span>{wsRtt}</span></div>
              </div>
              <div className="status-item">
                <strong>WebSocket</strong>
                <div className="led-row">
                  <span style={{color: connectionStatus.ws === 'Connected' ? 'var(--success)' : 'var(--error)'}}>
                    {connectionStatus.ws}
                  </span>
                  <div className={`status-dot ${connectionStatus.ws === 'Connected' ? 'ok' : 'err'}`}></div>
                </div>
              </div>
              <div className="status-item">
                <strong>Live Updates</strong>
                <div className="led-row">
                  <span style={{color: connectionStatus.sse === 'Connected' ? 'var(--success)' : 'var(--error)'}}>
                    {connectionStatus.sse}
                  </span>
                  <div className={`status-dot ${connectionStatus.sse === 'Connected' ? 'ok' : 'err'}`}></div>
                </div>
              </div>
              <div className="status-item">
                <strong>BTC/ZAR</strong>
                <div className="led-row">
                  <span>R{livePrices['BTC/ZAR']?.price?.toLocaleString() || '0'}</span>
                  <span style={{
                    color: livePrices['BTC/ZAR']?.change >= 0 ? 'var(--success)' : 'var(--error)',
                    fontSize: '0.8rem',
                    marginLeft: '8px'
                  }}>
                    {livePrices['BTC/ZAR']?.change >= 0 ? '+' : ''}{livePrices['BTC/ZAR']?.change?.toFixed(2) || '0.00'}%
                  </span>
                </div>
              </div>
              <div className="status-item">
                <strong>ETH/ZAR</strong>
                <div className="led-row">
                  <span>R{livePrices['ETH/ZAR']?.price?.toLocaleString() || '0'}</span>
                  <span style={{
                    color: livePrices['ETH/ZAR']?.change >= 0 ? 'var(--success)' : 'var(--error)',
                    fontSize: '0.8rem',
                    marginLeft: '8px'
                  }}>
                    {livePrices['ETH/ZAR']?.change >= 0 ? '+' : ''}{livePrices['ETH/ZAR']?.change?.toFixed(2) || '0.00'}%
                  </span>
                </div>
              </div>
              <div className="status-item">
                <strong>XRP/ZAR</strong>
                <div className="led-row">
                  <span>R{livePrices['XRP/ZAR']?.price?.toLocaleString() || '0'}</span>
                  <span style={{
                    color: livePrices['XRP/ZAR']?.change >= 0 ? 'var(--success)' : 'var(--error)',
                    fontSize: '0.8rem',
                    marginLeft: '8px'
                  }}>
                    {livePrices['XRP/ZAR']?.change >= 0 ? '+' : ''}{livePrices['XRP/ZAR']?.change?.toFixed(2) || '0.00'}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
    </section>
  );

  const renderApiSetup = () => {
    const providers = ['openai', 'luno', 'binance', 'kucoin', 'kraken', 'valr', 'flokx', 'fetchai'];
    
    return (
      <section className="section active">
        <div className="card">
          <h2>🔑 API Setup - All Integration Keys</h2>
          <p style={{color: 'var(--muted)', marginBottom: '20px', fontSize: '0.9rem'}}>
            Configure all API keys and credentials for exchanges, AI services, and integrations. All keys are encrypted and stored securely per-user.
          </p>
          <div className="api-accordion">
            {providers.map(provider => {
              const status = getApiStatus(provider);
              const isExpanded = expandedApis[provider];
              
              return (
                <div key={provider} className="api-card">
                  <div className="api-header" onClick={() => toggleApiExpand(provider)}>
                    <span>{provider.charAt(0).toUpperCase() + provider.slice(1)}</span>
                    <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                      <span className={`status-badge ${status.badge}`}>{status.text}</span>
                      <div className={`status-dot ${status.dot}`}></div>
                    </div>
                  </div>
                  <div className={`api-form ${isExpanded ? 'active' : ''}`} id={`form-${provider}`}>
                    {provider === 'openai' && (
                      <input name="api_key" placeholder="API Key (sk-...)" type="password" />
                    )}
                    {provider === 'luno' && (
                      <>
                        <input name="api_key" placeholder="Key ID" type="text" />
                        <input name="api_secret" placeholder="Secret" type="password" />
                      </>
                    )}
                    {provider === 'binance' && (
                      <>
                        <input name="api_key" placeholder="API Key" type="text" />
                        <input name="api_secret" placeholder="Secret" type="password" />
                      </>
                    )}
                    {provider === 'kucoin' && (
                      <>
                        <input name="api_key" placeholder="API Key" type="text" />
                        <input name="api_secret" placeholder="Secret Key" type="password" />
                        <input name="passphrase" placeholder="Passphrase" type="text" />
                      </>
                    )}
                    {provider === 'flokx' && (
                      <input name="api_token" placeholder="API Token" type="password" />
                    )}
                    {provider === 'fetchai' && (
                      <input name="api_key" placeholder="API Key" type="password" />
                    )}
                    {provider === 'kraken' && (
                      <>
                        <input name="api_key" placeholder="API Key" type="password" />
                        <input name="api_secret" placeholder="Private Key" type="password" />
                      </>
                    )}
                    {provider === 'valr' && (
                      <>
                        <input name="api_key" placeholder="API Key" type="password" />
                        <input name="api_secret" placeholder="API Secret" type="password" />
                      </>
                    )}
                    <div className="buttons">
                      <button onClick={() => handleSaveApiKey(provider)}>Save</button>
                      <button onClick={() => handleTestApiKey(provider)}>Test</button>
                      <button className="danger" onClick={() => handleDeleteApiKey(provider)}>Remove</button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    );
  };

  const renderBots = () => (
      <section className="section active">
        <div className="card">
          <h2>Bot Management</h2>
          <div className="bot-container">
            <div className="bot-left">
              <div className="bot-tabs">
                <button className={`bot-tab ${activeBotTab === 'exchange' ? 'active' : ''}`} onClick={() => setActiveBotTab('exchange')}>
                  Create Bot
                </button>
                <button className={`bot-tab ${activeBotTab === 'uagent' ? 'active' : ''}`} onClick={() => setActiveBotTab('uagent')}>
                  🤖 Add uAgent
                </button>
              </div>
              
              {/* SETUP TAB REMOVED - Users create starting bots manually, system spawns more automatically */}
              {false && activeBotTab === 'setup' && (
                <div className="bot-form-card" style={{background: 'var(--bg)', border: '1px solid var(--line)'}}>
                  <h3>⚙️ Bot Setup Wizard</h3>
                  <p style={{color: 'var(--muted)', marginBottom: '20px', fontSize: '0.9rem'}}>
                    Launch multiple paper trading bots with FAKE funds for 7 days
                  </p>
                  
                  <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                    <div style={{background: 'var(--panel)', padding: '16px', borderRadius: '8px', border: '1px solid var(--line)'}}>
                      <label style={{color: 'var(--text)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px', display: 'block'}}>
                        Exchange Platform
                      </label>
                      <select
                        value={botSetup.exchange}
                        onChange={(e) => setBotSetup({...botSetup, exchange: e.target.value})}
                        style={{
                          width: '100%',
                          padding: '12px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                          borderRadius: '6px',
                          color: 'var(--text)',
                          fontSize: '1rem'
                        }}
                      >
                        <option value="luno">🇿🇦 Luno (Best for South Africa - ZAR)</option>
                        <option value="binance">🌍 Binance (Global - USDT pairs)</option>
                        <option value="kucoin">🌐 KuCoin (Global - USDT pairs)</option>
                        <option value="kraken">🇺🇸 Kraken (USA/Europe - USDT pairs)</option>
                        <option value="valr">🇿🇦 VALR (South Africa - ZAR)</option>
                      </select>
                      <small style={{color: 'var(--muted)', display: 'block', marginTop: '6px'}}>
                        💡 Luno & VALR recommended for South African users (ZAR support)
                      </small>
                    </div>

                    <div style={{background: 'var(--panel)', padding: '16px', borderRadius: '8px', border: '1px solid var(--line)'}}>
                      <label style={{color: 'var(--text)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px', display: 'block'}}>
                        Total Bots (3-30)
                      </label>
                      <input
                        type="number"
                        min="3"
                        max="30"
                        value={botSetup.count}
                        onChange={(e) => setBotSetup({...botSetup, count: parseInt(e.target.value) || 3})}
                        style={{
                          width: '100%',
                          padding: '12px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                          borderRadius: '6px',
                          color: 'var(--text)',
                          fontSize: '1rem'
                        }}
                      />
                    </div>

                    <div style={{background: 'var(--panel)', padding: '16px', borderRadius: '8px', border: '1px solid var(--line)'}}>
                      <label style={{color: 'var(--text)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px', display: 'block'}}>
                        Capital Per Bot (Min R1000)
                      </label>
                      <input
                        type="number"
                        min="1000"
                        step="100"
                        value={botSetup.capital_per_bot}
                        onChange={(e) => setBotSetup({...botSetup, capital_per_bot: parseInt(e.target.value) || 1000})}
                        style={{
                          width: '100%',
                          padding: '12px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                          borderRadius: '6px',
                          color: 'var(--text)',
                          fontSize: '1rem'
                        }}
                      />
                      <small style={{color: 'var(--accent)', display: 'block', marginTop: '6px', fontWeight: 600}}>
                        💰 Total Capital: R{(botSetup.count * botSetup.capital_per_bot).toLocaleString()}
                      </small>
                    </div>

                    <div style={{background: 'var(--panel)', padding: '16px', borderRadius: '8px', border: '1px solid var(--line)'}}>
                      <h4 style={{marginBottom: '12px', color: 'var(--text)', fontSize: '0.95rem'}}>Risk Distribution</h4>
                      
                      <div style={{display: 'grid', gap: '12px'}}>
                        <div>
                          <label style={{color: 'var(--muted)', fontSize: '0.85rem', display: 'block', marginBottom: '6px'}}>
                            🛡️ Safe Bots
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={botSetup.safe_count}
                            onChange={(e) => setBotSetup({...botSetup, safe_count: parseInt(e.target.value) || 0})}
                            style={{
                              width: '100%',
                              padding: '10px',
                              background: 'var(--bg)',
                              border: '1px solid var(--line)',
                              borderRadius: '4px',
                              color: 'var(--text)'
                            }}
                          />
                        </div>

                        <div>
                          <label style={{color: 'var(--muted)', fontSize: '0.85rem', display: 'block', marginBottom: '6px'}}>
                            ⚡ Risky Bots
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={botSetup.risky_count}
                            onChange={(e) => setBotSetup({...botSetup, risky_count: parseInt(e.target.value) || 0})}
                            style={{
                              width: '100%',
                              padding: '10px',
                              background: 'var(--bg)',
                              border: '1px solid var(--line)',
                              borderRadius: '4px',
                              color: 'var(--text)'
                            }}
                          />
                        </div>

                        <div>
                          <label style={{color: 'var(--muted)', fontSize: '0.85rem', display: 'block', marginBottom: '6px'}}>
                            🚀 Aggressive Bots
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={botSetup.aggressive_count}
                            onChange={(e) => setBotSetup({...botSetup, aggressive_count: parseInt(e.target.value) || 0})}
                            style={{
                              width: '100%',
                              padding: '10px',
                              background: 'var(--bg)',
                              border: '1px solid var(--line)',
                              borderRadius: '4px',
                              color: 'var(--text)'
                            }}
                          />
                        </div>
                      </div>

                      <div style={{
                        padding: '10px',
                        background: botSetup.safe_count + botSetup.risky_count + botSetup.aggressive_count === botSetup.count ? 'var(--success)' : 'var(--error)',
                        color: 'white',
                        borderRadius: '4px',
                        marginTop: '12px',
                        fontSize: '0.85rem',
                        textAlign: 'center',
                        fontWeight: 600
                      }}>
                        {botSetup.safe_count + botSetup.risky_count + botSetup.aggressive_count === botSetup.count ? (
                          `✅ Total: ${botSetup.count} bots`
                        ) : (
                          `❌ Must equal ${botSetup.count} (currently ${botSetup.safe_count + botSetup.risky_count + botSetup.aggressive_count})`
                        )}
                      </div>
                    </div>

                    <button
                      onClick={handleBotSetup}
                      style={{
                        width: '100%',
                        padding: '14px',
                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '1rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        marginTop: '8px'
                      }}
                    >
                      🚀 Create Bots & Start Paper Trading
                    </button>

                    <div style={{padding: '12px', background: 'var(--glass)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--muted)', lineHeight: '1.6'}}>
                      📝 <strong>Note:</strong> All bots run with FAKE funds for 7 days.<br/>
                      💰 After 7 days, switch to LIVE with real money.<br/>
                      🤖 Autopilot manages bots automatically.
                    </div>
                  </div>
                </div>
              )}
              
              {activeBotTab === 'exchange' && (
                <div className="bot-form-card">
                  <h3>Create Single Bot</h3>
                  <form onSubmit={handleCreateBot}>
                    <div className="bot-form-grid">
                      <div className="form-group">
                        <label htmlFor="bot-name">Bot Name</label>
                        <input id="bot-name" name="bot-name" placeholder="My Trading Bot" type="text" required />
                      </div>
                      <div className="form-group">
                        <label htmlFor="bot-budget">Budget (Min R1000)</label>
                        <input 
                          id="bot-budget" 
                          name="bot-budget" 
                          type="number" 
                          min="1000" 
                          step="100"
                          defaultValue="1000"
                          placeholder="1000" 
                          required 
                        />
                        <small style={{color: 'var(--muted)', fontSize: '0.75rem'}}>
                          Minimum R1000 per bot
                        </small>
                      </div>
                      <div className="form-group">
                        <label htmlFor="bot-exchange">Exchange</label>
                        <select id="bot-exchange" name="bot-exchange">
                          <option value="luno">🇿🇦 Luno (ZAR)</option>
                          <option value="binance">🌍 Binance (USDT)</option>
                          <option value="kucoin">🌐 KuCoin (USDT)</option>
                          <option value="kraken">🇺🇸 Kraken (USDT)</option>
                          <option value="valr">🇿🇦 VALR (ZAR)</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label htmlFor="bot-risk">Risk Mode</label>
                        <select id="bot-risk" name="bot-risk">
                          <option value="safe">🛡️ Safe</option>
                          <option value="balanced">⚖️ Balanced</option>
                          <option value="aggressive">⚡ Aggressive</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <button type="submit">Create Bot (7 Day Learning)</button>
                      </div>
                    </div>
                    <div style={{marginTop: '12px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--muted)'}}>
                      📝 User-created bots undergo 7-day paper trading learning period
                    </div>
                  </form>
                </div>
              )}
              
              {activeBotTab === 'uagent' && (
                <div className="bot-form-card">
                  <h3>🤖 Upload Custom Fetch.ai uAgent</h3>
                  <p style={{color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '16px'}}>
                    Upload your own Fetch.ai uAgent code (.py file) for custom trading strategies
                  </p>
                  <form onSubmit={handleCreateUAgent}>
                    <div className="bot-form-grid">
                      <div className="form-group">
                        <label htmlFor="uagent-name">uAgent Name</label>
                        <input id="uagent-name" name="uagent-name" placeholder="My Custom Agent" type="text" required />
                      </div>
                      <div className="form-group">
                        <label htmlFor="uagent-file">Upload uAgent File (.py)</label>
                        <input id="uagent-file" name="uagent-file" type="file" accept=".py" required />
                      </div>
                      <div className="form-group">
                        <label htmlFor="uagent-strategy">Strategy Description</label>
                        <textarea id="uagent-strategy" name="uagent-strategy" placeholder="Describe what this uAgent does..." rows="4"></textarea>
                      </div>
                      <div className="form-group">
                        <button type="submit">Deploy uAgent</button>
                      </div>
                    </div>
                  </form>
                </div>
              )}
            </div>
          <div className="bot-right">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
              <h3>Running Bots ({bots.length})</h3>
              <select 
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                style={{
                  padding: '8px 16px',
                  background: 'var(--panel)',
                  border: '1px solid var(--line)',
                  borderRadius: '6px',
                  color: 'var(--text)',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Platforms</option>
                <option value="luno">🇿🇦 Luno Only</option>
                <option value="binance">🌍 Binance Only</option>
                <option value="kucoin">🌐 KuCoin Only</option>
                <option value="kraken">🇺🇸 Kraken Only</option>
                <option value="valr">🇿🇦 VALR Only</option>
              </select>
            </div>
            
            <div className="bot-list">
              {bots.length === 0 ? (
                <p style={{color: 'var(--muted)', padding: '20px', textAlign: 'center'}}>
                  No bots yet. Create one to get started!
                </p>
              ) : (
                bots
                  .filter(bot => platformFilter === 'all' || bot.exchange === platformFilter)
                  .map(bot => {
                    const isExpanded = expandedBots[bot.id];
                    const botMode = bot.trading_mode || bot.mode || 'paper';
                    const isLive = botMode === 'live';
                    const paperDays = bot.paper_start_date 
                      ? Math.floor((Date.now() - new Date(bot.paper_start_date).getTime()) / (1000 * 60 * 60 * 24)) + 1
                      : 1;
                    const riskMode = bot.risk_mode || 'safe';
                    
                    return (
                      <div key={bot.id} className="bot-card" style={{marginBottom: '12px'}}>
                        <div className="bot-header" onClick={() => toggleBotExpand(bot.id)}>
                          <div style={{display: 'flex', alignItems: 'center', gap: '12px', flex: 1}}>
                            <span style={{fontWeight: 600}}>
                              {editingBotId === bot.id ? (
                                <input
                                  type="text"
                                  value={editingBotName}
                                  onChange={(e) => setEditingBotName(e.target.value)}
                                  onClick={(e) => e.stopPropagation()}
                                  onBlur={() => handleSaveBotName(bot.id)}
                                  onKeyPress={(e) => e.key === 'Enter' && handleSaveBotName(bot.id)}
                                  style={{
                                    padding: '4px 8px',
                                    background: 'var(--bg)',
                                    border: '1px solid var(--accent)',
                                    borderRadius: '4px',
                                    color: 'var(--text)',
                                    fontSize: '1rem'
                                  }}
                                  autoFocus
                                />
                              ) : (
                                <>
                                  {bot.name}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingBotId(bot.id);
                                      setEditingBotName(bot.name);
                                    }}
                                    style={{
                                      marginLeft: '8px',
                                      padding: '2px 6px',
                                      background: 'transparent',
                                      border: '1px solid var(--line)',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '0.75rem'
                                    }}
                                  >
                                    ✏️
                                  </button>
                                </>
                              )}
                            </span>
                            <span style={{fontSize: '0.85rem', color: 'var(--muted)'}}>
                              {bot.exchange ? bot.exchange.toUpperCase() : 'N/A'}
                            </span>
                            {botMode === 'paper' && (
                              <span style={{
                                padding: '2px 8px',
                                background: 'var(--accent)',
                                color: 'white',
                                borderRadius: '12px',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}>
                                📄 Day {paperDays}/7
                              </span>
                            )}
                          </div>
                          <div className={`status-dot ${isLive ? 'ok' : 'err'}`} title={isLive ? 'Live Trading' : 'Paper Trading'}></div>
                        </div>
                        
                        {isExpanded && (
                          <div className="bot-details active">
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '12px'}}>
                              <div>
                                <label style={{fontSize: '0.85rem', color: 'var(--muted)', display: 'block', marginBottom: '4px'}}>
                                  Trading Mode
                                </label>
                                <button
                                  onClick={() => handleToggleBotMode(bot.id, botMode)}
                                  style={{
                                    width: '100%',
                                    padding: '8px',
                                    background: isLive ? 'var(--success)' : 'var(--accent)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    fontWeight: 600
                                  }}
                                >
                                  {botMode.toUpperCase()}
                                </button>
                              </div>
                              
                              <div>
                                <label style={{fontSize: '0.85rem', color: 'var(--muted)', display: 'block', marginBottom: '4px'}}>
                                  Risk Mode
                                </label>
                                <select
                                  value={riskMode}
                                  onChange={(e) => handleChangeRiskMode(bot.id, e.target.value)}
                                  style={{
                                    width: '100%',
                                    padding: '8px',
                                    background: 'var(--panel)',
                                    border: '1px solid var(--line)',
                                    borderRadius: '6px',
                                    color: 'var(--text)',
                                    cursor: 'pointer'
                                  }}
                                >
                                  <option value="safe">🛡️ Safe</option>
                                  <option value="balanced">⚖️ Balanced</option>
                                  <option value="aggressive">⚡ Aggressive</option>
                                </select>
                              </div>
                            </div>
                            
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', marginBottom: '12px'}}>
                              <div style={{textAlign: 'center'}}>
                                <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>Profit</div>
                                <div style={{fontSize: '1.1rem', fontWeight: 700, color: bot.total_profit > 0 ? 'var(--success)' : 'var(--error)'}}>
                                  R{(bot.total_profit || 0).toFixed(2)}
                                </div>
                              </div>
                              <div style={{textAlign: 'center'}}>
                                <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>Capital</div>
                                <div style={{fontSize: '1.1rem', fontWeight: 700, color: 'var(--text)'}}>
                                  R{(bot.current_capital || 0).toFixed(2)}
                                </div>
                              </div>
                              <div style={{textAlign: 'center'}}>
                                <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>Trades</div>
                                <div style={{fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent)'}}>
                                  {bot.trades_count || 0}
                                </div>
                              </div>
                            </div>
                            
                            <div className="buttons">
                              <button 
                                className="danger" 
                                onClick={() => handleDeleteBot(bot.id)}
                                style={{width: '100%'}}
                              >
                                🗑️ Delete Bot
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  const renderProfile = () => {
    
    return (
      <section className="section active">
        <div className="card">
          <h2>Profile Settings</h2>
          <div className="profile-grid">
            <div className="field-group">
              <label>Full Name</label>
              <input 
                type="text" 
                value={profileData.first_name || ''} 
                onChange={(e) => handleProfileChange('first_name', e.target.value)}
              />
            </div>
            <div className="field-group">
              <label>Email Address</label>
              <input 
                type="email" 
                value={profileData.email || ''} 
                onChange={(e) => handleProfileChange('email', e.target.value)}
              />
            </div>
            <div className="field-group">
              <label>Display Currency</label>
              <select 
                value={profileData.currency || 'ZAR'} 
                onChange={(e) => handleProfileChange('currency', e.target.value)}
              >
                <option value="ZAR">ZAR (South African Rand)</option>
                <option value="USD">USD (US Dollar)</option>
                <option value="EUR">EUR (Euro)</option>
                <option value="GBP">GBP (British Pound)</option>
              </select>
            </div>
            <div className="field-group">
              <label>New Password (optional)</label>
              <input 
                type="password" 
                placeholder="Leave blank to keep current" 
                value={profileData.new_password || ''}
                onChange={(e) => handleProfileChange('new_password', e.target.value)}
              />
            </div>
            <div className="field-group">
              <label>&nbsp;</label>
              <button onClick={handleProfileSave}>Save Profile</button>
            </div>
          </div>
          
          <div style={{marginTop: '24px', padding: '16px', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)'}}>
            <h3 style={{marginBottom: '12px'}}>Account Information</h3>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px'}}>
              <div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Account Status</div>
                <div style={{fontWeight: 600, marginTop: '4px', color: 'var(--success)'}}>Active</div>
              </div>
              <div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Member Since</div>
                <div style={{fontWeight: 600, marginTop: '4px'}}>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</div>
              </div>
              <div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Total Bots</div>
                <div style={{fontWeight: 600, marginTop: '4px'}}>{bots.length}</div>
              </div>
              <div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Active Bots</div>
                <div style={{fontWeight: 600, marginTop: '4px', color: 'var(--success)'}}>
                  {(() => {
                    const activeBots = bots.filter(b => b.status === 'active');
                    const paperBots = activeBots.filter(b => b.trading_mode === 'paper').length;
                    const liveBots = activeBots.filter(b => b.trading_mode === 'live').length;
                    if (liveBots > 0) {
                      return `${activeBots.length} (${liveBots} live, ${paperBots} paper)`;
                    }
                    return `${activeBots.length} (paper)`;
                  })()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    );
  };

  const renderAdmin = () => {
    
    return (
      <section className="section active">
        <div className="card">
          <h2>🔧 Admin Panel (God Mode)</h2>
          
          {/* System Stats */}
          {systemStats && (
            <div style={{marginBottom: '24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px'}}>
              <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', fontWeight: 700, color: 'var(--success)'}}>{systemStats.total_users || 0}</div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginTop: '4px'}}>Total Users</div>
              </div>
              <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', fontWeight: 700, color: 'var(--success)'}}>{systemStats.active_bots || 0}</div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginTop: '4px'}}>Active Bots</div>
              </div>
              <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', fontWeight: 700, color: 'var(--success)'}}>{systemStats.cpu_usage || 0}%</div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginTop: '4px'}}>CPU Usage</div>
              </div>
              <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', fontWeight: 700, color: 'var(--success)'}}>{systemStats.memory_usage || 0}MB</div>
                <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginTop: '4px'}}>Memory Usage</div>
              </div>
            </div>
          )}
          
          {/* Users Table */}
          <div style={{overflowX: 'auto'}}>
            <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem'}}>
              <thead>
                <tr style={{borderBottom: '2px solid var(--line)'}}>
                  <th style={{padding: '12px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600}}>User</th>
                  <th style={{padding: '12px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600}}>Email</th>
                  <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Bots</th>
                  <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>CPU</th>
                  <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>RAM</th>
                  <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Status</th>
                  <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allUsers.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{padding: '40px', textAlign: 'center', color: 'var(--muted)'}}>
                      No users found
                    </td>
                  </tr>
                ) : (
                  allUsers.map(usr => (
                    <tr key={usr.id} style={{borderBottom: '1px solid var(--line)'}}>
                      <td style={{padding: '12px'}}>{usr.first_name || 'N/A'}</td>
                      <td style={{padding: '12px'}}>{usr.email}</td>
                      <td style={{padding: '12px', textAlign: 'center'}}>
                        {systemStats ? Math.floor(systemStats.active_bots / systemStats.total_users) : 0}
                      </td>
                      <td style={{padding: '12px', textAlign: 'center'}}>
                        {systemStats ? Math.floor(systemStats.cpu_usage / systemStats.total_users) : 0}%
                      </td>
                      <td style={{padding: '12px', textAlign: 'center'}}>
                        {systemStats ? Math.floor(systemStats.memory_usage / systemStats.total_users) : 0}MB
                      </td>
                      <td style={{padding: '12px', textAlign: 'center'}}>
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: usr.blocked ? 'var(--error)' : 'var(--success)',
                          color: 'white'
                        }}>
                          {usr.blocked ? 'Blocked' : 'Active'}
                        </span>
                      </td>
                      <td style={{padding: '12px', textAlign: 'center'}}>
                        <div style={{display: 'flex', gap: '4px', justifyContent: 'center', flexWrap: 'wrap'}}>
                          <button 
                            onClick={() => handleChangePassword(usr.id)}
                            style={{
                              padding: '4px 8px',
                              fontSize: '0.75rem',
                              background: 'var(--accent2)',
                              color: 'var(--text)',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontWeight: 600
                            }}
                          >
                            Change PW
                          </button>
                          <button 
                            onClick={() => handleBlockUser(usr.id, usr.blocked)}
                            style={{
                              padding: '4px 8px',
                              fontSize: '0.75rem',
                              background: usr.blocked ? 'var(--success)' : '#f59e0b',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontWeight: 600
                            }}
                          >
                            {usr.blocked ? 'Unblock' : 'Block'}
                          </button>
                          <button 
                            onClick={() => handleDeleteUser(usr.id)}
                            style={{
                              padding: '4px 8px',
                              fontSize: '0.75rem',
                              background: 'var(--error)',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontWeight: 600
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          {/* AI Bodyguard Status */}
          {bodyguardStatus && (
            <div style={{marginTop: '24px', padding: '20px', background: 'var(--panel)', borderRadius: '8px', border: '2px solid ' + (bodyguardStatus.health_score >= 80 ? 'var(--success)' : bodyguardStatus.health_score >= 60 ? '#f59e0b' : 'var(--error)')}}>
              <h3 style={{marginBottom: '16px', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '8px'}}>
                🛡️ AI Bodyguard Status
                <span style={{
                  fontSize: '0.75rem', 
                  padding: '4px 8px', 
                  borderRadius: '4px', 
                  background: bodyguardStatus.health_score >= 80 ? 'var(--success)' : bodyguardStatus.health_score >= 60 ? '#f59e0b' : 'var(--error)',
                  color: 'white'
                }}>
                  {bodyguardStatus.health_status}
                </span>
              </h3>
              
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '16px'}}>
                <div style={{padding: '12px', background: 'var(--glass)', borderRadius: '6px', textAlign: 'center'}}>
                  <div style={{fontSize: '1.8rem', fontWeight: 700, color: bodyguardStatus.health_score >= 80 ? 'var(--success)' : 'var(--error)'}}>{bodyguardStatus.health_score}</div>
                  <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Health Score</div>
                </div>
                <div style={{padding: '12px', background: 'var(--glass)', borderRadius: '6px', textAlign: 'center'}}>
                  <div style={{fontSize: '1.8rem', fontWeight: 700, color: 'var(--text)'}}>{bodyguardStatus.system_health?.cpu_usage}%</div>
                  <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>CPU</div>
                </div>
                <div style={{padding: '12px', background: 'var(--glass)', borderRadius: '6px', textAlign: 'center'}}>
                  <div style={{fontSize: '1.8rem', fontWeight: 700, color: 'var(--text)'}}>{bodyguardStatus.system_health?.memory_usage}%</div>
                  <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Memory</div>
                </div>
                <div style={{padding: '12px', background: 'var(--glass)', borderRadius: '6px', textAlign: 'center'}}>
                  <div style={{fontSize: '1.8rem', fontWeight: 700, color: 'var(--accent)'}}>{bodyguardStatus.trading_health?.active_bots}</div>
                  <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Active Bots</div>
                </div>
              </div>
              
              {(bodyguardStatus.issues?.length > 0 || bodyguardStatus.warnings?.length > 0) && (
                <div style={{marginTop: '16px'}}>
                  {bodyguardStatus.issues?.length > 0 && (
                    <div style={{marginBottom: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '6px', border: '1px solid var(--error)'}}>
                      <div style={{fontWeight: 600, color: 'var(--error)', marginBottom: '8px'}}>🚨 Critical Issues ({bodyguardStatus.issues.length})</div>
                      <ul style={{margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text)'}}>
                        {bodyguardStatus.issues.map((issue, idx) => (
                          <li key={idx} style={{marginBottom: '4px'}}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {bodyguardStatus.warnings?.length > 0 && (
                    <div style={{padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '6px', border: '1px solid #f59e0b'}}>
                      <div style={{fontWeight: 600, color: '#f59e0b', marginBottom: '8px'}}>⚠️ Warnings ({bodyguardStatus.warnings.length})</div>
                      <ul style={{margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text)'}}>
                        {bodyguardStatus.warnings.map((warning, idx) => (
                          <li key={idx} style={{marginBottom: '4px'}}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              
              <div style={{marginTop: '12px', fontSize: '0.75rem', color: 'var(--muted)', textAlign: 'right'}}>
                Last check: {new Date(bodyguardStatus.timestamp).toLocaleString()}
              </div>
            </div>
          )}
          
          {/* User Storage Tracking */}
          {storageData && (
            <div style={{marginTop: '24px', padding: '20px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--line)'}}>
              <h3 style={{marginBottom: '16px', color: 'var(--accent)'}}>💾 User Storage Tracking</h3>
              
              <div style={{marginBottom: '16px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <div>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Total System Storage</div>
                  <div style={{fontSize: '1.5rem', fontWeight: 700, color: 'var(--text)'}}>{storageData.total_system_storage_mb?.toFixed(2)} MB</div>
                </div>
                <div>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Total Users</div>
                  <div style={{fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent)'}}>{storageData.total_users}</div>
                </div>
              </div>
              
              <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem'}}>
                  <thead style={{position: 'sticky', top: 0, background: 'var(--panel)'}}>
                    <tr style={{borderBottom: '2px solid var(--line)'}}>
                      <th style={{padding: '12px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600}}>User</th>
                      <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Chats</th>
                      <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Trades</th>
                      <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Bots</th>
                      <th style={{padding: '12px', textAlign: 'center', color: 'var(--muted)', fontWeight: 600}}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {storageData.users?.map((usr, idx) => (
                      <tr key={idx} style={{borderBottom: '1px solid var(--line)'}}>
                        <td style={{padding: '12px'}}>
                          <div>{usr.first_name}</div>
                          <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{usr.email}</div>
                        </td>
                        <td style={{padding: '12px', textAlign: 'center'}}>
                          <div style={{fontWeight: 600}}>{usr.storage_breakdown?.chat_messages?.size_mb?.toFixed(2)} MB</div>
                          <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{usr.storage_breakdown?.chat_messages?.count} msgs</div>
                        </td>
                        <td style={{padding: '12px', textAlign: 'center'}}>
                          <div style={{fontWeight: 600}}>{usr.storage_breakdown?.trades?.size_mb?.toFixed(2)} MB</div>
                          <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{usr.storage_breakdown?.trades?.count} trades</div>
                        </td>
                        <td style={{padding: '12px', textAlign: 'center'}}>
                          <div style={{fontWeight: 600}}>{usr.storage_breakdown?.bots?.size_mb?.toFixed(2)} MB</div>
                          <div style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{usr.storage_breakdown?.bots?.count} bots</div>
                        </td>
                        <td style={{padding: '12px', textAlign: 'center'}}>
                          <span style={{
                            padding: '6px 12px',
                            borderRadius: '4px',
                            fontWeight: 700,
                            background: usr.total_storage_mb > 10 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                            color: usr.total_storage_mb > 10 ? '#f59e0b' : 'var(--success)'
                          }}>
                            {usr.total_storage_mb?.toFixed(2)} MB
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          
          {/* Admin Tools - All in One Section */}
          <div style={{marginTop: '24px', padding: '20px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--accent)'}}>
            <h3 style={{marginBottom: '16px', color: 'var(--accent)'}}>🛠️ System Administration</h3>
            
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px'}}>
              <button 
                onClick={handleTriggerBodyguard}
                disabled={aiTaskLoading === 'bodyguard'}
                style={{
                  padding: '12px 16px',
                  background: aiTaskLoading === 'bodyguard' ? '#666' : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: aiTaskLoading === 'bodyguard' ? 'wait' : 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  transition: 'transform 0.2s',
                  opacity: aiTaskLoading === 'bodyguard' ? 0.7 : 1
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                {aiTaskLoading === 'bodyguard' ? '⏳ Scanning...' : '🛡️ AI Bodyguard'}
              </button>
              
              <button 
                onClick={handleEmailAllUsers}
                style={{
                  padding: '12px 16px',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  transition: 'transform 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                📧 Email All Users
              </button>
              
              <button 
                onClick={async () => {
                  try {
                    const res = await axios.get(`${API}/admin/health-check`, axiosConfig);
                    const services = res.data.services;
                    const score = res.data.health_score;
                    
                    let statusHTML = `Health Score: ${score}/100\n\n`;
                    statusHTML += 'Services Status:\n';
                    Object.entries(services).forEach(([name, status]) => {
                      const emoji = status === 'healthy' ? '✅' : '❌';
                      statusHTML += `${emoji} ${name}: ${status}\n`;
                    });
                    
                    // Add health report to chat
                    const reportMsg = `System Health Report (${score}/100)\n\n${statusHTML}`;
                    setChatMessages(prev => [...prev, 
                      { role: 'user', content: 'Check system health' },
                      { role: 'assistant', content: reportMsg }
                    ]);
                    
                    // Redirect to chat section
                    setActiveSection('welcome');
                    setTimeout(() => showSection('welcome'), 100);
                    
                    showNotification(`System Health: ${score}/100 - Check chat for details`, score >= 80 ? 'success' : 'warning');
                  } catch (err) {
                    showNotification('Health check failed', 'error');
                  }
                }}
                style={{
                  padding: '12px 16px',
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  transition: 'transform 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                🏥 System Health
              </button>
            </div>
            
            <p style={{fontSize: '0.75rem', color: 'var(--muted)', marginTop: '12px', lineHeight: '1.5'}}>
              Monitor system health, send notifications, and check backend services in real-time
            </p>
          </div>
          
          <div style={{marginTop: '16px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', border: '1px solid var(--error)', fontSize: '0.85rem'}}>
            <p style={{color: 'var(--error)', fontWeight: 600, marginBottom: '8px'}}>⚠️ Admin Warning</p>
            <p style={{color: 'var(--muted)'}}>
              You have full control over all users. Use these powers responsibly. All actions are logged.
            </p>
          </div>
        </div>
      </section>
    );
  };

  const renderSystemMode = () => (
    <section className="section active">
      <div className="card">
        <h2>System Mode</h2>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px'}}>
          <div className="system-card" onClick={() => toggleSystemMode('paperTrading')} style={{padding: '16px', background: 'var(--glass)', border: '2px solid ' + (systemModes.paperTrading ? 'var(--success)' : 'var(--line)'), borderRadius: '8px', cursor: 'pointer', textAlign: 'center'}}>
            <h3>🧪 Paper Trading</h3>
            <p style={{fontSize: '0.85rem', color: 'var(--muted)', margin: '8px 0'}}>Practice with simulated funds</p>
            <div style={{fontWeight: 600, fontSize: '1.2rem', color: systemModes.paperTrading ? 'var(--success)' : 'var(--error)'}}>
              {systemModes.paperTrading ? '✓ ON' : '✗ OFF'}
            </div>
          </div>
          <div className="system-card" onClick={() => toggleSystemMode('liveTrading')} style={{padding: '16px', background: 'var(--glass)', border: '2px solid ' + (systemModes.liveTrading ? '#f59e0b' : 'var(--line)'), borderRadius: '8px', cursor: 'pointer', textAlign: 'center'}}>
            <h3>💰 Live Trading</h3>
            <p style={{fontSize: '0.85rem', color: 'var(--muted)', margin: '8px 0'}}>⚠️ Execute REAL trades</p>
            <div style={{fontWeight: 600, fontSize: '1.2rem', color: systemModes.liveTrading ? '#f59e0b' : 'var(--error)'}}>
              {systemModes.liveTrading ? '⚡ ON' : '✗ OFF'}
            </div>
          </div>
          <div className="system-card" onClick={() => toggleSystemMode('autopilot')} style={{padding: '16px', background: 'var(--glass)', border: '2px solid ' + (systemModes.autopilot ? 'var(--success)' : 'var(--line)'), borderRadius: '8px', cursor: 'pointer', textAlign: 'center'}}>
            <h3>🤖 Autopilot</h3>
            <p style={{fontSize: '0.85rem', color: 'var(--muted)', margin: '8px 0'}}>Autonomous 24/7 trading</p>
            <div style={{fontWeight: 600, fontSize: '1.2rem', color: systemModes.autopilot ? 'var(--success)' : 'var(--error)'}}>
              {systemModes.autopilot ? '✓ ON' : '✗ OFF'}
            </div>
          </div>
        </div>
        <div style={{marginTop: '24px', padding: '16px', background: 'var(--panel)', border: '2px solid var(--error)', borderRadius: '8px'}}>
          <h3 style={{color: 'var(--error)', marginBottom: '8px'}}>🚨 Emergency Controls</h3>
          <p style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '12px'}}>
            Immediately stop ALL bots and trading activity system-wide
          </p>
          <button 
            onClick={handleEmergencyStop}
            style={{
              padding: '12px 24px', 
              background: 'var(--error)', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px', 
              fontWeight: 700, 
              fontSize: '1rem',
              cursor: 'pointer',
              width: '100%',
              maxWidth: '300px'
            }}
          >
            🚨 EMERGENCY STOP
          </button>
        </div>
      </div>
    </section>
  );

  const renderLiveTradeFeed = () => (
    <section className="section active">
      <div className="card">
        <h2>📊 Live Trade Feed</h2>
        <p style={{color: 'var(--muted)', marginBottom: '20px', fontSize: '0.9rem'}}>
          Real-time stream of all trades being executed
        </p>
        
        <div style={{background: 'var(--panel)', borderRadius: '8px', padding: '16px', maxHeight: '600px', overflowY: 'auto'}}>
          {recentTrades.length === 0 ? (
            <div style={{textAlign: 'center', padding: '40px', color: 'var(--muted)'}}>
              <p>📭 No trades yet. Trades will appear here in real-time.</p>
            </div>
          ) : (
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              {recentTrades.map((trade, idx) => {
                const isWin = trade.is_profitable || trade.profit_loss > 0;
                const profitColor = isWin ? 'var(--success)' : 'var(--error)';
                const profitIcon = isWin ? '🟢' : '🔴';
                
                return (
                  <div key={idx} style={{
                    background: 'var(--bg)',
                    border: '1px solid ' + (isWin ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'),
                    borderRadius: '8px',
                    padding: '12px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}>
                    <div style={{flex: '1 1 200px'}}>
                      <div style={{fontWeight: 600, color: 'var(--text)', marginBottom: '4px'}}>
                        🤖 {trade.bot_name || 'Bot'}
                      </div>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>
                        {trade.symbol} • {trade.exchange?.toUpperCase()}
                      </div>
                    </div>
                    
                    <div style={{flex: '0 0 auto', textAlign: 'center'}}>
                      <div style={{fontSize: '1.1rem', fontWeight: 700, color: profitColor}}>
                        {profitIcon} {isWin ? 'WIN' : 'LOSS'}
                      </div>
                      <div style={{fontSize: '0.9rem', color: profitColor, fontWeight: 600}}>
                        R{trade.profit_loss?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                    
                    <div style={{flex: '0 0 auto', textAlign: 'right', fontSize: '0.8rem', color: 'var(--muted)'}}>
                      {new Date(trade.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        <div style={{marginTop: '16px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', border: '1px solid var(--line)'}}>
          <div style={{display: 'flex', justifyContent: 'space-around', textAlign: 'center'}}>
            <div>
              <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Total Trades</div>
              <div style={{fontSize: '1.2rem', fontWeight: 700, color: 'var(--text)'}}>{recentTrades.length}</div>
            </div>
            <div>
              <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Win Rate</div>
              <div style={{fontSize: '1.2rem', fontWeight: 700, color: 'var(--success)'}}>
                {recentTrades.length > 0 
                  ? `${((recentTrades.filter(t => t.is_profitable || t.profit_loss > 0).length / recentTrades.length) * 100).toFixed(1)}%`
                  : '0%'}
              </div>
            </div>
            <div>
              <div style={{fontSize: '0.8rem', color: 'var(--muted)'}}>Total P/L</div>
              <div style={{fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent)'}}>
                R{recentTrades.reduce((sum, t) => sum + (t.profit_loss || 0), 0).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  const renderProfitGraphs = () => {
    
    const chartData = {
      labels: profitData?.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [{
        label: 'Profit (ZAR)',
        data: profitData?.values || [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.2)',
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2
      }]
    };
    
    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 42, 0.95)',
          titleColor: '#10b981',
          bodyColor: '#ffffff',
          borderColor: '#10b981',
          borderWidth: 2,
          padding: 12,
          titleFont: { size: 14, weight: 'bold' },
          bodyFont: { size: 13 }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { 
            color: '#8b8b8b',
            font: { size: 11 },
            callback: function(value) {
              return 'R' + value;
            }
          },
          grid: { 
            color: 'rgba(255, 255, 255, 0.05)',
            drawBorder: false
          },
          border: { display: false }
        },
        x: {
          ticks: { 
            color: '#8b8b8b',
            font: { size: 11 }
          },
          grid: { 
            display: false
          },
          border: { display: false }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    };
    
    return (
      <section className="section active">
        <div className="card">
          {/* Header with period selector */}
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px'}}>
            <h2 style={{margin: 0, fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px'}}>
              📊 Performance Analytics
            </h2>
            <div style={{display: 'flex', gap: '6px'}}>
              {['daily', 'weekly', 'monthly'].map(period => (
                <button 
                  key={period}
                  onClick={() => setGraphPeriod(period)}
                  style={{
                    padding: '6px 14px',
                    background: graphPeriod === period ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'var(--glass)',
                    color: graphPeriod === period ? '#ffffff' : 'var(--muted)',
                    border: graphPeriod === period ? 'none' : '1px solid var(--line)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    textTransform: 'capitalize',
                    transition: 'all 0.3s'
                  }}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>
          
          {/* Stats Cards Row */}
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px'}}>
            <div style={{
              padding: '16px',
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%)',
              borderRadius: '10px',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              textAlign: 'center'
            }}>
              <div style={{fontSize: '0.75rem', color: '#10b981', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px'}}>Total Profit</div>
              <div style={{fontSize: '1.75rem', fontWeight: 700, color: '#10b981', marginTop: '6px', display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '4px'}}>
                R{profitData?.total?.toFixed(2) || '0.00'}
                <span style={{fontSize: '0.75rem', color: 'var(--muted)'}}>ZAR</span>
              </div>
            </div>
            
            <div style={{
              padding: '16px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.05) 100%)',
              borderRadius: '10px',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              textAlign: 'center'
            }}>
              <div style={{fontSize: '0.75rem', color: '#3b82f6', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px'}}>Avg Daily</div>
              <div style={{fontSize: '1.75rem', fontWeight: 700, color: '#3b82f6', marginTop: '6px', display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '4px'}}>
                R{profitData?.avg_daily?.toFixed(2) || '0.00'}
                <span style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{profitData?.avg_daily ? '+12%' : ''}</span>
              </div>
            </div>
            
            <div style={{
              padding: '16px',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.05) 100%)',
              borderRadius: '10px',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              textAlign: 'center'
            }}>
              <div style={{fontSize: '0.75rem', color: '#f59e0b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px'}}>Best Day</div>
              <div style={{fontSize: '1.75rem', fontWeight: 700, color: '#f59e0b', marginTop: '6px', display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '4px'}}>
                R{profitData?.best_day ? profitData.best_day.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}
                <span style={{fontSize: '0.75rem', color: 'var(--muted)'}}>—</span>
              </div>
            </div>
            
            <div style={{
              padding: '16px',
              background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(147, 51, 234, 0.05) 100%)',
              borderRadius: '10px',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              textAlign: 'center'
            }}>
              <div style={{fontSize: '0.75rem', color: '#a855f7', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px'}}>Growth Rate</div>
              <div style={{fontSize: '1.75rem', fontWeight: 700, color: '#a855f7', marginTop: '6px', display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '4px'}}>
                {profitData?.growth_rate?.toFixed(2) || '0.00'}%
                <span style={{fontSize: '0.75rem', color: 'var(--muted)'}}>{profitData?.growth_rate > 0 ? '↑' : ''}</span>
              </div>
            </div>
          </div>
          
          {/* Chart */}
          <div style={{
            height: '280px', 
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(0, 0, 42, 0.4) 0%, rgba(0, 0, 20, 0.6) 100%)',
            borderRadius: '10px',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }}>
            {typeof window !== 'undefined' && (
              <Line data={chartData} options={chartOptions} />
            )}
          </div>
        </div>
      </section>
    );
  };

  const renderCountdown = () => {
    // Use countdown data from the new endpoint
    const countdownData = countdown || {};
    const progressDeg = countdownData.progress_pct ? (countdownData.progress_pct / 100) * 360 : 0;
    
    return (
      <section className="section active">
        <div className="card">
          <h2>🎯 Countdown to R1 Million</h2>
          
          {countdownData.status === 'achieved' ? (
            <div style={{textAlign: 'center', padding: '60px 20px'}}>
              <div style={{fontSize: '5rem', marginBottom: '20px'}}>🎉</div>
              <div style={{fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)', marginBottom: '15px'}}>
                TARGET ACHIEVED!
              </div>
              <div style={{fontSize: '1.3rem', color: 'var(--muted)'}}>
                You reached R1,000,000!
              </div>
            </div>
          ) : (
            <>
              <h3 style={{textAlign: 'center', margin: '16px 0 24px 0', fontSize: '1.2rem', fontWeight: 600, color: 'var(--muted)'}}>
                Real-Time Growth Projection - {countdownData.mode || 'Paper'} Mode
              </h3>
              
              <div style={{display: 'flex', gap: '20px', alignItems: 'stretch', flexWrap: 'wrap', marginBottom: '24px'}}>
                <div style={{flex: '1 1 350px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '32px', border: '2px solid var(--success)', borderRadius: '12px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%)'}}>
                  <div style={{fontSize: '4.5rem', fontWeight: 700, color: countdownData.days_remaining >= 9999 ? 'var(--error)' : 'var(--success)', margin: '12px 0', textShadow: '0 0 12px rgba(16, 185, 129, 0.5)'}}>
                    {countdownData.days_remaining < 9999 ? countdownData.days_remaining : '∞'}
                  </div>
                  <p style={{fontSize: '1.1rem', fontWeight: 600, color: 'var(--muted)', marginBottom: '8px'}}>
                    DAYS REMAINING
                  </p>
                  <p style={{fontSize: '2rem', fontWeight: 700, background: 'linear-gradient(45deg, var(--success), #34d399)', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', margin: '12px 0'}}>
                    TO YOUR FIRST MILLION
                  </p>
                  
                  <div style={{marginTop: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', width: '100%'}}>
                    <div style={{textAlign: 'center', padding: '12px', background: 'var(--panel)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Current Capital</div>
                      <div style={{fontSize: '1.3rem', fontWeight: 700, color: 'var(--text)'}}>
                        R{countdownData.current_capital?.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') || '0.00'}
                      </div>
                    </div>
                    <div style={{textAlign: 'center', padding: '12px', background: 'var(--panel)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Daily ROI</div>
                      <div style={{fontSize: '1.3rem', fontWeight: 700, color: 'var(--success)'}}>
                        {countdownData.metrics?.daily_roi_pct?.toFixed(3) || '0.000'}%
                      </div>
                    </div>
                  </div>
                </div>
                
                <div style={{flex: '1 1 300px', padding: '32px', border: '1px solid var(--line)', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', background: 'var(--panel)'}}>
                  <div style={{width: '240px', height: '240px', borderRadius: '50%', background: 'conic-gradient(var(--success) 0deg ' + progressDeg + 'deg, var(--accent) ' + progressDeg + 'deg 360deg)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 24px rgba(16, 185, 129, 0.4)'}}>
                    <div style={{width: '180px', height: '180px', borderRadius: '50%', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)', flexDirection: 'column'}}>
                      <div>{countdownData.progress_pct?.toFixed(1) || '0.0'}%</div>
                      <div style={{fontSize: '0.8rem', color: 'var(--muted)', marginTop: '6px'}}>Complete</div>
                    </div>
                  </div>
                  
                  <div style={{marginTop: '24px', width: '100%', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
                    <div style={{textAlign: 'center', padding: '12px', background: 'var(--glass)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '6px'}}>Remaining</div>
                      <div style={{fontSize: '1.1rem', fontWeight: 600, color: 'var(--text)'}}>
                        R{countdownData.remaining ? countdownData.remaining.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}
                      </div>
                    </div>
                    <div style={{textAlign: 'center', padding: '12px', background: 'var(--glass)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '6px'}}>Target</div>
                      <div style={{fontSize: '1.1rem', fontWeight: 600, color: 'var(--success)'}}>
                        R1,000,000
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Progress Bar */}
              <div style={{marginBottom: '24px'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '0.9rem', fontWeight: 600}}>
                  <span style={{color: 'var(--text)'}}>R{countdownData.current_capital ? countdownData.current_capital.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}</span>
                  <span style={{color: 'var(--success)'}}>R1,000,000</span>
                </div>
                <div style={{height: '16px', background: 'var(--panel)', borderRadius: '8px', overflow: 'hidden', border: '2px solid var(--line)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)'}}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(countdownData.progress_pct || 0, 100)}%`,
                    background: 'linear-gradient(90deg, var(--success) 0%, var(--accent) 100%)',
                    transition: 'width 1s ease-in-out',
                    boxShadow: '0 0 10px rgba(16, 185, 129, 0.5)'
                  }}></div>
                </div>
              </div>
              
              {/* Details Grid */}
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px'}}>
                <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Avg Daily Profit</div>
                  <div style={{fontSize: '1.3rem', fontWeight: 700, color: 'var(--success)'}}>
                    R{countdownData.metrics?.avg_daily_profit?.toFixed(2) || '0.00'}
                  </div>
                </div>
                <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Total Trades</div>
                  <div style={{fontSize: '1.3rem', fontWeight: 700, color: 'var(--accent)'}}>
                    {countdownData.metrics?.total_trades || 0}
                  </div>
                </div>
                <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Est. Completion</div>
                  <div style={{fontSize: '1.1rem', fontWeight: 700, color: 'var(--text)'}}>
                    {countdownData.completion_date || 'Unknown'}
                  </div>
                </div>
                <div style={{padding: '16px', background: 'var(--panel)', borderRadius: '8px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '6px'}}>Projection Type</div>
                  <div style={{fontSize: '1.1rem', fontWeight: 700, color: 'var(--text)', textTransform: 'capitalize'}}>
                    {countdownData.projections?.using || 'N/A'}
                  </div>
                </div>
              </div>
              
              {/* 12-Month AI Projection */}
              {countdownData.projections?.twelve_month && (
                <div style={{marginTop: '20px', padding: '20px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.05) 100%)', borderRadius: '12px', border: '2px solid #3b82f6'}}>
                  <h3 style={{color: '#3b82f6', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px'}}>
                    🔮 AI 12-Month Projection
                  </h3>
                  <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px'}}>
                    <div style={{textAlign: 'center', padding: '16px', background: 'var(--panel)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '8px'}}>Projected Value</div>
                      <div style={{fontSize: '1.6rem', fontWeight: 700, color: '#3b82f6'}}>
                        R{countdownData.projections?.twelve_month ? countdownData.projections.twelve_month.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}
                      </div>
                    </div>
                    <div style={{textAlign: 'center', padding: '16px', background: 'var(--panel)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '8px'}}>Expected Gain</div>
                      <div style={{fontSize: '1.6rem', fontWeight: 700, color: 'var(--success)'}}>
                        +R{countdownData.projections?.twelve_month_gain ? countdownData.projections.twelve_month_gain.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}
                      </div>
                    </div>
                    <div style={{textAlign: 'center', padding: '16px', background: 'var(--panel)', borderRadius: '8px'}}>
                      <div style={{fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '8px'}}>12-Month ROI</div>
                      <div style={{fontSize: '1.6rem', fontWeight: 700, color: '#3b82f6'}}>
                        {countdownData.projections?.twelve_month_roi?.toFixed(1) || '0'}%
                      </div>
                    </div>
                  </div>
                  <div style={{marginTop: '12px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--muted)', textAlign: 'center'}}>
                    💡 Based on current {countdownData.metrics?.daily_roi_pct?.toFixed(3) || '0'}% daily ROI with compound interest over 365 days
                  </div>
                </div>
              )}
              
              <div style={{marginTop: '16px', padding: '16px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%)', borderRadius: '8px', border: '2px solid var(--success)', textAlign: 'center'}}>
                <p style={{margin: 0, fontSize: '1rem', color: 'var(--text)', fontWeight: 600}}>
                  {countdownData.message || 'Keep trading to reach your goal!'}
                </p>
              </div>
              
              <div style={{marginTop: '12px', padding: '12px', background: 'var(--glass)', borderRadius: '6px', border: '1px solid var(--line)', fontSize: '0.85rem', color: 'var(--muted)'}}>
                <p><strong>How it works:</strong> Based on your current capital (R{countdownData.current_capital ? countdownData.current_capital.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0.00'}) and daily ROI ({countdownData.metrics?.daily_roi_pct?.toFixed(3) || '0'}%), the system uses compound interest calculations to project your path to R1,000,000. Updates in real-time as you trade!</p>
              </div>
            </>
          )}
        </div>
      </section>
    );
  };

  const renderWalletHub = () => {
    return (
      <section className="section active">
        <div className="card">
          <WalletHub />
        </div>
      </section>
    );
  };

  const renderDecisionTrace = () => {
    return (
      <section className="section active">
        <div className="card">
          <DecisionTrace />
        </div>
      </section>
    );
  };

  const renderWhaleFlow = () => {
    return (
      <section className="section active">
        <div className="card">
          <WhaleFlowHeatmap />
        </div>
      </section>
    );
  };

  const renderMetrics = () => {
    return (
      <section className="section active">
        <div className="card">
          <PrometheusMetrics />
        </div>
      </section>
    );
  };

  // Combined Intelligence section with tabs
  const renderIntelligence = () => {
    return (
      <section className="section active">
        <div className="card">
          <h2>🧠 Intelligence Dashboard</h2>
          
          {/* Intelligence Tabs */}
          <div style={{display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px'}}>
            <button 
              onClick={() => setIntelligenceTab('whale-flow')}
              style={{
                padding: '8px 16px',
                background: intelligenceTab === 'whale-flow' ? 'rgba(74, 144, 226, 0.3)' : 'transparent',
                border: '1px solid ' + (intelligenceTab === 'whale-flow' ? '#4a90e2' : 'rgba(255,255,255,0.2)'),
                borderRadius: '6px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: intelligenceTab === 'whale-flow' ? 'bold' : 'normal'
              }}
            >
              🐋 Whale Flow
            </button>
            <button 
              onClick={() => setIntelligenceTab('decision-trace')}
              style={{
                padding: '8px 16px',
                background: intelligenceTab === 'decision-trace' ? 'rgba(74, 144, 226, 0.3)' : 'transparent',
                border: '1px solid ' + (intelligenceTab === 'decision-trace' ? '#4a90e2' : 'rgba(255,255,255,0.2)'),
                borderRadius: '6px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: intelligenceTab === 'decision-trace' ? 'bold' : 'normal'
              }}
            >
              🎬 Decision Trace
            </button>
            <button 
              onClick={() => setIntelligenceTab('metrics')}
              style={{
                padding: '8px 16px',
                background: intelligenceTab === 'metrics' ? 'rgba(74, 144, 226, 0.3)' : 'transparent',
                border: '1px solid ' + (intelligenceTab === 'metrics' ? '#4a90e2' : 'rgba(255,255,255,0.2)'),
                borderRadius: '6px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: intelligenceTab === 'metrics' ? 'bold' : 'normal'
              }}
            >
              📊 Metrics
            </button>
          </div>

          {/* Tab Content */}
          {intelligenceTab === 'whale-flow' && <WhaleFlowHeatmap />}
          {intelligenceTab === 'decision-trace' && <DecisionTrace />}
          {intelligenceTab === 'metrics' && <PrometheusMetrics />}
        </div>
      </section>
    );
  };

  const renderAPIKeys = () => {
    return (
      <section className="section active">
        <div className="card">
          <APIKeySettings />
        </div>
      </section>
    );
  };

  const renderFlokxAlerts = () => {
    
    return (
      <section className="section active">
        <div className="card">
          <h2>Flokx Alerts</h2>
          
          {!isFlokxActive && (
            <div style={{padding: '40px', textAlign: 'center', background: 'var(--panel)', borderRadius: '6px', border: '1px solid var(--line)'}}>
              <p style={{color: 'var(--muted)', marginBottom: '12px'}}>
                ⚠️ Flokx alerts are not active. Configure your Flokx API key in the API Setup section to enable real-time alerts.
              </p>
              <button 
                onClick={() => showSection('api')}
                style={{
                  padding: '8px 16px',
                  background: 'var(--accent2)',
                  color: 'var(--text)',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Configure Flokx API
              </button>
            </div>
          )}
          
          {isFlokxActive && (
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <div style={{width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)'}}></div>
                  <span style={{fontSize: '0.85rem', color: 'var(--muted)'}}>Flokx Connected</span>
                </div>
                <button 
                  onClick={loadFlokxAlerts} 
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: 'var(--accent2)',
                    color: 'var(--text)',
                    border: 'none',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Refresh Alerts
                </button>
              </div>
              
              <div style={{background: 'var(--glass)', padding: '12px', borderRadius: '6px', border: '1px solid var(--line)'}}>
                {!Array.isArray(flokxAlerts) || flokxAlerts.length === 0 ? (
                  <p style={{color: 'var(--muted)', padding: '20px', textAlign: 'center'}}>
                    ✓ No alerts at this time - System running smoothly
                  </p>
                ) : (
                  <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                    {Array.isArray(flokxAlerts) && flokxAlerts.map((alert, idx) => (
                      <div 
                        key={idx}
                        style={{
                          padding: '12px',
                          background: 'var(--panel)',
                          borderRadius: '6px',
                          borderLeft: '4px solid ' + getAlertColor(alert.priority || alert.type || 'info'),
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <div>
                          <div style={{fontWeight: 600, marginBottom: '4px'}}>
                            {alert.title || alert.pair || 'Alert'}
                          </div>
                          <div style={{fontSize: '0.85rem', color: 'var(--muted)'}}>
                            {alert.message || 'No details available'}
                          </div>
                          <div style={{fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px'}}>
                            {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'No timestamp'}
                          </div>
                        </div>
                        {(alert.priority || alert.type) && (
                          <div style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: getAlertColor(alert.priority || alert.type || 'info'),
                            color: 'white'
                          }}>
                            {(alert.priority || alert.type || 'INFO').toUpperCase()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    );
  };

  return (
    <div className="app">
      {/* Sidebar - Desktop */}
      {!isMobile && (
        <aside className="sidebar">
          <img
            src="/assets/logo.png"
            className="logo"
            alt="Logo"
            onClick={() => showSection('overview')}
            style={{ cursor: 'pointer' }}
          />
          <nav className="nav" key={`nav-${showAdmin}`}>
            <a href="#" className={activeSection === 'welcome' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('welcome'); }}>🚀 Welcome</a>
            <a href="#" className={activeSection === 'api' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('api'); }}>🔑 API Setup</a>
            <a href="#" className={activeSection === 'bots' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('bots'); }}>🤖 Bot Management</a>
            <a href="#" className={activeSection === 'system' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('system'); }}>🎮 System Mode</a>
            <a href="#" className={activeSection === 'graphs' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('graphs'); }}>📈 Profit & Performance</a>
            <a href="#" className={activeSection === 'trades' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('trades'); }}>📊 Live Trades</a>
            
            {/* Metrics Section with Submenu */}
            <div style={{position: 'relative'}}>
              <a 
                href="#" 
                className={['flokx', 'decision-trace', 'whale-flow', 'metrics-panel'].includes(activeSection) ? 'active' : ''}
                onClick={(e) => { e.preventDefault(); setMetricsExpanded(!metricsExpanded); }}
                style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}
              >
                📊 Metrics {metricsExpanded ? '▼' : '▶'}
              </a>
              {metricsExpanded && (
                <div style={{paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px'}}>
                  <a 
                    href="#" 
                    className={activeSection === 'flokx' ? 'active' : ''}
                    onClick={(e) => { e.preventDefault(); showSection('flokx'); }}
                    style={{fontSize: '0.9em', padding: '6px 12px'}}
                  >
                    🔔 Flokx Alerts
                  </a>
                  <a 
                    href="#" 
                    className={activeSection === 'decision-trace' ? 'active' : ''}
                    onClick={(e) => { e.preventDefault(); showSection('decision-trace'); }}
                    style={{fontSize: '0.9em', padding: '6px 12px'}}
                  >
                    🎬 Decision Trace
                  </a>
                  <a 
                    href="#" 
                    className={activeSection === 'whale-flow' ? 'active' : ''}
                    onClick={(e) => { e.preventDefault(); showSection('whale-flow'); }}
                    style={{fontSize: '0.9em', padding: '6px 12px'}}
                  >
                    🐋 Whale Flow
                  </a>
                  <a 
                    href="#" 
                    className={activeSection === 'metrics-panel' ? 'active' : ''}
                    onClick={(e) => { e.preventDefault(); showSection('metrics-panel'); }}
                    style={{fontSize: '0.9em', padding: '6px 12px'}}
                  >
                    📊 System Metrics
                  </a>
                </div>
              )}
            </div>
            
            <a href="#" className={activeSection === 'countdown' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('countdown'); }}>⏱️ Countdown</a>
            <a href="#" className={activeSection === 'wallet' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('wallet'); }}>💰 Wallet Hub</a>
            <a href="#" className={activeSection === 'profile' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('profile'); }}>👤 Profile</a>
            {showAdmin && (
              <a href="#" className={activeSection === 'admin' ? 'active' : ''} onClick={(e) => { e.preventDefault(); showSection('admin'); }}>🔧 Admin</a>
            )}
          </nav>
        </aside>
      )}

      {/* Topbar - Desktop */}
      {!isMobile && (
        <header className="topbar">
          <h1>Amarktai Network</h1>
          <div className="top-actions">
            <div className="status-indicator" style={{padding: '4px 12px', background: systemHealth.errors === 0 && connectionStatus.api === 'Connected' ? 'var(--success)' : 'var(--error)', borderRadius: '6px', fontWeight: 600}}>
              <span>{systemHealth.errors === 0 && connectionStatus.api === 'Connected' ? '✓ System Healthy' : '⚠ System Issues'}</span>
            </div>
            <div className="status-indicator">
              <span>API</span>
              <div className={`status-dot ${connectionStatus.api === 'Connected' ? 'ok' : 'err'}`}></div>
            </div>
            <div className="status-indicator">
              <span>SSE</span>
              <div className={`status-dot ${connectionStatus.sse === 'Connected' ? 'ok' : 'err'}`}></div>
            </div>
            <div className="status-indicator">
              <span>WS</span>
              <div className={`status-dot ${connectionStatus.ws === 'Connected' ? 'ok' : 'err'}`}></div>
            </div>
            <div className="status-indicator">
              <span>RTT: {wsRtt}</span>
            </div>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>
      )}

      {/* Mobile Topbar */}
      {isMobile && (
        <div className="mobile-topbar">
          <button className="mobile-logo-btn" onClick={() => showSection('overview')}>
            <img
              src="/assets/logo.png"
              className="mobile-logo"
              alt="Logo"
            />
          </button>
          <div className="mobile-btns">
            <button className="mobile-btn" onClick={() => showSection('welcome')}>Welcome</button>
            <button className="mobile-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="main">
        {activeSection === 'welcome' && renderWelcome()}
        {activeSection === 'overview' && renderOverview()}
        {activeSection === 'api' && renderApiSetup()}
        {activeSection === 'bots' && renderBots()}
        {activeSection === 'system' && renderSystemMode()}
        {activeSection === 'graphs' && renderProfitGraphs()}
        {activeSection === 'trades' && renderLiveTradeFeed()}
        {activeSection === 'countdown' && renderCountdown()}
        {activeSection === 'wallet' && renderWalletHub()}
        {activeSection === 'flokx' && renderFlokxAlerts()}
        {activeSection === 'decision-trace' && renderDecisionTrace()}
        {activeSection === 'whale-flow' && renderWhaleFlow()}
        {activeSection === 'metrics-panel' && renderMetrics()}
        {activeSection === 'profile' && renderProfile()}
        {activeSection === 'admin' && showAdmin && renderAdmin()}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div>&copy; 2025 Amarktai Network. For personal use only.</div>
        <div>Need help? <a href="mailto:amarktainetwork@gmail.com">Contact us</a></div>
      </footer>

      {/* Bot Promotion Modal */}
      {showPromotionModal && eligibleBots.length > 0 && (
        <div className="modal-overlay" onClick={() => setShowPromotionModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>🎉 Bots Ready for Live Trading!</h2>
            <p style={{marginBottom: '20px'}}>
              {eligibleBots.length} bot(s) have completed their 7-day paper trading period and are eligible for live trading.
            </p>
            <div style={{marginBottom: '20px', textAlign: 'left', background: '#1a1a2e', padding: '15px', borderRadius: '8px'}}>
              <h3 style={{marginBottom: '10px', fontSize: '16px'}}>Eligible Bots:</h3>
              {eligibleBots.map(bot => (
                <div key={bot.id} style={{padding: '8px 0', borderBottom: '1px solid #333'}}>
                  <strong>{bot.name}</strong> - Capital: R{bot.current_capital?.toFixed(2)}, Profit: R{bot.profit?.toFixed(2)}
                </div>
              ))}
            </div>
            <div style={{marginBottom: '20px', textAlign: 'left', background: '#2a2a3e', padding: '15px', borderRadius: '8px'}}>
              <h3 style={{marginBottom: '10px', fontSize: '16px', color: '#ffcc00'}}>⚠️ Important Questions:</h3>
              <ol style={{paddingLeft: '20px'}}>
                <li style={{marginBottom: '8px'}}>Have you funded your LUNO wallet with real ZAR?</li>
                <li style={{marginBottom: '8px'}}>Do you want to use these paper-trained bots for live trading?</li>
                <li>Are you ready to trade with real money?</li>
              </ol>
            </div>
            <div style={{display: 'flex', gap: '10px', justifyContent: 'center'}}>
              <button
                className="btn-primary"
                onClick={() => confirmLiveSwitch(true, true)}
                style={{background: '#00ff88', color: '#000', padding: '12px 24px'}}
              >
                ✅ Yes, I've Funded LUNO - Switch to Live!
              </button>
              <button
                className="btn-danger"
                onClick={() => {
                  setShowPromotionModal(false);
                  toast.info('Please fund your LUNO wallet before enabling live trading');
                }}
                style={{padding: '12px 24px'}}
              >
                ❌ Not Yet - Keep Paper Trading
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
