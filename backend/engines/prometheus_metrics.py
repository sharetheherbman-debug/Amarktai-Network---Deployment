"""
Prometheus Metrics Integration
Exports Golden Signals for observability: Latency, Traffic, Errors, Saturation
Enables Grafana dashboards for real-time system monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
import time
from typing import Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus metrics exporter for trading system
    Tracks: Latency, Traffic, Errors, Saturation (Golden Signals)
    """
    
    def __init__(self):
        """Initialize Prometheus metrics collectors"""
        self.registry = CollectorRegistry()
        
        # Golden Signal 1: Latency (tick-to-trade)
        self.trade_latency = Histogram(
            'amarktai_trade_latency_seconds',
            'Time from market data to trade execution',
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.signal_generation_latency = Histogram(
            'amarktai_signal_generation_seconds',
            'Time to generate alpha fusion signal',
            ['signal_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
            registry=self.registry
        )
        
        # Golden Signal 2: Traffic
        self.trades_total = Counter(
            'amarktai_trades_total',
            'Total number of trades executed',
            ['exchange', 'symbol', 'side', 'mode'],
            registry=self.registry
        )
        
        self.api_requests_total = Counter(
            'amarktai_api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        self.signals_generated_total = Counter(
            'amarktai_signals_generated_total',
            'Total trading signals generated',
            ['signal_type', 'recommendation'],
            registry=self.registry
        )
        
        # Golden Signal 3: Errors
        self.errors_total = Counter(
            'amarktai_errors_total',
            'Total errors by component',
            ['component', 'error_type'],
            registry=self.registry
        )
        
        self.healing_attempts_total = Counter(
            'amarktai_healing_attempts_total',
            'Self-healing attempts',
            ['component', 'action', 'success'],
            registry=self.registry
        )
        
        # Golden Signal 4: Saturation
        self.active_bots = Gauge(
            'amarktai_active_bots',
            'Number of active trading bots',
            ['mode'],
            registry=self.registry
        )
        
        self.capital_utilization = Gauge(
            'amarktai_capital_utilization_ratio',
            'Capital utilization (deployed / total)',
            registry=self.registry
        )
        
        self.api_rate_limit_remaining = Gauge(
            'amarktai_api_rate_limit_remaining',
            'Remaining API rate limit',
            ['exchange'],
            registry=self.registry
        )
        
        # Trading Performance Metrics
        self.position_pnl = Gauge(
            'amarktai_position_pnl_dollars',
            'Current position P&L in dollars',
            ['bot_id', 'symbol'],
            registry=self.registry
        )
        
        self.win_rate = Gauge(
            'amarktai_win_rate',
            'Trading win rate',
            ['bot_id'],
            registry=self.registry
        )
        
        self.drawdown = Gauge(
            'amarktai_drawdown_percent',
            'Current drawdown percentage',
            ['bot_id'],
            registry=self.registry
        )
        
        # System Health Metrics
        self.component_health = Gauge(
            'amarktai_component_health',
            'Component health status (1=healthy, 0=degraded)',
            ['component'],
            registry=self.registry
        )
        
        self.regime_confidence = Gauge(
            'amarktai_regime_confidence',
            'Market regime detection confidence',
            ['symbol', 'regime'],
            registry=self.registry
        )
        
        # System Info
        self.system_info = Info(
            'amarktai_system',
            'System information',
            registry=self.registry
        )
        
        self.system_info.info({
            'version': '3.0.0',
            'architecture': 'multi-agent',
            'features': 'regime-adaptive,ofi,whale-tracking,alpha-fusion'
        })
        
        logger.info("Prometheus metrics initialized")
    
    # Latency Tracking
    def record_trade_latency(self, latency_seconds: float):
        """Record tick-to-trade latency"""
        self.trade_latency.observe(latency_seconds)
    
    def record_signal_latency(self, signal_type: str, latency_seconds: float):
        """Record signal generation latency"""
        self.signal_generation_latency.labels(signal_type=signal_type).observe(latency_seconds)
    
    # Traffic Tracking
    def record_trade(self, exchange: str, symbol: str, side: str, mode: str):
        """Record trade execution"""
        self.trades_total.labels(
            exchange=exchange,
            symbol=symbol,
            side=side,
            mode=mode
        ).inc()
    
    def record_api_request(self, endpoint: str, method: str, status: int):
        """Record API request"""
        self.api_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=str(status)
        ).inc()
    
    def record_signal(self, signal_type: str, recommendation: str):
        """Record signal generation"""
        self.signals_generated_total.labels(
            signal_type=signal_type,
            recommendation=recommendation
        ).inc()
    
    # Error Tracking
    def record_error(self, component: str, error_type: str):
        """Record error occurrence"""
        self.errors_total.labels(
            component=component,
            error_type=error_type
        ).inc()
    
    def record_healing(self, component: str, action: str, success: bool):
        """Record self-healing attempt"""
        self.healing_attempts_total.labels(
            component=component,
            action=action,
            success=str(success)
        ).inc()
    
    # Saturation Metrics
    def update_active_bots(self, mode: str, count: int):
        """Update active bot count"""
        self.active_bots.labels(mode=mode).set(count)
    
    def update_capital_utilization(self, ratio: float):
        """Update capital utilization ratio"""
        self.capital_utilization.set(ratio)
    
    def update_rate_limit(self, exchange: str, remaining: int):
        """Update API rate limit remaining"""
        self.api_rate_limit_remaining.labels(exchange=exchange).set(remaining)
    
    # Performance Metrics
    def update_position_pnl(self, bot_id: str, symbol: str, pnl: float):
        """Update position P&L"""
        self.position_pnl.labels(bot_id=bot_id, symbol=symbol).set(pnl)
    
    def update_win_rate(self, bot_id: str, win_rate: float):
        """Update win rate"""
        self.win_rate.labels(bot_id=bot_id).set(win_rate)
    
    def update_drawdown(self, bot_id: str, drawdown_pct: float):
        """Update drawdown"""
        self.drawdown.labels(bot_id=bot_id).set(drawdown_pct)
    
    # System Health
    def update_component_health(self, component: str, is_healthy: bool):
        """Update component health status"""
        self.component_health.labels(component=component).set(1 if is_healthy else 0)
    
    def update_regime_confidence(self, symbol: str, regime: str, confidence: float):
        """Update regime detection confidence"""
        self.regime_confidence.labels(symbol=symbol, regime=regime).set(confidence)
    
    # Export Metrics
    def export_metrics(self) -> tuple:
        """
        Export metrics in Prometheus format
        
        Returns:
            (content, content_type) for HTTP response
        """
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
    
    def get_metrics_dict(self) -> Dict:
        """
        Get current metrics as dictionary
        
        Returns:
            Dictionary of current metric values
        """
        # This is a simplified version - in production, scrape from registry
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics_exported': True
        }


# Context managers for timing
class TradeLatencyTimer:
    """Context manager for measuring trade latency"""
    
    def __init__(self, metrics: PrometheusMetrics):
        self.metrics = metrics
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        self.metrics.record_trade_latency(latency)


class SignalLatencyTimer:
    """Context manager for measuring signal generation latency"""
    
    def __init__(self, metrics: PrometheusMetrics, signal_type: str):
        self.metrics = metrics
        self.signal_type = signal_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        self.metrics.record_signal_latency(self.signal_type, latency)


# Global instance
prometheus_metrics = PrometheusMetrics()
