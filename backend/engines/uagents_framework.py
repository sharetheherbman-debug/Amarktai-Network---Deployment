"""
Fetch.ai uAgents Framework Integration
Transforms trading engines into autonomous, sovereign agents
Registers agents on Fetch.ai Almanac for decentralized coordination
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

try:
    from uagents import Agent, Bureau, Context, Model
    from uagents.setup import fund_agent_if_low
    UAGENTS_AVAILABLE = True
except ImportError:
    UAGENTS_AVAILABLE = False
    logging.warning("uAgents not available - agent features disabled")

logger = logging.getLogger(__name__)


# Protocol Messages
class MarketDataMessage(Model):
    """Market data update message"""
    symbol: str
    price: float
    volume: float
    timestamp: str


class SignalMessage(Model):
    """Trading signal message"""
    symbol: str
    signal_type: str
    recommendation: str
    confidence: float
    reasoning: str
    timestamp: str


class HealthCheckMessage(Model):
    """Health check message"""
    component: str
    status: str
    timestamp: str


class RegimeAgent:
    """
    Autonomous Regime Detection Agent
    Uses HMM/GMM to classify market states
    """
    
    def __init__(self, name: str = "regime_agent", port: int = 8001):
        """Initialize regime detection agent"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.agent = None
            return
        
        self.agent = Agent(
            name=name,
            port=port,
            seed=f"{name}_seed",
            endpoint=[f"http://localhost:{port}/submit"]
        )
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info(f"Regime Agent initialized: {self.agent.address}")
    
    def _setup_handlers(self):
        """Setup agent message handlers"""
        
        @self.agent.on_interval(period=60.0)  # Every 60 seconds
        async def update_regime(ctx: Context):
            """Periodic regime detection"""
            from engines.regime_detector import regime_detector
            
            try:
                # Get regime summary
                summary = await regime_detector.get_regime_summary()
                
                ctx.logger.info(f"Regime update: {len(summary)} symbols tracked")
                
                # Broadcast regime changes to other agents
                for symbol, regime_data in summary.items():
                    signal = SignalMessage(
                        symbol=symbol,
                        signal_type="regime",
                        recommendation=regime_data['regime'],
                        confidence=regime_data['confidence'],
                        reasoning=f"Regime: {regime_data['regime']} with {regime_data['confidence']:.0%} confidence",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    
                    # In full implementation: broadcast to other agents
                    ctx.logger.debug(f"Regime signal: {symbol} -> {regime_data['regime']}")
                    
            except Exception as e:
                ctx.logger.error(f"Regime detection error: {e}")
        
        @self.agent.on_message(model=MarketDataMessage)
        async def handle_market_data(ctx: Context, sender: str, msg: MarketDataMessage):
            """Handle incoming market data"""
            from engines.regime_detector import regime_detector
            
            try:
                # Update price data
                await regime_detector.update_price_data(
                    symbol=msg.symbol,
                    price=msg.price,
                    volume=msg.volume
                )
                
                ctx.logger.debug(f"Market data received: {msg.symbol} @ ${msg.price}")
                
            except Exception as e:
                ctx.logger.error(f"Market data handling error: {e}")


class OFIAgent:
    """
    Autonomous Order Flow Imbalance Agent
    Calculates micro-scale entry signals
    """
    
    def __init__(self, name: str = "ofi_agent", port: int = 8002):
        """Initialize OFI agent"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.agent = None
            return
        
        self.agent = Agent(
            name=name,
            port=port,
            seed=f"{name}_seed",
            endpoint=[f"http://localhost:{port}/submit"]
        )
        
        self._setup_handlers()
        
        logger.info(f"OFI Agent initialized: {self.agent.address}")
    
    def _setup_handlers(self):
        """Setup agent message handlers"""
        
        @self.agent.on_interval(period=1.0)  # Every second
        async def calculate_ofi(ctx: Context):
            """Calculate OFI signals"""
            from engines.order_flow_imbalance import ofi_calculator
            
            try:
                # Check all tracked symbols
                for symbol in ofi_calculator.snapshots.keys():
                    signal = await ofi_calculator.get_signal(symbol)
                    
                    if signal and signal.recommendation != 'neutral':
                        ctx.logger.info(
                            f"OFI signal: {symbol} -> {signal.recommendation} "
                            f"(strength: {signal.signal_strength:.2f})"
                        )
                        
                        # Broadcast signal to other agents
                        # In full implementation: send to trading agent
                        
            except Exception as e:
                ctx.logger.error(f"OFI calculation error: {e}")


class WhaleAgent:
    """
    Autonomous Whale Activity Monitoring Agent
    Tracks large blockchain transactions
    """
    
    def __init__(self, name: str = "whale_agent", port: int = 8003):
        """Initialize whale monitoring agent"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.agent = None
            return
        
        self.agent = Agent(
            name=name,
            port=port,
            seed=f"{name}_seed",
            endpoint=[f"http://localhost:{port}/submit"]
        )
        
        self._setup_handlers()
        
        logger.info(f"Whale Agent initialized: {self.agent.address}")
    
    def _setup_handlers(self):
        """Setup agent message handlers"""
        
        @self.agent.on_interval(period=300.0)  # Every 5 minutes
        async def monitor_whale_activity(ctx: Context):
            """Monitor whale transactions"""
            from engines.on_chain_monitor import whale_monitor
            
            try:
                # Get whale summary
                summary = await whale_monitor.get_summary()
                
                for coin, data in summary.items():
                    signal = data.get('signal')
                    if signal and signal['type'] != 'unknown':
                        ctx.logger.info(
                            f"Whale signal: {coin} -> {signal['type']} "
                            f"({signal['strength']:.0%}): {signal['reason']}"
                        )
                        
                        # Broadcast to other agents
                        # In full implementation: send to alpha fusion agent
                        
            except Exception as e:
                ctx.logger.error(f"Whale monitoring error: {e}")


class AlphaFusionAgent:
    """
    Autonomous Alpha Fusion Agent
    Combines signals from multiple sources
    """
    
    def __init__(self, name: str = "alpha_fusion_agent", port: int = 8004):
        """Initialize alpha fusion agent"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.agent = None
            return
        
        self.agent = Agent(
            name=name,
            port=port,
            seed=f"{name}_seed",
            endpoint=[f"http://localhost:{port}/submit"]
        )
        
        self._setup_handlers()
        
        logger.info(f"Alpha Fusion Agent initialized: {self.agent.address}")
    
    def _setup_handlers(self):
        """Setup agent message handlers"""
        
        @self.agent.on_message(model=SignalMessage)
        async def handle_signal(ctx: Context, sender: str, msg: SignalMessage):
            """Handle incoming trading signals"""
            ctx.logger.info(
                f"Signal received from {sender}: {msg.symbol} -> {msg.recommendation} "
                f"({msg.confidence:.0%})"
            )
            
            # In full implementation: accumulate signals and fuse
            
        @self.agent.on_interval(period=30.0)  # Every 30 seconds
        async def fuse_signals(ctx: Context):
            """Fuse all available signals"""
            from engines.alpha_fusion_engine import alpha_fusion
            
            try:
                # Example: fuse signals for main symbols
                symbols = ["BTC/USDT", "ETH/USDT"]
                
                for symbol in symbols:
                    fused_signal = await alpha_fusion.fuse_signals(symbol)
                    
                    if fused_signal:
                        ctx.logger.info(
                            f"Fused signal: {symbol} -> {fused_signal.signal.value} "
                            f"(confidence: {fused_signal.confidence:.0%})"
                        )
                        
                        # Broadcast fused signal to trading agent
                        # In full implementation: send to execution agent
                        
            except Exception as e:
                ctx.logger.error(f"Signal fusion error: {e}")


class SelfHealingAgent:
    """
    Autonomous Self-Healing Agent
    Monitors system health and applies fixes
    """
    
    def __init__(self, name: str = "self_healing_agent", port: int = 8005):
        """Initialize self-healing agent"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.agent = None
            return
        
        self.agent = Agent(
            name=name,
            port=port,
            seed=f"{name}_seed",
            endpoint=[f"http://localhost:{port}/submit"]
        )
        
        self._setup_handlers()
        
        logger.info(f"Self-Healing Agent initialized: {self.agent.address}")
    
    def _setup_handlers(self):
        """Setup agent message handlers"""
        
        @self.agent.on_interval(period=60.0)  # Every minute
        async def run_reflexion_cycle(ctx: Context):
            """Run Reflexion loop for self-healing"""
            from engines.reflexion_loop import reflexion_loop
            
            try:
                # Run reflexion cycle
                cycle = await reflexion_loop.run_reflexion_cycle()
                
                if cycle.get('success'):
                    ctx.logger.info(
                        f"Reflexion cycle {cycle['cycle_id']} completed: "
                        f"{len(cycle.get('changes', {}).get('changes_applied', []))} changes applied"
                    )
                else:
                    ctx.logger.error(f"Reflexion cycle failed: {cycle.get('error')}")
                    
            except Exception as e:
                ctx.logger.error(f"Reflexion cycle error: {e}")
        
        @self.agent.on_message(model=HealthCheckMessage)
        async def handle_health_check(ctx: Context, sender: str, msg: HealthCheckMessage):
            """Handle health check from other agents"""
            ctx.logger.debug(f"Health check from {sender}: {msg.component} is {msg.status}")
            
            # In full implementation: update component health tracking


class AgentBureau:
    """
    Bureau for coordinating all trading agents
    Manages agent lifecycle and inter-agent communication
    """
    
    def __init__(self):
        """Initialize agent bureau"""
        if not UAGENTS_AVAILABLE:
            logger.error("uAgents not available")
            self.bureau = None
            self.regime_agent = None
            self.ofi_agent = None
            self.whale_agent = None
            self.alpha_fusion_agent = None
            self.self_healing_agent = None
            return
        
        self.bureau = Bureau()
        
        # Initialize all agents
        self.regime_agent = RegimeAgent()
        self.ofi_agent = OFIAgent()
        self.whale_agent = WhaleAgent()
        self.alpha_fusion_agent = AlphaFusionAgent()
        self.self_healing_agent = SelfHealingAgent()
        
        # Add agents to bureau if they were successfully created
        if self.regime_agent and hasattr(self.regime_agent, 'agent') and self.regime_agent.agent:
            self.bureau.add(self.regime_agent.agent)
        if self.ofi_agent and hasattr(self.ofi_agent, 'agent') and self.ofi_agent.agent:
            self.bureau.add(self.ofi_agent.agent)
        if self.whale_agent and hasattr(self.whale_agent, 'agent') and self.whale_agent.agent:
            self.bureau.add(self.whale_agent.agent)
        if self.alpha_fusion_agent and hasattr(self.alpha_fusion_agent, 'agent') and self.alpha_fusion_agent.agent:
            self.bureau.add(self.alpha_fusion_agent.agent)
        if self.self_healing_agent and hasattr(self.self_healing_agent, 'agent') and self.self_healing_agent.agent:
            self.bureau.add(self.self_healing_agent.agent)
        
        logger.info("Agent Bureau initialized with 5 agents")
    
    def run(self):
        """Run the bureau"""
        if not self.bureau:
            logger.error("Bureau not initialized")
            return
        
        logger.info("Starting Agent Bureau...")
        self.bureau.run()


# Global instance (lazy initialization)
_agent_bureau = None


def get_agent_bureau() -> Optional[AgentBureau]:
    """Get or create agent bureau instance"""
    global _agent_bureau
    
    if not UAGENTS_AVAILABLE:
        logger.warning("uAgents not available - agent features disabled")
        return None
    
    if _agent_bureau is None:
        _agent_bureau = AgentBureau()
    
    return _agent_bureau


def start_agent_system():
    """Start the multi-agent system"""
    bureau = get_agent_bureau()
    
    if bureau:
        logger.info("Starting multi-agent trading system...")
        bureau.run()
    else:
        logger.warning("Agent system not started - uAgents not available")
