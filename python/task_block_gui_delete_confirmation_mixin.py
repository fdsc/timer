import tkinter as tk
from tkinter import messagebox
from datetime import timedelta, datetime
from constants import *

class DeleteConfirmationMixin:
    def _start_delete_confirmation(self):
        """Активирует режим подтверждения удаления: кнопка меняется на «Точно удалить» на 10 секунд."""
        # Если уже в режиме удаления или задача просрочена, удаляем задачу без дополнительных запросов
        if self.getDeleteConfirmationResult() or self.getRemained() == 0:
            self.delete_task()
            return

        self._delete_confirm_active = datetime.now()
        self.btn_del.config(text="Точно удалить?")

        # Планируем сброс через 10 секунд
        self.frame.after(int(DELETE_CONFIRM_MAX_SECONDS * 1000), self._cancel_delete_confirmation)


    def getDeleteConfirmationTime(self):
        """Возвращает время в секундах (float), прошедшее с момента первого нажатия на кнопку 'удалить'"""
        if self._delete_confirm_active is False:
            return 0.0;

        now = datetime.now()
        delta = now - self._delete_confirm_active
        return delta.total_seconds();
    
    def getDeleteConfirmationResult(self):
        time = self.getDeleteConfirmationTime()
        # Если значение времени, прошедшее с момента нажатия кнопки "удалить", слишком мало
        if time <= DELETE_CONFIRM_MIN_SECONDS:
            return False
        if time >= DELETE_CONFIRM_MAX_SECONDS:
            return False

        return True

    def _cancel_delete_confirmation(self):
        """Сбрасывает режим подтверждения, если пользователь не подтвердил удаление за 10 секунд."""
        self._delete_confirm_active = False
        self.btn_del.config(text="Удалить")
