import fcntl
import os
import sys
from pathlib import Path

class AppSingletone:
    def __init__(self, data_dir: Path):
        self.lock_file_path = data_dir / ".lock"
        self.lock_fd = None

    def acquire(self):
        try:
            self.lock_fd = open(self.lock_file_path, "w")
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Приложение уже запущено.")
            sys.exit(1)

    def release(self):
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
            except Exception:
                pass

