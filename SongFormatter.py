import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

import markdown
from tkhtmlview import HTMLScrolledText

from convertrawtext import FormatText
from settings import SettingsEditor, get

version = "0.12 Fixes"
SESSION_DIR = Path(".songformatter_workspace")
SESSION_FILE = SESSION_DIR / "session.json"


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


icon_path = resource_path(r"icon.png")
help_path = resource_path("README.md")


def activate_next_module():
    pass


def select_main_tab(tab_widget):
    main_notebook.select(tab_widget)


def get_active_document():
    current_tab = documents_notebook.select()
    if not current_tab:
        return None
    return documents_notebook.nametowidget(current_tab)


def refresh_bpm_label():
    doc = get_active_document()
    bpm_label.set(doc.get_bpm_label() if doc else "Tap BPM")


def format_key_status(doc):
    if doc is None or doc.last_key_analysis is None or doc.last_key_analysis.final.winner is None:
        return "Key: unknown"

    final = doc.last_key_analysis.final
    winner = final.winner
    detector_winners = [
        result.winner.label
        for result in doc.last_key_analysis.detectors
        if result.detector != "weighted" and result.winner is not None
    ]
    agreement = detector_winners.count(winner.label)
    status = f"Key: {winner.label}"
    if len(final.candidates) > 1 and final.candidates[1].label != winner.label:
        status += f" | Alt: {final.candidates[1].label}"
    status += f" | Agree: {agreement}/{max(1, len(detector_winners))}"
    return status


def update_analysis_window():
    if analysis_text is None or not analysis_text.winfo_exists():
        return

    doc = get_active_document()
    analysis_text.configure(state="normal")
    analysis_text.delete("1.0", tk.END)

    if doc is None or doc.last_key_analysis is None:
        analysis_text.insert("1.0", "No key analysis available.")
    else:
        final = doc.last_key_analysis.final
        winner = final.winner.label if final.winner is not None else "unknown"
        analysis_text.insert(tk.END, f"Combined Result\n", ("heading",))
        analysis_text.insert(tk.END, f"{winner}\n", ("winner",))
        analysis_text.insert(tk.END, f"{final.summary}\n")
        if final.candidates:
            analysis_text.insert(
                tk.END,
                "Top combined candidates: "
                + ", ".join(candidate.to_text() for candidate in final.candidates[:5])
                + "\n\n",
            )

        grouped_detectors = [
            ("Tonal Detectors", {"note_counting", "note_count_circle_of_fifths", "functional_harmony", "cadence", "tonic_emphasis"}),
            ("Modal Detectors", {"scale_fit", "violation_count"}),
            ("Combined", {"weighted"}),
        ]

        for heading, detector_names in grouped_detectors:
            section_results = [
                result for result in doc.last_key_analysis.detectors
                if result.detector in detector_names
            ]
            if not section_results:
                continue

            analysis_text.insert(tk.END, f"{heading}\n", ("section",))

            for result in section_results:
                analysis_text.insert(tk.END, f"{result.detector}\n", ("heading",))
                analysis_text.insert(tk.END, f"{result.summary}\n")

                if result.winner is not None:
                    analysis_text.insert(tk.END, f"Winner: {result.winner.to_text()}\n")

                if result.candidates:
                    analysis_text.insert(
                        tk.END,
                        "Candidates: " + ", ".join(candidate.to_text() for candidate in result.candidates[:5]) + "\n",
                    )

                if result.evidence:
                    analysis_text.insert(tk.END, "Evidence:\n", ("label",))
                    for line in result.evidence[:6]:
                        analysis_text.insert(tk.END, f"  - {line}\n")

                debug_keys = ", ".join(sorted(result.debug.keys()))
                if debug_keys:
                    analysis_text.insert(tk.END, f"Debug fields: {debug_keys}\n")

                analysis_text.insert(tk.END, "\n")

    analysis_text.configure(state="disabled")


def refresh_status_bar():
    status_var.set(format_key_status(get_active_document()))
    update_analysis_window()


def get_document_title(doc):
    if doc.file_path:
        base_title = Path(doc.file_path).stem or Path(doc.file_path).name
    else:
        base_title = doc.get_suggested_basename()
    return f"* {base_title}" if doc.is_dirty else base_title


