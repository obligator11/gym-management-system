import os
import shutil
import datetime
from pathlib import Path
from typing import Tuple, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config

# Permissions we need (Read/Write)
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def create_local_backup() -> Tuple[Optional[str], Optional[str]]:
    """
    Compresses the Gym Data folder into a Zip file.
    
    Returns:
        Tuple[str, None]: (Path to zip file, None) if successful.
        Tuple[None, str]: (None, Error message) if failed.
    """
    if not config.BASE_FOLDER or not config.BASE_FOLDER.exists():
        return None, "No data folder found to backup."

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    zip_filename = f"SolidGym_Backup_{timestamp}"

    # Save zip to Desktop temporarily
    # Using Path.home() ensures this works on any user's machine
    desktop = Path.home() / "Desktop"
    
    # Fallback if Desktop doesn't exist (e.g., on some servers/configs)
    if not desktop.exists():
        desktop = Path.home()
        
    save_path = desktop / zip_filename

    try:
        # Create Zip
        # shutil.make_archive automatically adds .zip extension
        archive_path = shutil.make_archive(str(save_path), 'zip', config.BASE_FOLDER)
        return archive_path, None
    except Exception as e:
        return None, str(e)


def upload_to_drive(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Uploads a specified file to Google Drive.
    Requires 'credentials.json' from Google Cloud Console to be in the project root.
    
    Args:
        file_path (str): The full path to the file to upload.
        
    Returns:
        Tuple[bool, str]: (Success, File ID or Error Message).
    """
    creds = None

    # Check for credentials file
    # NOTE: Ensure 'credentials.json' and 'token.json' are in your .gitignore file!
    creds_file = Path("credentials.json") 
    token_file = Path("token.json") 

    if not creds_file.exists():
        return False, "Missing credentials.json! Please download it from Google Cloud Console."

    # Load existing tokens if the user has logged in before
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception:
            # If token is corrupt or format changed, ignore it and re-login
            creds = None

    # Log in if needed
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save tokens for next time
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            return False, f"Authentication failed: {str(e)}"

    try:
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': Path(file_path).name}
        media = MediaFileUpload(file_path, mimetype='application/zip')

        # Execute upload
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        return True, file.get('id')

    except Exception as e:
        return False, f"Upload failed: {str(e)}"