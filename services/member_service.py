import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import config
from core.utils import month_name
from models.member import Member
from services.pdf_service import create_member_pdf, parse_member_from_pdf

# --- CORE SAVING & FINDING ---

def save_new_member(member: Member) -> str:
    """
    Saves a member's data as a PDF and logs the entry in a monthly text file.
    Handles re-admission by creating sub-folders if the ID already exists.
    
    Args:
        member (Member): The member object containing all details.
        
    Returns:
        str: The file path of the saved PDF.
    """
    year = str(member.year)
    monthn = month_name(member.month)
    day = f"{member.day:02d}"

    # Structure: Gym Data / Year / Month / Day / MemberID
    base = config.BASE_FOLDER / year / monthn / day / member.id
    base.mkdir(parents=True, exist_ok=True)

    # Check for re-admission (existing PDF implies previous registration)
    existing = list(base.glob("*.pdf"))
    if existing:
        # Create a subfolder like "ReAdmission_1"
        count = len([d for d in base.iterdir() if d.is_dir()]) + 1
        re_dir = base / f"ReAdmission_{count}"
        re_dir.mkdir(parents=True, exist_ok=True)
        save_path = re_dir / f"{member.id}.pdf"
    else:
        save_path = base / f"{member.id}.pdf"

    # Generate the actual PDF
    create_member_pdf(save_path, member.__dict__)

    # Log to monthly text file (Quick lookup log)
    log_file = config.BASE_FOLDER / year / monthn / "monthly_members.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    entry = f"{member.id} — {member.name} — {member.day:02d}/{member.month:02d}/{member.year} — {member.status}\n"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"Failed to write to text log: {e}")

    return str(save_path)


def find_photo(member_id: str) -> Optional[str]:
    """
    Helper to find a member's photo path regardless of extension (.jpg, .png) or casing.
    """
    if not config.PHOTOS_FOLDER.exists():
        return None

    # 1. Check exact match with common extensions
    for ext in [".jpg", ".png", ".jpeg", ".bmp"]:
        p = config.PHOTOS_FOLDER / f"{member_id}{ext}"
        if p.exists():
            return str(p)

    # 2. Check case-insensitive match (slower, but safer)
    clean_id = member_id.strip().lower()
    for f in config.PHOTOS_FOLDER.iterdir():
        if f.stem.lower() == clean_id:
            return str(f)
            
    return None


def search_members(query: str) -> Dict[str, Any]:
    """
    Searches for members by ID or Name across all stored PDFs.
    
    Args:
        query (str): The search term (ID or Name).
        
    Returns:
        Dict: Contains 'matches' (list of paths) and 'parsed' (data of best match).
    """
    ql = query.lower().strip()
    
    # 1. Quick Search: Match filename (ID)
    matches = [p for p in config.BASE_FOLDER.rglob("*.pdf") if ql in p.stem.lower()]

    # 2. Deep Search: Parse PDFs to match Name (if no filename match)
    if not matches:
        for pdf_path in config.BASE_FOLDER.rglob("*.pdf"):
            try:
                parsed = parse_member_from_pdf(pdf_path)
                if parsed and ql in parsed.get('name', '').lower():
                    matches.append(pdf_path)
            except Exception:
                continue

    if not matches:
        return {"matches": []}

    # Find the most recently modified file among matches to show as "Best Result"
    latest = max(matches, key=lambda p: p.stat().st_mtime)
    parsed = parse_member_from_pdf(latest)

    if parsed:
        photo = find_photo(parsed.get('id', ''))
        if photo:
            parsed['photo_path'] = photo

    return {"matches": [str(p) for p in matches], "parsed": parsed}


