import sqlite3
from typing import List, Tuple, Any
import config

def mark_attendance(member_id: str) -> bool:
    """
    Records a check-in for the member in the database.
    
    Args:
        member_id (str): The ID of the member checking in.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not config.DB_FILE:
        return False

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO attendance (member_id) VALUES (?)", (member_id,))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error during attendance mark: {e}")
        return False

def get_recent_logs(limit: int = 50) -> List[Tuple[Any, ...]]:
    """
    Gets the most recent check-ins for the dashboard display.
    
    Args:
        limit (int): Number of records to retrieve. Defaults to 50.
        
    Returns:
        List[Tuple]: A list of rows containing (member_id, check_in_time).
    """
    if not config.DB_FILE:
        return []

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT member_id, check_in_time FROM attendance ORDER BY id DESC LIMIT ?", (limit,))
            return c.fetchall()
    except sqlite3.Error as e:
        print(f"Database error fetching recent logs: {e}")
        return []

def get_all_attendance_data() -> List[Tuple[Any, ...]]:
    """
    Fetches ALL attendance history for AI analysis.
    
    Returns:
        List[Tuple]: A list of all (member_id, check_in_time) records.
    """
    if not config.DB_FILE:
        return []

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT member_id, check_in_time FROM attendance")
            return c.fetchall()
    except sqlite3.Error as e:
        print(f"Database error fetching all data: {e}")
        return []