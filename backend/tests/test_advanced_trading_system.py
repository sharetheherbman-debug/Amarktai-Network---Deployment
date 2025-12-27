"""
Tests for Advanced Trading System Components
Tests: Regime Detection, OFI, Whale Monitoring, Sentiment Analysis, Alpha Fusion
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
import numpy as np

# Import modules to test
from engines.regime_detector import regime_detector, MarketRegime
from engines.order_flow_imbalance import ofi_calculator
from engines.on_chain_monitor import whale_monitor, WhaleActivityType
from engines.sentiment_analyzer import sentiment_analyzer, SentimentType
from engines.macro_news_monitor import macro_monitor, MacroEventType, RiskImpact
from engines.alpha_fusion_engine import alpha_fusion, SignalStrength


class TestRegimeDetector:
    """Test regime detection with HMM/GMM"""
    
    @pytest.mark.asyncio
    async def test_update_price_data(self):
        """Test price data update"""
        symbol = "BTC/USDT"
        await regime_detector.update_price_data(symbol, 50000.0, 100.0)
        
        assert symbol in regime_detector.price_history
        assert len(regime_detector.price_history[symbol]) == 1
        assert regime_detector.price_history[symbol][0]['price'] == 50000.0
    
    @pytest.mark.asyncio
    async def test_regime_detection_insufficient_data(self):
        """Test regime detection with insufficient data"""
        symbol = "TEST/USDT"
        
        # Add only a few data points
        for i in range(5):
            await regime_detector.update_price_data(symbol, 50000.0 + i * 10, 100.0)
        
        regime_state = await regime_detector.detect_regime(symbol)
        
        # Should return unknown regime with low confidence
        assert regime_state is not None
        assert regime_state.regime == MarketRegime.UNKNOWN
        assert regime_state.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_regime_detection_sufficient_data(self):
        """Test regime detection with sufficient data"""
        symbol = "BTC/USDT"
        
        # Simulate bullish trend
        base_price = 50000
        for i in range(100):
            price = base_price + i * 100  # Upward trend
            await regime_detector.update_price_data(symbol, price, 100.0)
        
        regime_state = await regime_detector.detect_regime(symbol)
        
        assert regime_state is not None
        assert regime_state.regime in [MarketRegime.BULLISH_CALM, MarketRegime.UNKNOWN]
        assert 0.0 <= regime_state.confidence <= 1.0
        assert regime_state.volatility >= 0
    
    @pytest.mark.asyncio
    async def test_trading_parameters(self):
        """Test adaptive trading parameters"""
        # Create mock regime state
        from engines.regime_detector import RegimeState
        
        regime_state = RegimeState(
            regime=MarketRegime.BULLISH_CALM,
            confidence=0.8,
            volatility=0.01,
            trend_strength=0.5,
            timestamp=datetime.now(timezone.utc),
            features={}
        )
        
        params = regime_detector.get_trading_parameters(regime_state)
        
        assert 'position_size_multiplier' in params
        assert 'stop_loss_pct' in params
        assert 'take_profit_pct' in params
        assert params['position_size_multiplier'] > 0
        assert params['stop_loss_pct'] > 0
        assert params['take_profit_pct'] > 0


class TestOrderFlowImbalance:
    """Test Order Flow Imbalance calculations"""
    
    @pytest.mark.asyncio
    async def test_add_snapshot(self):
        """Test adding order book snapshot"""
        symbol = "BTC/USDT"
        
        await ofi_calculator.add_snapshot(
            symbol=symbol,
            bid_price=50000.0,
            bid_qty=1.0,
            ask_price=50050.0,
            ask_qty=1.5
        )
        
        assert symbol in ofi_calculator.snapshots
        assert len(ofi_calculator.snapshots[symbol]) == 1
    
    @pytest.mark.asyncio
    async def test_ofi_calculation(self):
        """Test OFI calculation with multiple snapshots"""
        symbol = "ETH/USDT"
        
        # Add initial snapshot
        await ofi_calculator.add_snapshot(
            symbol=symbol,
            bid_price=3000.0,
            bid_qty=10.0,
            ask_price=3005.0,
            ask_qty=8.0
        )
        
        # Add second snapshot with price increase (buying pressure)
        await ofi_calculator.add_snapshot(
            symbol=symbol,
            bid_price=3002.0,
            bid_qty=12.0,
            ask_price=3007.0,
            ask_qty=7.0
        )
        
        # Should have calculated OFI
        assert len(ofi_calculator.ofi_history[symbol]) > 0
    
    @pytest.mark.asyncio
    async def test_ofi_signal_generation(self):
        """Test OFI signal generation"""
        symbol = "BTC/USDT"
        
        # Simulate market data
        await ofi_calculator.simulate_market_data(symbol, base_price=50000.0, n_ticks=50)
        
        signal = await ofi_calculator.get_signal(symbol)
        
        assert signal is not None
        assert signal.recommendation in ['buy', 'sell', 'neutral']
        assert -1.0 <= signal.signal_strength <= 1.0
        assert signal.ofi_value is not None
    
    @pytest.mark.asyncio
    async def test_ofi_predictive_features(self):
        """Test predictive feature extraction"""
        symbol = "ETH/USDT"
        
        # Simulate data
        await ofi_calculator.simulate_market_data(symbol, base_price=3000.0, n_ticks=30)
        
        features = await ofi_calculator.get_predictive_features(symbol)
        
        assert features is not None
        assert 'ofi_mean' in features
        assert 'ofi_std' in features
        assert 'ofi_trend' in features
        assert 'buy_pressure_ratio' in features


class TestWhaleMonitor:
    """Test on-chain whale activity monitoring"""
    
    @pytest.mark.asyncio
    async def test_add_transaction(self):
        """Test adding whale transaction"""
        tx = await whale_monitor.add_transaction(
            coin='BTC',
            amount=150.0,  # Large amount
            from_address='whale_address',
            to_address='1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s',  # Binance
            tx_hash='0x123'
        )
        
        assert tx is not None
        assert tx.coin == 'BTC'
        assert tx.activity_type == WhaleActivityType.EXCHANGE_INFLOW
        assert tx.exchange_name == 'binance'
    
    @pytest.mark.asyncio
    async def test_exchange_flows(self):
        """Test exchange flow calculation"""
        await whale_monitor.simulate_whale_activity(coin='BTC', n_transactions=20)
        
        flows = await whale_monitor.calculate_exchange_flows('BTC', hours=1)
        
        assert 'net_flow' in flows
        assert 'inflows' in flows
        assert 'outflows' in flows
        assert flows['transaction_count'] > 0
    
    @pytest.mark.asyncio
    async def test_whale_signal(self):
        """Test whale signal generation"""
        await whale_monitor.simulate_whale_activity(coin='ETH', n_transactions=30)
        
        signal = await whale_monitor.get_whale_signal('ETH')
        
        assert signal is not None
        assert signal.signal in ['bullish', 'bearish', 'neutral']
        assert 0.0 <= signal.strength <= 1.0
        assert len(signal.recent_transactions) > 0


class TestSentimentAnalyzer:
    """Test sentiment analysis"""
    
    @pytest.mark.asyncio
    async def test_keyword_sentiment(self):
        """Test keyword-based sentiment analysis"""
        bullish_text = "Bitcoin surges to all-time high with institutional adoption"
        bearish_text = "Crypto crash as regulation fears spread across markets"
        
        bullish_sentiment = await sentiment_analyzer.analyze_text(
            bullish_text,
            source='test',
            use_ai=False  # Use keyword-based only
        )
        
        bearish_sentiment = await sentiment_analyzer.analyze_text(
            bearish_text,
            source='test',
            use_ai=False
        )
        
        assert bullish_sentiment.score > 0
        assert bearish_sentiment.score < 0
        assert len(bullish_sentiment.keywords) > 0
    
    @pytest.mark.asyncio
    async def test_sentiment_classification(self):
        """Test sentiment type classification"""
        very_bullish = "Massive breakout, ATH, moon, institutional adoption breakthrough"
        
        sentiment = await sentiment_analyzer.analyze_text(
            very_bullish,
            source='test',
            use_ai=False
        )
        
        assert sentiment.sentiment in [SentimentType.VERY_BULLISH, SentimentType.BULLISH]
    
    @pytest.mark.asyncio
    async def test_aggregated_sentiment(self):
        """Test aggregated sentiment for coin"""
        # Analyze sentiment (will use simulated news)
        agg_sentiment = await sentiment_analyzer.analyze_coin_sentiment('BTC', hours=24)
        
        assert agg_sentiment is not None
        assert agg_sentiment.coin == 'BTC'
        assert agg_sentiment.recommendation in ['buy', 'sell', 'hold']
        assert 0.0 <= agg_sentiment.confidence <= 1.0
        assert agg_sentiment.article_count > 0


class TestMacroMonitor:
    """Test macro news monitoring"""
    
    @pytest.mark.asyncio
    async def test_add_event(self):
        """Test adding macro event"""
        event = await macro_monitor.add_event(
            event_type=MacroEventType.FED_RATE_DECISION,
            title="Fed Holds Rates Steady",
            description="Federal Reserve maintains interest rates",
            actual_value=5.25,
            expected_value=5.25,
            previous_value=5.00
        )
        
        assert event is not None
        assert event.event_type == MacroEventType.FED_RATE_DECISION
        assert event.impact in [RiskImpact.RISK_ON, RiskImpact.RISK_OFF, RiskImpact.NEUTRAL]
    
    @pytest.mark.asyncio
    async def test_macro_signal(self):
        """Test macro signal generation"""
        # Add some events
        await macro_monitor.simulate_events(n_events=10)
        
        signal = await macro_monitor.get_macro_signal()
        
        assert signal is not None
        assert signal.signal in ['increase_risk', 'decrease_risk', 'maintain']
        assert 0.5 <= signal.risk_multiplier <= 1.5
        assert len(signal.reason) > 0
    
    @pytest.mark.asyncio
    async def test_risk_multiplier_update(self):
        """Test risk multiplier calculation"""
        # Add positive event
        await macro_monitor.add_event(
            event_type=MacroEventType.CPI_RELEASE,
            title="CPI Below Expectations",
            description="Inflation lower than expected",
            actual_value=3.0,
            expected_value=3.5,
            previous_value=3.7
        )
        
        assert 0.5 <= macro_monitor.current_risk_multiplier <= 1.5


class TestAlphaFusion:
    """Test multi-modal alpha fusion"""
    
    @pytest.mark.asyncio
    async def test_fuse_signals(self):
        """Test signal fusion for a symbol"""
        symbol = "BTC/USDT"
        
        # Generate some test data for each component
        # Regime detection
        for i in range(50):
            await regime_detector.update_price_data(symbol, 50000.0 + i * 100, 100.0)
        
        # OFI data
        await ofi_calculator.simulate_market_data(symbol, base_price=50000.0, n_ticks=30)
        
        # Whale activity
        await whale_monitor.simulate_whale_activity(coin='BTC', n_transactions=20)
        
        # Macro events
        await macro_monitor.simulate_events(n_events=5)
        
        # Fuse signals
        fused = await alpha_fusion.fuse_signals(symbol)
        
        assert fused is not None
        assert fused.symbol == symbol
        assert isinstance(fused.signal, SignalStrength)
        assert 0.0 <= fused.confidence <= 1.0
        assert -1.0 <= fused.score <= 1.0
        assert fused.position_size_multiplier > 0
        assert len(fused.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_component_weights(self):
        """Test that component weights sum to 1.0"""
        weights = alpha_fusion.weights
        total_weight = sum(weights.values())
        
        assert abs(total_weight - 1.0) < 0.001  # Allow small floating point error
    
    @pytest.mark.asyncio
    async def test_portfolio_signals(self):
        """Test getting signals for multiple symbols"""
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        # Generate test data
        for symbol in symbols:
            for i in range(30):
                await regime_detector.update_price_data(symbol, 50000.0 + i * 100, 100.0)
            await ofi_calculator.simulate_market_data(symbol, n_ticks=20)
        
        signals = await alpha_fusion.get_portfolio_signals(symbols)
        
        assert len(signals) > 0
        for symbol, signal in signals.items():
            assert signal.symbol == symbol
            assert isinstance(signal.signal, SignalStrength)
    
    @pytest.mark.asyncio
    async def test_signal_summary(self):
        """Test portfolio signal summary"""
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        # Generate test data
        for symbol in symbols:
            for i in range(30):
                await regime_detector.update_price_data(symbol, 50000.0, 100.0)
            await ofi_calculator.simulate_market_data(symbol, n_ticks=20)
        
        signals = await alpha_fusion.get_portfolio_signals(symbols)
        summary = alpha_fusion.get_summary(signals)
        
        assert 'total_symbols' in summary
        assert 'signal_distribution' in summary
        assert 'average_score' in summary
        assert 'average_confidence' in summary
        assert summary['total_symbols'] == len(signals)


class TestSelfHealingAI:
    """Test self-healing AI system"""
    
    @pytest.mark.asyncio
    async def test_report_error(self):
        """Test error reporting"""
        from engines.self_healing_ai import self_healing_ai
        
        try:
            raise ValueError("Test error for self-healing")
        except Exception as e:
            error_event = await self_healing_ai.report_error(
                error=e,
                component='test_component',
                context={'test': 'context'}
            )
        
        assert error_event is not None
        assert error_event.component == 'test_component'
        assert 'test_component' in self_healing_ai.component_health
    
    @pytest.mark.asyncio
    async def test_error_classification(self):
        """Test error classification"""
        from engines.self_healing_ai import self_healing_ai, ErrorSeverity
        
        timeout_error = Exception("Connection timeout occurred")
        error_event = await self_healing_ai.report_error(
            error=timeout_error,
            component='network'
        )
        
        assert error_event.error_type == 'connection_timeout'
        assert error_event.severity == ErrorSeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_heal_error(self):
        """Test error healing"""
        from engines.self_healing_ai import self_healing_ai
        
        # Report an error
        try:
            raise ConnectionError("API connection timeout")
        except Exception as e:
            error_event = await self_healing_ai.report_error(
                error=e,
                component='api_client'
            )
        
        # Attempt to heal
        healing_attempt = await self_healing_ai.heal_error(error_event)
        
        assert healing_attempt is not None
        assert isinstance(healing_attempt.success, bool)
        assert len(healing_attempt.result_message) > 0
    
    @pytest.mark.asyncio
    async def test_health_report(self):
        """Test health report generation"""
        from engines.self_healing_ai import self_healing_ai
        
        report = await self_healing_ai.get_health_report()
        
        assert 'overall_status' in report
        assert 'metrics' in report
        assert 'component_health' in report
        assert report['overall_status'] in ['healthy', 'degraded']


class TestIntegration:
    """Integration tests for the full system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_signal_generation(self):
        """Test complete signal generation pipeline"""
        symbol = "BTC/USDT"
        
        # 1. Update market regime
        for i in range(50):
            price = 50000.0 + np.sin(i / 10) * 1000  # Simulate price oscillation
            await regime_detector.update_price_data(symbol, price, 100.0)
        
        regime_state = await regime_detector.detect_regime(symbol)
        assert regime_state is not None
        
        # 2. Generate OFI signals
        await ofi_calculator.simulate_market_data(symbol, n_ticks=40)
        ofi_signal = await ofi_calculator.get_signal(symbol)
        assert ofi_signal is not None
        
        # 3. Simulate whale activity
        await whale_monitor.simulate_whale_activity(coin='BTC', n_transactions=15)
        whale_signal = await whale_monitor.get_whale_signal('BTC')
        assert whale_signal is not None
        
        # 4. Analyze sentiment
        sentiment = await sentiment_analyzer.analyze_coin_sentiment('BTC', hours=24)
        assert sentiment is not None
        
        # 5. Add macro events
        await macro_monitor.simulate_events(n_events=5)
        macro_signal = await macro_monitor.get_macro_signal()
        assert macro_signal is not None
        
        # 6. Fuse all signals
        fused_signal = await alpha_fusion.fuse_signals(symbol)
        
        assert fused_signal is not None
        assert fused_signal.regime_signal is not None
        assert fused_signal.ofi_signal is not None
        assert len(fused_signal.reasoning) > 0
        
        # Verify all components contributed
        assert 'regime' in fused_signal.component_scores
        assert 'ofi' in fused_signal.component_scores
        assert 'whale' in fused_signal.component_scores
        assert 'sentiment' in fused_signal.component_scores
        assert 'macro' in fused_signal.component_scores


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
