import tkinter as tk
from tkinter import ttk
import helper
from constants import (
    COLOR_BTN_DEFER_BG, COLOR_BTN_DEFER_FG, COLOR_BTN_DEFER_ACTIVE_BG,
    COLOR_BTN_DEFER_ACTIVE_FG, COLOR_BTN_ADD_NORMAL_BG, COLOR_BTN_ADD_NORMAL_ACTIVE_BG,
    COLOR_BTN_ADD_IMPORTANT_BG, COLOR_BTN_ADD_IMPORTANT_ACTIVE_BG,
    COLOR_BTN_ADD_QUIET_BG, COLOR_BTN_ADD_QUIET_ACTIVE_BG, COLOR_BTN_MUTE_HOVER_BG
)

class InputPanelMixin:
    def build_input_panel(self, root):
        top = tk.Frame(root)
        top.pack(fill="x", padx=8, pady=8)

        task_row = tk.Frame(top)
        task_row.pack(fill="x", pady=(0, 4))

        tk.Label(task_row, text="Задача:").pack(side="left")
        self.entry_task = tk.Entry(task_row, width=50)
        self.entry_task.pack(side="left", padx=(4, 8))
        self._setup_copy_menu(self.entry_task)

        btn_defer = tk.Button(
            task_row,
            text="Отл",
            command=lambda: self.do_defer(is_important=False),
            width=2,
            bg=COLOR_BTN_DEFER_BG,
            fg=COLOR_BTN_DEFER_FG,
            activebackground=COLOR_BTN_DEFER_ACTIVE_BG,
            activeforeground=COLOR_BTN_DEFER_ACTIVE_FG
        )
        btn_defer.pack(side="left", padx=(0, 2))

        self.comboDefer = ttk.Combobox(task_row, values=helper.get10percentList(), width=10, state="readonly")
        self.comboDefer.current(self.opts["combodefer"])
        self.comboDefer.pack(side="left", padx=(0, 8))
        self.comboDefer.bind("<<ComboboxSelected>>", self.on_combo_change)

        self.lbl_quiet_overdue_indicator = tk.Label(
            top,
            text="⚠️ Есть просроченные тихие задачи!",
            fg="#b71c1c",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_quiet_overdue_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.lbl_quiet_overdue_indicator.pack_forget()

        time_and_btn_row = tk.Frame(top)
        time_and_btn_row.pack(fill="x", pady=(0, 0))

        self.btn_add_normal = tk.Button(
            time_and_btn_row,
            text="+",
            command=lambda: self.add_task(is_important=False),
            width=2,
            bg=COLOR_BTN_ADD_NORMAL_BG,
            activebackground=COLOR_BTN_ADD_NORMAL_ACTIVE_BG
        )
        self.btn_add_normal.pack(side="left", padx=(0, 8))

        self.btn_add_important = tk.Button(
            time_and_btn_row,
            text="!",
            command=lambda: self.add_task(is_important=True),
            width=2,
            bg=COLOR_BTN_ADD_IMPORTANT_BG,
            activebackground=COLOR_BTN_ADD_IMPORTANT_ACTIVE_BG
        )
        self.btn_add_important.pack(side="left", padx=(0, 16))

        self.btn_add_quiet = tk.Button(
            time_and_btn_row,
            text="V",
            command=lambda: self.add_task(is_important=False, is_quiet=True),
            width=2,
            bg=COLOR_BTN_ADD_QUIET_BG,
            activebackground=COLOR_BTN_ADD_QUIET_ACTIVE_BG
        )
        self.btn_add_quiet.pack(side="left", padx=(0, 8))

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
            activebackground=COLOR_BTN_MUTE_HOVER_BG
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
