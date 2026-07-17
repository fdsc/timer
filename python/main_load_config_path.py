import notifier
from config_manager   import get_user_data_dir, load_or_create_opts, init_media_config, load_media_paths
from task_block       import TaskBlock
from constants        import TEST_SOUND_PATH
from task_block_tasks import TaskType


class LoadConfigPathMixin:
    @staticmethod
    def load_config(app):
        app.data_dir = get_user_data_dir()
        app.opts     = load_or_create_opts(app.data_dir)

        app.volume_factor         = app.opts.get("volume_percent", 100) / 100.0
        app._pending_volume_value = None

        app.media_config_path    = init_media_config(app.data_dir)
        app.media_paths          = load_media_paths (app.media_config_path)
        notifier.MEDIA_PATHS     = app.media_paths
        notifier.TEST_SOUND_PATH = TEST_SOUND_PATH


    def _restore_task_from_dict(self, data: dict):
        """Восстанавливает задачу из словаря (после загрузки с диска) в UI."""
        task_id = data.get("task_id", "")
        if not task_id or task_id in self.tasks:
            print(f"Обнаружена задача без id или копия задачи с id {task_id} и текстом {data.get("text")}. Игнорирована.")
            return

        text         = data.get("text", "ошибка загрузки")
        is_important = bool(data.get("is_important", False))
        _type        = TaskType(data.get("type", TaskType.NORMAL))
        alert_time   = data.get("alert_time") # Уже переведено в datetime

        frame = self.quiet_list_frame if _type == TaskType.QUIET else self.list_frame

        task_block = TaskBlock(
            parent=self,
            frame=frame,
            task_id=task_id,
            text=text,
            alert_time=alert_time,
            is_important_initial=is_important,
            _type=_type
        )

        self.tasks[task_id] = task_block
