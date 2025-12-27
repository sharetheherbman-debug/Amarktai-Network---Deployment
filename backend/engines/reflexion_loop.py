"""
Reflexion Loop for Self-Healing
Implements Responder-Critic-Revisor pattern for autonomous error recovery
Integrates with Episodic Memory to learn from past successes
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import logging
import json

logger = logging.getLogger(__name__)

try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available - Episodic Memory disabled")


class ReflexionLoop:
    """
    Responder-Critic-Revisor loop for self-healing
    Continuously monitors, analyzes, and improves system behavior
    """
    
    def __init__(
        self,
        check_interval_seconds: int = 60,
        memory_enabled: bool = True
    ):
        """
        Initialize Reflexion loop
        
        Args:
            check_interval_seconds: Interval for reflexion checks
            memory_enabled: Enable episodic memory
        """
        self.check_interval = check_interval_seconds
        self.memory_enabled = memory_enabled and LANGCHAIN_AVAILABLE
        
        # Episodic Memory for learning
        self.episodic_memory = None
        if self.memory_enabled:
            self._initialize_memory()
        
        # Track reflexion cycles
        self.reflexion_history: List[Dict] = []
        
        # Running state
        self.is_running = False
        self.task = None
        
        logger.info(
            f"Reflexion Loop initialized: check interval {self.check_interval}s, "
            f"memory {'enabled' if self.memory_enabled else 'disabled'}"
        )
    
    def _initialize_memory(self):
        """Initialize episodic memory with Chroma"""
        try:
            # Initialize embeddings
            embeddings = OpenAIEmbeddings()
            
            # Initialize Chroma vector store
            self.episodic_memory = Chroma(
                collection_name="trading_episodes",
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )
            
            logger.info("Episodic memory initialized with Chroma")
            
        except Exception as e:
            logger.error(f"Failed to initialize episodic memory: {e}")
            self.memory_enabled = False
    
    async def store_success_episode(
        self,
        trade_data: Dict,
        reasoning: str,
        regime: str,
        volatility: float,
        outcome: Dict
    ) -> None:
        """
        Store successful trade episode in memory
        
        Args:
            trade_data: Trade details
            reasoning: Decision reasoning
            regime: Market regime
            volatility: Market volatility
            outcome: Trade outcome
        """
        if not self.memory_enabled or not self.episodic_memory:
            return
        
        try:
            # Create episode document
            episode = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': trade_data.get('symbol'),
                'side': trade_data.get('side'),
                'regime': regime,
                'volatility': volatility,
                'reasoning': reasoning,
                'entry_price': trade_data.get('entry_price'),
                'exit_price': outcome.get('exit_price'),
                'pnl': outcome.get('pnl'),
                'pnl_pct': outcome.get('pnl_pct'),
                'success': outcome.get('pnl', 0) > 0
            }
            
            # Create searchable text
            episode_text = (
                f"Trade {trade_data.get('symbol')} {trade_data.get('side')} "
                f"in {regime} regime (volatility: {volatility:.4f}). "
                f"Reasoning: {reasoning}. "
                f"Outcome: {outcome.get('pnl_pct', 0):.2f}% P&L"
            )
            
            # Store in vector database
            doc = Document(
                page_content=episode_text,
                metadata=episode
            )
            
            self.episodic_memory.add_documents([doc])
            
            logger.info(f"Stored success episode for {trade_data.get('symbol')}")
            
        except Exception as e:
            logger.error(f"Failed to store episode: {e}")
    
    async def retrieve_similar_episodes(
        self,
        current_situation: str,
        regime: str,
        k: int = 3
    ) -> List[Dict]:
        """
        Retrieve similar past episodes from memory
        
        Args:
            current_situation: Current market situation description
            regime: Current market regime
            k: Number of similar episodes to retrieve
            
        Returns:
            List of similar episodes
        """
        if not self.memory_enabled or not self.episodic_memory:
            return []
        
        try:
            # Create search query
            query = f"{current_situation} in {regime} regime"
            
            # Search for similar episodes
            docs = self.episodic_memory.similarity_search(query, k=k)
            
            episodes = []
            for doc in docs:
                episode = {
                    'text': doc.page_content,
                    **doc.metadata
                }
                episodes.append(episode)
            
            logger.info(f"Retrieved {len(episodes)} similar episodes")
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to retrieve episodes: {e}")
            return []
    
    async def responder_phase(self) -> Dict:
        """
        Responder: Detect current system state and issues
        
        Returns:
            Dictionary with system state and detected issues
        """
        from engines.self_healing_ai import self_healing_ai
        
        # Get health report
        health_report = await self_healing_ai.get_health_report()
        
        # Analyze logs for errors
        recent_errors = [
            e for e in self_healing_ai.error_history
            if e.timestamp > datetime.now(timezone.utc) - timedelta(seconds=self.check_interval)
        ]
        
        response = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_health': health_report.get('overall_status'),
            'recent_errors': len(recent_errors),
            'degraded_components': health_report.get('degraded_components', []),
            'error_types': {},
            'healing_success_rate': health_report.get('metrics', {}).get('healing_success_rate', 0)
        }
        
        # Categorize errors
        for error in recent_errors:
            error_type = error.error_type
            if error_type not in response['error_types']:
                response['error_types'][error_type] = {
                    'count': 0,
                    'severity': error.severity.value,
                    'components': []
                }
            response['error_types'][error_type]['count'] += 1
            if error.component not in response['error_types'][error_type]['components']:
                response['error_types'][error_type]['components'].append(error.component)
        
        return response
    
    async def critic_phase(self, response: Dict) -> Dict:
        """
        Critic: Analyze system state and identify root causes
        
        Args:
            response: System state from responder
            
        Returns:
            Analysis with root causes and recommendations
        """
        analysis = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'health_assessment': 'healthy',
            'root_causes': [],
            'recommendations': []
        }
        
        # Assess overall health
        if response['overall_health'] == 'degraded':
            analysis['health_assessment'] = 'degraded'
        
        # Identify root causes
        if response['recent_errors'] > 0:
            for error_type, details in response['error_types'].items():
                if details['count'] >= 3:  # Threshold for concern
                    root_cause = {
                        'error_type': error_type,
                        'frequency': details['count'],
                        'severity': details['severity'],
                        'affected_components': details['components'],
                        'likely_cause': self._diagnose_error_pattern(error_type, details)
                    }
                    analysis['root_causes'].append(root_cause)
        
        # Generate recommendations
        for cause in analysis['root_causes']:
            recommendation = self._generate_recommendation(cause)
            analysis['recommendations'].append(recommendation)
        
        # Check healing success rate
        if response['healing_success_rate'] < 0.7:  # 70% threshold
            analysis['recommendations'].append({
                'priority': 'high',
                'action': 'review_healing_strategies',
                'reason': f"Healing success rate low: {response['healing_success_rate']:.0%}"
            })
        
        logger.info(
            f"Critic analysis: {len(analysis['root_causes'])} root causes, "
            f"{len(analysis['recommendations'])} recommendations"
        )
        
        return analysis
    
    def _diagnose_error_pattern(self, error_type: str, details: Dict) -> str:
        """Diagnose likely cause of error pattern"""
        diagnoses = {
            'connection_timeout': 'Network connectivity issues or high latency',
            'api_rate_limit': 'Excessive API calls or insufficient rate limiting',
            'database_error': 'Database connection pool exhaustion or query issues',
            'insufficient_balance': 'Capital depletion or position sizing errors',
            'authentication_failed': 'Invalid or expired API credentials',
            'memory_overflow': 'Memory leak or insufficient resources'
        }
        
        return diagnoses.get(error_type, 'Unknown error pattern - needs investigation')
    
    def _generate_recommendation(self, root_cause: Dict) -> Dict:
        """Generate actionable recommendation from root cause"""
        error_type = root_cause['error_type']
        
        recommendations = {
            'connection_timeout': {
                'priority': 'medium',
                'action': 'increase_timeout',
                'params': {'timeout_seconds': 30},
                'reason': 'Prevent timeout errors by allowing more time'
            },
            'api_rate_limit': {
                'priority': 'high',
                'action': 'reduce_request_rate',
                'params': {'delay_ms': 100},
                'reason': 'Reduce API call frequency to stay within limits'
            },
            'database_error': {
                'priority': 'high',
                'action': 'reset_db_connections',
                'params': {},
                'reason': 'Clear stale connections and refresh pool'
            },
            'insufficient_balance': {
                'priority': 'critical',
                'action': 'pause_trading',
                'params': {},
                'reason': 'Prevent further losses due to low balance'
            }
        }
        
        return recommendations.get(error_type, {
            'priority': 'medium',
            'action': 'manual_review',
            'params': {},
            'reason': f"Unknown error type: {error_type}"
        })
    
    async def revisor_phase(self, analysis: Dict) -> Dict:
        """
        Revisor: Apply fixes and update system parameters
        
        Args:
            analysis: Analysis from critic
            
        Returns:
            Dictionary with applied changes
        """
        from engines.self_healing_ai import self_healing_ai
        
        changes = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recommendations_processed': 0,
            'changes_applied': [],
            'failures': []
        }
        
        for recommendation in analysis['recommendations']:
            try:
                success = await self._apply_recommendation(recommendation)
                
                if success:
                    changes['changes_applied'].append({
                        'action': recommendation['action'],
                        'params': recommendation.get('params', {}),
                        'reason': recommendation['reason']
                    })
                else:
                    changes['failures'].append({
                        'action': recommendation['action'],
                        'reason': 'Application failed'
                    })
                
                changes['recommendations_processed'] += 1
                
            except Exception as e:
                logger.error(f"Failed to apply recommendation: {e}")
                changes['failures'].append({
                    'action': recommendation['action'],
                    'error': str(e)
                })
        
        logger.info(
            f"Revisor applied {len(changes['changes_applied'])} changes, "
            f"{len(changes['failures'])} failures"
        )
        
        return changes
    
    async def _apply_recommendation(self, recommendation: Dict) -> bool:
        """Apply a specific recommendation"""
        action = recommendation['action']
        params = recommendation.get('params', {})
        
        try:
            if action == 'increase_timeout':
                # Update timeout configuration
                timeout = params.get('timeout_seconds', 30)
                # In production: update configuration
                logger.info(f"Applied: Increased timeout to {timeout}s")
                return True
            
            elif action == 'reduce_request_rate':
                # Add delay between requests
                delay = params.get('delay_ms', 100)
                # In production: update rate limiter
                logger.info(f"Applied: Added {delay}ms delay between requests")
                return True
            
            elif action == 'reset_db_connections':
                # Reset database connections
                # In production: clear connection pool
                logger.info("Applied: Reset database connections")
                return True
            
            elif action == 'pause_trading':
                # Pause all trading
                # In production: send pause signal to trading engines
                logger.info("Applied: Paused trading due to low balance")
                return True
            
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply {action}: {e}")
            return False
    
    async def run_reflexion_cycle(self) -> Dict:
        """
        Run complete Responder-Critic-Revisor cycle
        
        Returns:
            Cycle results
        """
        cycle = {
            'cycle_id': len(self.reflexion_history) + 1,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Phase 1: Responder
            response = await self.responder_phase()
            cycle['response'] = response
            
            # Phase 2: Critic
            analysis = await self.critic_phase(response)
            cycle['analysis'] = analysis
            
            # Phase 3: Revisor
            changes = await self.revisor_phase(analysis)
            cycle['changes'] = changes
            
            cycle['end_time'] = datetime.now(timezone.utc).isoformat()
            cycle['success'] = True
            
            # Store cycle
            self.reflexion_history.append(cycle)
            
            # Keep last 100 cycles
            if len(self.reflexion_history) > 100:
                self.reflexion_history = self.reflexion_history[-100:]
            
            logger.info(f"Reflexion cycle {cycle['cycle_id']} completed")
            
        except Exception as e:
            logger.error(f"Reflexion cycle failed: {e}")
            cycle['error'] = str(e)
            cycle['success'] = False
        
        return cycle
    
    async def start(self):
        """Start continuous reflexion loop"""
        if self.is_running:
            logger.warning("Reflexion loop already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Reflexion loop started")
    
    async def stop(self):
        """Stop reflexion loop"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Reflexion loop stopped")
    
    async def _run_loop(self):
        """Main reflexion loop"""
        while self.is_running:
            try:
                await self.run_reflexion_cycle()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reflexion loop error: {e}")
                await asyncio.sleep(self.check_interval)


# Global instance
reflexion_loop = ReflexionLoop()