def update_document_tab_title(doc):
    try:
        documents_notebook.tab(doc, text=get_document_title(doc))
    except tk.TclError:
        return
    update_window_title()


def update_window_title():
    doc = get_active_document()
    title = get_document_title(doc) if doc else "Song Formatter"
    root.title(f"Song Formatter - {title}")


def save_session():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    docs = []
    for tab_id in documents_notebook.tabs():
        doc = documents_notebook.nametowidget(tab_id)
        docs.append(
            {
                "file_path": doc.file_path,
                "text": doc.get_document_text(),
                "last_saved_text": doc.last_saved_text,
                "is_dirty": doc.is_dirty,
            }
        )

    payload = {
        "active_index": documents_notebook.index("current") if documents_notebook.tabs() else 0,
        "documents": docs,
    }
    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=True, indent=2)


def on_document_change(doc):
    update_document_tab_title(doc)
    refresh_bpm_label()
    refresh_status_bar()
    save_session()


def create_document_tab(text="", file_path=None, select=True, last_saved_text=None, is_dirty=None):
    doc = FormatText(documents_notebook, on_next=activate_next_module, on_change=on_document_change)
    documents_notebook.add(doc, text="Untitled Song")
    doc.set_document_text(
        text,
        file_path=file_path,
        last_saved_text=text if last_saved_text is None and file_path else last_saved_text,
        is_dirty=bool(text.strip()) and file_path is None if is_dirty is None else is_dirty,
    )
    if select:
        documents_notebook.select(doc)
        select_main_tab(documents_frame)
        doc.raw_text.focus_set()
    update_document_tab_title(doc)
    return doc


def get_reusable_document():
    doc = get_active_document()
    if doc is not None and doc.is_reusable_blank():
        return doc
    return None


def new_document():
    doc = get_reusable_document()
    if doc is not None:
        select_main_tab(documents_frame)
        documents_notebook.select(doc)
        doc.raw_text.focus_set()
        return
    create_document_tab()


def load_file_as_new_tab():
    doc = get_reusable_document()
    if doc is None:
        doc = create_document_tab(select=True)
    else:
        select_main_tab(documents_frame)
        documents_notebook.select(doc)
    doc.load_file()


def close_current_document():
    doc = get_active_document()
    if doc is None:
        return
    documents_notebook.forget(doc)
    if not documents_notebook.tabs():
        create_document_tab()
    refresh_bpm_label()
    update_window_title()
    save_session()


def focus_editor():
    doc = get_active_document()
    if doc is not None:
        doc.raw_text.focus_set()


def refresh_preview():
    doc = get_active_document()
    if doc is None:
        return
    select_main_tab(documents_frame)
    doc.convert_text()
    focus_editor()


def open_settings():
    settings_module.populate_frame()
    select_main_tab(settings_module)


def open_key_analysis_window():
    global analysis_window, analysis_text

    if analysis_window is not None and analysis_window.winfo_exists():
        analysis_window.deiconify()
        analysis_window.lift()
        update_analysis_window()
        return

    analysis_window = tk.Toplevel(root)
    analysis_window.title("Key Analysis")
    analysis_window.geometry("900x420")

    analysis_text = tk.Text(analysis_window, wrap=tk.WORD)
    analysis_text.pack(fill=tk.BOTH, expand=True)
    analysis_text.tag_configure("section", font=("TkDefaultFont", 11, "bold"))
    analysis_text.tag_configure("heading", font=("TkDefaultFont", 10, "bold"))
    analysis_text.tag_configure("winner", font=("TkDefaultFont", 12, "bold"))
    analysis_text.tag_configure("label", font=("TkDefaultFont", 9, "bold"))
    update_analysis_window()


def apply_bpm():
    doc = get_active_document()
    if doc is None:
        return
    bpm_label.set(doc.tap_bpm())


def select_background_image():
    doc = get_active_document()
    if doc is None:
        return
    doc.select_image()
    focus_editor()


def paste_as_new():
    source_doc = get_active_document()
    if source_doc is None:
        return
    try:
        clipboard_text = source_doc.raw_text.clipboard_get()
    except tk.TclError:
        messagebox.showinfo("Paste As New", "Clipboard does not contain text.")
        return
    doc = get_reusable_document()
    if doc is None:
        create_document_tab(text=clipboard_text, file_path=None, select=True)
    else:
        select_main_tab(documents_frame)
        documents_notebook.select(doc)
        doc.set_document_text(clipboard_text, file_path=None, last_saved_text="", is_dirty=bool(clipboard_text.strip()))
        doc.raw_text.focus_set()


