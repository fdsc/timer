from   tkinter  import messagebox
from   datetime import datetime, timedelta
from   notifier import cancel_notify_for_task
import math
import tasks_storage

from enum import IntEnum

class TaskType(IntEnum):
    NORMAL  = 0
    QUIET   = 1
    CONTROL = 2


class TasksMixin:

    @property
    def is_normal(self):
        return self.type == TaskType.NORMAL

    @property
    def is_quiet(self):
        return self.type == TaskType.QUIET

    @property
    def is_control(self):
        return self.type == TaskType.CONTROL

    def set_defer_time(self, new_defer_time: datetime):
        self.defer_time = new_defer_time
        # Пересчитываем отображение таймера с учётом изменившихся величин
        self.update_timer()

    def getRemained(self):
        if self.is_control:
            now = datetime.now()
            delta = (now - self.alert_time).total_seconds()
            return max(1, int(delta))

        now   = datetime.now()
        delta = self.defer_time - now
        return max(0, int(math.ceil(delta.total_seconds())))

    def getRemainedAlert(self):
        now   = datetime.now()
        delta = self.alert_time - now
        return max(0, int(math.ceil(delta.total_seconds())))

    def save(self):
        if self.parent.io_error_flag:
            return False

        isSuccess = tasks_storage.save_task(
            data_dir=self.parent.data_dir,
            task_data={
                "task_id":          self.task_id,
                "text":             self.text,
                "alert_time":       self.alert_time,
                "is_important":     self.is_important,
                "type":             self.type,
                "control_interval": self.control_interval,
            },
            lock=self.parent.storage_lock,
            io_error_flag=self.parent.io_error_flag
        )

        if not isSuccess:
            self.parent.io_error_flag = True
            messagebox.showerror("Ошибка доступа к диску", f"Не удалось сохранить задачу. Сохранение отключено. '{tasks_storage.get_tasks_dir()}'")
            self.parent._disable_add_buttons()

        return isSuccess

    def delete_task(self):
        """Выполняет удаление задачи."""
        # Сбрасываем флаг подтверждения перед удалением
        self._delete_confirm_active = False
        self._on_delete_direct()
        self.parent.check_control_tasks()

        if len(self.parent.get_quiet_tasks_not_remained()) == 0:
            self.resetQuietTab()
        if len(self.parent.get_normal_tasks_not_remained()) == 0:
            self.parent.is_muted = True
            self.parent.toggle_mute()


    def _on_delete_direct(self):
        """Реальная логика удаления задачи."""
        if self.task_id not in self.parent.tasks:
            return
        if self.parent.io_error_flag:
            return

        del self.parent.tasks[self.task_id]
        if hasattr(self, "frame") and self.frame.winfo_exists():
            self.frame.destroy()
        self._stopped = True
        cancel_notify_for_task(self.task_id)

        # Удаляем файл на диске
        success = tasks_storage.delete_task_file(
            data_dir      = self.parent.data_dir,
            task_id       = self.task_id,
            lock          = self.parent.storage_lock,
            io_error_flag = self.parent.io_error_flag
        )

        if not success:
            self.parent.io_error_flag = True
            messagebox.showerror("Ошибка доступа к диску", f"Не удалось удалить файл задачи. Сохранение отключено. '{tasks_storage.get_tasks_dir()}'")
            self.parent._disable_add_buttons()
