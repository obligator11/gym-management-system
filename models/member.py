from dataclasses import dataclass
from typing import Optional

@dataclass
class Member:
    """
    Represents a single gym member's profile and subscription details.
    """
    id: str
    name: str
    phone: str
    blood: str
    gender: str
    cnic: str  # National Identity Card Number
    day: int   # Birth Day
    month: int # Birth Month
    year: int  # Birth Year
    membership_months: int
    package: str
    end_date: str
    status: str  # e.g., 'Active', 'Expired'
    photo_path: Optional[str] = None
    fingerprint_data: Optional[str] = None