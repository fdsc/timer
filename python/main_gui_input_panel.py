import notifier
import tkinter    as tk
from   tkinter    import messagebox
from   tkinter    import ttk
from   datetime   import timedelta, datetime

from   task_block_tasks import TaskType
from   task_block       import TaskBlock
from   date_utils       import build_alert_time
from   constants        import *


class InputPanelMixin:
    
    def on_combo_change(self, event=None):
        current_idx = self.comboDefer.current()
        saved_idx   = self.opts["combodefer"]

        if current_idx != saved_idx:
            self.opts["combodefer"] = current_idx
            save_opts_debounced(self.data_dir, self.opts)

    def _disable_add_buttons(self):
        """Блокирует кнопки добавления задач."""
        for btn in [self.btn_add_normal, self.btn_add_important, self.btn_add_quiet]:
            btn.config(state="disabled")

    def _calculate_task_type(self, is_quiet: bool, is_control: bool) -> TaskType:
        if is_control:
            return TaskType.CONTROL
        elif is_quiet:
            return TaskType.QUIET
        else:
            return TaskType.NORMAL

    def _get_frame_by_task_type(self, task_type: TaskType) -> tk.Frame:
        if task_type == TaskType.CONTROL:
            return self.control_list_frame
        elif task_type == TaskType.QUIET:
            return self.quiet_list_frame
        elif task_type == TaskType.NORMAL:
            return self.list_frame
        else:
            raise ValueError(f"Неизвестный тип задачи: {task_type}")

    def add_task(self, is_important: bool = False, is_quiet: bool = False, is_control: bool = False):
        """Добавляет задачу, создаёт TaskBlock и сохраняет на диск."""
        if self.io_error_flag:
            return

        text = self.entry_task.get().strip()
        if not text:
            messagebox.showwarning("Ошибка ввода", "Наименование задачи не может быть пустым.")
            return

        alert_time    = None
        total_seconds = 0

        # Сначала пробуем абсолютную дату
        year_str  = self.entry_abs_year.get() .strip()
        month_str = self.entry_abs_month.get().strip()
        day_str   = self.entry_abs_day.get()  .strip()
        time_str  = self.entry_abs_time.get() .strip()

        task_type = self._calculate_task_type(is_quiet=is_quiet, is_control=is_control)
        frame     = self._get_frame_by_task_type(task_type)

        if year_str or month_str or day_str or time_str:
            try:
                alert_time = build_alert_time(year_str, month_str, day_str, time_str)
            except ValueError as e:
                messagebox.showerror("Ошибка", str(e))
                return
        else:
            # Fallback на относительное время, если не задана полная абсолютная дата
            try:
                now         = datetime.now()
                days_str    = self.entry_days.get()   .strip()
                hours_str   = self.entry_hours.get()  .strip()
                minutes_str = self.entry_minutes.get().strip()
                seconds_str = self.entry_seconds.get().strip()

                days    = int(days_str)    if days_str    else 0
                hours   = int(hours_str)   if hours_str   else 0
                minutes = int(minutes_str) if minutes_str else 0
                seconds = int(seconds_str) if seconds_str else 0

                total_seconds = (
                    days    * SECONDS_PER_DAY    +
                    hours   * SECONDS_PER_HOUR   +
                    minutes * SECONDS_PER_MINUTE +
                    seconds
                )

                if total_seconds > MAX_DELAY_DAYS * SECONDS_PER_DAY:
                    messagebox.showerror(
                        "Ошибка",
                        f"Слишком большая задержка. Максимум: {MAX_DELAY_DAYS} дней."
                    )
                    return

                if total_seconds <= 0 and task_type != TaskType.CONTROL:
                    messagebox.showerror("Ошибка", "Общее время должно быть больше 0 секунд.")
                    return

                alert_time = now + timedelta(seconds=total_seconds)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать задачу: {e}")
                return

        task_id = self._generate_task_id()

        block = TaskBlock(
            parent=self,
            task_id=task_id,
            frame=frame,
            text=text,
            alert_time=alert_time,
            is_important_initial=is_important,
            _type=task_type,
            control_interval=total_seconds
        )
        self.tasks[task_id] = block

        self.entry_task.delete(0, tk.END)
        # Сбрасываем относительные поля
        self.entry_days.delete(0, tk.END)
        self.entry_hours.delete(0, tk.END)
        self.entry_minutes.delete(0, tk.END)
        self.entry_seconds.delete(0, tk.END)
        # Сбрасываем абсолютные поля
        self.entry_abs_year.delete(0, tk.END)
        self.entry_abs_month.delete(0, tk.END)
        self.entry_abs_day.delete(0, tk.END)
        self.entry_abs_time.delete(0, tk.END)


        # Сохраняем на диск (alert_time=None превратится в текущее время)
        block.save()

        # Пересортировываем задачи по приоритету
        self.check_control_tasks()
        self._reorder_tasks_in_frame(frame)


    def do_defer_list(self, tlist, base_seconds: int, lastDefer: datetime) -> datetime:
        """Вспомогательная функция, откладывающая задачи из выбранного списка"""
        applied_count = 0

        for i, task in enumerate(tlist):

            important_interval = base_seconds // 2 if not task.is_important else base_seconds
            normal_interval    = base_seconds

            # Определяем, какой интервал использовать для этой задачи
            interval_seconds = important_interval if task.is_important else normal_interval

            if i == 0:
                delta_sec = (task.defer_time - lastDefer).total_seconds()
                if delta_sec > interval_seconds:
                    break

                new_defer = max(lastDefer + timedelta(seconds=interval_seconds), task.defer_time)
                if new_defer != task.defer_time:
                    task.set_defer_time(new_defer)
                    lastDefer = new_defer
                    applied_count += 1

                continue


            prev_task = tlist[i - 1]
            delta_sec = (task.defer_time - prev_task.defer_time).total_seconds()

            if delta_sec <= interval_seconds:
                # Задача слишком близко к предыдущей — сдвигаем её
                new_defer = prev_task.defer_time + timedelta(seconds=interval_seconds)
                task.set_defer_time(new_defer)
                lastDefer = new_defer
                applied_count += 1
            else:
                break

        return lastDefer


    def do_defer(self, is_important: bool = False):
        """
        Откладывает НЕ тихие задачи так, чтобы между ними был заданный интервал.

        Параметры:
          is_important=False: важные задачи откладываются с половинным интервалом.
          is_important=True:  все задачи откладываются с полным интервалом.

        Логика:
          1. Игнорируем тихие задачи.
          2. Сортируем все не тихие задачи по alert_time (не только просроченные).
          3. Проходим по списку и «выравниваем» defer_time так, чтобы соседние задачи
             отстояли друг от друга не меньше чем на нужный интервал.
          4. Если очередная задача отстоит от предыдущей меньше чем на интервал —
             сдвигаем её на этот интервал вперёд от предыдущей.
          5. Как только встречаем задачу, которая уже отстоит больше чем на интервал,
             дальше не трогаем (процесс завершается).
        """

        notifier.cancel_notify_for_task(notifier.BULK_TASK_ID)
        for task in self.tasks.values():
            notifier.cancel_notify_for_task(task.task_id)

        now = datetime.now()

        # 1. Получаем все НЕ тихие задачи и сортируем по alert_time
        normal_tasks_i = [t for t in self.tasks.values() if not t.type == TaskType.NORMAL and     t.is_important]
        normal_tasks_n = [t for t in self.tasks.values() if not t.type == TaskType.NORMAL and not t.is_important]
        if not normal_tasks_i and not normal_tasks_n:
            return

        normal_tasks_i.sort(key=lambda t: t.alert_time)
        normal_tasks_n.sort(key=lambda t: t.alert_time)

        # 2. Получаем интервал из comboDefer
        combo_value_str = self.comboDefer.get()
        try:
            base_seconds = int(combo_value_str)*60
        except (ValueError, TypeError):
            base_seconds = 60

        if base_seconds <= 0:
            base_seconds = 60

        lastDefer = self.do_defer_list(normal_tasks_i, base_seconds, now)
        self.do_defer_list(normal_tasks_n, base_seconds, lastDefer)

        # Пересортировать задачи в UI по defer_time, чтобы порядок соответствовал новому расписанию
        self._reorder_tasks_in_frame(self.list_frame)

    def clear_input_fields(self):
        """Очищает все поля ввода новой задачи"""
        self.entry_task.delete(0, tk.END)
        self.entry_days.delete(0, tk.END)
        self.entry_hours.delete(0, tk.END)
        self.entry_minutes.delete(0, tk.END)
        self.entry_seconds.delete(0, tk.END)
        self.entry_abs_year.delete(0, tk.END)
        self.entry_abs_month.delete(0, tk.END)
        self.entry_abs_day.delete(0, tk.END)
        self.entry_abs_time.delete(0, tk.END)

    def build_input_panel(self, root):
        top = tk.Frame(root)
        top.pack(fill="x", padx=8, pady=8)

        task_row = tk.Frame(top)
        task_row.pack(fill="x", pady=(0, 4))

        self.init_tooltip()

        tk.Label(task_row, text="Задача:").pack(side="left")
        self.entry_task = tk.Entry(task_row, width=50)
        self.entry_task.pack(side="left", padx=(4, 8))
        self.create_tooltip(self.entry_task, "Введите имя задачи")

        self.btn_defer = tk.Button(
            task_row,
            text="Отл",
            command=lambda: self.do_defer(is_important=False),
            width=2,
            bg=COLOR_BTN_DEFER_BG,
            fg=COLOR_BTN_DEFER_FG,
            activebackground=COLOR_BTN_DEFER_ACTIVE_BG,
            activeforeground=COLOR_BTN_DEFER_ACTIVE_FG
        )
        self.btn_defer.pack(side="left", padx=(0, 2))
        self.create_tooltip(self.btn_defer, "Отложить задачи")

        self.comboDefer = ttk.Combobox(task_row, values=self.get10percentList(), width=10, state="readonly")
        self.comboDefer.current(self.opts["combodefer"])
        self.comboDefer.pack(side="left", padx=(0, 8))
        self.comboDefer.bind("<<ComboboxSelected>>", self.on_combo_change)
        self.create_tooltip(self.comboDefer, "Интервал, с которым будут идти отложенные задачи")

        # Кнопка очистки
        self.btn_clear = tk.Button(
            task_row,
            text="X",
            command=self.clear_input_fields,
            width=2,
            bg=COLOR_NORMAL_BG,
            activebackground="#FFFFFF"
        )
        self.btn_clear.pack(side="left")
        self.create_tooltip(self.btn_clear, "Очистить поля ввода")

        time_and_btn_row = tk.Frame(top)
        time_and_btn_row.pack(fill="x", pady=(0, 0))

        self.btn_add_normal = tk.Button(
            time_and_btn_row,
            text="+",
            command=lambda: self.add_task(is_important=False),
            width=2,
            bg=COLOR_BTN_ADD_NORMAL_BG,
            activebackground=COLOR_BTN_ADD_NORMAL_ACTIVE_BG
        )
        self.btn_add_normal.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.btn_add_normal, "Добавить обычную задачу в список")

        self.btn_add_important = tk.Button(
            time_and_btn_row,
            text="!",
            command=lambda: self.add_task(is_important=True),
            width=2,
            bg=COLOR_BTN_ADD_IMPORTANT_BG,
            activebackground=COLOR_BTN_ADD_IMPORTANT_ACTIVE_BG
        )
        self.btn_add_important.pack(side="left", padx=(0, 16))
        self.create_tooltip(self.btn_add_important, "Добавить важную задачу\n[задача будет подсвечена и при просрочке и отложении будет приоритетной]")

        self.btn_add_quiet = tk.Button(
            time_and_btn_row,
            text="V",
            command=lambda: self.add_task(is_important=False, is_quiet=True),
            width=2,
            bg=COLOR_BTN_ADD_QUIET_BG,
            activebackground=COLOR_BTN_ADD_QUIET_ACTIVE_BG
        )
        self.btn_add_quiet.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.btn_add_quiet, "Добавить \"Тихую\" задачу\n[Тихие задачи работают без уведомлений]")

        self.btn_add_control = tk.Button(
            time_and_btn_row,
            text="K",
            command=lambda: self.add_task(is_important=False, is_quiet=False, is_control=True),
            width=2,
            bg="#8B4513",  # темно-коричневый цвет
            activebackground="#A52A2A"
        )
        self.btn_add_control.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.btn_add_control, "Добавить контрольную задачу\n[Контрольные задачи будут напоминать, если не поставлена такая же задачу во вкладку задач или тихих задач]")

        time_frame = tk.Frame(time_and_btn_row)
        time_frame.pack(side="left")

        tk.Label(time_frame, text="Д:").pack(side="left")
        self.entry_days = tk.Entry(time_frame, width=5)
        self.entry_days.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_days, "Количество полных суток до того, как необходимо оповещение о задаче")

        tk.Label(time_frame, text="Ч:").pack(side="left")
        self.entry_hours = tk.Entry(time_frame, width=5)
        self.entry_hours.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_hours, "Количество полных часов до того, как необходимо оповещение о задаче")

        tk.Label(time_frame, text="М:").pack(side="left")
        self.entry_minutes = tk.Entry(time_frame, width=5)
        self.entry_minutes.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_minutes, "Количество полных минут до того, как необходимо оповещение о задаче")

        tk.Label(time_frame, text="С:").pack(side="left")
        self.entry_seconds = tk.Entry(time_frame, width=5)
        self.entry_seconds.pack(side="left", padx=(0, 0))
        self.create_tooltip(self.entry_seconds, "Количество полных секунд до того, как необходимо оповещение о задаче")

        self.lbl_quiet_overdue_indicator = tk.Label(
            top,
            text="⚠️ Есть просроченные тихие задачи! ⚠️",
            fg="#b71c1c",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_quiet_overdue_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.lbl_quiet_overdue_indicator.pack_forget()
        self.create_tooltip(self.lbl_quiet_overdue_indicator, "Зайдите на вкладку \"Тихие\" для просмотра")

        self.lbl_control_unpaired_indicator = tk.Label(
            top,
            text="⚠️ Есть непоставленные контрольные задачи! ⚠️",
            fg="#b71c1c",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_control_unpaired_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.lbl_control_unpaired_indicator.pack_forget()
        self.create_tooltip(self.lbl_control_unpaired_indicator, "Зайдите на вкладку \"К\" для просмотра")

        # Третья строка: абсолютная дата и регулятор громкости
        third_row = tk.Frame(root)
        third_row.pack(fill="x", padx=8, pady=4)

        # Абсолютная дата (слева)
        abs_date_frame = tk.Frame(third_row)
        abs_date_frame.pack(side="left", anchor="e")

        tk.Label(abs_date_frame, text="Год:").pack(side="left")
        self.entry_abs_year = tk.Entry(abs_date_frame, width=7)
        self.entry_abs_year.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_abs_year, "Год срабатывания (2026; 26) или интервал в годах (+1)")

        tk.Label(abs_date_frame, text="Месяц:").pack(side="left")
        self.entry_abs_month = tk.Entry(abs_date_frame, width=5)
        self.entry_abs_month.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_abs_month, "Месяц срабатывания (числом; 1==январь) или интервал в месяцах (+1)")

        tk.Label(abs_date_frame, text="День:").pack(side="left")
        self.entry_abs_day = tk.Entry(abs_date_frame, width=5)
        self.entry_abs_day.pack(side="left", padx=(0, 8))
        self.create_tooltip(self.entry_abs_day, "День срабатывания (числом или двухбуквенной аббривеатурой, например. ср) или интервал в днях (+1)")

        tk.Label(abs_date_frame, text="Время (Ч:М):").pack(side="left")
        self.entry_abs_time = tk.Entry(abs_date_frame, width=9)
        self.entry_abs_time.insert(0, "")
        self.entry_abs_time.pack(side="left", padx=(0, 0))
        self.create_tooltip(self.entry_abs_time, "Время срабатывания часы:минуты (11:15) или только часы (11 то же, что и 11:00)")

        # Регулятор громкости (справа)
        vol_frame = tk.Frame(third_row)
        vol_frame.pack(side="right", anchor="e")  # anchor="e" прижмёт фрейм вправо

        # Кнопка глушения звука
        self.is_muted = True
        self.btn_mute = tk.Button(
            vol_frame,
            text="O",
            command=self.toggle_mute,
            width=2,
            activebackground=COLOR_BTN_MUTE_HOVER_BG
        )
        self.toggle_mute()
        self.btn_mute.pack(side="left", padx=(4, 8))
        self.create_tooltip(self.entry, "Нажмите, чтобы заглушить звук. После удаления всех просроченных задач, звук включится сам.")

        # Сначала метка «Громкость:»
        lbl_vol_label = tk.Label(vol_frame, text="Громкость:")
        lbl_vol_label.pack(side="left", padx=(0, 8))

        # Слайдер
        self.scale_volume = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            resolution=0.5,
            orient="horizontal",
            length=200,
            showvalue=False,
            tickinterval=0,
            command=self._on_volume_change
        )
        self.scale_volume.set(self.volume_factor*100)
        self.scale_volume.pack(side="left", padx=(4, 0))
        self.create_tooltip(self.scale_volume, "Регулятор громкости звукового оповещения")

        # Метка с процентами (справа от слайдера)
        self.lbl_vol_value = tk.Label(vol_frame, text=str(int(self.volume_factor*100)) + "%", width=5, anchor="e")
        self.lbl_vol_value.pack(side="left", padx=(8, 0))
        self.create_tooltip(self.lbl_vol_value, "Громкость звукового оповещения. Нажмите, чтобы прослушать")

        # Привязываем клик по метке громкости для ручного теста звука
        self.lbl_vol_value.bind("<Button-1>", self._on_test_sound_click)


    def SetUpTabsWarning(self):
        now = datetime.now()
        # Показываем оповещение о наличии просроченных тихих задачах. Если необходимо
        has_overdue_quiet = any(
            t.is_quiet and t.alert_time is not None and (now - t.alert_time).total_seconds() >= 0
            for t in self.tasks.values()
        )

        if has_overdue_quiet:
            self.upsetQuietTab()
        else:
            self.resetQuietTab()

        # Показываем оповещение о наличии непарных контрольных задачах. Если необходимо
        has_control_unpaired = any(
            t.is_unpaired for t in self.tasks.values()
        )

        if has_control_unpaired:
            self.upsetControlTab()
        else:
            self.resetControlTab()

    def upsetQuietTab(self):
        self.lbl_quiet_overdue_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.notebook.tab(self.quiet_tab_frame, text="----- Тихие -----")

    def resetQuietTab(self):
        self.lbl_quiet_overdue_indicator.pack_forget()
        self.notebook.tab(self.quiet_tab_frame, text="Тихие")

    def upsetControlTab(self):
        self.lbl_control_unpaired_indicator.pack(fill="x", padx=4, pady=(0, 4))
        self.notebook.tab(self.control_tab, text="----- К -----")

    def resetControlTab(self):
        self.lbl_control_unpaired_indicator.pack_forget()
        self.notebook.tab(self.control_tab, text="К")
