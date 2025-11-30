from pathlib import Path
from typing import Optional, Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader
import config
from services.file_manager import ensure_folder


def create_member_pdf(save_path: Path, member_dict: Dict[str, Any]) -> None:
    """
    Generates a standardized PDF card for a gym member.
    
    Args:
        save_path (Path): The full path where the PDF will be saved.
        member_dict (dict): A dictionary containing member details (name, id, package, etc).
    """
    ensure_folder(save_path.parent)
    c = canvas.Canvas(str(save_path), pagesize=A4)
    w, h = A4
    y = h - 50

    # --- HEADER ---
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.8, 0.0, 0.0) # Dark Red
    c.drawString(60, y, f"💪 SOLID GYM ({member_dict.get('id', 'Unknown')})")

    y -= 30
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)

    # --- BODY FIELDS ---
    fields = ["id", "name", "phone", "blood", "gender", "cnic"]
    for field in fields:
        val = member_dict.get(field, "N/A")
        c.drawString(60, y, f"{field.title()}: {val}")
        y -= 18

    # Dates
    day = member_dict.get('day', 0)
    month = member_dict.get('month', 0)
    year = member_dict.get('year', 0)
    c.drawString(60, y, f"Join Date: {day:02d}/{month:02d}/{year}")

    # Membership Details
    if 'membership_months' in member_dict:
        y -= 18
        c.drawString(60, y, f"Membership: {member_dict['membership_months']} months")

        y -= 18
        package = member_dict.get('package', 'Bronze')  # Default to Bronze
        c.drawString(60, y, f"Package: {package}")

        y -= 18
        c.drawString(60, y, f"End Date: {member_dict.get('end_date', 'N/A')}")
        y -= 18
        c.drawString(60, y, f"Status: {member_dict.get('status', 'N/A')}")

    # --- FOOTER (Credits) ---
    y -= 30
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    
    # Safe access to config in case variables are missing
    creator = getattr(config, 'CREATOR_NAME', 'Admin')
    c.drawString(60, 70, f"Created by: {creator}")

    # Social Links
    socials = getattr(config, 'SOCIALS', {})
    for i, (n, u) in enumerate(socials.items()):
        c.drawString(60, 55 - i * 12, f"{n}: {u}")

    c.save()


def parse_member_from_pdf(pdf_path: Path) -> Optional[Dict[str, Any]]:
    """
    Reads a generated PDF and extracts member data back into a dictionary.
    Useful for reconstructing the database from files.
    """
    try:
        reader = PdfReader(str(pdf_path))
        text = "".join(p.extract_text() or "" for p in reader.pages)
    except Exception:
        return None

    # Initialize with defaults
    d = {k: "" for k in ["id", "name", "phone", "blood", "gender", "cnic", "package"]}
    d.update({"day": None, "month": None, "year": None})

    for ln in text.splitlines():
        # Standard Fields
        for key in ["id", "name", "phone", "blood", "gender", "cnic"]:
            if ln.lower().startswith(f"{key}:"):
                try:
                    d[key] = ln.split(":", 1)[1].strip()
                except IndexError:
                    pass

        # Parse Package
        if ln.startswith("Package:"):
            try:
                d["package"] = ln.split(":", 1)[1].strip()
            except IndexError:
                pass

        # Parse Join Date
        if ln.startswith("Join Date:"):
            try:
                parts = ln.split(":")[1].strip().split("/")
                d["day"], d["month"], d["year"] = int(parts[0]), int(parts[1]), int(parts[2])
            except (IndexError, ValueError):
                pass

        # Parse Membership Duration
        if ln.startswith("Membership:"):
            try:
                # Extracts "3" from "Membership: 3 months"
                d["membership_months"] = int(ln.split(":")[1].strip().split()[0])
            except (IndexError, ValueError):
                pass

        # Parse Dates & Status
        if ln.startswith("End Date:"):
            try:
                d["end_date"] = ln.split(":", 1)[1].strip()
            except IndexError:
                pass

        if ln.startswith("Status:"):
            try:
                d["status"] = ln.split(":", 1)[1].strip()
            except IndexError:
                pass

    # Fallback: If ID wasn't found in text, use filename
    if not d.get("id"):
        d["id"] = pdf_path.stem

    return d