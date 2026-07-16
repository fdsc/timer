#!/bin/python3
# Требуются пакеты sox, tk, zenity
# Проверка наличия tkinter: python3 -m tkinter

import tkinter as tk
from tkinter import ttk,messagebox
import time
from datetime import timedelta, datetime
from pathlib import Path
import traceback
import threading
import fcntl


import notifier
import helper
import tasks_storage
from task_block import TaskBlock
from config_manager import get_user_data_dir, load_or_create_opts, save_opts, init_media_config, load_media_paths, save_opts_debounced
from date_utils import build_alert_time

import constants
from constants import (
    SECONDS_PER_MINUTE,
    SECONDS_PER_HOUR,
    SECONDS_PER_DAY,
    MAX_DELAY_DAYS,
    TEST_SOUND_PATH,
)

from app_singletone import AppSingletone
from main_load_config_path import LoadConfigPathMixin
from main_gui_input_panel import InputPanelMixin
from main_gui_tabs_layout import TabsLayoutMixin
from main_gui_resize_handler import ResizeHandlerMixin
from main_gui_task_frames_sorting_logic import TaskFramesSortingLogicMixin
from main_gui_audio_control import AudioControlMixin


# nuitka???

class App(
    LoadConfigPathMixin,
    InputPanelMixin,
    TabsLayoutMixin,
    ResizeHandlerMixin,
    TaskFramesSortingLogicMixin,
    AudioControlMixin
):
    def __init__(self, root):
        self.root = root
        self.root.title("Отслеживание задач")

        # Счётчик задач для именования новых задач
        self.task_id_counter=0
        # Блокировка для доступа к файлам
        self.storage_lock = threading.Lock()
        # Флаг неисправности ввода-вывода
        self.io_error_flag = False

        # Загружаем основные пути к настройкам
        LoadConfigPathMixin.load_config(self)

        # Блокировка для предотвращения запуска двух экземпляров приложения
        self.lock_mgr = AppSingletone(self.data_dir)
        self.lock_mgr.acquire()

        # Загружаем или создаём opts.json (основной файл настроек)
        self.opts = load_or_create_opts(self.data_dir)
        # Инициализируем громкость из настроек
        self.volume_factor = self.opts.get("volume_percent", 100) / 100.0
        # Несохранённое значение громкости
        self._pending_volume_value = None

        self.root.geometry(self.opts["geometry"])
        self.root.bind("<Configure>", self.rootResize)

        # Новое поле: состояние логики общего фонового сигнала
        # !!!
        self.alert_sound_state = {
            "first_pending_add_time": None,      # datetime | None
            "is_general_mode_active": False,     # bool
            "general_sound_timer_id": None       # int | None (ID от root.after)
        }

        # Здесь размещаются как тихие задачи, так и обычные
        self.tasks = {}

        self.build_input_panel(root)
        self.build_tabs(root)

        # ------------------------------------------------
        # Инициализация хранилища задач
        if not tasks_storage.ensure_tasks_dir(self.data_dir):
            self.io_error_flag = True
            messagebox.showerror("Ошибка доступа к диску", f"Не удалось создать или получить доступ к папке для хранения задач. Закройте программу и устраните ошибку. '{tasks_storage.get_tasks_dir()}'")
            # Блокируем кнопки добавления
            self._disable_add_buttons()
            # Дальше не пытаемся загружать задачи
            self.tasks = {}
        else:
            # Загрузка задач
            loaded = tasks_storage.load_all_tasks(self.data_dir, self.storage_lock)
            self.tasks = {}  # словарь task_id -> TaskBlock
            for t in loaded:
                # Восстанавливаем задачу в UI
                self._restore_task_from_dict(t)


        # Отключаем кнопки, если есть ошибка ввода-вывода
        if self.io_error_flag:
            self._disable_add_buttons()

        # Привязка закрытия окна (без финального сохранения)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Сортируем задачи в визуальном интерфейсе
        self._reorder_tasks_in_frame(self.list_frame)
        self._reorder_tasks_in_frame(self.quiet_list_frame)


    def get_quiet_tasks(self):
        return [task for task in self.tasks.values() if task.is_quiet]
   
    def get_quiet_tasks_not_remained(self):
        return [task for task in self.tasks.values() if task.is_quiet and task.getRemained() <= 0]

    def get_non_quiet_tasks(self):
        return [task for task in self.tasks.values() if not task.is_quiet]

    def get_non_quiet_tasks_not_remained(self):
        return [task for task in self.tasks.values() if not task.is_quiet and task.getRemained() <= 0]


    def add_task(self, is_important: bool = False, is_quiet: bool = False):
        """Добавляет задачу, создаёт TaskBlock и сохраняет на диск."""
        if self.io_error_flag:
            return

        text = self.entry_task.get().strip()
        if not text:
            messagebox.showwarning("Ошибка ввода", "Наименование задачи не может быть пустым.")
            return

        alert_time = None

        # Сначала пробуем абсолютную дату
        year_str  = self.entry_abs_year.get() .strip()
        month_str = self.entry_abs_month.get().strip()
        day_str   = self.entry_abs_day.get()  .strip()
        time_str  = self.entry_abs_time.get() .strip()

        if year_str or month_str or day_str or time_str:
            try:
                alert_time = build_alert_time(year_str, month_str, day_str, time_str)
            except ValueError as e:
                messagebox.showerror("Ошибка", str(e))
                return
        else:
            # Fallback на относительное время, если не задана полная абсолютная дата
            try:
                now         = datetime.now()
                days_str    = self.entry_days.get()   .strip()
                hours_str   = self.entry_hours.get()  .strip()
                minutes_str = self.entry_minutes.get().strip()
                seconds_str = self.entry_seconds.get().strip()

                days    = int(days_str)    if days_str    else 0
                hours   = int(hours_str)   if hours_str   else 0
                minutes = int(minutes_str) if minutes_str else 0
                seconds = int(seconds_str) if seconds_str else 0

                total_seconds = (
                    days    * SECONDS_PER_DAY    +
                    hours   * SECONDS_PER_HOUR   +
                    minutes * SECONDS_PER_MINUTE +
                    seconds
                )

                if total_seconds <= 0:
                    self._on_test_sound_click()
                    raise ValueError

                if total_seconds > MAX_DELAY_DAYS * SECONDS_PER_DAY:
                    messagebox.showerror(
                        "Ошибка",
                        f"Слишком большая задержка. Максимум: {MAX_DELAY_DAYS} дней."
                    )
                    return

                if total_seconds <= 0:
                    messagebox.showerror("Ошибка", "Общее время должно быть больше 0 секунд.")
                    return

                alert_time = now + timedelta(seconds=total_seconds)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать задачу: {e}")
                return

        task_id = self._generate_task_id()
        self.task_id_counter += 1

        block = TaskBlock(
            parent=self,
            task_id=task_id,
            frame=self.quiet_list_frame if is_quiet else self.list_frame,
            text=text,
            alert_time=alert_time,
            is_important_initial=is_important,
            is_quiet=is_quiet
        )
        self.tasks[task_id] = block

        self.entry_task.delete(0, tk.END)
        # Сбрасываем относительные поля
        self.entry_days.delete(0, tk.END)
        self.entry_hours.delete(0, tk.END)
        self.entry_minutes.delete(0, tk.END)
        self.entry_seconds.delete(0, tk.END)
        # Сбрасываем абсолютные поля
        self.entry_abs_year.delete(0, tk.END)
        self.entry_abs_month.delete(0, tk.END)
        self.entry_abs_day.delete(0, tk.END)
        self.entry_abs_time.delete(0, tk.END)


        # Сохраняем на диск (alert_time=None превратится в текущее время)
        block.save()

        # Пересортировываем задачи по приоритету
        frame=self.quiet_list_frame if block.is_quiet else self.list_frame
        self._reorder_tasks_in_frame(frame)

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

    def _disable_add_buttons(self):
        """Блокирует кнопки добавления задач."""
        for btn in [self.btn_add_normal, self.btn_add_important, self.btn_add_quiet]:
            btn.config(state="disabled")

    def on_close(self):
        """Закрытие окна: ничего не сохраняем, просто уничтожаем окно."""
        save_opts(self.data_dir, self.opts)

        if not messagebox.askyesno("Закрыть список задач?", "Задачи перестанут отслеживаться в случае закрытия."):
            return

        self.quit_window()


    def _generate_task_id(self) -> str:
        """Генерирует уникальный task_id по новому правилу."""
        base = str(int(time.time() * 1000))
        task_id = f"{base}{self.task_id_counter}"
        self.task_id_counter += 1
        return task_id

    def destroy(self):
        self.lock_mgr.release()
        self.root.destroy()
        super().destroy() if hasattr(super(), "destroy") else None


    def quit_window(self):
        """Выход из приложения"""
        save_opts(self.data_dir, self.opts)
        self.root.quit()
        self.destroy()

if __name__ == "__main__":
    from datetime import datetime
    root = tk.Tk()
    app = App(root)
    root.mainloop()
