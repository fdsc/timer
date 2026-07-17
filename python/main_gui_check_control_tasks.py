import tkinter as tk
from task_block_tasks import TaskType

class CheckControlTasksMixin:

    # Метод проверки соответствия задач
    def check_control_tasks(self):
        """Подсвечивает жёлтым контрольные задачи, для которых нет парной normal/quiet задачи с тем же текстом."""
        normal_texts = {t.text for t in self.tasks.values() if t.type == TaskType.NORMAL}
        quiet_texts  = {t.text for t in self.tasks.values() if t.type == TaskType.QUIET}
        all_non_control = normal_texts | quiet_texts

        for task in self.tasks.values():
            if task.is_control:
                task.is_unpaired = task.text not in all_non_control
                if hasattr(task, 'frame') and task.frame.winfo_exists():
                    bg = task.getBgColor()
                    task.frame.config         (bg=bg)
                    task.lbl_text.config      (bg=bg)
                    task.lbl_time_left.config (bg=bg)
                    task.lbl_time_alert.config(bg=bg)
