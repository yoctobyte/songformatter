import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from convertrawtext import *
from test2 import *
from settings import *
import markdown
#import markdown.extensions.breaks
#from tkinterhtml import HtmlFrame
from tkhtmlview import HTMLScrolledText

version = "0.12 Fixes" 

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

icon_path = resource_path(r"icon.png")
help_path = resource_path('README.md')


def activate_next_module():
    # Implement the logic to activate the next module
    pass


# Initialize the main window
root = tk.Tk()
root.title("Song Formatter")
root.geometry(get("UI", "WindowSize", "1280x800"))
if os.path.exists(icon_path):
    root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=icon_path))

def check_buttons_greyed():
    save_allowed = (format_text_module.file_path is not None)
    if save_allowed:
        file_menu.entryconfigure("Save", state="normal")
    else:
        file_menu.entryconfigure("Save", state="disabled")

def display_help():
    global help_path
    try:
        with open(help_path, 'r') as file:
            text = file.read()
    except FileNotFoundError:
        text = 'The help file is missing. Expect it to be at '+help_path

    # Convert Markdown to HTML
    html = markdown.markdown(text, extensions=['markdown.extensions.nl2br', 'markdown.extensions.toc'])

    help_window = tk.Toplevel(root)
    help_window.title("Help")
    help_window.geometry("1024x800")

    html_label = HTMLScrolledText(help_window, html=html)
    html_label.pack(fill="both", expand=True)

def show_version():
    messagebox.showinfo("About", f"Version: {version}\n2023 - BOB RMT")



# Create main menu
menu = tk.Menu(root)
root.config(menu=menu)

file_menu = tk.Menu(menu) 
menu.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.destroy)

help_menu = tk.Menu(menu)
menu.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Manual", command=display_help)
help_menu.add_command(label="About", command=show_version)

# Create top and bottom panels
top_panel = ttk.Frame(root)
top_panel.pack(side=tk.TOP, fill=tk.X)

bottom_panel = ttk.Frame(root)
bottom_panel.pack(side=tk.BOTTOM, fill=tk.X)

# Create a Notebook (tab container)
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill=tk.BOTH)

## Add the Load File module
#load_file_module = LoadFileModule(notebook)
#notebook.add(load_file_module, text="Load File")

# Add the Settings module
settings_module = SettingsEditor(notebook)
notebook.add(settings_module, text="Settings")


# Create an instance of the FormatText module
format_text_module = FormatText(notebook, on_next=activate_next_module)
#format_text_module.pack(expand=True, fill=tk.BOTH)
notebook.add(format_text_module, text="Format")

notebook.select(format_text_module)

file_menu.add_command(label="Load", command=format_text_module.load_file)
file_menu.add_command(label="Save", command=format_text_module.save_file)
file_menu.add_command(label="Save as...", command=format_text_module.save_as_file)
file_menu.add_command(label="Save PDF", command=format_text_module.save_pdf_file)

#file_menu.postcommand(check_buttons_greyed) #that would be for a dropdown menu from OptionMenu
#file_menu.bind("<Map>", check_buttons_greyed)
file_menu.configure(postcommand=check_buttons_greyed)

# Run the main loop
root.mainloop()

