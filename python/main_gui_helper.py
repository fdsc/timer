import math
import time
import tkinter  as tk
from   tkinter  import ttk,messagebox
from   datetime import timedelta, datetime

from config_manager import save_opts, save_opts_debounced

class Main_HelperMixin:
    
    def get_quiet_tasks(self):
        return [task for task in self.tasks.values() if task.is_quiet]
   
    def get_quiet_tasks_not_remained(self):
        return [task for task in self.tasks.values() if task.is_quiet and task.getRemained() <= 0]

    def get_non_quiet_tasks(self):
        return [task for task in self.tasks.values() if not task.is_quiet]

    def get_non_quiet_tasks_not_remained(self):
        return [task for task in self.tasks.values() if not task.is_quiet and task.getRemained() <= 0]

    def check_bulk_alerts(self, countOfPendingNotifications):
        """
        Проверяет количество активных задач и при необходимости показывает
        одно массовое критическое оповещение вместо множества одиночных.
        """
        now = datetime.now()
        # Считаем «активными» все задачи, у которых alert_time уже наступило или прошло
        active_tasks = [
            t for t in self.tasks.values()
            if t.alert_time is None or t.getRemained() <= 0
        ]

        from notifier import show_bulk_critical_alert

        if len(active_tasks) > 2 or countOfPendingNotifications > 1:
            show_bulk_critical_alert(self, active_tasks, icon_path=None)
            return True
        else:
            return False

    def _generate_task_id(self) -> str:
        """Генерирует уникальный task_id по новому правилу."""
        base = str(int(time.time() * 1000))
        task_id = f"{base}-{self.task_id_counter}"
        self.task_id_counter += 1
        return task_id

    def get10percentList(self, maxVal: int = 60, expStep: float = 0.17, minVal: int = 1) -> int:
        values = []
        current = 1
        while current <= maxVal:
            values.append(str(current))
            step = max(minVal, math.floor(current * expStep))
            current += step

        return values
