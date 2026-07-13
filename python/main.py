import tkinter as tk
from tkinter import messagebox
import time
from datetime import timedelta
from task_block import TaskBlock  # импорт нашего модуля

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

        # Область списка задач
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
            on_delete=self.delete_task
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
    from datetime import datetime  # нужен для main, но импортируем тут, чтобы не дублировать в task_block
    root = tk.Tk()
    app = App(root)
    root.mainloop()
