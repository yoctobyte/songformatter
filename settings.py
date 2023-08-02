import configparser
import tkinter as tk
from tkinter import StringVar

# Configuration
CONFIG_FILE = 'songformatter_settings.ini'

class CasePreservingConfigParser(configparser.ConfigParser):
    # Override the optionxform method to preserve the case of the option names
    def optionxform(self, optionstr):
        return optionstr

# Read the configuration file on import
#cfg = configparser.configparser()
cfg = CasePreservingConfigParser()
cfg.read(CONFIG_FILE)

def get(section, option, default=None):
    if not cfg.has_section(section):
        cfg.add_section(section)
    if not cfg.has_option(section, option):
        set(section, option, default)
    return cfg.get(section, option)

def set(section, option, value):
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, option, str(value))
    with open(CONFIG_FILE, 'w') as f:
        cfg.write(f)

def getF(*args, **kwargs):
    return float(get(*args, **kwargs))

def getI(*args, **kwargs):
    return int(get(*args, **kwargs))


class SettingsEditor(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=80)  # column for labels
        self.grid_columnconfigure(1, weight=1, minsize=120)
        self.grid_columnconfigure(1, weight=1, minsize=620)

        self.vars = {}

        self.populate_frame()

        # Bind the focus event to the refresh method
        self.bind("<FocusIn>", self.refresh)

    def populate_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        row = 0
        for section in cfg.sections():
            sect_label = tk.Label(self, text=f"{section}")
            sect_label.grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1

            for key, value in cfg.items(section):
                label = tk.Label(self, text=f"{key}")
                label.grid(row=row, column=0, sticky="e")

                var = StringVar()
                var.set(value)

                entry = tk.Entry(self, textvariable=var)
                entry.grid(row=row, column=1, sticky="we")

                var.trace("w", lambda *args, key=key, section=section, var=var: self.update_setting(section, key, var))
                row += 1

    def update_setting(self, section, key, var):
        set(section, key, var.get())

    # This method is called when the frame gets focus
    def refresh(self, event):
        if self.focus_get() == self:
            self.populate_frame()


## Usage:

#root = tk.Tk()
#editor = SettingsEditor(root)
#editor.pack(fill="both", expand=True)
#root.mainloop()

