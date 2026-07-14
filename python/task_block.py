import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from notifier import show_alert,sound_alert,cancel_notify_for_task
import math
import tasks_storage


class TaskBlock:
    COLOR_NORMAL_BG        = "#f0f0f0"
    COLOR_NORMAL_ACTIVE    = "#e0e0e0"
    COLOR_IMPORTANT_BG     = "#ffebee"
    COLOR_IMPORTANT_ACTIVE = "#ffcdd2"
    COLOR_FRAME_NORMAL     = "#ffffff"
    COLOR_FRAME_IMPORTANT  = "#fff0f0"

    def getBgColor(self):
        return self.COLOR_FRAME_IMPORTANT if self.is_important else self.COLOR_FRAME_NORMAL

    def __init__(self, parent, frame: tk.Frame, task_id, text, alert_time, is_important_initial: bool = False, is_quiet: bool = False):
        self.parent       = parent
        self.task_id      = task_id
        self.alert_time   = alert_time
        self.text         = text
        self.is_quiet     = is_quiet
        self.is_important = is_important_initial

        self._stopped = False
        self._alerted_once = False
        self._retry_scheduled = False
        self._retry_delay_sec_important   = 60
        self._retry_delay_sec_important_s = 15
        self._retry_delay_sec_normal      = 300
        self._retry_delay_sec_normal_s    = 60
        self._delete_confirmation_max_interval=10;
        self._delete_confirmation_min_interval=0.350;
        self._delete_confirm_active = False

        self._container_frame = frame

        self.root = parent.list_frame.winfo_toplevel()

        bg_color = self.getBgColor()
        self.frame = tk.Frame(self._container_frame, bd=1, relief="solid", padx=4, pady=4, bg=bg_color)
        self.frame.pack(fill="x", pady=(0, 2))

        self.lbl_text = tk.Label(
            self.frame,
            text=text,
            anchor="w",
            justify="left",
            font=("TkDefaultFont", 11),
            bg=bg_color
        )
        self.lbl_text.grid(row=0, column=0, sticky="w", columnspan=2)

        self._setup_copy_menu_for_label(self.lbl_text, text)

        self.lbl_time_info = tk.Label(
            self.frame,
            text="",
            anchor="w",
            justify="left",
            fg="#555",
            bg=bg_color
        )
        self.lbl_time_info.grid(row=1, column=0, sticky="w", columnspan=2)

        self.btn_del = tk.Button(
            self.frame,
            text="Удалить",
            #command=lambda: self.on_delete(self.task_id),
            command=self._start_delete_confirmation,
            width=10,
            bg="#f0f0f0"
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

    def getRemained(self):
        # Возвращает просрочку задачи в секундах (целое)
        now = datetime.now()
        delta = self.alert_time - now
        return max(0, int(math.ceil(delta.total_seconds())))


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
        alert_datetime_str = self.alert_time.strftime("%Y-%m-%d %H:%M:%S")

        self.lbl_time_info.config(
            text=f"Осталось: {time_left_str} | Оповещение: {alert_datetime_str}"
        )

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
        self.frame.after(1000, self.update_timer)

    def trigger_retry_alert(self):
        # Проверяем, существует ли ещё этот блок (не удалили ли задачу)
        if not hasattr(self, "frame") or not self.frame.winfo_exists():
            return

        now   = datetime.now()
        delta = now - self.last_notification
        ts    = delta.total_seconds()

        delta = now - self.last_sound
        tss   = delta.total_seconds()

        if not self.is_quiet:
            if self.is_important:
                if ts  > self._retry_delay_sec_important:
                    show_alert(self)
                if tss > self._retry_delay_sec_important_s:
                    sound_alert(self)
            else:
                if ts  > self._retry_delay_sec_normal:
                    show_alert(self)
                if tss > self._retry_delay_sec_normal_s:
                    sound_alert(self)

        self.frame.after(1000, self.trigger_retry_alert)


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
        if self.is_important:
            self.btn_priority.config(
                text="Важная",
                bg=self.COLOR_IMPORTANT_BG,
                activebackground=self.COLOR_IMPORTANT_ACTIVE
            )
            self.frame.config(bg=self.COLOR_FRAME_IMPORTANT)
            self.lbl_text.config(font=("TkDefaultFont", 11, "bold"), fg="#b71c1c", bg=self.getBgColor())
            self.lbl_time_info.config(bg=self.COLOR_FRAME_IMPORTANT)
        else:
            self.btn_priority.config(
                text="Не важная",
                bg=self.COLOR_NORMAL_BG,
                activebackground=self.COLOR_NORMAL_ACTIVE
            )
            self.frame.config(bg=self.COLOR_FRAME_NORMAL)
            self.lbl_text.config(font=("TkDefaultFont", 11), fg="#000000", bg=self.getBgColor())
            self.lbl_time_info.config(bg=self.COLOR_FRAME_NORMAL)

    def _start_delete_confirmation(self):
        """Активирует режим подтверждения удаления: кнопка меняется на «Точно удалить» на 10 секунд."""
        # Если уже в режиме удаления или задача просрочена, удаляем задачу без дополнительных запросов
        if self.getDeleteConfirmationResult() or self.getRemained() == 0:
            self.delete_task()
            return

        self._delete_confirm_active = datetime.now()
        self.btn_del.config(text="Точно удалить?")

        # Планируем сброс через 10 секунд
        self.frame.after(10000, self._cancel_delete_confirmation)

    def getDeleteConfirmationTime(self):
        """Возвращает время в секундах (float), прошедшее с момента первого нажатия на кнопку 'удалить'"""
        if self._delete_confirm_active == False:
            return 0.0;

        now = datetime.now()
        delta = now - self._delete_confirm_active
        return delta.total_seconds();
    
    def getDeleteConfirmationResult(self):
        time = self.getDeleteConfirmationTime()
        # Если значение времени, прошедшее с момента нажатия кнопки "удалить", слишком мало
        if time <= self._delete_confirmation_min_interval:
            return False
        if time >= self._delete_confirmation_max_interval:
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

        if len(self.parent.get_quiet_tasks()) == 0:
            self.resetQuietTab()
        if len(self.parent.get_non_quiet_tasks()) == 0:
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

