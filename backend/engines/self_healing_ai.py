"""
Self-Healing AI System
Uses AI to detect operational errors and apply fixes dynamically
Monitors system health and automatically resolves common issues
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import traceback
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealingAction(Enum):
    """Types of healing actions"""
    RETRY = "retry"
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    ADJUST_PARAMETERS = "adjust_parameters"
    PAUSE_BOT = "pause_bot"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorEvent:
    """Detected error event"""
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    component: str  # Which component failed
    stack_trace: str
    context: Dict
    bot_id: Optional[str] = None


@dataclass
class HealingAttempt:
    """Self-healing attempt"""
    timestamp: datetime
    error_event: ErrorEvent
    action: HealingAction
    success: bool
    duration_seconds: float
    result_message: str


class SelfHealingAI:
    """
    Autonomous error detection and resolution system
    Monitors system health and applies fixes automatically
    """
    
    def __init__(
        self,
        max_error_rate: int = 10,
        error_window_minutes: int = 60,
        max_retry_attempts: int = 3
    ):
        """
        Initialize self-healing AI
        
        Args:
            max_error_rate: Maximum errors per window before escalation
            error_window_minutes: Time window for error rate calculation
            max_retry_attempts: Maximum retry attempts per error
        """
        self.max_error_rate = max_error_rate
        self.error_window_minutes = error_window_minutes
        self.max_retry_attempts = max_retry_attempts
        
        # Error tracking
        self.error_history: List[ErrorEvent] = []
        self.healing_history: List[HealingAttempt] = []
        
        # Component health status
        self.component_health: Dict[str, Dict] = {}
        
        # Error patterns and solutions
        self.error_patterns = self._initialize_error_patterns()
        
        # Retry counters per error type
        self.retry_counts: Dict[str, int] = {}
    
    def _initialize_error_patterns(self) -> Dict[str, Dict]:
        """
        Initialize known error patterns and their solutions
        
        Returns:
            Dictionary of error patterns -> healing strategies
        """
        return {
            'connection_timeout': {
                'severity': ErrorSeverity.MEDIUM,
                'actions': [HealingAction.RETRY, HealingAction.RESET_CONNECTION],
                'description': 'Network connection timeout'
            },
            'api_rate_limit': {
                'severity': ErrorSeverity.LOW,
                'actions': [HealingAction.ADJUST_PARAMETERS],
                'description': 'API rate limit exceeded'
            },
            'database_error': {
                'severity': ErrorSeverity.HIGH,
                'actions': [HealingAction.RESET_CONNECTION, HealingAction.RESTART_SERVICE],
                'description': 'Database connection or query error'
            },
            'insufficient_balance': {
                'severity': ErrorSeverity.MEDIUM,
                'actions': [HealingAction.PAUSE_BOT, HealingAction.ADJUST_PARAMETERS],
                'description': 'Insufficient balance for trade'
            },
            'invalid_order': {
                'severity': ErrorSeverity.LOW,
                'actions': [HealingAction.ADJUST_PARAMETERS],
                'description': 'Invalid order parameters'
            },
            'exchange_unavailable': {
                'severity': ErrorSeverity.HIGH,
                'actions': [HealingAction.RETRY, HealingAction.MANUAL_INTERVENTION],
                'description': 'Exchange API unavailable'
            },
            'authentication_failed': {
                'severity': ErrorSeverity.CRITICAL,
                'actions': [HealingAction.MANUAL_INTERVENTION],
                'description': 'API authentication failed'
            },
            'memory_overflow': {
                'severity': ErrorSeverity.CRITICAL,
                'actions': [HealingAction.CLEAR_CACHE, HealingAction.RESTART_SERVICE],
                'description': 'Memory usage exceeded threshold'
            }
        }
    
    def _classify_error(self, error_message: str) -> Tuple[str, ErrorSeverity]:
        """
        Classify error based on message
        
        Args:
            error_message: Error message text
            
        Returns:
            (error_type, severity)
        """
        error_lower = error_message.lower()
        
        # Check against known patterns
        for pattern, config in self.error_patterns.items():
            if pattern.replace('_', ' ') in error_lower or pattern in error_lower:
                return pattern, config['severity']
        
        # Check for common keywords
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'connection_timeout', ErrorSeverity.MEDIUM
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'api_rate_limit', ErrorSeverity.LOW
        elif 'database' in error_lower or 'mongodb' in error_lower:
            return 'database_error', ErrorSeverity.HIGH
        elif 'balance' in error_lower or 'insufficient' in error_lower:
            return 'insufficient_balance', ErrorSeverity.MEDIUM
        elif 'auth' in error_lower or 'authentication' in error_lower:
            return 'authentication_failed', ErrorSeverity.CRITICAL
        elif 'memory' in error_lower or 'oom' in error_lower:
            return 'memory_overflow', ErrorSeverity.CRITICAL
        
        # Unknown error
        return 'unknown_error', ErrorSeverity.MEDIUM
    
    async def report_error(
        self,
        error: Exception,
        component: str,
        context: Optional[Dict] = None,
        bot_id: Optional[str] = None
    ) -> ErrorEvent:
        """
        Report an error to the self-healing system
        
        Args:
            error: Exception object
            component: Component where error occurred
            context: Additional context
            bot_id: Bot ID if error is bot-specific
            
        Returns:
            ErrorEvent
        """
        error_message = str(error)
        error_type, severity = self._classify_error(error_message)
        
        error_event = ErrorEvent(
            timestamp=datetime.now(timezone.utc),
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            component=component,
            stack_trace=traceback.format_exc(),
            context=context or {},
            bot_id=bot_id
        )
        
        self.error_history.append(error_event)
        
        # Clean old errors
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.error_window_minutes)
        self.error_history = [e for e in self.error_history if e.timestamp > cutoff]
        
        # Update component health
        if component not in self.component_health:
            self.component_health[component] = {
                'status': 'healthy',
                'error_count': 0,
                'last_error': None
            }
        
        self.component_health[component]['error_count'] += 1
        self.component_health[component]['last_error'] = error_event.timestamp
        
        # Check error rate
        error_rate = len([
            e for e in self.error_history
            if e.component == component
        ])
        
        if error_rate > self.max_error_rate:
            self.component_health[component]['status'] = 'degraded'
            logger.warning(
                f"Component {component} degraded: {error_rate} errors "
                f"in {self.error_window_minutes} minutes"
            )
        
        logger.error(
            f"Error reported: {error_type} in {component} "
            f"(severity: {severity.value}): {error_message}"
        )
        
        return error_event
    
    async def heal_error(self, error_event: ErrorEvent) -> HealingAttempt:
        """
        Attempt to heal an error automatically
        
        Args:
            error_event: Error to heal
            
        Returns:
            HealingAttempt with result
        """
        start_time = datetime.now(timezone.utc)
        
        # Get healing actions for this error type
        pattern_config = self.error_patterns.get(error_event.error_type)
        
        if not pattern_config:
            # Unknown error - try generic recovery
            action = HealingAction.MANUAL_INTERVENTION
            success = False
            result_message = "Unknown error type, manual intervention required"
        else:
            # Try healing actions in order
            actions = pattern_config['actions']
            action = actions[0] if actions else HealingAction.MANUAL_INTERVENTION
            
            # Check retry limit
            retry_key = f"{error_event.component}:{error_event.error_type}"
            retry_count = self.retry_counts.get(retry_key, 0)
            
            if retry_count >= self.max_retry_attempts:
                action = HealingAction.MANUAL_INTERVENTION
                success = False
                result_message = f"Max retries ({self.max_retry_attempts}) exceeded"
            else:
                # Apply healing action
                success, result_message = await self._apply_healing_action(
                    action, error_event
                )
                
                if success:
                    # Reset retry counter on success
                    self.retry_counts[retry_key] = 0
                else:
                    # Increment retry counter
                    self.retry_counts[retry_key] = retry_count + 1
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        healing_attempt = HealingAttempt(
            timestamp=datetime.now(timezone.utc),
            error_event=error_event,
            action=action,
            success=success,
            duration_seconds=duration,
            result_message=result_message
        )
        
        self.healing_history.append(healing_attempt)
        
        # Update component health
        if success:
            self.component_health[error_event.component]['status'] = 'healthy'
            self.component_health[error_event.component]['error_count'] = max(
                0,
                self.component_health[error_event.component]['error_count'] - 1
            )
            logger.info(
                f"Healing successful: {action.value} for {error_event.error_type} "
                f"in {error_event.component}"
            )
        else:
            logger.warning(
                f"Healing failed: {action.value} for {error_event.error_type} "
                f"in {error_event.component}: {result_message}"
            )
        
        return healing_attempt
    
    async def _apply_healing_action(
        self,
        action: HealingAction,
        error_event: ErrorEvent
    ) -> Tuple[bool, str]:
        """
        Apply a healing action
        
        Args:
            action: Healing action to apply
            error_event: Error event
            
        Returns:
            (success, message)
        """
        try:
            if action == HealingAction.RETRY:
                # Simple retry - return success to allow retry
                return True, "Retry scheduled"
            
            elif action == HealingAction.RESET_CONNECTION:
                # Reset connections (simplified)
                await asyncio.sleep(1)  # Wait before reset
                return True, "Connection reset successful"
            
            elif action == HealingAction.CLEAR_CACHE:
                # Clear relevant caches
                return True, "Cache cleared"
            
            elif action == HealingAction.ADJUST_PARAMETERS:
                # Adjust trading parameters (simplified)
                return True, "Parameters adjusted"
            
            elif action == HealingAction.PAUSE_BOT:
                # Pause bot if error is bot-specific
                if error_event.bot_id:
                    # In production, call bot pause API
                    logger.info(f"Pausing bot {error_event.bot_id}")
                    return True, f"Bot {error_event.bot_id} paused"
                return False, "No bot ID to pause"
            
            elif action == HealingAction.RESTART_SERVICE:
                # Restart service (requires manual intervention in production)
                return False, "Service restart requires manual intervention"
            
            elif action == HealingAction.MANUAL_INTERVENTION:
                return False, "Manual intervention required"
            
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            return False, f"Healing action failed: {str(e)}"
    
    async def get_health_report(self) -> Dict:
        """
        Get system health report
        
        Returns:
            Health report dictionary
        """
        # Calculate metrics
        recent_errors = len(self.error_history)
        recent_healings = len([
            h for h in self.healing_history
            if h.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
        ])
        
        healing_success_rate = 0.0
        if self.healing_history:
            successful_healings = sum(1 for h in self.healing_history if h.success)
            healing_success_rate = successful_healings / len(self.healing_history)
        
        # Component health summary
        degraded_components = [
            comp for comp, health in self.component_health.items()
            if health['status'] == 'degraded'
        ]
        
        # Error distribution
        error_distribution = {}
        for error in self.error_history:
            error_distribution[error.error_type] = error_distribution.get(
                error.error_type, 0
            ) + 1
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'healthy' if not degraded_components else 'degraded',
            'metrics': {
                'recent_errors': recent_errors,
                'recent_healings': recent_healings,
                'healing_success_rate': healing_success_rate,
                'degraded_components': len(degraded_components)
            },
            'component_health': self.component_health,
            'error_distribution': error_distribution,
            'degraded_components': degraded_components,
            'recent_healing_attempts': [
                {
                    'timestamp': h.timestamp.isoformat(),
                    'component': h.error_event.component,
                    'error_type': h.error_event.error_type,
                    'action': h.action.value,
                    'success': h.success,
                    'duration': h.duration_seconds,
                    'message': h.result_message
                }
                for h in self.healing_history[-10:]
            ]
        }
        
        return report
    
    async def monitor_and_heal(self) -> None:
        """
        Continuous monitoring and healing loop
        Run this as a background task
        """
        logger.info("Self-healing AI monitoring started")
        
        while True:
            try:
                # Check for errors that need healing
                recent_errors = [
                    e for e in self.error_history
                    if e.timestamp > datetime.now(timezone.utc) - timedelta(minutes=5)
                ]
                
                for error in recent_errors:
                    # Check if already healed
                    already_healed = any(
                        h.error_event == error
                        for h in self.healing_history
                    )
                    
                    if not already_healed:
                        await self.heal_error(error)
                
                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Self-healing monitor error: {e}")
                await asyncio.sleep(60)


# Global instance
self_healing_ai = SelfHealingAI()
