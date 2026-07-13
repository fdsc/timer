import tkinter as tk
from tkinter import messagebox
import time
from datetime import timedelta
from task_block import TaskBlock

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Кастомные блоки задач (4 строки)")
        self.root.geometry("600x500")

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
        time_frame.pack(side="right")

        tk.Label(time_frame, text="Д:").pack(side="left")
        self.entry_days = tk.Entry(time_frame, width=3)
        # Пустое значение по умолчанию вместо "0"
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

        self.list_frame = tk.Frame(root)
        self.list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tasks = {}


    def add_task(self, is_important: bool = False):
        text = self.entry_task.get().strip()
        if not text:
            import tkinter.messagebox as mb
            mb.showwarning("Внимание", "Введите текст задачи.")
            return

        try:
            # Пустая строка интерпретируется как 0
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
        except ValueError:
            import tkinter.messagebox as mb
            mb.showerror("Ошибка", "Укажите неотрицательные целые числа для дней, часов, минут и секунд (можно оставить пустыми — будет 0).")
            return

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

        task_id = str(int(time.time() * 1000)) + str(len(self.tasks))
        alert_time = datetime.now() + timedelta(seconds=total_seconds)

        block = TaskBlock(
            parent=self.list_frame,
            task_id=task_id,
            text=text,
            alert_time=alert_time,
            on_delete=self.delete_task,
            is_important_initial=is_important
        )
        self.tasks[task_id] = block

        self.entry_task   .delete(0, tk.END)
        # Сбрасываем поля в пустые строки
        self.entry_days   .delete(0, tk.END)
        self.entry_hours  .delete(0, tk.END)
        self.entry_minutes.delete(0, tk.END)
        self.entry_seconds.delete(0, tk.END)


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


if __name__ == "__main__":
    from datetime import datetime
    root = tk.Tk()
    app = App(root)
    root.mainloop()
