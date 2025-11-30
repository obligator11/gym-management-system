import sqlite3
import bcrypt
from typing import Optional, List, Tuple, Any
import config

def admin_exists() -> bool:
    """
    Checks if an admin user already exists in the database.
    Useful for ensuring the setup flow only runs once.
    
    Returns:
        bool: True if an admin exists, False otherwise.
    """
    if not config.DB_FILE:
        return False
        
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM users WHERE role='admin'")
            return c.fetchone() is not None
    except sqlite3.Error as e:
        print(f"Database error checking admin existence: {e}")
        return False

def create_user(username: str, password: str, role: str, gender: Optional[str] = None) -> None:
    """
    Creates a new user in the database with a securely hashed password.
    
    Args:
        username (str): Unique username.
        password (str): Plain text password (will be hashed).
        role (str): Role of the user ('admin' or 'user').
        gender (str, optional): Gender of the user.
        
    Raises:
        ValueError: If the username already exists.
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash, role, gender) VALUES (?, ?, ?, ?)",
                      (username, hashed, role, gender))
            conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")
    except sqlite3.Error as e:
        print(f"Database error creating user: {e}")
        raise e

def verify_user(username: str, password: str) -> Optional[Tuple[str, str]]:
    """
    Verifies user login credentials against the database.
    
    Args:
        username (str): Input username.
        password (str): Input password.
        
    Returns:
        Optional[Tuple[str, str]]: A tuple (role, gender) if login succeeds, None otherwise.
    """
    if not config.DB_FILE:
        return None
        
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT password_hash, role, gender FROM users WHERE username=?", (username,))
            row = c.fetchone()
            
        if row and bcrypt.checkpw(password.encode('utf-8'), row[0]):
            return (row[1], row[2])
            
    except sqlite3.Error as e:
        print(f"Database error verifying user: {e}")
        
    return None

# --- USER MANAGEMENT FUNCTIONS ---

def get_all_users() -> List[Tuple[Any, ...]]:
    """
    Retrieves a list of all users.
    
    Returns:
        List[Tuple]: A list of (id, username, role, gender) tuples.
    """
    if not config.DB_FILE:
        return []

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT id, username, role, gender FROM users")
            return c.fetchall()
    except sqlite3.Error as e:
        print(f"Database error fetching users: {e}")
        return []

def delete_user_by_id(user_id: int) -> None:
    """
    Permanently deletes a user from the database by their ID.
    """
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error deleting user: {e}")

def update_user(user_id: int, password: Optional[str] = None, role: Optional[str] = None, gender: Optional[str] = None) -> None:
    """
    Updates an existing user's details.
    Only updates the password if a new one is provided.
    """
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            
            if password:
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                c.execute("UPDATE users SET password_hash=?, role=?, gender=? WHERE id=?",
                          (hashed, role, gender, user_id))
            else:
                # If no new password, just update role and gender
                c.execute("UPDATE users SET role=?, gender=? WHERE id=?",
                          (role, gender, user_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating user: {e}")