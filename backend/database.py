"""
Database module - Normalized contract for MongoDB access.

This module provides a stable, consistent interface to MongoDB collections
and connection management. All imports should use:
    import database
    
    # Then access collections via:
    database.users_collection
    database.bots_collection
    # etc.

Exported globals:
- client: AsyncIOMotorClient instance (None until connect() called)
- db: Database instance (None until connect() called)
- All collection handles (users_collection, bots_collection, etc.)

Exported functions:
- get_database(): Returns the database instance
- async connect(): Initialize database connection (idempotent)
- async connect_db(): Alias for connect()
- async close_db(): Clean shutdown of database client
- setup_collections(): Initialize all collection globals
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent

# Load environment variables from `.env` if present.
load_dotenv(ROOT_DIR / '.env')

# Determine Mongo connection URI.  Prefer `MONGO_URI` (documented in .env.example) and
# fall back to the legacy `MONGO_URL` used in older deployments.  Default to a local
# instance if neither is provided to ensure the application boots in development.
mongo_url = os.environ.get('MONGO_URI') or os.environ.get('MONGO_URL', 'mongodb://localhost:27017')

# Determine the database name.  Prefer `MONGO_DB_NAME` (documented in .env.example) and
# fall back to the legacy `DB_NAME`.  Default to `amarktai_trading` if neither is set.
db_name = os.environ.get('MONGO_DB_NAME') or os.environ.get('DB_NAME', 'amarktai_trading')

# Global database client and database handle (initialized lazily by connect())
client = None
db = None
_connected = False

# =============================================================================
# COLLECTION GLOBALS
# All collections used anywhere in the codebase MUST be defined here.
# Initialize to None, then call setup_collections() to assign actual collection handles.
# =============================================================================

# Core Collections
users_collection = None
api_keys_collection = None
bots_collection = None
trades_collection = None
alerts_collection = None
chat_messages_collection = None
system_modes_collection = None

# Learning & Data Collections
learning_data_collection = None
learning_logs_collection = None

# Audit & Tracking Collections
audit_log_collection = None
audit_logs_collection = None  # Backward compatibility alias
audit_logs = None  # Backward compatibility alias
autopilot_actions_collection = None
rogue_detections_collection = None

# Financial Tracking Collections
wallets_collection = None
wallet_balances_collection = None
ledger_collection = None
profits_collection = None

# Additional collections that may be used in routes or engines
# (Add any missing collections here to prevent ImportErrors)
orders_collection = None
positions_collection = None
balance_snapshots_collection = None
performance_metrics_collection = None

# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def get_database():
    """
    Get the database instance.
    
    Returns:
        Database: The MongoDB database handle (may be None if not connected)
    """
    return db


async def connect():
    """
    Initialize database connection (idempotent).
    
    This function can be called multiple times safely.
    It will set up the client, database handle, and all collection globals.
    """
    global client, db, _connected
    
    if _connected and client is not None:
        logger.info("✅ Database already connected")
        return
    
    try:
        # Create client and database handle
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        _connected = True
        logger.info(f"✅ Database connected: {db_name} at {mongo_url[:30]}...")
        
        # Setup collections
        setup_collections()
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        client = None
        db = None
        _connected = False
        raise


async def connect_db():
    """
    Alias for connect() - for backwards compatibility.
    """
    await connect()


async def close_db():
    """
    Close database connection cleanly.
    
    This function should be called during application shutdown to
    ensure all connections are properly closed.
    """
    try:
        if client:
            client.close()
            logger.info("✅ Database connection closed")
    except Exception as e:
        logger.warning(f"⚠️  Error closing database: {e}")


def setup_collections():
    """
    Initialize all collection globals.
    
    This function assigns actual collection handles to all global collection variables.
    Call this after database is connected.
    """
    global users_collection, api_keys_collection, bots_collection, trades_collection
    global alerts_collection, chat_messages_collection, system_modes_collection
    global learning_data_collection, learning_logs_collection
    global audit_log_collection, audit_logs_collection, audit_logs, autopilot_actions_collection, rogue_detections_collection
    global wallets_collection, wallet_balances_collection, ledger_collection, profits_collection
    global orders_collection, positions_collection, balance_snapshots_collection, performance_metrics_collection
    
    if db is None:
        logger.warning("⚠️  Cannot setup collections - database not connected")
        return
    
    # Core Collections
    users_collection = db.users
    api_keys_collection = db.api_keys
    bots_collection = db.bots
    trades_collection = db.trades
    alerts_collection = db.alerts
    chat_messages_collection = db.chat_messages
    system_modes_collection = db.system_modes
    
    # Learning & Data Collections
    learning_data_collection = db.learning_data
    learning_logs_collection = db.learning_logs
    
    # Audit & Tracking Collections
    audit_log_collection = db.audit_log
    audit_logs_collection = audit_log_collection  # Backward compatibility alias
    audit_logs = audit_log_collection  # Backward compatibility alias
    autopilot_actions_collection = db.autopilot_actions
    rogue_detections_collection = db.rogue_detections
    
    # Financial Tracking Collections
    wallets_collection = db.wallets
    wallet_balances_collection = db.wallet_balances
    ledger_collection = db.ledger
    profits_collection = db.profits
    
    # Additional collections
    orders_collection = db.orders
    positions_collection = db.positions
    balance_snapshots_collection = db.balance_snapshots
    performance_metrics_collection = db.performance_metrics
    
    logger.info("✅ All collection globals initialized")


# DO NOT call setup_collections() at import time - it will be called by connect()


# =============================================================================
# DATABASE INITIALIZATION (Indexes)
# =============================================================================

async def init_db():
    """Initialize database indexes"""
    try:
        # User indexes
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("id", unique=True)
        
        # API Keys indexes
        await api_keys_collection.create_index(["user_id", "provider"])
        
        # Bots indexes
        await bots_collection.create_index("user_id")
        await bots_collection.create_index("id", unique=True)
        await bots_collection.create_index("created_at")
        await bots_collection.create_index([("user_id", 1), ("mode", 1)])  # For promotion queries
        
        # Trades indexes
        await trades_collection.create_index("bot_id")
        await trades_collection.create_index("user_id")
        await trades_collection.create_index("timestamp")
        
        # Learning data indexes
        await learning_data_collection.create_index("user_id")
        await learning_data_collection.create_index("date")
        
        # Alerts indexes
        await alerts_collection.create_index("user_id")
        await alerts_collection.create_index("timestamp")
        
        # Audit log indexes
        await audit_log_collection.create_index("user_id")
        await audit_log_collection.create_index("timestamp")
        
        # Chat messages indexes
        await chat_messages_collection.create_index("user_id")
        await chat_messages_collection.create_index("timestamp")
        
        # System modes indexes
        await system_modes_collection.create_index("user_id", unique=True)
        
        # Phase 2 indexes
        await learning_logs_collection.create_index("user_id")
        await learning_logs_collection.create_index("timestamp")
        await learning_logs_collection.create_index("bot_id")
        
        await autopilot_actions_collection.create_index("user_id")
        await autopilot_actions_collection.create_index("timestamp")
        await autopilot_actions_collection.create_index("action_type")
        
        await rogue_detections_collection.create_index("user_id")
        await rogue_detections_collection.create_index("bot_id")
        await rogue_detections_collection.create_index("timestamp")
        
        logger.info("✅ Database indexes created")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        # Don't raise - indexes are nice to have but not critical for startup
