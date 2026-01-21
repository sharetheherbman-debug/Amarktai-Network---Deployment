"""
Training Pipeline for New Bots
Ensures new bots never start live without training
Enhanced with training run management and history tracking
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import os
import uuid

from auth import get_current_user
import database as db
from realtime_events import rt_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["Bot Training"])


# Training graduation criteria
MIN_TRADES = 20
MIN_RUNTIME_HOURS = 6
MIN_PNL_THRESHOLD = 0  # Must be profitable
MAX_DRAWDOWN_THRESHOLD = 0.25  # 25% max drawdown

# Live Training Bay - minimum hours before live trading allowed
LIVE_MIN_TRAINING_HOURS = int(os.getenv('LIVE_MIN_TRAINING_HOURS', '24'))


async def seed_bot_from_top_performers(bot_id: str, user_id: str) -> Dict:
    """Seed new bot with training profile from top 3 performing bots
    
    Args:
        bot_id: Bot ID to seed
        user_id: User ID
        
    Returns:
        Seeding result with source bot IDs
    """
    try:
        # Get top 3 performing bots for this user (paper or live, completed training)
        top_bots = await db.bots_collection.find(
            {
                "user_id": user_id,
                "training_complete": True,
                "total_profit": {"$gt": 0}
            },
            {"_id": 0}
        ).sort("total_profit", -1).limit(3).to_list(3)
        
        if not top_bots:
            # No top bots - use default conservative profile
            profile = {
                "risk_mode": "safe",
                "position_size_pct": 0.20,  # 20% per trade
                "stop_loss_pct": 0.15,  # 15% stop loss
                "take_profit_pct": 0.10,  # 10% take profit
                "max_daily_trades": 10,
                "seeded_from": "default_conservative"
            }
        else:
            # Average parameters from top bots
            avg_position_size = sum(b.get('position_size_pct', 0.25) for b in top_bots) / len(top_bots)
            avg_stop_loss = sum(b.get('stop_loss_pct', 0.15) for b in top_bots) / len(top_bots)
            
            profile = {
                "risk_mode": top_bots[0].get('risk_mode', 'balanced'),
                "position_size_pct": round(avg_position_size, 3),
                "stop_loss_pct": round(avg_stop_loss, 3),
                "take_profit_pct": 0.10,
                "max_daily_trades": 15,
                "seeded_from": [b.get('id') for b in top_bots]
            }
        
        # Update bot with training profile
        await db.bots_collection.update_one(
            {"id": bot_id},
            {"$set": {
                "training_profile": profile,
                "training_seeded_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Bot {bot_id} seeded with training profile from {len(top_bots)} top bots")
        return {"success": True, "profile": profile, "source_count": len(top_bots)}
        
    except Exception as e:
        logger.error(f"Bot seeding error: {e}")
        return {"success": False, "error": str(e)}


async def evaluate_training(bot_id: str) -> Dict:
    """Evaluate if bot has graduated from training
    
    Criteria:
    - min_trades >= 20
    - min_runtime_hours >= 6
    - net_pnl > 0
    - max_drawdown <= 25%
    
    Args:
        bot_id: Bot ID to evaluate
        
    Returns:
        Evaluation result with pass/fail and reason
    """
    try:
        bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
        if not bot:
            return {"passed": False, "reason": "Bot not found"}
        
        # Check trade count
        trades_count = bot.get('trades_count', 0)
        if trades_count < MIN_TRADES:
            return {
                "passed": False,
                "reason": f"Insufficient trades: {trades_count}/{MIN_TRADES}",
                "suggestion": "Continue paper trading to accumulate more trade history"
            }
        
        # Check runtime
        started_at = bot.get('started_at') or bot.get('created_at')
        if started_at:
            started_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            runtime_hours = (datetime.now(timezone.utc) - started_dt).total_seconds() / 3600
            if runtime_hours < MIN_RUNTIME_HOURS:
                return {
                    "passed": False,
                    "reason": f"Insufficient runtime: {runtime_hours:.1f}h / {MIN_RUNTIME_HOURS}h",
                    "suggestion": "Let bot trade for longer to assess performance"
                }
        
        # Check PnL
        net_pnl = bot.get('total_profit', 0)
        if net_pnl <= MIN_PNL_THRESHOLD:
            return {
                "passed": False,
                "reason": f"Not profitable: R{net_pnl:.2f}",
                "suggestion": "Bot must be profitable before going live. Review strategy."
            }
        
        # Check drawdown
        max_drawdown = bot.get('max_drawdown', 0)
        if max_drawdown > MAX_DRAWDOWN_THRESHOLD:
            return {
                "passed": False,
                "reason": f"Excessive drawdown: {max_drawdown*100:.1f}% > {MAX_DRAWDOWN_THRESHOLD*100:.1f}%",
                "suggestion": "Reduce risk or improve strategy to lower drawdown"
            }
        
        # All checks passed!
        return {
            "passed": True,
            "reason": "Training complete - all criteria met",
            "stats": {
                "trades_count": trades_count,
                "runtime_hours": runtime_hours if started_at else 0,
                "net_pnl": net_pnl,
                "max_drawdown": max_drawdown
            }
        }
        
    except Exception as e:
        logger.error(f"Training evaluation error: {e}")
        return {"passed": False, "reason": f"Evaluation error: {str(e)}"}


@router.get("/queue")
async def get_training_queue(user_id: str = Depends(get_current_user)):
    """Get all bots in training for current user
    
    Returns bots with training state and progress
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        List of bots in training with evaluation status
    """
    try:
        # Get all bots in training or training_failed state
        training_bots = await db.bots_collection.find(
            {
                "user_id": user_id,
                "$or": [
                    {"status": "training"},
                    {"training_in_progress": True},
                    {"status": "training_failed"}
                ]
            },
            {"_id": 0}
        ).to_list(1000)
        
        # Evaluate each bot
        enriched_bots = []
        for bot in training_bots:
            evaluation = await evaluate_training(bot.get('id'))
            
            enriched_bot = {
                "id": bot.get('id'),
                "name": bot.get('name'),
                "exchange": bot.get('exchange'),
                "status": bot.get('status'),
                "training_state": "training" if bot.get('status') == 'training' else "training_failed",
                "trades_count": bot.get('trades_count', 0),
                "total_profit": bot.get('total_profit', 0),
                "max_drawdown": bot.get('max_drawdown', 0),
                "started_at": bot.get('started_at') or bot.get('created_at'),
                "evaluation": evaluation
            }
            enriched_bots.append(enriched_bot)
        
        return {
            "success": True,
            "training_bots": enriched_bots,
            "total": len(enriched_bots),
            "ready_for_promotion": len([b for b in enriched_bots if b['evaluation'].get('passed')])
        }
        
    except Exception as e:
        logger.error(f"Get training queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/promote")
async def promote_bot_from_training(
    bot_id: str,
    data: Optional[Dict] = None,
    user_id: str = Depends(get_current_user)
):
    """Promote bot from training to active (paused_ready state)
    
    Requires training graduation criteria to be met
    Bot moves to paused_ready state (manual activate required)
    
    Args:
        bot_id: Bot ID to promote
        data: Optional data (mode: 'paper' or 'live')
        user_id: Current user ID from auth
        
    Returns:
        Promotion result
    """
    try:
        # Verify bot belongs to user
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Evaluate training
        evaluation = await evaluate_training(bot_id)
        if not evaluation.get('passed'):
            return {
                "success": False,
                "message": "Bot has not passed training",
                "reason": evaluation.get('reason'),
                "suggestion": evaluation.get('suggestion')
            }
        
        # Determine target mode
        if data is None:
            data = {}
        target_mode = data.get('mode', bot.get('trading_mode', 'paper'))
        
        # Promote to paused_ready state (requires manual activation)
        promoted_at = datetime.now(timezone.utc).isoformat()
        
        await db.bots_collection.update_one(
            {"id": bot_id},
            {"$set": {
                "status": "paused",
                "training_complete": True,
                "training_completed_at": promoted_at,
                "paused_at": promoted_at,
                "pause_reason": "Training complete - ready for manual activation",
                "paused_by_system": True,
                "training_in_progress": False,
                "trading_mode": target_mode
            }}
        )
        
        # Get updated bot
        updated_bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Emit realtime event
        await rt_events.training_completed(user_id, updated_bot)
        
        logger.info(f"✅ Bot {bot['name']} promoted from training to paused_ready")
        
        return {
            "success": True,
            "message": f"Bot '{bot['name']}' training complete - ready for activation",
            "bot": updated_bot,
            "evaluation": evaluation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Promote bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/fail")
async def fail_training(
    bot_id: str,
    data: Dict,
    user_id: str = Depends(get_current_user)
):
    """Mark bot training as failed with reason
    
    Admin/system endpoint to mark training as failed
    
    Args:
        bot_id: Bot ID
        data: {reason: str, suggestion: str}
        user_id: Current user ID from auth
        
    Returns:
        Updated bot status
    """
    try:
        # Verify bot belongs to user
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        reason = data.get('reason', 'Training criteria not met')
        suggestion = data.get('suggestion', 'Review bot configuration and retry')
        
        await db.bots_collection.update_one(
            {"id": bot_id},
            {"$set": {
                "status": "training_failed",
                "training_failed": True,
                "training_failed_at": datetime.now(timezone.utc).isoformat(),
                "training_failed_reason": reason,
                "training_failed_suggestion": suggestion,
                "training_in_progress": False
            }}
        )
        
        # Get updated bot
        updated_bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Emit realtime event
        await rt_events.training_failed(user_id, updated_bot)
        
        logger.warning(f"Bot {bot['name']} training failed: {reason}")
        
        return {
            "success": True,
            "message": f"Bot training marked as failed",
            "bot": updated_bot,
            "reason": reason,
            "suggestion": suggestion
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fail training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-bay")
async def get_live_training_bay(user_id: str = Depends(get_current_user)):
    """Get all bots in Live Training Bay quarantine
    
    Shows bots that are new/spawned in LIVE mode and must wait >= 24h before trading
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        List of bots in quarantine with time remaining
    """
    try:
        from mode_manager import mode_manager
        
        # Check if user is in live mode
        system_mode = await mode_manager.get_system_mode(user_id)
        is_live_mode = system_mode.get('liveTrading', False)
        
        if not is_live_mode:
            return {
                "success": True,
                "live_mode_active": False,
                "quarantine_bots": [],
                "total": 0,
                "message": "Live mode not active - no training bay quarantine"
            }
        
        # Get all bots in live_training_bay status
        quarantine_bots = await db.bots_collection.find(
            {
                "user_id": user_id,
                "trading_mode": "live",
                "$or": [
                    {"status": "live_training_bay"},
                    {"in_live_training_bay": True}
                ]
            },
            {"_id": 0}
        ).to_list(1000)
        
        # Enrich with time remaining
        now = datetime.now(timezone.utc)
        enriched_bots = []
        
        for bot in quarantine_bots:
            # Get creation or spawn time
            created_at = bot.get('created_at') or bot.get('spawned_at')
            if created_at:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_dt = created_at
                
                # Ensure timezone-aware
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                
                hours_elapsed = (now - created_dt).total_seconds() / 3600
                hours_remaining = max(0, LIVE_MIN_TRAINING_HOURS - hours_elapsed)
                eligible = hours_elapsed >= LIVE_MIN_TRAINING_HOURS
            else:
                hours_elapsed = 0
                hours_remaining = LIVE_MIN_TRAINING_HOURS
                eligible = False
            
            enriched_bot = {
                "id": bot.get('id'),
                "name": bot.get('name'),
                "exchange": bot.get('exchange'),
                "created_at": created_at,
                "hours_elapsed": round(hours_elapsed, 1),
                "hours_remaining": round(hours_remaining, 1),
                "eligible_for_promotion": eligible,
                "total_profit": bot.get('total_profit', 0),
                "trades_count": bot.get('trades_count', 0)
            }
            enriched_bots.append(enriched_bot)
        
        # Sort by hours_remaining (ascending - closest to promotion first)
        enriched_bots.sort(key=lambda x: x['hours_remaining'])
        
        return {
            "success": True,
            "live_mode_active": True,
            "quarantine_bots": enriched_bots,
            "total": len(enriched_bots),
            "ready_for_promotion": len([b for b in enriched_bots if b['eligible_for_promotion']]),
            "min_training_hours": LIVE_MIN_TRAINING_HOURS
        }
        
    except Exception as e:
        logger.error(f"Get live training bay error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_training_history(user_id: str = Depends(get_current_user)):
    """Get training history for user's bots
    
    Note: For optimal performance, ensure a compound index exists on
    learning_logs_collection: (user_id, type, created_at)
    
    Args:
        user_id: Current user ID from auth
        
    Returns:
        Training history with runs and their results
    """
    try:
        # Query training runs from database
        # Recommended index: db.learning_logs_collection.create_index([("user_id", 1), ("type", 1), ("created_at", -1)])
        training_runs = await db.learning_logs_collection.find({
            "user_id": user_id,
            "type": "training_run"
        }).sort("created_at", -1).limit(50).to_list(50)
        
        history = []
        for run in training_runs:
            history.append({
                "run_id": run.get("run_id"),
                "bot_id": run.get("bot_id"),
                "bot_name": run.get("bot_name"),
                "exchange": run.get("exchange"),
                "mode": run.get("mode", "paper"),
                "duration": run.get("duration_hours", 0),
                "final_pnl": run.get("final_pnl_pct", 0.0),
                "status": run.get("status", "completed"),
                "started_at": run.get("started_at"),
                "completed_at": run.get("completed_at"),
                "trades_executed": run.get("trades_executed", 0)
            })
        
        return {
            "success": True,
            "history": history,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Get training history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_training(
    bot_id: str,
    duration_hours: Optional[int] = 1,
    user_id: str = Depends(get_current_user)
):
    """Start training run for a bot
    
    Args:
        bot_id: Bot ID to train
        duration_hours: Training duration in hours
        user_id: Current user ID from auth
        
    Returns:
        Training run information
    """
    try:
        # Verify bot exists and belongs to user
        bot = await db.bots_collection.find_one({
            "id": bot_id,
            "user_id": user_id
        })
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Create training run
        run_id = str(uuid.uuid4())
        training_run = {
            "run_id": run_id,
            "bot_id": bot_id,
            "bot_name": bot.get("name"),
            "user_id": user_id,
            "exchange": bot.get("exchange"),
            "mode": "training",
            "type": "training_run",
            "duration_hours": duration_hours,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "initial_capital": bot.get("current_capital", 1000.0),
            "trades_executed": 0
        }
        
        await db.learning_logs_collection.insert_one(training_run)
        
        # Update bot status to training
        await db.bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "training",
                    "current_training_run": run_id,
                    "training_in_progress": True
                }
            }
        )
        
        logger.info(f"Started training run {run_id[:8]} for bot {bot_id[:8]}")
        
        return {
            "success": True,
            "run_id": run_id,
            "message": f"Training started for {duration_hours} hours"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/status")
async def get_training_status(
    run_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get status of a training run
    
    Args:
        run_id: Training run ID
        user_id: Current user ID from auth
        
    Returns:
        Training run status and progress
    """
    try:
        # Get training run
        training_run = await db.learning_logs_collection.find_one({
            "run_id": run_id,
            "user_id": user_id
        })
        
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")
        
        # Calculate progress
        started_at = datetime.fromisoformat(training_run["started_at"].replace('Z', '+00:00'))
        duration_hours = training_run.get("duration_hours", 1)
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds() / 3600
        progress = min(100, (elapsed / duration_hours) * 100)
        
        # Get current bot stats
        bot = await db.bots_collection.find_one({"id": training_run["bot_id"]})
        current_pnl = 0.0
        trades_executed = 0
        
        if bot:
            initial_capital = training_run.get("initial_capital", 1000.0)
            current_capital = bot.get("current_capital", initial_capital)
            current_pnl = ((current_capital - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0
            trades_executed = bot.get("trades_count", 0)
        
        return {
            "success": True,
            "run_id": run_id,
            "status": training_run.get("status"),
            "progress_pct": round(progress, 1),
            "elapsed_hours": round(elapsed, 2),
            "total_hours": duration_hours,
            "current_pnl": round(current_pnl, 2),
            "trades_executed": trades_executed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get training status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{run_id}/stop")
async def stop_training(
    run_id: str,
    user_id: str = Depends(get_current_user)
):
    """Stop a training run
    
    Args:
        run_id: Training run ID
        user_id: Current user ID from auth
        
    Returns:
        Stop confirmation
    """
    try:
        # Get training run
        training_run = await db.learning_logs_collection.find_one({
            "run_id": run_id,
            "user_id": user_id
        })
        
        if not training_run:
            raise HTTPException(status_code=404, detail="Training run not found")
        
        # Get final bot stats
        bot = await db.bots_collection.find_one({"id": training_run["bot_id"]})
        final_pnl_pct = 0.0
        trades_executed = 0
        
        if bot:
            initial_capital = training_run.get("initial_capital", 1000.0)
            current_capital = bot.get("current_capital", initial_capital)
            final_pnl_pct = ((current_capital - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0
            trades_executed = bot.get("trades_count", 0)
        
        # Update training run status
        await db.learning_logs_collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": "stopped",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "final_pnl_pct": final_pnl_pct,
                    "trades_executed": trades_executed
                }
            }
        )
        
        # Update bot status back to paused
        bot_id = training_run["bot_id"]
        await db.bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "paused",
                    "training_in_progress": False
                },
                "$unset": {
                    "current_training_run": ""
                }
            }
        )
        
        logger.info(f"Stopped training run {run_id[:8]} - Final P&L: {final_pnl_pct:.2f}%")
        
        return {
            "success": True,
            "message": "Training stopped",
            "final_pnl_pct": round(final_pnl_pct, 2),
            "trades_executed": trades_executed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stop training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

