from PySide6 import QtCore
from services.member_service import get_monthly_list, get_members_by_status


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.
    
    Attributes:
        finished (str): Emitted with the result string when the task is done.
        error (str): Emitted with an error message if the task fails.
    """
    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)


class MonthlyListWorker(QtCore.QRunnable):
    """
    Background worker to fetch the text-based monthly member list.
    Prevents the UI from freezing during file I/O.
    """
    def __init__(self, year: int, month: int):
        super().__init__()
        self.year = year
        self.month = month
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            content = get_monthly_list(self.year, self.month)
            self.signals.finished.emit(content)
        except Exception as e:
            self.signals.error.emit(str(e))


class StatusListWorker(QtCore.QRunnable):
    """
    Background worker to fetch a list of members filtered by status (e.g., Active, Expired).
    Prevents the UI from freezing during the search.
    """
    def __init__(self, status: str):
        super().__init__()
        self.status = status
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            content = get_members_by_status(self.status)
            self.signals.finished.emit(content)
        except Exception as e:
            self.signals.error.emit(str(e))