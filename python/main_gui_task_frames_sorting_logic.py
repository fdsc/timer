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
                return (True, 0, 0)
            
            now = datetime.now()
            # Просроченная задача
            is_overdue = block.alert_time is not None and block.getRemainedAlert() <= 0

            if is_overdue:
                if block.is_important:
                    return (0, 0, block.alert_time.timestamp())
                else:
                    return (0, 1, block.alert_time.timestamp())
            else:
                return (1, 0, block.alert_time.timestamp())

        childrens.sort(key=sort_key)

        # Переотображение в новом порядке
        for child in childrens:
            child.pack_forget()
        for child in childrens:
            child.pack(fill="x", pady=(0, 2))
