import tkinter as tk
from tkinter import messagebox

class DeleteConfirmationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._delete_confirm_active = False
        self._delete_confirm_timer_id = None

    def _start_delete_confirmation(self):
        if self._delete_confirm_active:
            return
        self._delete_confirm_active = True
        self.btn_del.config(text="Подтвердить удаление", bg="#ffcccc")
        
        # Таймер подтверждения (5 секунд)
        self._delete_confirm_timer_id = self.root.after(5000, self._cancel_delete_confirmation)

    def _cancel_delete_confirmation(self):
        if self._delete_confirm_timer_id:
            self.root.after_cancel(self._delete_confirm_timer_id)
            self._delete_confirm_timer_id = None
        self._delete_confirm_active = False
        self.btn_del.config(text="Удалить", bg=self.getBgColor())

    def getDeleteConfirmationTime(self) -> int:
        return 5

    def getDeleteConfirmationResult(self, confirmed: bool):
        if confirmed:
            self._perform_actual_deletion()
        else:
            self._cancel_delete_confirmation()

    def _perform_actual_deletion(self):
        self.stop_timer()
        # Логика удаления из родителя и хранилища
        if hasattr(self, '_container_frame') and self.frame.winfo_exists():
            self.frame.destroy()
        if hasattr(self, 'root') and hasattr(self.root, 'tasks'):
            self.root.tasks.pop(self.task_id, None)
            self.root._reorder_tasks_in_frame(self._container_frame)
