import threading
from datetime import datetime
import time
#from notifier import play_sound, notify_user

class TimerAndAlertMixin:
    def start_timer_loop(self):
        self._stopped = False
        self._update_loop()


    def _update_loop(self):
        if self._stopped:
            return

        now = datetime.now()
        if self.alert_time and now >= self.alert_time:
            if not self._alert_triggered:
                self._trigger_alert()
                self._alert_triggered = True
            # Повторные оповещения
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                self.root.after(self._retry_interval_ms, self._update_loop)
                return


        elif self.alert_time:
            delta = (self.alert_time - now).total_seconds()
            self._update_time_labels(delta)

        if not self._stopped:
            self.root.after(1000, self._update_loop)


    def _trigger_alert(self):
        if not self.is_muted:
            play_sound(self.sound_path, self.volume_factor)
        notify_user(self.text, self.alert_time)
        self._update_visual_state_on_alert()

    def stop_timer(self):
        self._stopped = True

    def _update_visual_state_on_alert(self):
        # Обновляет цвета/текст при срабатывании алерта
        from constants import COLOR_TIME_ALERT_OVERDUE
        self.lbl_time_alert.config(bg=COLOR_TIME_ALERT_OVERDUE, text="ПРОСРОЧЕНО")
        self.frame.config(bd=2, relief="ridge")
