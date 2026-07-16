#!/bin/python3
# Требуются пакеты sox, tk, zenity
# Проверка наличия tkinter: python3 -m tkinter

import tkinter as tk
from tkinter import ttk,messagebox
from datetime import timedelta, datetime
from pathlib import Path
import traceback
import threading
import fcntl


import notifier
import tasks_storage
from config_manager import get_user_data_dir, load_or_create_opts, save_opts, init_media_config, load_media_paths, save_opts_debounced

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
from main_gui_window import WindowMixin
from main_gui_helper import Main_HelperMixin

# nuitka???

class App(
    LoadConfigPathMixin,
    InputPanelMixin,
    TabsLayoutMixin,
    ResizeHandlerMixin,
    TaskFramesSortingLogicMixin,
    AudioControlMixin,
    WindowMixin,
    Main_HelperMixin
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


if __name__ == "__main__":
    from datetime import datetime
    root = tk.Tk()
    app = App(root)
    root.mainloop()
