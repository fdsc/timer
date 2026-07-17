import tkinter as tk

class ToolTip:
    # self.create_tooltip(self.entry, "")
    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            # Создаем всплывающее окно
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)  # Убираем заголовок окна
            self.tooltip.wm_geometry(f"+{event.x_root+20}+{event.y_root+10}")  # Позиция

            # Настраиваем внешний вид подсказки
            label = tk.Label(
                self.tooltip, 
                text=text, 
                background="#ffffb3", 
                relief=tk.SOLID, 
                borderwidth=1,
                padx=8, 
                pady=4,
                font=("TkDefaultFont", 10)
            )
            label.pack()

        def hide_tooltip(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                del self.tooltip

        # Привязываем события мыши
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
