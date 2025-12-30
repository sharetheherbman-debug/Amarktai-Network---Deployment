"""
Database module for Amarktai Network.
Handles all database operations including user management, wallets, transactions, and capital injections.
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

class Database:
    """Database handler for Amarktai Network operations."""
    
    def __init__(self, db_path: str = "amarktai.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Wallets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wallet_address TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_wallet TEXT NOT NULL,
                to_wallet TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)
        
        # Capital injections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capital_injections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'system',
                notes TEXT,
                FOREIGN KEY (wallet_address) REFERENCES wallets (wallet_address)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # User Management Methods
    def create_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Create a new user account."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            
            user_id = cursor.lastrowid
            
            # Create wallet for user
            wallet_address = self._generate_wallet_address()
            cursor.execute(
                "INSERT INTO wallets (user_id, wallet_address, balance) VALUES (?, ?, ?)",
                (user_id, wallet_address, 0.0)
            )
            
            conn.commit()
            conn.close()
            
            return True, wallet_address
        except sqlite3.IntegrityError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user credentials."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
            (username, password_hash)
        )
        
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            conn.commit()
            
            # Get wallet info
            cursor.execute(
                "SELECT wallet_address, balance FROM wallets WHERE user_id = ?",
                (user['id'],)
            )
            wallet = cursor.fetchone()
            
            conn.close()
            
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'wallet_address': wallet['wallet_address'] if wallet else None,
                'balance': wallet['balance'] if wallet else 0.0
            }
        
        conn.close()
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute(
                "SELECT wallet_address, balance FROM wallets WHERE user_id = ?",
                (user_id,)
            )
            wallet = cursor.fetchone()
            
            conn.close()
            
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'created_at': user['created_at'],
                'last_login': user['last_login'],
                'wallet_address': wallet['wallet_address'] if wallet else None,
                'balance': wallet['balance'] if wallet else 0.0
            }
        
        conn.close()
        return None
    
    # Wallet Management Methods
    def get_wallet_balance(self, wallet_address: str) -> float:
        """Get balance for a wallet address."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT balance FROM wallets WHERE wallet_address = ?",
            (wallet_address,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result['balance'] if result else 0.0
    
    def get_all_wallet_balances(self) -> List[Dict]:
        """Get all wallet balances."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.wallet_address, w.balance, u.username, u.email
            FROM wallets w
            JOIN users u ON w.user_id = u.id
            ORDER BY w.balance DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    # Alias for get_all_wallet_balances
    def wallet_balances(self) -> List[Dict]:
        """Alias for get_all_wallet_balances."""
        return self.get_all_wallet_balances()
    
    def update_wallet_balance(self, wallet_address: str, new_balance: float) -> bool:
        """Update wallet balance."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE wallets SET balance = ? WHERE wallet_address = ?",
                (new_balance, wallet_address)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def transfer_funds(self, from_wallet: str, to_wallet: str, amount: float) -> Tuple[bool, str]:
        """Transfer funds between wallets."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check sender balance
            cursor.execute(
                "SELECT balance FROM wallets WHERE wallet_address = ?",
                (from_wallet,)
            )
            sender = cursor.fetchone()
            
            if not sender:
                conn.close()
                return False, "Sender wallet not found"
            
            if sender['balance'] < amount:
                conn.close()
                return False, "Insufficient balance"
            
            # Check recipient exists
            cursor.execute(
                "SELECT balance FROM wallets WHERE wallet_address = ?",
                (to_wallet,)
            )
            recipient = cursor.fetchone()
            
            if not recipient:
                conn.close()
                return False, "Recipient wallet not found"
            
            # Perform transfer
            cursor.execute(
                "UPDATE wallets SET balance = balance - ? WHERE wallet_address = ?",
                (amount, from_wallet)
            )
            
            cursor.execute(
                "UPDATE wallets SET balance = balance + ? WHERE wallet_address = ?",
                (amount, to_wallet)
            )
            
            # Record transaction
            cursor.execute(
                """INSERT INTO transactions 
                   (from_wallet, to_wallet, amount, transaction_type, status) 
                   VALUES (?, ?, ?, ?, ?)""",
                (from_wallet, to_wallet, amount, 'transfer', 'completed')
            )
            
            conn.commit()
            conn.close()
            
            return True, "Transfer successful"
        except Exception as e:
            return False, str(e)
    
    # Transaction Methods
    def get_transaction_history(self, wallet_address: str, limit: int = 50) -> List[Dict]:
        """Get transaction history for a wallet."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT * FROM transactions 
               WHERE from_wallet = ? OR to_wallet = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (wallet_address, wallet_address, limit)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def get_all_transactions(self, limit: int = 100) -> List[Dict]:
        """Get all transactions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    # Capital Injection Methods
    def add_capital_injection(self, wallet_address: str, amount: float, source: str = "system", notes: str = "") -> Tuple[bool, str]:
        """Add capital injection to a wallet."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if wallet exists
            cursor.execute(
                "SELECT balance FROM wallets WHERE wallet_address = ?",
                (wallet_address,)
            )
            wallet = cursor.fetchone()
            
            if not wallet:
                conn.close()
                return False, "Wallet not found"
            
            # Update wallet balance
            cursor.execute(
                "UPDATE wallets SET balance = balance + ? WHERE wallet_address = ?",
                (amount, wallet_address)
            )
            
            # Record capital injection
            cursor.execute(
                """INSERT INTO capital_injections 
                   (wallet_address, amount, source, notes) 
                   VALUES (?, ?, ?, ?)""",
                (wallet_address, amount, source, notes)
            )
            
            # Record as transaction
            cursor.execute(
                """INSERT INTO transactions 
                   (from_wallet, to_wallet, amount, transaction_type, status, notes) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ('system', wallet_address, amount, 'capital_injection', 'completed', notes)
            )
            
            conn.commit()
            conn.close()
            
            return True, "Capital injection successful"
        except Exception as e:
            return False, str(e)
    
    def get_capital_injections(self, wallet_address: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get capital injection history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if wallet_address:
            cursor.execute(
                """SELECT * FROM capital_injections 
                   WHERE wallet_address = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (wallet_address, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM capital_injections ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def get_all_capital_injections(self, limit: int = 100) -> List[Dict]:
        """Get all capital injections."""
        return self.get_capital_injections(wallet_address=None, limit=limit)
    
    # Alias for get_all_capital_injections
    def capital_injections(self, limit: int = 100) -> List[Dict]:
        """Alias for get_all_capital_injections."""
        return self.get_all_capital_injections(limit=limit)
    
    # Utility Methods
    def _generate_wallet_address(self) -> str:
        """Generate a unique wallet address."""
        return "AMKT" + secrets.token_hex(16).upper()
    
    def get_system_stats(self) -> Dict:
        """Get system-wide statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()['count']
        
        # Total wallets
        cursor.execute("SELECT COUNT(*) as count FROM wallets")
        total_wallets = cursor.fetchone()['count']
        
        # Total balance in system
        cursor.execute("SELECT SUM(balance) as total FROM wallets")
        total_balance = cursor.fetchone()['total'] or 0.0
        
        # Total transactions
        cursor.execute("SELECT COUNT(*) as count FROM transactions")
        total_transactions = cursor.fetchone()['count']
        
        # Total capital injections
        cursor.execute("SELECT COUNT(*) as count, SUM(amount) as total FROM capital_injections")
        injection_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_wallets': total_wallets,
            'total_balance': total_balance,
            'total_transactions': total_transactions,
            'total_capital_injections': injection_stats['count'] or 0,
            'total_capital_injected': injection_stats['total'] or 0.0
        }
    
    def close(self):
        """Close database connection."""
        pass  # Connections are closed after each operation
