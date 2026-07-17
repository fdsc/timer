import tkinter as tk

from constants import *
from task_block_gui_layout import TaskBlockLayoutMixin
from task_block_timer_and_alert import TimerAndAlertMixin
from task_block_gui_delete_confirmation_mixin import DeleteConfirmationMixin
from task_block_gui_priority_colors import PriorityColorsMixin
from task_block_tasks import TasksMixin
from task_block_tasks import TaskType


class TaskBlock(
    TaskBlockLayoutMixin,
    TimerAndAlertMixin,
    DeleteConfirmationMixin,
    PriorityColorsMixin,
    TasksMixin
):
    def __init__(self, parent, frame: tk.Frame, task_id, text, alert_time, is_important_initial: bool = False, _type: TaskType = TaskType.NORMAL, control_interval: int = 0):
        self.parent       = parent
        self.task_id      = task_id
        self.alert_time   = alert_time
        self.defer_time   = alert_time              # Не должен сохраняться
        self.text         = text
        self.type         = _type
        self.is_important = is_important_initial
        self.control_interval = control_interval

        self._stopped               = False
        self._alerted_once          = False
        self._retry_scheduled       = False
        self._delete_confirm_active = False
        self.is_unpaired            = False             # Для контрольных задач

        self._container_frame = frame

        self.root = parent.list_frame.winfo_toplevel()

        self.build_layout()
        self.start_timer_loop()
