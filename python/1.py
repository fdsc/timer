import tkinter as tk
from tkinter import messagebox
import time
from datetime import datetime, timedelta

class TaskBlock:
    """Один блок задачи: ровно 4 строки, как в ТЗ."""
    def __init__(self, parent, task_id, text, alert_time, on_delete, on_toggle):
        self.task_id = task_id
        self.alert_time = alert_time
        self.is_important = False
        self.on_delete = on_delete
        self.on_toggle = on_toggle

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

        # Строка 3: кнопки «Удалить» и «Важная/не важная»
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
            width=12
        )
        self.btn_priority.grid(row=2, column=1, sticky="w")

        # Строка 4: разделитель (подчёркивание)
        sep = tk.Frame(self.frame, height=2, bg="gray")
        sep.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # Запускаем обновление таймера для этого блока
        self.update_timer()

    def update_timer(self):
        now = datetime.now()
        delta = self.alert_time - now
        total_seconds = max(0, int(delta.total_seconds()))

        mins, secs = divmod(total_seconds, 60)
        hrs, mins = divmod(mins, 60)

        time_left_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        alert_datetime_str = self.alert_time.strftime("%Y-%m-%d %H:%M:%S")

        self.lbl_time_info.config(text=f"Осталось: {time_left_str} | Оповещение: {alert_datetime_str}")

        if total_seconds == 0:
            # Чтобы не спамить оповещениями, ставим флаг (простой вариант)
            if not hasattr(self, "_alerted"):
                self._alerted = True
                messagebox.showinfo("Оповещение", f"Время вышло!\nЗадача: {self.lbl_text.cget('text')}")
                # Если нужно автоудаление — раскомментируй:
                # self.on_delete(self.task_id)

        # Следующий тик через 1 секунду
        self.frame.after(1000, self.update_timer)

    def toggle_priority(self):
        self.is_important = not self.is_important
        if self.is_important:
            self.btn_priority.config(text="Не важная", bg="#ffebee", activebackground="#ffcdd2")
            self.frame.config(bg="#fff0f0")
            self.lbl_text.config(font=("TkDefaultFont", 11, "bold"))
        else:
            self.btn_priority.config(text="Важная", bg="SystemButtonFace", activebackground="SystemButtonFace")
            self.frame.config(bg="SystemFace")
            self.lbl_text.config(font=("TkDefaultFont", 11))


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Кастомные блоки задач (4 строки)")
        self.root.geometry("600x500")

        # Верхняя панель: ввод и кнопка
        top = tk.Frame(root)
        top.pack(fill="x", padx=8, pady=8)

        tk.Label(top, text="Задача:").pack(side="left")
        self.entry_task = tk.Entry(top, width=30)
        self.entry_task.pack(side="left", padx=(4, 8))

        tk.Label(top, text="Секунд до оповещения:").pack(side="left")
        self.entry_seconds = tk.Entry(top, width=8)
        self.entry_seconds.insert(0, "60")
        self.entry_seconds.pack(side="left", padx=(4, 8))

        btn_add = tk.Button(top, text="Добавить задачу", command=self.add_task)
        btn_add.pack(side="left")

        # Область списка задач (скролл через Canvas — опционально, здесь просто pack)
        self.list_frame = tk.Frame(root)
        self.list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tasks = {}  # task_id -> TaskBlock

    def add_task(self):
        text = self.entry_task.get().strip()
        if not text:
            messagebox.showwarning("Внимание", "Введите текст задачи.")
            return

        try:
            seconds = int(self.entry_seconds.get())
            if seconds <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Укажите положительное число секунд.")
            return

        task_id = str(int(time.time() * 1000)) + str(len(self.tasks))
        alert_time = datetime.now() + timedelta(seconds=seconds)

        block = TaskBlock(
            parent=self.list_frame,
            task_id=task_id,
            text=text,
            alert_time=alert_time,
            on_delete=self.delete_task,
            on_toggle=lambda tid=task_id: None  # не используется напрямую, логика внутри TaskBlock
        )
        self.tasks[task_id] = block

        # Очистка полей
        self.entry_task.delete(0, tk.END)
        self.entry_seconds.delete(0, tk.END)
        self.entry_seconds.insert(0, "60")

    def delete_task(self, task_id):
        block = self.tasks.pop(task_id, None)
        if block:
            block.frame.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
