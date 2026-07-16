import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from notifier import show_alert,sound_alert,cancel_notify_for_task
import math
import tasks_storage

from constants import *
#import constants
#from constants import (
#    RETRY_DELAY_IMPORTANT_SEC,
#    RETRY_DELAY_IMPORTANT_SOUND_SEC,
#    RETRY_DELAY_NORMAL_SEC,
#    RETRY_DELAY_NORMAL_SOUND_SEC,
#    DELETE_CONFIRM_MAX_SECONDS,
#    DELETE_CONFIRM_MIN_SECONDS,
#    TICK_INTERVAL_MS,
#    ALERT_INTERVAL_MS,
#)

from task_block_gui_layout import TaskBlockLayoutMixin
from task_block_timer_and_alert import TimerAndAlertMixin
from task_block_gui_delete_confirmation_mixin import DeleteConfirmationMixin
from task_block_gui_priority_colors import PriorityColorsMixin


class TaskBlock(
    TaskBlockLayoutMixin,
    TimerAndAlertMixin,
    DeleteConfirmationMixin,
    PriorityColorsMixin
):
    def getBgColor(self):
        return COLOR_FRAME_IMPORTANT if self.is_important else COLOR_FRAME_NORMAL

    def __init__(self, parent, frame: tk.Frame, task_id, text, alert_time, is_important_initial: bool = False, is_quiet: bool = False):
        self.parent       = parent
        self.task_id      = task_id
        self.alert_time   = alert_time
        self.defer_time   = alert_time              # Не должен сохраняться
        self.text         = text
        self.is_quiet     = is_quiet
        self.is_important = is_important_initial

        self._stopped               = False
        self._alerted_once          = False
        self._retry_scheduled       = False
        self._delete_confirm_active = False

        self._container_frame = frame

        self.build_layout()
        self.root = parent.list_frame.winfo_toplevel()

        self.build_layout()
        #self.start_timer_loop()


        sep = tk.Frame(self.frame, height=2, bg="gray")
        sep.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        self._update_priority_ui()
        self.update_timer()


    def _setup_copy_menu_for_label(self, label, text_to_copy):
        """Создаёт контекстное меню для Label, чтобы копировать текст задачи."""
        menu = tk.Menu(label, tearoff=0)

        def copy_text():
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)

        menu.add_command(label="Копировать текст задачи", command=copy_text)

        def popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        label.bind("<Button-3>", popup)

    def upsetQuietTab(self):
        self.parent.lbl_quiet_overdue_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.parent.notebook.tab(self.parent.quiet_tab_frame, text="----- Тихие -----")

    def resetQuietTab(self):
        self.parent.lbl_quiet_overdue_indicator.pack_forget()
        self.parent.notebook.tab(self.parent.quiet_tab_frame, text="Тихие")


    def update_timer(self):
        if self._stopped:
            return

        now = datetime.now()
        total_seconds = self.getRemained()

        mins, secs = divmod(total_seconds, 60)
        hrs, mins = divmod(mins, 60)

        time_left_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        self.lbl_time_left.config(text=f"Осталось: {time_left_str}")
        alert_datetime_str = self.alert_time.strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_time_alert.config(text=f"Оповещение: {alert_datetime_str}")

        # Логика цвета фона для «Оповещение»
        # Считаем, что «первичное оповещение наступило», если now >= alert_time
        is_alert_due = now >= self.alert_time

        if is_alert_due and total_seconds <= 0:
            # Оповещение наступило и задача не отложена — красный фон
            self.lbl_time_alert.config(bg=COLOR_TIME_ALERT_OVERDUE)
        elif is_alert_due and total_seconds > 0:
            # Оповещение уже было, но задача отложена — голубой фон
            self.lbl_time_alert.config(bg=COLOR_TIME_ALERT_POSTPONED)
        else:
            # Всё ещё впереди — прозрачный фон
            self.lbl_time_alert.config(bg=COLOR_TIME_ALERT_NORMAL)

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

        self.frame.after(constants.ALERT_INTERVAL_MS, self.trigger_retry_alert)


    def save(self):
        if self.parent.io_error_flag:
            return False

        isSuccess = tasks_storage.save_task(
            data_dir=self.parent.data_dir,
            task_data={
                "task_id":      self.task_id,
                "text":         self.text,
                "alert_time":   self.alert_time,
                "is_important": self.is_important,
                "is_quiet":     self.is_quiet,
            },
            lock=self.parent.storage_lock,
            io_error_flag=self.parent.io_error_flag
        )

        if not isSuccess:
            self.parent.io_error_flag = True
            messagebox.showerror("Ошибка доступа к диску", f"Не удалось сохранить задачу. Сохранение отключено. '{tasks_storage.get_tasks_dir()}'")
            self.parent._disable_add_buttons()

        return isSuccess

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


    def _start_delete_confirmation(self):
        """Активирует режим подтверждения удаления: кнопка меняется на «Точно удалить» на 10 секунд."""
        # Если уже в режиме удаления или задача просрочена, удаляем задачу без дополнительных запросов
        if self.getDeleteConfirmationResult() or self.getRemained() == 0:
            self.delete_task()
            return

        self._delete_confirm_active = datetime.now()
        self.btn_del.config(text="Точно удалить?")

        # Планируем сброс через 10 секунд
        self.frame.after(int(constants.DELETE_CONFIRM_MAX_SECONDS * 1000), self._cancel_delete_confirmation)


    def getDeleteConfirmationTime(self):
        """Возвращает время в секундах (float), прошедшее с момента первого нажатия на кнопку 'удалить'"""
        if self._delete_confirm_active is False:
            return 0.0;

        now = datetime.now()
        delta = now - self._delete_confirm_active
        return delta.total_seconds();
    
    def getDeleteConfirmationResult(self):
        time = self.getDeleteConfirmationTime()
        # Если значение времени, прошедшее с момента нажатия кнопки "удалить", слишком мало
        if time <= DELETE_CONFIRM_MIN_SECONDS:
            return False
        if time >= DELETE_CONFIRM_MAX_SECONDS:
            return False

        return True

    def _cancel_delete_confirmation(self):
        """Сбрасывает режим подтверждения, если пользователь не подтвердил удаление за 10 секунд."""
        self._delete_confirm_active = False
        self.btn_del.config(text="Удалить")

    def delete_task(self):
        """Выполняет удаление задачи."""
        # Сбрасываем флаг подтверждения перед удалением
        self._delete_confirm_active = False
        self._on_delete_direct()

        if len(self.parent.get_quiet_tasks_not_remained()) == 0:
            self.resetQuietTab()
        if len(self.parent.get_non_quiet_tasks_not_remained()) == 0:
            self.parent.is_muted = True
            self.parent.toggle_mute()


    def _on_delete_direct(self):
        """Реальная логика удаления задачи."""
        if self.task_id not in self.parent.tasks:
            return
        if self.parent.io_error_flag:
            return

        del self.parent.tasks[self.task_id]
        if hasattr(self, "frame") and self.frame.winfo_exists():
            self.frame.destroy()
        self._stopped = True
        cancel_notify_for_task(self.task_id)

        # Удаляем файл на диске
        success = tasks_storage.delete_task_file(
            data_dir      = self.parent.data_dir,
            task_id       = self.task_id,
            lock          = self.parent.storage_lock,
            io_error_flag = self.parent.io_error_flag
        )

        if not success:
            self.parent.io_error_flag = True
            messagebox.showerror("Ошибка доступа к диску", f"Не удалось удалить файл задачи. Сохранение отключено. '{tasks_storage.get_tasks_dir()}'")
            self.parent._disable_add_buttons()

    def set_defer_time(self, new_defer_time: datetime):
        self.defer_time = new_defer_time
        # Пересчитываем отображение таймера с учётом изменившихся величин
        self.update_timer()

    def getRemained(self):
        now   = datetime.now()
        delta = self.defer_time - now
        return max(0, int(math.ceil(delta.total_seconds())))

    def getRemainedAlert(self):
        now   = datetime.now()
        delta = self.alert_time - now
        return max(0, int(math.ceil(delta.total_seconds())))

    def _on_click_title(self):
        """Вставляет текст задачи в поле ввода задачи главного окна."""
        if not hasattr(self.parent, "entry_task") or not self.parent.entry_task.winfo_exists():
            return
        self.parent.entry_task.delete(0, tk.END)
        self.parent.entry_task.insert(0, self.text)

    def _on_click_alert_time(self):
        """Вставляет часы:минуты из alert_time в поле entry_abs_time главного окна."""
        if not hasattr(self.parent, "entry_abs_time") or not self.parent.entry_abs_time.winfo_exists():
            return
        t = self.alert_time
        time_str = f"{t.hour:02d}:{t.minute:02d}"
        self.parent.entry_abs_time.delete(0, tk.END)
        self.parent.entry_abs_time.insert(0, time_str)
