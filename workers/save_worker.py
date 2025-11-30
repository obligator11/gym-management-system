from PySide6 import QtCore
from services.member_service import save_new_member
from models.member import Member


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.
    
    Attributes:
        finished (str): Emitted with the saved file path when successful.
        error (str): Emitted with an error message if saving fails.
    """
    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)


class SaveWorker(QtCore.QRunnable):
    """
    Background worker that handles the file I/O operations for saving a new member.
    This prevents the GUI from freezing while generating PDFs and writing logs.
    """
    def __init__(self, member: Member):
        super().__init__()
        self.member = member
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        """
        Executes the save operation.
        """
        try:
            # save_new_member returns the path to the generated PDF
            path = save_new_member(self.member)
            self.signals.finished.emit(path)
        except Exception as e:
            self.signals.error.emit(str(e))