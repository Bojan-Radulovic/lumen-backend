import hashlib
from constants import DATABASE_PATH, DATABASE_DIR
import sqlite3
import os
from constants import ADMIN_EMAIL, ADMIN_PASSWORD

def initialize_database():
    """Initialize database with required tables"""
    ensure_database_directory()
    
    conn = get_db_connection_service()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_human BOOLEAN NOT NULL,
            image_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_temporary_password BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL,
            used_at DATETIME NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    admin_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    
    cursor.execute('SELECT * FROM users WHERE email = ? AND is_admin = TRUE', (ADMIN_EMAIL,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (email, password_hash, is_temporary_password, is_admin) 
            VALUES (?, ?, FALSE, TRUE)
        ''', (ADMIN_EMAIL, admin_hash))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Database initialized at: {DATABASE_PATH}")


def ensure_database_directory():
    """Create the database directory if it doesn't exist"""
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)
        print(f"Created database directory: {DATABASE_DIR}")

def get_db_connection_service():
    """Get database connection, creating directory if needed"""
    ensure_database_directory()
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    """Dependency to get database connection"""
    return get_db_connection_service()