import threading
from datetime import datetime
import time
from constants import *
from notifier import show_alert,sound_alert

class TimerAndAlertMixin:
    def start_timer_loop(self):
        self._update_priority_ui()
        self.update_timer()

    def toggle_priority(self):
        if self.parent.io_error_flag:
            return

        self.is_important = not self.is_important
        self._update_priority_ui()
        self.save()

    def _update_priority_ui(self):
        bg_color = self.getBgColor()
        self.lbl_time_left.config(bg=bg_color)
        self.lbl_time_alert.config(bg=bg_color)
        
        if self.is_important:
            self.btn_priority.config(
                text="Важная",
                bg=COLOR_IMPORTANT_BG,
                activebackground=COLOR_IMPORTANT_ACTIVE
            )
            self.frame.config(bg=COLOR_FRAME_IMPORTANT)
            self.lbl_text.config(font=("TkDefaultFont", 11, "bold"), fg="#b71c1c", bg=self.getBgColor())
        else:
            self.btn_priority.config(
                text="Не важная",
                bg=COLOR_NORMAL_BG,
                activebackground=COLOR_NORMAL_ACTIVE
            )
            self.frame.config(bg=COLOR_FRAME_NORMAL)
            self.lbl_text.config(font=("TkDefaultFont", 11), fg="#000000", bg=self.getBgColor())



    def update_timer(self):
        if self._stopped:
            return

        now = datetime.now()
        total_seconds = self.getRemained()

        mins, secs = divmod(total_seconds, 60)
        hrs,  mins = divmod(mins, 60)

        time_left_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        self.lbl_time_left.config(text=f"Осталось: {time_left_str}")
        alert_datetime_str = self.alert_time.strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_time_alert.config(text=f"Оповещение: {alert_datetime_str}")

        # Логика цвета фона для «Оповещение»
        # Считаем, что «первичное оповещение наступило», если now >= alert_time
        is_alert_due = now >= self.alert_time

        if is_alert_due:
            # Оповещение наступило и задача не отложена — красный фон
            self.lbl_time_alert.config(bg=COLOR_TIME_ALERT_OVERDUE)
        else:
            # Всё ещё впереди — прозрачный фон
            self.lbl_time_alert.config(bg=self.getBgColor())

        if is_alert_due and total_seconds > 0:
            # Оповещение уже было, но задача отложена — голубой фон
            self.lbl_time_left.config(bg=COLOR_TIME_ALERT_POSTPONED)
        else:
            self.lbl_time_left.config(bg=self.getBgColor())

        if total_seconds <= 0:
            self.btn_del.config(bg=COLOR_BTN_DELETE_OVERDUE)
        else:
            self.btn_del.config(bg=COLOR_BTN_DELETE_NORMAL)

        # ЛОГИКА ОПОВЕЩЕНИЙ
        if total_seconds == 0:
            # Первое оповещение
            if not self._alerted_once:
                self._alerted_once     = True       # Это нельзя сохранять в файле
                self._retry_scheduled  = True
                self.last_notification = datetime(1900, 1, 1, 0, 0, 0)
                self.last_sound        = datetime(1900, 1, 1, 0, 0, 0)
                self.trigger_retry_alert()

                frame=self.parent.quiet_list_frame if self.is_quiet else self.parent.list_frame
                self.parent._reorder_tasks_in_frame(frame)


        has_overdue_quiet = any(
            t.alert_time is not None and (now - t.alert_time).total_seconds() >= 0 and t.is_quiet
            for t in self.parent.tasks.values()
        )

        if has_overdue_quiet:
            self.upsetQuietTab()
        else:
            self.resetQuietTab()

        # Следующий тик через 1 секунду
        self.frame.after(TICK_INTERVAL_MS, self.update_timer)

    def trigger_retry_alert(self):
        # Проверяем, существует ли ещё этот блок (не удалили ли задачу)
        if not hasattr(self, "frame") or not self.frame.winfo_exists():
            return

        total_seconds = self.getRemained()
        # Если задача отложена, то может быть, что total_seconds снова больше 0
        if total_seconds <= 0:
        
            now   = datetime.now()
            delta = now - self.last_notification
            ts    = delta.total_seconds()

            delta = now - self.last_sound
            tss   = delta.total_seconds()

            if not self.is_quiet:
                if self.is_important:
                    if ts  > RETRY_DELAY_IMPORTANT_SEC:
                        show_alert(self)
                    if tss > RETRY_DELAY_IMPORTANT_SOUND_SEC:
                        sound_alert(self)
                else:
                    if ts  > RETRY_DELAY_NORMAL_SEC:
                        show_alert(self)
                    if tss > RETRY_DELAY_NORMAL_SOUND_SEC:
                        sound_alert(self)

        self.frame.after(ALERT_INTERVAL_MS, self.trigger_retry_alert)
