import datetime
import calendar

def month_name(m: int) -> str:
    """
    Returns the full name of a month.
    Example: 1 -> 'January', 2 -> 'February'.
    """
    # 1900 is an arbitrary valid year used just to format the month name
    return datetime.date(1900, m, 1).strftime("%B")

def add_months(start_date: datetime.date, months: int) -> datetime.date:
    """
    Calculates the date N months from the start_date.
    Handles year rollovers and end-of-month adjustments (e.g., Jan 31 + 1 month -> Feb 28).
    """
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    
    # Get the number of days in the new month to ensure valid date
    # monthrange returns (weekday_of_first_day, number_of_days)
    days_in_new_month = calendar.monthrange(year, month)[1]
    
    # Clamp the day (e.g., if start was 31st but new month only has 30 days)
    day = min(start_date.day, days_in_new_month)
    
    return datetime.date(year, month, day)

def days_until(end_date: datetime.date) -> int:
    """
    Calculates the number of days remaining until end_date.
    Returns negative numbers if the date has passed.
    """
    return (end_date - datetime.date.today()).days