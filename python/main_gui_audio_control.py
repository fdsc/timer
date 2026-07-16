from config_manager import save_opts_debounced

class AudioControlMixin:
    def _on_volume_change(self, val: str):
        """Обработчик изменения громкости: обновляет метку, множитель и сохраняет в opts.json."""
        # Проверка того, что окно вообще не закрыто
        if not hasattr(self, "lbl_vol_value") or not self.lbl_vol_value.winfo_exists():
            return

        v = float(val.replace(',', '.'))
        self.lbl_vol_value.config(text=f"{v}%")
        self.volume_factor = v / 100.0

        self.opts["volume_percent"] = v
        self._pending_volume_value  = v

        # Сохраняем настройки в файл
        save_opts_debounced(self.data_dir, self.opts)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        from constants import COLOR_BTN_MUTE_ACTIVE_BG, COLOR_BTN_MUTE_INACTIVE_BG
        if self.is_muted:
            self.btn_mute.config(text="X", bg=COLOR_BTN_MUTE_ACTIVE_BG)
        else:
            self.btn_mute.config(text="O", bg=COLOR_BTN_MUTE_INACTIVE_BG)

    def _on_test_sound_click(self, event=None):
        from notifier import play_sound
        play_sound(TEST_SOUND_PATH, self.volume_factor)
