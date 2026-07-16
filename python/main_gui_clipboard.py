import tkinter as tk

class ClipboardMixin:
    def _setup_copy_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))

        def popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", popup)
