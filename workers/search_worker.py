from typing import Optional, Dict, Any
from PySide6 import QtCore
from services.member_service import search_members


class WorkerSignals(QtCore.QObject):
    """
    Defines signals for the SearchWorker.
    
    Attributes:
        finished (dict): Emitted with search results (matches list and parsed data).
        error (str): Emitted on failure.
    """
    finished = QtCore.Signal(dict)
    error = QtCore.Signal(str)


class SearchWorker(QtCore.QRunnable):
    """
    Background worker to perform member searches.
    Includes logic to restrict results based on staff gender (Security Check).
    """
    def __init__(self, query: str, is_admin: bool = False, user_gender: Optional[str] = None):
        super().__init__()
        self.query = query
        self.is_admin = is_admin
        self.user_gender = user_gender
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        """
        Executes the search logic.
        """
        try:
            result = search_members(self.query)

            # --- SECURITY CHECK (Gender Enforcement) ---
            # If not admin, ensure staff can only view members of their own gender.
            if not self.is_admin and result.get("parsed"):
                parsed = result["parsed"]
                
                member_gender = parsed.get('gender', '').strip().lower()
                # Handle None case for user_gender safely
                my_gender = str(self.user_gender).strip().lower() if self.user_gender else ""

                if my_gender and member_gender != my_gender:
                    # Block access if genders do not match
                    self.signals.finished.emit({"matches": [], "access_denied": True})
                    return

            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))