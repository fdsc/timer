import tkinter as tk
from tkinter import ttk,messagebox
from config_manager import save_opts, save_opts_debounced

class WindowMixin:
    def destroy(self):
        self.lock_mgr.release()
        self.root.destroy()
        super().destroy() if hasattr(super(), "destroy") else None


    def quit_window(self):
        """Выход из приложения"""
        save_opts(self.data_dir, self.opts)
        self.root.quit()
        self.destroy()

    def on_close(self):
        """Закрытие окна: ничего не сохраняем, просто уничтожаем окно."""
        save_opts(self.data_dir, self.opts)

        if not messagebox.askyesno("Закрыть список задач?", "Задачи перестанут отслеживаться в случае закрытия."):
            return

        self.quit_window()
