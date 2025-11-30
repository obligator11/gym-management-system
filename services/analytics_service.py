import datetime
from pathlib import Path
from typing import List, Dict, Optional
import config
from core.utils import month_name
from services.pdf_service import parse_member_from_pdf

def generate_daily_brief(target_date: Optional[datetime.date] = None) -> str:
    """
    Generates a text report for a specific day by scanning the file system.
    Focuses on Member Activity (Counts and Names).

    Args:
        target_date (datetime.date, optional): The date to generate the report for. 
                                               Defaults to today.

    Returns:
        str: A formatted string containing the daily briefing.
    """
    if not target_date:
        target_date = datetime.date.today()

    day_str = f"{target_date.day:02d}"
    month_str = month_name(target_date.month)
    year_str = str(target_date.year)

    # Path to search: e.g., Gym Data / 2025 / November / 05
    # We use config.BASE_FOLDER to ensure this works on any machine
    daily_folder = config.BASE_FOLDER / year_str / month_str / day_str

    # 1. Gather Data
    new_members: List[str] = []
    package_counts: Dict[str, int] = {}

    if daily_folder.exists():
        # Look inside every member folder for that day
        for member_folder in daily_folder.iterdir():
            if member_folder.is_dir():
                # Find the PDF (assuming one PDF per member folder)
                pdf_files = list(member_folder.glob("*.pdf"))
                
                if pdf_files:
                    # Parse PDF to get Name and Package
                    # Ensure parse_member_from_pdf handles errors gracefully internally
                    data = parse_member_from_pdf(pdf_files[0])
                    
                    if data:
                        # Store Name
                        new_members.append(data.get('name', 'Unknown Member'))

                        # Count Package Popularity
                        pkg = data.get('package', 'Unknown Package')
                        package_counts[pkg] = package_counts.get(pkg, 0) + 1

    # 2. Build the Narrative
    count = len(new_members)
    
    # helper for clean lines
    lines = []
    lines.append(f"📅 **EVENING BRIEFING** ({target_date.strftime('%B %d, %Y')})")
    lines.append("-" * 40)
    lines.append("")

    # Activity Section
    if count == 0:
        lines.append("📉 **Activity:** It was a quiet day. No new memberships were recorded today.")
    elif count < 3:
        lines.append(f"⚖️ **Activity:** Steady pace today. You had **{count} new joiners**.")
    else:
        lines.append(f"🚀 **Activity:** It was a busy day! You welcomed **{count} new members**.")
    
    lines.append("")

    # Details Section
    if count > 0:
        # Find best selling package
        if package_counts:
            best_pkg = max(package_counts, key=package_counts.get)
            lines.append(f"🏆 **Most Popular:** The majority of people today chose the **{best_pkg}** package.")
            lines.append("")

        # List Names
        lines.append("📝 **New Joiners:**")
        for name in new_members:
            lines.append(f" • {name}")

    # Footer
    lines.append("")
    lines.append("-" * 40)
    lines.append("End of Report. Have a good evening! 🌙")

    return "\n".join(lines)