def export_both():
    doc = get_active_document()
    if doc is not None:
        doc.export_both()


def save_document():
    doc = get_active_document()
    if doc is not None:
        doc.save_file()


def save_document_as():
    doc = get_active_document()
    if doc is not None:
        doc.save_as_file()


def save_pdf():
    doc = get_active_document()
    if doc is not None:
        doc.save_pdf_file()


def cut_selection():
    doc = get_active_document()
    if doc is not None:
        doc.cut_selection()


def copy_selection():
    doc = get_active_document()
    if doc is not None:
        doc.copy_selection()


def paste_clipboard():
    doc = get_active_document()
    if doc is not None:
        doc.paste_clipboard()


def select_all():
    doc = get_active_document()
    if doc is not None:
        doc.select_all()


def load_session():
    if SESSION_FILE.is_file():
        try:
            with SESSION_FILE.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            documents = payload.get("documents", [])
            for document in documents:
                create_document_tab(
                    text=document.get("text", ""),
                    file_path=document.get("file_path") or None,
                    select=False,
                    last_saved_text=document.get("last_saved_text"),
                    is_dirty=document.get("is_dirty"),
                )
            if documents_notebook.tabs():
                active_index = min(payload.get("active_index", 0), len(documents_notebook.tabs()) - 1)
                documents_notebook.select(active_index)
                return
        except (OSError, json.JSONDecodeError):
            pass

    last = Path("lastopened.txt")
    if last.is_file():
        create_document_tab(text=last.read_text(), select=True)
    else:
        create_document_tab(select=True)


def on_documents_tab_changed(event):
    if main_notebook.select() == str(documents_frame):
        refresh_bpm_label()
        update_window_title()
        focus_editor()
    refresh_status_bar()
    save_session()


def get_tab_index_at(x, y):
    try:
        return documents_notebook.index(f"@{x},{y}")
    except tk.TclError:
        return None


def close_document_by_index(index):
    if index is None:
        return
    tabs = documents_notebook.tabs()
    if index < 0 or index >= len(tabs):
        return
    doc = documents_notebook.nametowidget(tabs[index])
    documents_notebook.select(doc)
    close_current_document()


def on_tab_middle_click(event):
    index = get_tab_index_at(event.x, event.y)
    close_document_by_index(index)


def show_tab_context_menu(event):
    index = get_tab_index_at(event.x, event.y)
    if index is None:
        return
    documents_notebook.select(index)
    tab_menu.tk_popup(event.x_root, event.y_root)


def display_help():
    global help_path
    try:
        with open(help_path, "r") as file:
            text = file.read()
    except FileNotFoundError:
        text = "The help file is missing. Expect it to be at " + help_path

    html = markdown.markdown(text, extensions=["markdown.extensions.nl2br", "markdown.extensions.toc"])

    help_window = tk.Toplevel(root)
    help_window.title("Help")
    help_window.geometry("1024x800")

    html_label = HTMLScrolledText(help_window, html=html)
    html_label.pack(fill="both", expand=True)


def show_version():
    messagebox.showinfo("About", f"Version: {version}\n2023 - BOB RMT")


def check_buttons_greyed():
    active = "normal" if get_active_document() is not None else "disabled"
    for label in ["Save", "Save as...", "Save PDF", "Export Both", "Close Document"]:
        file_menu.entryconfigure(label, state=active)


def on_app_close():
    save_session()
    root.destroy()


root = tk.Tk()
root.title("Song Formatter")
root.geometry(get("UI", "WindowSize", "1280x800"))
if os.path.exists(icon_path):
    root.tk.call("wm", "iconphoto", root._w, tk.PhotoImage(file=icon_path))

menu = tk.Menu(root)
root.config(menu=menu)

file_menu = tk.Menu(menu)
menu.add_cascade(label="File", menu=file_menu)

edit_menu = tk.Menu(menu)
menu.add_cascade(label="Edit", menu=edit_menu)

