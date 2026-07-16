from config_manager import get_user_data_dir, load_or_create_opts, init_media_config, load_media_paths
import notifier
from constants import TEST_SOUND_PATH

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
