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
from config_manager import get_user_data_dir, load_or_create_opts, save_opts, init_media_config, load_media_paths
from date_utils import build_alert_time


# nuitka???

class App:
    def rootResize(self, e):
        self.opts["geometry"] = self.root.geometry()
        self.root.after(3000, save_opts, self.data_dir, self.opts)

        for task in self.tasks.values():
            if task._stopped: continue

            task.lbl_text.configure(
                wraplength=self.canvas_m.winfo_width() - self.scrollbar.winfo_width()-8
            )

    def __init__(self, root):
        self.root = root
        self.root.title("Кастомные блоки задач (4 строки)")

        # Счётчик задач для именования новых задач
        self.task_id_counter=0
        # Блокировка для доступа к файлам
        self.storage_lock = threading.Lock()
        # Флаг неисправности ввода-вывода
        self.io_error_flag = False

        # Получаем путь к папке данных (спрашивает при первом запуске)
        self.data_dir = get_user_data_dir()

        # ------------------------------------------------------
        # Блокировка для предотвращения запуска двух экземпляров
        self.lock_file_path = Path(self.data_dir) / ".lock"
        self._acquire_single_instance_lock()

        # Загружаем или создаём opts.json
        self.opts = load_or_create_opts(self.data_dir)
        # Инициализируем громкость из настроек
        self.volume_factor = self.opts.get("volume_percent", 100) / 100.0
        # Несохранённое значение громкости
        self._pending_volume_value = None


        self.root.geometry(self.opts["geometry"])
        self.root.bind("<Configure>", self.rootResize)

        # Инициализируем media.conf, если нет
        self.media_config_path = init_media_config(self.data_dir)

        # Загружаем пути к медиафайлам
        media_paths = load_media_paths(self.media_config_path)
        notifier.MEDIA_PATHS = media_paths  # передаём в notifier

        # Новое поле: состояние логики общего фонового сигнала
        self.alert_sound_state = {
            "first_pending_add_time": None,      # datetime | None
            "is_general_mode_active": False,     # bool
            "general_sound_timer_id": None       # int | None (ID от root.after)
        }


        top = tk.Frame(root)
        top.pack(fill="x", padx=8, pady=8)

        # Строка 1: текст задачи
        task_row = tk.Frame(top)
        task_row.pack(fill="x", pady=(0, 4))

        tk.Label(task_row, text="Задача:").pack(side="left")
        self.entry_task = tk.Entry(task_row, width=50)
        self.entry_task.pack(side="left", padx=(4, 8))
        # Привязываем контекстное меню для копирования текста задачи
        self._setup_copy_menu(self.entry_task)

        # Отложить
        btn_defer = tk.Button(
            task_row,
            text="Отл",
            command=lambda: self.do_defer(is_important=False),
            width=2,
            bg="#888888",
            fg="#000000",
            activebackground="#000000",
            activeforeground="#FFFFFF"
        )
        btn_defer.pack(side="left", padx=(0, 2))

        self.comboDefer = ttk.Combobox(task_row, values=helper.get10percentList(), width=10, state="readonly")
        self.comboDefer.current(self.opts["combodefer"])
        self.comboDefer.pack(side="left", padx=(0, 8))      # или grid, если используешь grid
        self.comboDefer.bind("<<ComboboxSelected>>", self.on_combo_change)

        # Индикатор просроченных тихих задач на основной вкладке
        self.lbl_quiet_overdue_indicator = tk.Label(
            top,
            text="⚠️ Есть просроченные тихие задачи!",
            fg="#b71c1c",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_quiet_overdue_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.lbl_quiet_overdue_indicator.pack_forget()  # скрываем по умолчанию


        # Строка 2: кнопки добавления + компоненты времени (справа от кнопок)
        time_and_btn_row = tk.Frame(top)
        time_and_btn_row.pack(fill="x", pady=(0, 0))

        # Кнопки добавления (слева во второй строке)
        btn_add_normal = tk.Button(
            time_and_btn_row,
            text="+",
            command=lambda: self.add_task(is_important=False),
            width=2,
            bg="#e0ffe0",
            activebackground="#c6e9c6"
        )
        btn_add_normal.pack(side="left", padx=(0, 8))

        btn_add_important = tk.Button(
            time_and_btn_row,
            text="!",
            command=lambda: self.add_task(is_important=True),
            width=2,
            bg="#ffebee",
            activebackground="#ffcdd2"
        )
        btn_add_important.pack(side="left", padx=(0, 16))

        # Кнопка тихой задачи
        btn_add_quiet = tk.Button(
            time_and_btn_row,
            text="V",
            command=lambda: self.add_task(is_important=False, is_quiet=True),
            width=2,
            bg="#888888",
            activebackground="#AAAAAA"
        )
        btn_add_quiet.pack(side="left", padx=(0, 8))

        # Компоненты времени (справа во второй строке)
        time_frame = tk.Frame(time_and_btn_row)
        time_frame.pack(side="left")

        tk.Label(time_frame, text="Д:").pack(side="left")
        self.entry_days = tk.Entry(time_frame, width=5)
        self.entry_days.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="Ч:").pack(side="left")
        self.entry_hours = tk.Entry(time_frame, width=5)
        self.entry_hours.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="М:").pack(side="left")
        self.entry_minutes = tk.Entry(time_frame, width=5)
        self.entry_minutes.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="С:").pack(side="left")
        self.entry_seconds = tk.Entry(time_frame, width=5)
        self.entry_seconds.pack(side="left", padx=(0, 0))

        # Третья строка: абсолютная дата и регулятор громкости
        third_row = tk.Frame(root)
        third_row.pack(fill="x", padx=8, pady=4)

        # Абсолютная дата (слева)
        abs_date_frame = tk.Frame(third_row)
        abs_date_frame.pack(side="left", anchor="e")

        tk.Label(abs_date_frame, text="Год:").pack(side="left")
        self.entry_abs_year = tk.Entry(abs_date_frame, width=7)
        self.entry_abs_year.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="Месяц:").pack(side="left")
        self.entry_abs_month = tk.Entry(abs_date_frame, width=5)
        self.entry_abs_month.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="День:").pack(side="left")
        self.entry_abs_day = tk.Entry(abs_date_frame, width=5)
        self.entry_abs_day.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="Время (Ч:М):").pack(side="left")
        self.entry_abs_time = tk.Entry(abs_date_frame, width=9)
        self.entry_abs_time.insert(0, "")
        self.entry_abs_time.pack(side="left", padx=(0, 0))

        # Регулятор громкости (справа)
        vol_frame = tk.Frame(third_row)
        vol_frame.pack(side="right", anchor="e")  # anchor="e" прижмёт фрейм вправо

        # Кнопка глушения звука
        self.is_muted = True
        self.btn_mute = tk.Button(
            vol_frame,
            text="O",
            command=self.toggle_mute,
            width=2,
            activebackground="#ffaaaa"
        )
        self.toggle_mute()
        self.btn_mute.pack(side="left", padx=(4, 8))

        # Сначала метка «Громкость:»
        lbl_vol_label = tk.Label(vol_frame, text="Громкость:")
        lbl_vol_label.pack(side="left", padx=(0, 8))

        # Слайдер
        self.scale_volume = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            resolution=0.5,
            orient="horizontal",
            length=200,
            showvalue=False,
            tickinterval=0,
            command=self._on_volume_change
        )
        self.scale_volume.set(self.volume_factor*100)
        self.scale_volume.pack(side="left", padx=(4, 0))

        # Метка с процентами (справа от слайдера)
        self.lbl_vol_value = tk.Label(vol_frame, text=str(int(self.volume_factor*100)) + "%", width=5, anchor="e")
        self.lbl_vol_value.pack(side="left", padx=(8, 0))

        # Привязываем клик по метке громкости для ручного теста звука
        self.lbl_vol_value.bind("<Button-1>", self._on_test_sound_click)

        # Здесь размещаются как тихие задачи, так и обычные
        self.tasks = {}

        # ----- Вкладки -----
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # Основная вкладка
        self.main_tab_frame = tk.Frame(self.notebook)
        self.notebook.add(self.main_tab_frame, text="Задачи")
        
        self.canvas_m = tk.Canvas(self.main_tab_frame, highlightthickness=0)
        self.canvas_m.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.main_tab_frame, orient="vertical", command=self.canvas_m.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas_m.configure(yscrollcommand=self.scrollbar.set)

        self.list_frame = tk.Frame(self.canvas_m)
        self.list_frame.bind("<Configure>", lambda e: self.canvas_m.configure(scrollregion=self.canvas_m.bbox("all")))
        self.canvas_m.create_window((0, 0), window=self.list_frame, anchor="nw")
        #self.list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Вкладка тихих задач
        self.quiet_tab_frame = tk.Frame(self.notebook)
        self.notebook.add(self.quiet_tab_frame, text="Тихие")

        self.canvas_q = tk.Canvas(self.quiet_tab_frame, highlightthickness=0)
        self.canvas_q.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.quiet_tab_frame, orient="vertical", command=self.canvas_q.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas_q.configure(yscrollcommand=self.scrollbar.set)

        self.quiet_list_frame = tk.Frame(self.canvas_q)
        self.quiet_list_frame.bind("<Configure>", lambda e: self.canvas_q.configure(scrollregion=self.canvas_q.bbox("all")))
        self.canvas_q.create_window((0, 0), window=self.quiet_list_frame, anchor="nw")


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

    def get_non_quiet_tasks(self):
        return [task for task in self.tasks.values() if not task.is_quiet]


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

                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                if total_seconds <= 0:
                    raise ValueError

                MAX_DELAY_DAYS = 380
                if total_seconds > MAX_DELAY_DAYS * 86400:
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


    def _reorder_tasks_in_frame(self, frame: tk.Frame):
        """Переупаковывает блоки задач в frame согласно приоритету: важные и просроченные — выше."""
        # Получаем все виджеты-потомки (это наши TaskBlock.frame)
        children = list(frame.winfo_children())
        # Сортируем: сначала важные, потом просроченные, потом по времени создания (по убыванию task_id)
        def sort_key(child):
            # child — это frame внутри TaskBlock; нужно получить сам TaskBlock
            # У нас нет прямой ссылки, поэтому ищем по task_id в self.tasks
            # Предполагаем, что task_id хранится в self у TaskBlock, а frame уникален
            block = None
            for t in self.tasks.values():
                if t.frame is child:
                    block = t
                    break
            if not block:
                return (True, 0, 0)  # на всякий случай — в конец
            now = datetime.now()
            is_overdue = block.alert_time is not None and (now - block.alert_time).total_seconds() >= 0
            # Приоритет: (не просрочен → 1, (не важный → 1, важный → 0), просрочен → 0), затем alert_time (чем больше, тем новее)
            if is_overdue:
                if block.is_important:
                    return (0, 0, block.alert_time.timestamp())
                else:
                    return (0, 1, block.alert_time.timestamp())
            else:
                return (1, 0, block.alert_time.timestamp())

        children.sort(key=sort_key)

        # Переpack-им в новом порядке
        for child in children:
            child.pack_forget()
        for child in children:
            child.pack(fill="x", pady=(0, 2))


    def check_bulk_alerts(self, countOfPendingNotifications):
        """
        Проверяет количество активных задач и при необходимости показывает
        одно массовое критическое оповещение вместо множества одиночных.
        """
        now = datetime.now()
        # Считаем «активными» все задачи, у которых alert_time уже наступило или прошло
        active_tasks = [
            t for t in self.tasks.values()
            if t.alert_time is None or (now - t.alert_time).total_seconds() >= 0
        ]

        from notifier import show_bulk_critical_alert

        if len(active_tasks) > 2 or countOfPendingNotifications > 1:
            show_bulk_critical_alert(self, active_tasks, icon_path=None)
            return True
        else:
            return False


    def _on_volume_change(self, val: str):
        """Обработчик изменения громкости: обновляет метку, множитель и сохраняет в opts.json."""
        v = float(val)
        self.lbl_vol_value.config(text=f"{v}%")
        self.volume_factor = v / 100.0

        # Обновляем значение в словаре настроек
        self.opts["volume_percent"] = v
        self._pending_volume_value  = v

        # Сохраняем в файл с отложенным выполнением
        self.root.after(3000, save_opts, self.data_dir, self.opts)


    def _on_test_sound_click(self, event=None):
        """Проигрывает тестовый звук при клике по метке с процентом громкости."""
        sound_file = "/usr/share/sounds/freedesktop/stereo/complete.oga"
        from notifier import play_sound
        play_sound(sound_file, self.volume_factor)

    def _setup_copy_menu(self, widget):
        """Создаёт контекстное меню с пунктом «Копировать» для виджета Entry."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))

        def popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", popup)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.config(text="X", bg="#FF0000")
        else:
            self.btn_mute.config(text="O", bg="#888888")

    def _disable_add_buttons(self):
        """Блокирует кнопки добавления задач."""
        for btn in [self.btn_add_normal, self.btn_add_important, self.btn_add_quiet]:
            btn.config(state="disabled")

    def on_close(self):
        """Закрытие окна: ничего не сохраняем, просто уничтожаем окно."""
        save_opts(self.data_dir, self.opts)   # твоё сохранение

        if not messagebox.askyesno("Закрыть список задач?", "Задачи перестанут отслеживаться в случае закрытия."):
            return

        self.root.destroy()

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
            print(f"Обнаружена задача без id или копия задачи с id {task_id} и текстом {task_id.text}. Игнорирована.")
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
            save_opts(self.data_dir, self.opts)

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

        now = datetime.now()

        # 1. Получаем все НЕ тихие задачи и сортируем по alert_time
        non_quiet_tasks = [t for t in self.tasks.values() if not t.is_quiet]
        if not non_quiet_tasks:
            return

        non_quiet_tasks.sort(key=lambda t: t.alert_time)

        # 2. Получаем интервал из comboDefer
        combo_value_str = self.comboDefer.get()
        try:
            base_seconds = int(combo_value_str)*60
        except (ValueError, TypeError):
            base_seconds = 60

        if base_seconds <= 0:
            base_seconds = 60


        important_interval = base_seconds // 2 if not is_important else base_seconds
        normal_interval    = base_seconds

        applied_count = 0

        for i, task in enumerate(non_quiet_tasks):

            # Определяем, какой интервал использовать для этой задачи
            interval_seconds = important_interval if task.is_important else normal_interval

            if i == 0:
                delta_sec = (task.defer_time - now).total_seconds()
                if delta_sec > interval_seconds:
                    break

                new_defer = max(now + timedelta(seconds=interval_seconds), task.defer_time)
                if new_defer != task.defer_time:
                    task.set_defer_time(new_defer)
                    applied_count += 1

                continue


            prev_task = non_quiet_tasks[i - 1]
            delta_sec = (task.defer_time - prev_task.defer_time).total_seconds()

            if delta_sec <= interval_seconds:
                # Задача слишком близко к предыдущей — сдвигаем её
                new_defer = prev_task.defer_time + timedelta(seconds=interval_seconds)
                task.set_defer_time(new_defer)
                applied_count += 1
            else:
                break

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
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()
        except Exception:
            pass
        super().destroy() if hasattr(super(), "destroy") else None

if __name__ == "__main__":
    from datetime import datetime
    root = tk.Tk()
    app = App(root)
    root.mainloop()
