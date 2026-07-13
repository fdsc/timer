import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

class TaskBlock:
    """
    Кастомный блок задачи: ровно 4 строки.
    1: текст задачи
    2: время до оповещения + дата/время оповещения
    3: кнопки «Удалить» и «Важная/не важная»
    4: разделитель (подчёркивание)
    """

    # Цвета: используем явные значения вместо SystemButtonFace
    COLOR_NORMAL_BG = "#f0f0f0"       # нейтральный светло‑серый фон кнопки
    COLOR_NORMAL_ACTIVE = "#e0e0e0"   # фон при наведении
    COLOR_IMPORTANT_BG = "#ffebee"    # розовый для важной
    COLOR_IMPORTANT_ACTIVE = "#ffcdd2"
    COLOR_FRAME_NORMAL = "#ffffff"
    COLOR_FRAME_IMPORTANT = "#fff0f0"

    def __init__(self, parent, task_id, text, alert_time, on_delete):
        self.task_id = task_id
        self.alert_time = alert_time
        self.is_important = False
        self.on_delete = on_delete

        # Контейнер блока
        self.frame = tk.Frame(parent, bd=1, relief="solid", padx=4, pady=4)
        self.frame.pack(fill="x", pady=(0, 2))

        # Строка 1: текст задачи
        self.lbl_text = tk.Label(
            self.frame,
            text=text,
            anchor="w",
            justify="left",
            font=("TkDefaultFont", 11)
        )
        self.lbl_text.grid(row=0, column=0, sticky="w", columnspan=2)

        # Строка 2: время до оповещения и дата/время оповещения
        self.lbl_time_info = tk.Label(
            self.frame,
            text="",
            anchor="w",
            justify="left",
            fg="#555"
        )
        self.lbl_time_info.grid(row=1, column=0, sticky="w", columnspan=2)

        # Строка 3: кнопки
        btn_del = tk.Button(
            self.frame,
            text="Удалить",
            command=lambda: self.on_delete(self.task_id),
            width=10
        )
        btn_del.grid(row=2, column=0, padx=(0, 8), sticky="w")

        self.btn_priority = tk.Button(
            self.frame,
            text="Важная",
            command=self.toggle_priority,
            width=12,
            bg=self.COLOR_NORMAL_BG,
            activebackground=self.COLOR_NORMAL_ACTIVE
        )
        self.btn_priority.grid(row=2, column=1, sticky="w")

        # Строка 4: разделитель
        sep = tk.Frame(self.frame, height=2, bg="gray")
        sep.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # Таймер
        self.update_timer()

    def update_timer(self):
        now = datetime.now()
        delta = self.alert_time - now
        total_seconds = max(0, int(delta.total_seconds()))

        mins, secs = divmod(total_seconds, 60)
        hrs, mins = divmod(mins, 60)

        time_left_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        alert_datetime_str = self.alert_time.strftime("%Y-%m-%d %H:%M:%S")

        self.lbl_time_info.config(
            text=f"Осталось: {time_left_str} | Оповещение: {alert_datetime_str}"
        )

        if total_seconds == 0:
            if not hasattr(self, "_alerted"):
                self._alerted = True
                messagebox.showinfo(
                    "Оповещение",
                    f"Время вышло!\nЗадача: {self.lbl_text.cget('text')}"
                )
                # Если нужно автоудаление — раскомментируй:
                # self.on_delete(self.task_id)

        self.frame.after(1000, self.update_timer)

    def toggle_priority(self):
        self.is_important = not self.is_important
        if self.is_important:
            self.btn_priority.config(
                text="Не важная",
                bg=self.COLOR_IMPORTANT_BG,
                activebackground=self.COLOR_IMPORTANT_ACTIVE
            )
            self.frame.config(bg=self.COLOR_FRAME_IMPORTANT)
            self.lbl_text.config(font=("TkDefaultFont", 11, "bold"))
        else:
            self.btn_priority.config(
                text="Важная",
                bg=self.COLOR_NORMAL_BG,
                activebackground=self.COLOR_NORMAL_ACTIVE
            )
            self.frame.config(bg=self.COLOR_FRAME_NORMAL)
            self.lbl_text.config(font=("TkDefaultFont", 11))