view_menu = tk.Menu(menu)
menu.add_cascade(label="View", menu=view_menu)

tools_menu = tk.Menu(menu)
menu.add_cascade(label="Tools", menu=tools_menu)

help_menu = tk.Menu(menu)
menu.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Manual", command=display_help)
help_menu.add_command(label="About", command=show_version)

top_panel = ttk.Frame(root, padding=(8, 6))
top_panel.pack(side=tk.TOP, fill=tk.X)

status_frame = ttk.Frame(root, padding=(8, 4))
status_frame.pack(side=tk.BOTTOM, fill=tk.X)

main_notebook = ttk.Notebook(root)
main_notebook.pack(expand=True, fill=tk.BOTH)

documents_frame = ttk.Frame(main_notebook)
documents_frame.pack(fill=tk.BOTH, expand=True)
main_notebook.add(documents_frame, text="Documents")

settings_module = SettingsEditor(main_notebook)
main_notebook.add(settings_module, text="Settings")

documents_notebook = ttk.Notebook(documents_frame)
documents_notebook.pack(fill=tk.BOTH, expand=True)
documents_notebook.bind("<<NotebookTabChanged>>", on_documents_tab_changed)
documents_notebook.bind("<Button-2>", on_tab_middle_click)
documents_notebook.bind("<Button-3>", show_tab_context_menu)

tab_menu = tk.Menu(root, tearoff=0)
tab_menu.add_command(label="Close", command=close_current_document)
tab_menu.add_command(label="New Document", command=new_document)

analysis_window = None
analysis_text = None

ttk.Button(top_panel, text="New", command=new_document).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Load", command=load_file_as_new_tab).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Paste As New", command=paste_as_new).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Close", command=close_current_document).pack(side=tk.LEFT, padx=(0, 6))
ttk.Separator(top_panel, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
ttk.Button(top_panel, text="Save", command=save_document).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Save As", command=save_document_as).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Save PDF", command=save_pdf).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Export Both", command=export_both).pack(side=tk.LEFT, padx=(0, 6))
ttk.Separator(top_panel, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
ttk.Button(top_panel, text="Refresh Preview", command=refresh_preview).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Select Image", command=select_background_image).pack(side=tk.LEFT, padx=(0, 6))
ttk.Button(top_panel, text="Settings", command=open_settings).pack(side=tk.LEFT, padx=(0, 6))

bpm_label = tk.StringVar(value="Tap BPM")
ttk.Separator(top_panel, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
ttk.Button(top_panel, textvariable=bpm_label, command=apply_bpm).pack(side=tk.LEFT)

status_var = tk.StringVar(value="Key: unknown")
ttk.Label(status_frame, textvariable=status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

file_menu.add_command(label="New Document", command=new_document)
file_menu.add_command(label="Load", command=load_file_as_new_tab)
file_menu.add_command(label="Paste As New", command=paste_as_new)
file_menu.add_command(label="Close Document", command=close_current_document)
file_menu.add_separator()
file_menu.add_command(label="Save", command=save_document)
file_menu.add_command(label="Save as...", command=save_document_as)
file_menu.add_command(label="Save PDF", command=save_pdf)
file_menu.add_command(label="Export Both", command=export_both)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_app_close)

edit_menu.add_command(label="Cut", command=cut_selection)
edit_menu.add_command(label="Copy", command=copy_selection)
edit_menu.add_command(label="Paste", command=paste_clipboard)
edit_menu.add_command(label="Paste As New", command=paste_as_new)
edit_menu.add_command(label="Select All", command=select_all)

view_menu.add_command(label="Documents", command=lambda: select_main_tab(documents_frame))
view_menu.add_command(label="Settings", command=open_settings)

tools_menu.add_command(label="Refresh Preview", command=refresh_preview)
tools_menu.add_command(label="Select Image", command=select_background_image)
tools_menu.add_command(label="Tap BPM", command=apply_bpm)
tools_menu.add_command(label="Export Both", command=export_both)
tools_menu.add_command(label="Key Analysis", command=open_key_analysis_window)

file_menu.configure(postcommand=check_buttons_greyed)
root.protocol("WM_DELETE_WINDOW", on_app_close)

load_session()
select_main_tab(documents_frame)
refresh_bpm_label()
refresh_status_bar()
update_window_title()

root.mainloop()
