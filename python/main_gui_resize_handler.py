from config_manager import save_opts_debounced

class ResizeHandlerMixin:
    def rootResize(self, e):
        g = self.root.geometry()
        if g == self.opts["geometry"]:
            return

        self.opts["geometry"] = g
        
        save_opts_debounced(self.data_dir, self.opts)

        for task in self.tasks.values():
            if task._stopped:
                continue

            w = self.canvas_m.winfo_width()
            sb_w = self.scrollbar.winfo_width() if hasattr(self, 'scrollbar') else 0
            task.lbl_text.configure(wraplength=w - sb_w - 8)
