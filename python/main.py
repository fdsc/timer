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

    def _restore_task_from_dict(self, data: dict):
        """Восстанавливает задачу из словаря (после загрузки с диска) в UI."""
        task_id = data.get("task_id", "")
        if not task_id or task_id in self.tasks:
            print(f"Обнаружена задача без id или копия задачи с id {task_id} и текстом {data.get("text")}. Игнорирована.")
            return

        text         = data.get("text", "ошибка загрузки")
        is_important = bool(data.get("is_important", False))
        is_quiet     = bool(data.get("is_quiet", False))
        alert_time   = data.get("alert_time") # Уже переведено в datetime

        frame = self.quiet_list_frame if is_quiet else self.list_frame

        task_block = TaskBlock(
            parent=self,
            frame=frame,
            task_id=task_id,
            text=text,
            alert_time=alert_time,
            is_important_initial=is_important,
            is_quiet=is_quiet
        )

        self.tasks[task_id] = task_block

    def on_combo_change(self, event=None):
        current_idx = self.comboDefer.current()
        saved_idx   = self.opts["combodefer"]

        if current_idx != saved_idx:
            self.opts["combodefer"] = current_idx
            save_opts_debounced(self.data_dir, self.opts)

    def do_defer_list(self, tlist, base_seconds: int, lastDefer: datetime) -> datetime:
        applied_count = 0

        for i, task in enumerate(tlist):

            important_interval = base_seconds // 2 if not task.is_important else base_seconds
            normal_interval    = base_seconds

            # Определяем, какой интервал использовать для этой задачи
            interval_seconds = important_interval if task.is_important else normal_interval

            if i == 0:
                delta_sec = (task.defer_time - lastDefer).total_seconds()
                if delta_sec > interval_seconds:
                    break

                new_defer = max(lastDefer + timedelta(seconds=interval_seconds), task.defer_time)
                if new_defer != task.defer_time:
                    task.set_defer_time(new_defer)
                    lastDefer = new_defer
                    applied_count += 1

                continue


            prev_task = tlist[i - 1]
            delta_sec = (task.defer_time - prev_task.defer_time).total_seconds()

            if delta_sec <= interval_seconds:
                # Задача слишком близко к предыдущей — сдвигаем её
                new_defer = prev_task.defer_time + timedelta(seconds=interval_seconds)
                task.set_defer_time(new_defer)
                lastDefer = new_defer
                applied_count += 1
            else:
                break

        return lastDefer


    def do_defer(self, is_important: bool = False):
        """
        Откладывает НЕ тихие задачи так, чтобы между ними был заданный интервал.

        Параметры:
          is_important=False: важные задачи откладываются с половинным интервалом.
          is_important=True:  все задачи откладываются с полным интервалом.

        Логика:
          1. Игнорируем тихие задачи.
          2. Сортируем все не тихие задачи по alert_time (не только просроченные).
          3. Проходим по списку и «выравниваем» defer_time так, чтобы соседние задачи
             отстояли друг от друга не меньше чем на нужный интервал.
          4. Если очередная задача отстоит от предыдущей меньше чем на интервал —
             сдвигаем её на этот интервал вперёд от предыдущей.
          5. Как только встречаем задачу, которая уже отстоит больше чем на интервал,
             дальше не трогаем (процесс завершается).
        """

        notifier.cancel_notify_for_task(notifier.BULK_TASK_ID)
        for task in self.tasks.values():
            notifier.cancel_notify_for_task(task.task_id)

        now = datetime.now()

        # 1. Получаем все НЕ тихие задачи и сортируем по alert_time
        non_quiet_tasks_i = [t for t in self.tasks.values() if not t.is_quiet and t.is_important]
        non_quiet_tasks_n = [t for t in self.tasks.values() if not t.is_quiet and not t.is_important]
        if not non_quiet_tasks_i and not non_quiet_tasks_n:
            return

        non_quiet_tasks_i.sort(key=lambda t: t.alert_time)
        non_quiet_tasks_n.sort(key=lambda t: t.alert_time)

        # 2. Получаем интервал из comboDefer
        combo_value_str = self.comboDefer.get()
        try:
            base_seconds = int(combo_value_str)*60
        except (ValueError, TypeError):
            base_seconds = 60

        if base_seconds <= 0:
            base_seconds = 60

        lastDefer = self.do_defer_list(non_quiet_tasks_i, base_seconds, now)
        self.do_defer_list(non_quiet_tasks_n, base_seconds, lastDefer)

        # Пересортировать задачи в UI по defer_time, чтобы порядок соответствовал новому расписанию
        self._reorder_tasks_in_frame(self.list_frame)

    def _acquire_single_instance_lock(self):
        self.lock_fd = open(self.lock_file_path, "w")
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Приложение уже запущено. \nЕсли вам нужно запускать два экземпляра одновременно, запускайте их из-под разных пользователей с разными директориями для сохранения.")
            raise SystemExit(1)

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
