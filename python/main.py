#!/bin/python3
# Требуются пакеты sox, tk, zenity
# Проверка наличия tkinter: python3 -m tkinter

import tkinter as tk
from tkinter import messagebox
import time
from datetime import timedelta, datetime
from pathlib import Path

import notifier
from task_block import TaskBlock
from config_manager import get_user_data_dir, load_or_create_opts, save_opts, init_media_config, load_media_paths


# nuitka???

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Кастомные блоки задач (4 строки)")
        self.root.geometry("1024x768")

        # Получаем путь к папке данных (спрашивает при первом запуске)
        self.data_dir = get_user_data_dir()
        # Загружаем или создаём opts.json
        self.opts = load_or_create_opts(self.data_dir)
        # Инициализируем громкость из настроек
        self.volume_factor = self.opts.get("volume_percent", 100) / 100.0
        # Несохранённое значение громкости
        self._pending_volume_value = None

        # Инициализируем media_config.txt, если нет
        self.media_config_path = init_media_config(self.data_dir)

        # Загружаем пути к медиафайлам
        media_paths = load_media_paths(self.media_config_path)
        notifier.MEDIA_PATHS = media_paths  # передаём в notifier


        top = tk.Frame(root)
        top.pack(fill="x", padx=8, pady=8)

        # Строка 1: текст задачи
        task_row = tk.Frame(top)
        task_row.pack(fill="x", pady=(0, 4))

        tk.Label(task_row, text="Задача:").pack(side="left")
        self.entry_task = tk.Entry(task_row, width=30)
        self.entry_task.pack(side="left", padx=(4, 8))
        # Привязываем контекстное меню для копирования текста задачи
        self._setup_copy_menu(self.entry_task)

        # Строка 2: кнопки добавления + компоненты времени (справа от кнопок)
        time_and_btn_row = tk.Frame(top)
        time_and_btn_row.pack(fill="x", pady=(0, 0))

        # Кнопки добавления (слева во второй строке)
        btn_add_normal = tk.Button(
            time_and_btn_row,
            text="+",
            command=lambda: self.add_task(is_important=False),
            width=2
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

        # Компоненты времени (справа во второй строке)
        time_frame = tk.Frame(time_and_btn_row)
        time_frame.pack(side="left")

        tk.Label(time_frame, text="Д:").pack(side="left")
        self.entry_days = tk.Entry(time_frame, width=3)
        self.entry_days.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="Ч:").pack(side="left")
        self.entry_hours = tk.Entry(time_frame, width=3)
        self.entry_hours.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="М:").pack(side="left")
        self.entry_minutes = tk.Entry(time_frame, width=3)
        self.entry_minutes.pack(side="left", padx=(0, 8))

        tk.Label(time_frame, text="С:").pack(side="left")
        self.entry_seconds = tk.Entry(time_frame, width=3)
        self.entry_seconds.pack(side="left", padx=(0, 0))

        # Третья строка: абсолютная дата и регулятор громкости
        third_row = tk.Frame(root)
        third_row.pack(fill="x", padx=8, pady=4)

        # Абсолютная дата (слева)
        abs_date_frame = tk.Frame(third_row)
        abs_date_frame.pack(side="left", anchor="e")

        tk.Label(abs_date_frame, text="Год:").pack(side="left")
        self.entry_abs_year = tk.Entry(abs_date_frame, width=5)
        self.entry_abs_year.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="Месяц:").pack(side="left")
        self.entry_abs_month = tk.Entry(abs_date_frame, width=3)
        self.entry_abs_month.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="День:").pack(side="left")
        self.entry_abs_day = tk.Entry(abs_date_frame, width=3)
        self.entry_abs_day.pack(side="left", padx=(0, 8))

        tk.Label(abs_date_frame, text="Время (Ч:М):").pack(side="left")
        self.entry_abs_time = tk.Entry(abs_date_frame, width=7)
        self.entry_abs_time.insert(0, "")
        self.entry_abs_time.pack(side="left", padx=(0, 0))

        # Регулятор громкости (справа)
        vol_frame = tk.Frame(third_row)
        vol_frame.pack(side="right", anchor="e")  # anchor="e" прижмёт фрейм вправо

        # Сначала метка «Громкость:»
        lbl_vol_label = tk.Label(vol_frame, text="Громкость:")
        lbl_vol_label.pack(side="left", padx=(0, 8))

        # Слайдер
        self.scale_volume = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient="horizontal",
            length=200,
            command=self._on_volume_change
        )
        self.scale_volume.set(self.volume_factor*100)
        self.scale_volume.pack(side="left", padx=(4, 0))

        # Метка с процентами (справа от слайдера)
        self.lbl_vol_value = tk.Label(vol_frame, text=str(int(self.volume_factor*100)) + "%", width=4, anchor="e")
        self.lbl_vol_value.pack(side="left", padx=(8, 0))

        # Привязываем клик по метке громкости для ручного теста звука
        self.lbl_vol_value.bind("<Button-1>", self._on_test_sound_click)


        self.list_frame = tk.Frame(root)
        self.list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tasks = {}


    def add_task(self, is_important: bool = False):
        text = self.entry_task.get().strip()
        if not text:
            mb.showwarning("Внимание", "Введите текст задачи.")
            return

        alert_time = None

        # Сначала пробуем абсолютную дату
        year_str = self.entry_abs_year.get().strip()
        month_str = self.entry_abs_month.get().strip()
        day_str = self.entry_abs_day.get().strip()
        time_str = self.entry_abs_time.get().strip()

        if year_str and month_str and day_str:
            try:
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)

                # Парсим время: если пусто — берём текущее; если есть — разбираем Ч:М
                now = datetime.now()
                hour = now.hour
                minute = now.minute

                if time_str:
                    parts = time_str.split(":")
                    if len(parts) == 1:
                        hour = int(parts[0])
                    elif len(parts) >= 2:
                        hour = int(parts[0])
                        minute = int(parts[1])

                alert_time = datetime(year, month, day, hour, minute, 0)
            except ValueError:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка", "Некорректная абсолютная дата или время. Проверьте формат.")
                return
        else:
            # Иначе используем относительное время
            try:
                days_str = self.entry_days.get().strip()
                hours_str = self.entry_hours.get().strip()
                minutes_str = self.entry_minutes.get().strip()
                seconds_str = self.entry_seconds.get().strip()

                days = int(days_str) if days_str else 0
                hours = int(hours_str) if hours_str else 0
                minutes = int(minutes_str) if minutes_str else 0
                seconds = int(seconds_str) if seconds_str else 0

                if days < 0 or hours < 0 or minutes < 0 or seconds < 0:
                    raise ValueError

                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds

                MAX_DELAY_DAYS = 380
                if total_seconds > MAX_DELAY_DAYS * 86400:
                    import tkinter.messagebox as mb
                    mb.showerror(
                        "Ошибка",
                        f"Слишком большая задержка. Максимум: {MAX_DELAY_DAYS} дней."
                    )
                    return

                if total_seconds <= 0:
                    import tkinter.messagebox as mb
                    mb.showerror("Ошибка", "Общее время должно быть больше 0 секунд.")
                    return

                alert_time = datetime.now() + timedelta(seconds=total_seconds)
            except ValueError:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка", "Укажите корректные неотрицательные целые числа для дней, часов, минут и секунд (можно оставить пустыми — будет 0).")
                return

        task_id = str(int(time.time() * 1000)) + str(len(self.tasks))

        block = TaskBlock(
            parent=self,
            task_id=task_id,
            text=text,
            alert_time=alert_time,
            on_delete=self.delete_task,
            is_important_initial=is_important
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
        print(len(active_tasks))
        for t in active_tasks:
            print(t.text)
        if len(active_tasks) > 2 or countOfPendingNotifications > 1:
            show_bulk_critical_alert(self, active_tasks, icon_path=None)
            return True
        else:
            return False


    def _on_volume_change(self, val: str):
        """Обработчик изменения громкости: обновляет метку, множитель и сохраняет в opts.json."""
        v = int(val)
        self.lbl_vol_value.config(text=f"{v}%")
        self.volume_factor = v / 100.0

        # Обновляем значение в словаре настроек
        self.opts["volume_percent"] = v
        self._pending_volume_value  = v

        # Сохраняем в файл с отложенным выполнением
        self.root.after(3000, self.save_pending_volume)

    def save_pending_volume(self):
        """Гарантированно сохраняет последнее значение громкости, если оно ещё не было сохранено."""
        if self._pending_volume_value is not None:
            self.opts["volume_percent"] = self._pending_volume_value
            save_opts(self.data_dir, self.opts)
            self._pending_volume_value = None

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


    def delete_task(self, task_id):
        block = self.tasks.get(task_id)
        if not block:
            return

        confirm = tk.messagebox.askyesno(
            "Удалить задачу?",
            f"Удалить задачу «{block.text}»?"
        )
        if not confirm:
            return

        del self.tasks[task_id]
        block.frame.destroy()
        block._stopped = True


if __name__ == "__main__":
    from datetime import datetime
    root = tk.Tk()
    app = App(root)
    root.mainloop()
    
    # Завершение работы приложения
    app.save_pending_volume()
