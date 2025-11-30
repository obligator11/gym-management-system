import sqlite3
from typing import List, Tuple, Any
import config

def log_fee_update(staff_name: str, member_id: str, months: int) -> bool:
    """
    Records a fee update transaction in the database.
    
    Args:
        staff_name (str): The name of the staff member (admin) performing the action.
        member_id (str): The ID of the member receiving the update.
        months (int): Number of months added to the membership.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not config.DB_FILE:
        return False

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO fee_logs (staff_name, member_id, months_added) VALUES (?, ?, ?)",
                      (staff_name, member_id, months))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error logging fee: {e}")
        return False

def get_fee_logs() -> List[Tuple[Any, ...]]:
    """
    Fetches all fee records from the database, sorted by newest first.
    
    Returns:
        List[Tuple]: A list of tuples containing (id, timestamp, staff_name, member_id, months_added).
    """
    if not config.DB_FILE:
        return []

    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT id, timestamp, staff_name, member_id, months_added FROM fee_logs ORDER BY id DESC")
            return c.fetchall()
    except sqlite3.Error as e:
        print(f"Database error fetching fee logs: {e}")
        return []