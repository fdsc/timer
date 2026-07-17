import tkinter as tk

class ToolTip:
    def init_tooltip(self, delay=2000):  # добавили widget в параметры
        self.tooltip_delay = delay

    def create_tooltip(self, widget, text):
        widget.tooltip_text = text

        def show_tooltip_after_delay():
            if not widget.tooltip:
                widget.tooltip = tk.Toplevel(widget)
                widget.tooltip.wm_overrideredirect(True)
                # Получаем координаты относительно корневого окна
                x = widget.winfo_rootx() + 20
                y = widget.winfo_rooty() + 10
                widget.tooltip.wm_geometry(f"+{x}+{y}")

                tk.Label(
                    widget.tooltip, 
                    text=widget.tooltip_text,
                    background="#ffffb3", 
                    relief=tk.SOLID, 
                    borderwidth=1,
                    padx=8, 
                    pady=4,
                    font=("TkDefaultFont", 10)
                ).pack()

        def show_tooltip(event):
            # Устанавливаем задержку появления
            if not widget.alt_pressed:
                widget.after_id = widget.after(self.tooltip_delay, show_tooltip_after_delay)
            else:
                show_tooltip_after_delay()

        def hide_tooltip(event):
            if widget.after_id:
                widget.after_cancel(widget.after_id)
                widget.after_id = None
            if widget.tooltip:
                widget.tooltip.destroy()
                widget.tooltip = None

        def on_alt_press( event):
            widget.alt_pressed = True
            if widget.after_id:
                event.widget.after_cancel(widget.after_id)
                widget.after_id = None
                widget.show_tooltip_after_delay()

        def on_alt_release( event):
            widget.alt_pressed = False
            if widget.tooltip:
                widget.tooltip.destroy()
                widget.tooltip = None


        widget.after_id    = None
        widget.alt_pressed = False
        widget.tooltip     = None
        # Привязываем события мыши
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

        # Добавляем обработку клавиш
        #widget.bind("<Alt_L>",            on_alt_press)
        #widget.bind("<KeyRelease-Alt_L>", on_alt_release)


# Пример использования:
# self.create_tooltip(self.entry, "Введите текст")
