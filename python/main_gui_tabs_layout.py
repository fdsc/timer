import tkinter as tk
from tkinter import ttk

class TabsLayoutMixin:
    def build_tabs(self, root):
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # -------- Вкладка "Задачи" --------
        self.main_tab_frame = tk.Frame(self.notebook)
        self.notebook.add(self.main_tab_frame, text="Задачи")
        
        self.canvas_m = tk.Canvas(self.main_tab_frame, highlightthickness=0)
        self.canvas_m.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.main_tab_frame, orient="vertical", command=self.canvas_m.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas_m.configure(yscrollcommand=self.scrollbar.set)

        self.list_frame = tk.Frame(self.canvas_m)
        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas_m.configure(scrollregion=self.canvas_m.bbox("all"))
        )
        self.canvas_m.create_window((0, 0), window=self.list_frame, anchor="nw")

        # -------- Вкладка "Тихие" --------
        self.quiet_tab_frame = tk.Frame(self.notebook)
        self.notebook.add(self.quiet_tab_frame, text="Тихие")

        self.canvas_q = tk.Canvas(self.quiet_tab_frame, highlightthickness=0)
        self.canvas_q.pack(side="left", fill="both", expand=True)

        self.q_scrollbar = ttk.Scrollbar(self.quiet_tab_frame, orient="vertical", command=self.canvas_q.yview)
        self.q_scrollbar.pack(side="right", fill="y")
        self.canvas_q.configure(yscrollcommand=self.q_scrollbar.set)

        self.quiet_list_frame = tk.Frame(self.canvas_q)
        self.quiet_list_frame.bind(
            "<Configure>",
            lambda e: self.canvas_q.configure(scrollregion=self.canvas_q.bbox("all"))
        )
        self.canvas_q.create_window((0, 0), window=self.quiet_list_frame, anchor="nw")

        # -------- Вкладка "Контрольные" --------
        self.control_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.control_tab, text="К")

        self.canvas_c = tk.Canvas(self.control_tab, highlightthickness=0)
        self.canvas_c.pack(side="left", fill="both", expand=True)

        self.c_scrollbar = ttk.Scrollbar(self.control_tab, orient="vertical", command=self.canvas_c.yview)
        self.c_scrollbar.pack(side="right", fill="y")
        self.canvas_c.configure(yscrollcommand=self.c_scrollbar.set)

        # создание фрейма для контрольных задач
        self.control_list_frame = tk.Frame(self.canvas_c)
        self.control_list_frame.bind(
            "<Configure>", 
            lambda e: self.canvas_c.configure(scrollregion=self.canvas_c.bbox("all"))
        )
        self.canvas_c.create_window((0, 0), window=self.control_list_frame, anchor="nw")


