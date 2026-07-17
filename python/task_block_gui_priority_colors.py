from constants import (
    COLOR_FRAME_NORMAL, COLOR_FRAME_IMPORTANT,
    COLOR_BTN_DELETE_NORMAL, COLOR_BTN_DELETE_OVERDUE
)

class PriorityColorsMixin:

    def getBgColor(self):
        if self.is_unpaired:
            return "#FFCC88" if self.is_important else "#FFFFCC"

        return COLOR_FRAME_IMPORTANT if self.is_important else COLOR_FRAME_NORMAL

    def toggle(self):
        self.is_important = not self.is_important
        self._apply_priority_style()

    def _apply_priority_style(self):
        bg_color = COLOR_FRAME_IMPORTANT if self.is_important else COLOR_FRAME_NORMAL
        self.frame.config(bg=bg_color)
        self.lbl_text.config(bg=bg_color, font=("TkDefaultFont", 11, "bold" if self.is_important else "normal"))
        self.lbl_time_left.config(bg=bg_color)
        
        # Обновление кнопки приоритета (текст/иконка)
        self.btn_priority.config(
            text="Снять важность" if self.is_important else "Сделать важным",
            bg="#ffe0b2" if self.is_important else "#e8f5e9"
        )
