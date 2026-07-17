from datetime import datetime

class TaskFramesSortingLogicMixin:
    def _reorder_tasks_in_frame(self, frame):
        """Переупаковывает блоки задач в frame согласно приоритету: важные и просроченные — выше."""
        # Получаем все виджеты-потомки
        childrens = list(frame.winfo_children())

        def sort_key(child):
            block = None

            for t in self.tasks.values():
                if t.frame is child:
                    block = t
                    break
            if not block:
                return (0, 0, 0)

            # Просроченная задача
            if block.is_control:
                is_overdue = False
            else:
                is_overdue = block.alert_time is None or block.getRemainedAlert() <= 0

            ta = block.text if block.is_control else block.alert_time.timestamp()
            if is_overdue or block.is_unpaired:
                if block.is_important:
                    return (0, 0, ta)
                else:
                    return (0, 1, ta)
            else:
                if block.is_control:
                    return (1, int(not block.is_important), ta)
                else:
                    return (1, 0, ta)

        childrens.sort(key=sort_key)

        # Переотображение в новом порядке
        for child in childrens:
            child.pack_forget()
        for child in childrens:
            child.pack(fill="x", pady=(0, 2))

        self.SetUpTabsWarning()

    def _reorder_tasks(self):
        # Устанавливаем is_unpaired для задач
        self.check_control_tasks()
        # Добавляем сортировку для всех типов задач
        self._reorder_tasks_in_frame(self.list_frame)
        self._reorder_tasks_in_frame(self.quiet_list_frame)
        self._reorder_tasks_in_frame(self.control_list_frame)