def get_member_by_id(member_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the latest member data for a specific ID.
    Used for Check-In, Renewal, and Status Updates.
    """
    found_pdfs = []
    # Find all PDFs with this ID (could be original + readmissions)
    for pdf_path in config.BASE_FOLDER.rglob("*.pdf"):
        if pdf_path.stem.lower() == member_id.lower().strip():
            found_pdfs.append(pdf_path)

    if not found_pdfs:
        return None

    # Get the newest one
    latest_pdf = max(found_pdfs, key=lambda p: p.stat().st_mtime)
    data = parse_member_from_pdf(latest_pdf)

    if data:
        photo = find_photo(data.get('id', ''))
        if photo:
            data['photo_path'] = photo

    return data


# --- APPROVAL & STATUS MANAGEMENT ---

def get_pending_members() -> List[Dict[str, Any]]:
    """
    Scans all records for members with 'Status: Pending'.
    Returns a list of summary dictionaries for the dashboard.
    """
    pending_list = []
    if not config.BASE_FOLDER.exists():
        return []

    for pdf_path in config.BASE_FOLDER.rglob("*.pdf"):
        try:
            data = parse_member_from_pdf(pdf_path)
            if data and data.get('status', '').lower() == 'pending':
                pending_list.append({
                    'id': data.get('id', 'Unknown'),
                    'name': data.get('name', 'Unknown'),
                    'gender': data.get('gender', 'Unknown'),
                    'date': f"{data.get('day')}/{data.get('month')}/{data.get('year')}",
                    'path': str(pdf_path)
                })
        except Exception:
            continue
            
    return pending_list


def update_member_status(member_id: str, new_status: str) -> None:
    """
    Updates a member's status (e.g., Pending -> Active) by regenerating their PDF.
    """
    data = get_member_by_id(member_id)
    if not data:
        raise ValueError("Member not found")

    # Reconstruct the Member object with the new status
    m = Member(
        id=data['id'],
        name=data['name'],
        phone=data.get('phone'),
        blood=data.get('blood'),
        gender=data.get('gender'),
        cnic=data.get('cnic'),
        day=int(data.get('day', 1)),
        month=int(data.get('month', 1)),
        year=int(data.get('year', 2000)),
        membership_months=int(data.get('membership_months', 1)),
        package=data.get('package'),
        end_date=data.get('end_date'),
        status=new_status,
        photo_path=data.get('photo_path'),
        fingerprint_data=data.get('fingerprint_data')
    )
    save_new_member(m)


def delete_member(member_id: str) -> bool:
    """
    Permanently deletes a member's entire folder structure.
    """
    deleted = False
    # rglob finds folders matching the ID anywhere in the hierarchy
    for folder in config.BASE_FOLDER.rglob(member_id):
        if folder.is_dir() and folder.name == member_id:
            try:
                shutil.rmtree(folder)
                deleted = True
            except Exception as e:
                print(f"Error deleting folder {folder}: {e}")
                
    return deleted


def renew_membership(member_id: str, new_start_date: datetime.date, new_end_date: datetime.date, months_added: int) -> str:
    """
    Renews a membership by updating dates and saving a new PDF record.
    """
    current_data = get_member_by_id(member_id)
    if not current_data:
        raise ValueError(f"Member {member_id} not found.")

    updated_member = Member(
        id=current_data['id'],
        name=current_data['name'],
        phone=current_data.get('phone', ''),
        blood=current_data.get('blood', ''),
        gender=current_data.get('gender', ''),
        cnic=current_data.get('cnic', ''),
        day=new_start_date.day,
        month=new_start_date.month,
        year=new_start_date.year,
        membership_months=months_added,
        package=current_data.get('package', 'Bronze'),
        end_date=str(new_end_date),
        status='Active',
        photo_path=current_data.get('photo_path'),
        fingerprint_data=current_data.get('fingerprint_data')
    )
    return save_new_member(updated_member)


# --- REPORTING FUNCTIONS ---

def get_monthly_list(year: int, month: int) -> str:
    """
    Reads the 'monthly_members.txt' file for a specific month.
    """
    file_path = config.BASE_FOLDER / str(year) / month_name(month) / "monthly_members.txt"
    
    if not file_path.exists():
        return "No new members recorded this month."
        
    try:
        return file_path.read_text(encoding="utf-8").strip() or "No entries found."
    except Exception as e:
        return f"Error reading log file: {e}"


def get_members_by_status(status: str) -> str:
    """
    Scans all PDFs to find members with a specific status (Active/Expired).
    Returns a formatted string list.
    """
    if not config.BASE_FOLDER.exists():
        return f"No members found with status: {status}"

    member_dict = {}

    # Scan all PDFs
    for pdf_path in config.BASE_FOLDER.rglob("*.pdf"):
        try:
            parsed = parse_member_from_pdf(pdf_path)
            if parsed and parsed.get('status', '').lower() == status.lower():
                member_id = parsed.get('id', '')
                
                # Keep only the latest record for each ID (handle re-admissions/renewals)
                # member_dict value format: (parsed_data, modification_time)
                if member_id not in member_dict or pdf_path.stat().st_mtime > member_dict[member_id][1]:
                    member_dict[member_id] = (parsed, pdf_path.stat().st_mtime)
        except Exception:
            continue

    # Sort by date modified (newest first)
    sorted_members = sorted(member_dict.items(), key=lambda x: x[1][1], reverse=True)

    lines = []
    for _, (parsed, _) in sorted_members:
        lines.append(f"{parsed['id']} — {parsed['name']} — Status: {parsed['status']}")

    if not lines:
        return f"No members found with status: {status}"

    return "\n".join(lines)