import configparser
import tkinter as tk
from tkinter import BooleanVar, StringVar

# Configuration
CONFIG_FILE = 'songformatter_settings.ini'

DEFAULT_SETTINGS = {
    "UI": {
        "WindowSize": "1280x800",
    },
    "Render": {
        "TopMargin": "24",
        "LeftMarginLeft": "80",
        "RightMargin": "36",
        "BottomMargin": "36",
        "FontSize": "13",
        "HeaderSize": "18",
        "LineSpacing": "2",
        "Font": "Helvetica",
        "CursiveFont": "Helvetica-Oblique",
        "ChordFont": "Helvetica-Oblique",
        "ChordFontSize": "11.5",
        "ChordsWidth": "120",
        "Tuning": "EADGBE",
        "Capo": "0",
        "Transpose": "0",
    },
    "Options": {
        "PrintGuitarChords": "1",
        "PrintPianoChords": "1",
    },
    "Background": {
        "Image": "",
        "Position": "250x20",
        "Size": "200x100",
        "Opacity": "50",
        "Show": "1",
    },
    "Misc": {
        "A4MarkerColor": "[0.7, 0.7, 0.5]",
        "MarginMarkerColor": "[0.9, 0.9, 0.7]",
    },
    "Format": {
        "PageBreakFlexibleLines": "4",
    },
}

BOOLEAN_SETTINGS = {
    ("Options", "PrintGuitarChords"),
    ("Options", "PrintPianoChords"),
    ("Background", "Show"),
}

class CasePreservingConfigParser(configparser.ConfigParser):
    # Override the optionxform method to preserve the case of the option names
    def optionxform(self, optionstr):
        return optionstr

# Read the configuration file on import
#cfg = configparser.configparser()
cfg = CasePreservingConfigParser()
cfg.read(CONFIG_FILE)


def _write_config():
    with open(CONFIG_FILE, 'w') as f:
        cfg.write(f)


def ensure_default_settings():
    changed = False
    for section, options in DEFAULT_SETTINGS.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
            changed = True
        for option, value in options.items():
            if not cfg.has_option(section, option):
                cfg.set(section, option, str(value))
                changed = True
    if changed:
        _write_config()


ensure_default_settings()

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
    _write_config()

def getF(*args, **kwargs):
    return float(get(*args, **kwargs))

def getI(*args, **kwargs):
    return int(get(*args, **kwargs))


class SettingsEditor(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.vars = {}
        self._build_layout()
        self.populate_frame()

        self.bind("<FocusIn>", self.refresh)

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas)

        self.content.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._resize_content)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.content)

    def _resize_content(self, event):
        self.canvas.itemconfigure(self.content_window, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel_linux, add="+")
        widget.bind("<Button-5>", self._on_mousewheel_linux, add="+")

    def _on_mousewheel(self, event):
        if event.delta == 0:
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def _is_boolean_setting(self, section, key, value):
        return (section, key) in BOOLEAN_SETTINGS or value in {"0", "1"}

    def populate_frame(self):
        ensure_default_settings()

        for widget in self.content.winfo_children():
            widget.destroy()

        row = 0
        section_names = list(DEFAULT_SETTINGS.keys())
        extras = [section for section in cfg.sections() if section not in DEFAULT_SETTINGS]
        section_names.extend(sorted(extras))

        for section in section_names:
            if not cfg.has_section(section):
                continue

            sect_label = tk.Label(self.content, text=section, anchor="w", font=("TkDefaultFont", 10, "bold"))
            sect_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=8, pady=(10, 2))
            row += 1

            for key, value in cfg.items(section):
                label = tk.Label(self.content, text=key, anchor="e")
                label.grid(row=row, column=0, sticky="e", padx=(8, 6), pady=2)

                if self._is_boolean_setting(section, key, value):
                    var = BooleanVar(value=(str(value) == "1"))
                    field = tk.Checkbutton(
                        self.content,
                        variable=var,
                        onvalue=True,
                        offvalue=False,
                        anchor="w",
                    )
                    field.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=2)
                    var.trace_add("write", lambda *args, key=key, section=section, var=var: self.update_boolean_setting(section, key, var))
                else:
                    var = StringVar(value=value)
                    field = tk.Entry(self.content, textvariable=var)
                    field.grid(row=row, column=1, sticky="we", padx=(0, 8), pady=2)
                    var.trace_add("write", lambda *args, key=key, section=section, var=var: self.update_setting(section, key, var))

                self._bind_mousewheel(label)
                self._bind_mousewheel(field)
                row += 1

        self.content.grid_columnconfigure(0, weight=0, minsize=180)
        self.content.grid_columnconfigure(1, weight=1, minsize=320)

    def update_setting(self, section, key, var):
        set(section, key, var.get())

    def update_boolean_setting(self, section, key, var):
        set(section, key, "1" if var.get() else "0")

    # This method is called when the frame gets focus
    def refresh(self, event):
        if self.focus_get() == self:
            self.populate_frame()


## Usage:

#root = tk.Tk()
#editor = SettingsEditor(root)
#editor.pack(fill="both", expand=True)
#root.mainloop()
