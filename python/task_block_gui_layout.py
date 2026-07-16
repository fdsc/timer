import tkinter as tk
from constants import (
    COLOR_FRAME_NORMAL, COLOR_FRAME_IMPORTANT,
    COLOR_BTN_DELETE_NORMAL, COLOR_BTN_DELETE_OVERDUE,
    COLOR_TIME_ALERT_OVERDUE, COLOR_TIME_ALERT_POSTPONED, COLOR_TIME_ALERT_NORMAL
)

class TaskBlockLayoutMixin:
    def build_layout(self):
        bg_color = self.getBgColor()
        self.frame = tk.Frame(self._container_frame, bd=1, relief="solid", padx=4, pady=4, bg=bg_color)
        self.frame.pack(fill="x", pady=(0, 2))

        self.lbl_text = tk.Label(
            self.frame,
            text=self.text,
            anchor="w",
            justify="left",
            font=("TkDefaultFont", 11),
            bg=bg_color,
        )
        self.lbl_text.grid(row=0, column=0, sticky="w", columnspan=2)

        self._setup_copy_menu_for_label(self.lbl_text, self.text)

        self.lbl_time_left = tk.Label(
            self.frame,
            text="",
            anchor="w",
            justify="left",
            fg="#555",
            bg=bg_color
        )
        self.lbl_time_left.grid(row=1, column=0, sticky="w", columnspan=2)

        self.lbl_time_alert = tk.Label(
            self.frame,
            text="",
            anchor="e",
            justify="left",
            fg="#555",
            bg=COLOR_TIME_ALERT_NORMAL,
            font=("TkDefaultFont", 10)
        )
        self.lbl_time_alert.grid(row=1, column=1, sticky="w", padx=(0, 0))

        self.lbl_text.bind("<Button-1>", lambda e: self._on_click_title())
        self.lbl_time_alert.bind("<Button-1>", lambda e: self._on_click_alert_time())

        self.btn_del = tk.Button(
            self.frame,
            text="Удалить",
            command=self._start_delete_confirmation,
            width=10,
            bg=COLOR_BTN_DELETE_NORMAL
        )
        self.btn_del.grid(row=2, column=0, padx=(0, 8), sticky="w")

        self.btn_priority = tk.Button(
            self.frame,
            text="",
            command=self.toggle_priority,
            width=12,
            bg="#f0f0f0",
            activebackground=self.COLOR_IMPORTANT_ACTIVE if self.is_important else "#e0e0e0"
        )
        self.btn_priority.grid(row=2, column=1, sticky="w")

    def _setup_copy_menu_for_label(self, label, text):
        import tkinter as tk
        menu = tk.Menu(label, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self._copy_text(text))

        def popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        label.bind("<Button-3>", popup)

    def _copy_text(self, text):
        self._container_frame.clipboard_clear()
        self._container_frame.clipboard_append(text)

