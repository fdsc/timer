import tkinter as tk
from datetime import datetime, timedelta
from notifier import show_alert

class TaskBlock:
    COLOR_NORMAL_BG = "#f0f0f0"
    COLOR_NORMAL_ACTIVE = "#e0e0e0"
    COLOR_IMPORTANT_BG = "#ffebee"
    COLOR_IMPORTANT_ACTIVE = "#ffcdd2"
    COLOR_FRAME_NORMAL = "#ffffff"
    COLOR_FRAME_IMPORTANT = "#fff0f0"

    def __init__(self, parent, task_id, text, alert_time, on_delete):
        self.task_id = task_id
        self.alert_time = alert_time  # notifier сам посчитает просрочку по этому полю
        self.text = text
        self.is_important = False
        self.on_delete = on_delete

        # Флаги для логики повторных оповещений
        self._alerted_once    = False       # было ли первое оповещение
        self._retry_scheduled = False     # запланировано ли повторное?
        self._retry_delay_sec_important = 60        # задержка перед повторным оповещением (сек). Для важных задач.
        self._retry_delay_sec_normal    = 900       # задержка перед повторным оповещением (сек). Для неважных задач.

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

        # Строка 2: время до/после оповещения
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

        # Строка 4: разделитель на всю ширину
        sep = tk.Frame(
            self.frame,
            height=2,
            bg="gray"
        )
        # columnspan=2 + sticky="ew" растягивают разделитель на всю ширину контейнера
        sep.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        # Гарантируем растяжение колонок внутри фрейма блока
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

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

        # ЛОГИКА ОПОВЕЩЕНИЙ
        if total_seconds == 0:
            # Первое оповещение
            if not self._alerted_once:
                self._alerted_once = True
                # Передаем только себя — notifier сам прочитает alert_time и посчитает просрочку
                show_alert(self)

                # Если задача важная, планируем повторное оповещение через 60 сек
                if self.is_important and not self._retry_scheduled:
                    self._retry_scheduled = True
                    self.frame.after(self._retry_delay_sec_important * 1000, self.trigger_retry_alert)
                if not self.is_important and not self._retry_scheduled:
                    self._retry_scheduled = True
                    self.frame.after(self._retry_delay_sec_normal * 1000, self.trigger_retry_alert)

        # Следующий тик через 1 секунду
        self.frame.after(1000, self.update_timer)

    def trigger_retry_alert(self):
        """Вызывается через 60 секунд после первого оповещения, если задача важная."""
        # Проверяем, существует ли ещё этот блок (не удалили ли задачу)
        if not hasattr(self, "frame") or not self.frame.winfo_exists():
            return

        # Показываем оповещение снова.
        # notifier увидит актуальный alert_time, посчитает новую просрочку
        # и при необходимости повысит urgency (если прошло больше 5 минут)
        show_alert(self)

        # Если нужно бесконечное напоминание каждую минуту — раскомментируй строку ниже:
        # self.frame.after(self._retry_delay_sec * 1000, self.trigger_retry_alert)
        # Сейчас реализовано только ОДНО повторное напоминание.

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
