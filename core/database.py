import sqlite3
import bcrypt
from typing import Optional
import config

def init_db():
    """
    Initializes the SQLite database.
    Creates tables for users, attendance, and fee logs if they do not exist.
    """
    if not config.DB_FILE:
        print("Database path not found in config.")
        return

    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()

    # 1. Users Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            gender TEXT
        )
    """)

    # 2. Attendance Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Fee Logs Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS fee_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_name TEXT NOT NULL,
            member_id TEXT NOT NULL,
            months_added INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def admin_exists() -> bool:
    """
    Checks if an administrator account already exists in the database.
    Returns: True if an admin exists, False otherwise.
    """
    if not config.DB_FILE:
        return False
        
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE role='admin'")
    exists = c.fetchone() is not None
    conn.close()
    return exists


def create_user(username: str, password: str, role: str, gender: str = None):
    """
    Creates a new user with a hashed password.
    
    Args:
        username (str): The unique username.
        password (str): The raw password (will be hashed).
        role (str): 'admin' or 'user'.
        gender (str, optional): User's gender.
    
    Raises:
        ValueError: If the username already exists.
    """
    # Hash the password using bcrypt (Safe for production)
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, role, gender) VALUES (?, ?, ?, ?)",
                  (username, hashed, role, gender))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[tuple]:
    """
    Verifies a user's login credentials.

    Args:
        username (str): The username input.
        password (str): The raw password input.

    Returns:
        tuple (role, gender): If login succeeds.
        None: If login fails.
    """
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    
    # Retrieve the hash from the DB
    c.execute("SELECT password_hash, role, gender FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    # Compare the input password to the stored hash
    if row and bcrypt.checkpw(password.encode('utf-8'), row[0]):
        return (row[1], row[2])
    
    return None