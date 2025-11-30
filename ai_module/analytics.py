import datetime
from collections import Counter
from services.attendance_service import get_all_attendance_data

class GymAI:
    def predict_peak_hours(self):
        """
        Analyzes check-in history to find the busiest hour of the day.
        Returns: String message (e.g., "Peak time is 6 PM")
        """
        data = get_all_attendance_data()

        if not data:
            return "Not enough data to predict peak hours yet."

        # Extract hours from timestamps (Format: YYYY-MM-DD HH:MM:SS)
        # We assume timestamp is at index 1
        hours = []
        for row in data:
            try:
                # row[1] is the string timestamp
                dt = datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
                hours.append(dt.hour)
            except (ValueError, IndexError):
                # Skip rows with invalid date formats or missing indices
                continue

        if not hours:
            return "Insufficient daily data."

        # Find most common hour
        # most_common is the hour (0-23), count is the frequency
        most_common, count = Counter(hours).most_common(1)[0]

        # Format nice string (e.g., 18 -> 6 PM)
        if most_common == 0:
            return "Peak time is Midnight."
        if most_common == 12:
            return "Peak time is 12 PM (Noon)."
        if most_common < 12:
            return f"Peak time is {most_common} AM."
        
        return f"Peak time is {most_common - 12} PM."

    def get_churn_risk(self, member_id):
        """
        Checks if a specific member hasn't visited in 14 days.
        """
        # In a real scenario, we would query specifically for this member's last log.
        # For this lite version, we scan the data.
        data = get_all_attendance_data()

        last_visit = None
        for mid, timestamp in data:
            if mid == member_id:
                try:
                    dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    if last_visit is None or dt > last_visit:
                        last_visit = dt
                except ValueError:
                    continue

        if not last_visit:
            return "No attendance history."

        days_since = (datetime.datetime.now() - last_visit).days

        if days_since > 21:
            return "High Risk (Absent 3+ weeks)"
        elif days_since > 14:
            return "Medium Risk (Absent 2 weeks)"
        else:
            return "Low Risk (Active)"