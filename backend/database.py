from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection string from environment variable
MONGO_URI = os.getenv("MONGO_URI")

# Global database and collection variables - initialized to None
client = None
db = None

# Collection globals
users_collection = None
wallets_collection = None
transactions_collection = None
validators_collection = None
stake_pools_collection = None
blocks_collection = None
wallet_balances_collection = None
capital_injections_collection = None

# Aliases for backward compatibility
wallet_balances = None
capital_injections = None


async def connect_db():
    """Connect to MongoDB and initialize database"""
    global client, db
    
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable is not set")
    
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.amarktai_network
    print("Connected to MongoDB successfully")


async def setup_collections():
    """Initialize all collections and create indexes"""
    global users_collection, wallets_collection, transactions_collection
    global validators_collection, stake_pools_collection, blocks_collection
    global wallet_balances_collection, capital_injections_collection
    global wallet_balances, capital_injections
    
    if db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    
    # Initialize collections
    users_collection = db.users
    wallets_collection = db.wallets
    transactions_collection = db.transactions
    validators_collection = db.validators
    stake_pools_collection = db.stake_pools
    blocks_collection = db.blocks
    wallet_balances_collection = db.wallet_balances
    capital_injections_collection = db.capital_injections
    
    # Set up aliases for backward compatibility
    wallet_balances = wallet_balances_collection
    capital_injections = capital_injections_collection
    
    # Create indexes for users collection
    await users_collection.create_index("username", unique=True)
    await users_collection.create_index("email", unique=True)
    
    # Create indexes for wallets collection
    await wallets_collection.create_index("user_id")
    await wallets_collection.create_index("address", unique=True)
    
    # Create indexes for transactions collection
    await transactions_collection.create_index("from_address")
    await transactions_collection.create_index("to_address")
    await transactions_collection.create_index("timestamp")
    await transactions_collection.create_index("block_number")
    
    # Create indexes for validators collection
    await validators_collection.create_index("address", unique=True)
    await validators_collection.create_index("stake")
    
    # Create indexes for stake_pools collection
    await stake_pools_collection.create_index("pool_id", unique=True)
    await stake_pools_collection.create_index("validator_address")
    
    # Create indexes for blocks collection
    await blocks_collection.create_index("block_number", unique=True)
    await blocks_collection.create_index("timestamp")
    await blocks_collection.create_index("validator_address")
    
    # Create indexes for wallet_balances collection
    await wallet_balances_collection.create_index("wallet_address", unique=True)
    await wallet_balances_collection.create_index("balance")
    await wallet_balances_collection.create_index("last_updated")
    
    # Create indexes for capital_injections collection
    await capital_injections_collection.create_index("injection_id", unique=True)
    await capital_injections_collection.create_index("wallet_address")
    await capital_injections_collection.create_index("timestamp")
    await capital_injections_collection.create_index("amount")
    
    print("Collections initialized and indexes created successfully")


async def close_db():
    """Close MongoDB connection"""
    global client
    
    if client:
        client.close()
        print("MongoDB connection closed")


async def init_db():
    """Initialize database connection and setup collections"""
    await connect_db()
    await setup_collections()
