import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import time, os, sys, json, socket, csv
from datetime import datetime, timedelta

# Set paths for configuration files.
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(application_path, "subject_log.json")
PRE_CONFIG_CSV = os.path.join(application_path, "pre_config.csv")


def show_startup_menu(root, font):
    print("Showing startup menu...")
    menu_win = tk.Toplevel(root)
    menu_win.title("Select Configuration")
    menu_win.configure(bg="#333333")
    menu_win.geometry("400x300")
    menu_win.transient(root)
    menu_win.lift()
    menu_win.focus_force()
    tk.Label(menu_win, text="Select Configuration Option:", font=font, bg="#333333", fg="white").pack(pady=20)
    choice = {"value": None}
    def set_choice(val):
        choice["value"] = val
        menu_win.destroy()
    tk.Button(menu_win, text="New Config", font=font, bg="#3498db", fg="white",
              relief="flat", command=lambda: set_choice("new")).pack(pady=10)
    tk.Button(menu_win, text="Load Last Config", font=font, bg="#2ecc71", fg="white",
              relief="flat", command=lambda: set_choice("last")).pack(pady=10)
    tk.Button(menu_win, text="Load Pre-Config", font=font, bg="#f39c12", fg="white",
              relief="flat", command=lambda: set_choice("pre")).pack(pady=10)
    root.wait_window(menu_win)
    print("Startup menu closed with choice:", choice["value"])
    return choice["value"]


class CreateToolTip:
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)
    def enter(self, event=None):
        self.schedule()
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)
    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)
    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class AutocompleteEntry(tk.Entry):
    """
    An Entry widget with autocompletion functionality.
    Suggestions are in the format "CODE - Subject Name". Only the code is inserted.
    Autocompletion starts from the first letter.
    """
    def __init__(self, master, autocomplete_list, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.autocomplete_list = autocomplete_list
        self.var = self["textvariable"]
        if not self.var:
            self.var = self["textvariable"] = tk.StringVar()
        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Up>", self.move_up)
        self.bind("<Down>", self.move_down)
        self.listbox_up = False
    def changed(self, name, index, mode):
        if self.var.get() == '':
            if self.listbox_up:
                self.listbox.destroy()
                self.listbox_up = False
        else:
            words = self.comparison()
            if words:
                if not self.listbox_up:
                    self.listbox = tk.Listbox(self.master, width=self["width"], font=self["font"])
                    self.listbox.bind("<Button-1>", self.selection)
                    self.listbox.bind("<Right>", self.selection)
                    self.listbox.place(x=self.winfo_x(), y=self.winfo_y() + self.winfo_height())
                    self.listbox_up = True
                self.listbox.delete(0, tk.END)
                for w in words:
                    self.listbox.insert(tk.END, w)
            else:
                if self.listbox_up:
                    self.listbox.destroy()
                    self.listbox_up = False
    def selection(self, event):
        if self.listbox_up:
            index = self.listbox.nearest(event.y)
            value = self.listbox.get(index)
            if " - " in value:
                value = value.split(" - ")[0]
            self.var.set(value)
            self.listbox.destroy()
            self.listbox_up = False
            self.icursor(tk.END)
    def move_up(self, event):
        if self.listbox_up:
            if self.listbox.curselection() == ():
                index = '0'
            else:
                index = self.listbox.curselection()[0]
            if index != '0':
                self.listbox.selection_clear(first=index)
                index = str(int(index) - 1)
                self.listbox.selection_set(first=index)
                self.listbox.activate(index)
    def move_down(self, event):
        if self.listbox_up:
            if self.listbox.curselection() == ():
                index = '-1'
            else:
                index = self.listbox.curselection()[0]
            if index != tk.END:
                self.listbox.selection_clear(first=index)
                index = str(int(index) + 1)
                self.listbox.selection_set(first=index)
                self.listbox.activate(index)
    def comparison(self):
        pattern = self.var.get().lower()
        return [w for w in self.autocomplete_list if w.lower().startswith(pattern)]


class FullScreenClockApp:
    def __init__(self, root, config_choice):
        self.root = root
        self.root.title("Exam Clock & Information")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="#1a1a1a")
        # Adaptive fonts and icon sizes.
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1280:
            self.clock_font = ("Helvetica", 80, "bold")
            self.info_font = ("Helvetica", 18, "bold")
            self.sub_header_font = ("Helvetica", 24)
            self.custom_font = ("Helvetica", 18)
            self.icon_font = ("Helvetica", 12)
        else:
            self.clock_font = ("Helvetica", 140, "bold")
            self.info_font = ("Helvetica", 28, "bold")
            self.sub_header_font = ("Helvetica", 32)
            self.custom_font = ("Helvetica", 20)
            self.icon_font = ("Helvetica", 16)
        self.flash_count = 6
        self.flash_delay = 500
        self.main_bg_color = "#1a1a1a"
        self.header_bg_color = "#2c2c2c"
        self.clock_fg_color = "#FFFF00"
        self.clock_bg_color = "#000000"
        self.time_offset = 0
        self.exam_date = time.strftime("%d-%b-%Y", time.localtime())
        self.exam_start_time = None
        self.exam_end_time = None
        self.demo_mode = False
        self.original_exam_start_time = None
        self.original_exam_end_time = None
        self.edit_mode = False
        # Load configuration based on startup choice.
        if config_choice == "new":
            self.subject_info = self.get_subject_info()
            self.exam_start_time, self.exam_end_time = self.get_exam_times()
        elif config_choice == "last":
            config = self.load_configuration()
            self.subject_info = config.get("subject_info", [])
            self.exam_start_time = config.get("exam_start_time")
            self.exam_end_time = config.get("exam_end_time")
        elif config_choice == "pre":
            pre_config = self.load_pre_config()
            if pre_config:
                self.exam_date = pre_config.get("exam_date", self.exam_date)
                self.exam_start_time = pre_config.get("exam_start_time")
                self.exam_end_time = pre_config.get("exam_end_time")
                self.subject_info = []
                for code, name in pre_config.get("subject_info", []):
                    rows = self.custom_simpledialog("Input", f"Enter the seat rows for {code} - {name}:")
                    if not rows:
                        rows = "No Rows Provided"
                    self.subject_info.append((code, name, rows))
            else:
                self.subject_info = self.get_subject_info()
                self.exam_start_time, self.exam_end_time = self.get_exam_times()
        else:
            self.subject_info = self.get_subject_info()
            self.exam_start_time, self.exam_end_time = self.get_exam_times()
        self.save_configuration()
        self.check_internet_and_time()
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("custom.Horizontal.TProgressbar", troughcolor="#444444", background="#2ecc71")
        self.setup_ui()
        self.update_clock()
        self.root.bind("<Escape>", self.exit_fullscreen)
    
    def bind_double_click(self, widget, row_index):
        """Recursively bind double-click events to widget and all its children."""
        widget.bind("<Double-Button-1>", lambda e, idx=row_index: self.edit_subject_dialog(idx))
        for child in widget.winfo_children():
            self.bind_double_click(child, row_index)
    
    def setup_ui(self):
        self.main_frame = tk.Frame(self.root, bg=self.main_bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.header_frame = tk.Frame(self.main_frame, bg=self.header_bg_color)
        self.header_frame.pack(fill="x", pady=(0, 10))
        self.header_frame.columnconfigure(0, weight=1)
        self.header_frame.columnconfigure(1, weight=0)
        self.header_frame.columnconfigure(2, weight=0)
        self.header_frame.columnconfigure(3, weight=0)
        exam_info_text = f"Date: {self.exam_date}    |    Exam Start: {self.exam_start_time}    |    Exam End: {self.exam_end_time}"
        self.exam_info_label = tk.Label(self.header_frame, text=exam_info_text,
                                        font=self.sub_header_font, fg="white", bg=self.header_bg_color)
        self.exam_info_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        help_button = tk.Button(self.header_frame, text="❓", command=self.open_help_window,
                                 font=self.icon_font, bg="#8e44ad", fg="white", relief="flat")
        help_button.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        CreateToolTip(help_button, "Tutorial, Demo Mode & Edit Layout")
        settings_button = tk.Button(self.header_frame, text="⚙", command=self.open_settings_window,
                                    font=self.icon_font, bg="#3498db", fg="white", relief="flat")
        settings_button.grid(row=0, column=2, sticky="e", padx=10, pady=10)
        CreateToolTip(settings_button, "Settings")
        exit_button = tk.Button(self.header_frame, text="✖", command=self.exit_fullscreen,
                                font=self.icon_font, bg="#e74c3c", fg="white", relief="flat")
        exit_button.grid(row=0, column=3, sticky="e", padx=10, pady=10)
        CreateToolTip(exit_button, "Exit")
        self.clock_frame = tk.Frame(self.main_frame, bg=self.clock_bg_color, bd=6, relief="ridge")
        self.clock_frame.pack(fill="both", expand=True, pady=10)
        self.clock_label = tk.Label(self.clock_frame, text="",
                                    font=self.clock_font, fg=self.clock_fg_color, bg=self.clock_bg_color)
        self.clock_label.pack(expand=True)
        self.progress_frame = tk.Frame(self.main_frame, bg=self.main_bg_color)
        self.progress_frame.pack(fill="x", pady=10)
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal",
                                        mode="determinate", maximum=100,
                                        style="custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=20)
        self.subject_frame = tk.Frame(self.main_frame, bg=self.main_bg_color)
        self.subject_frame.pack(fill="x", pady=(10, 0))
        self.display_subject_info()
    
    def open_settings_window(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.configure(bg="#333333")
        settings_win.grab_set()
        labels = ["Clock Font Size:", "Info Font Size:", "Subheader Font Size:", "Flash Count:",
                  "Flash Delay (ms):", "Main BG Color:", "Header BG Color:", "Clock FG Color:", "Clock BG Color:"]
        current_values = [str(self.clock_font[1]), str(self.info_font[1]), str(self.sub_header_font[1]),
                          str(self.flash_count), str(self.flash_delay), self.main_bg_color,
                          self.header_bg_color, self.clock_fg_color, self.clock_bg_color]
        entries = {}
        for i, (label_text, current) in enumerate(zip(labels, current_values)):
            tk.Label(settings_win, text=label_text, font=self.custom_font, bg="#333333", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky="e")
            entry = tk.Entry(settings_win, font=self.custom_font, width=20)
            entry.insert(0, current)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            entries[label_text] = entry
        def save_settings():
            try:
                clock_font_size = int(entries["Clock Font Size:"].get())
                info_font_size = int(entries["Info Font Size:"].get())
                sub_header_font_size = int(entries["Subheader Font Size:"].get())
                self.clock_font = ("Helvetica", clock_font_size, "bold")
                self.info_font = ("Helvetica", info_font_size, "bold")
                self.sub_header_font = ("Helvetica", sub_header_font_size)
                self.flash_count = int(entries["Flash Count:"].get())
                self.flash_delay = int(entries["Flash Delay (ms):"].get())
                self.main_bg_color = entries["Main BG Color:"].get()
                self.header_bg_color = entries["Header BG Color:"].get()
                self.clock_fg_color = entries["Clock FG Color:"].get()
                self.clock_bg_color = entries["Clock BG Color:"].get()
                self.main_frame.configure(bg=self.main_bg_color)
                self.header_frame.configure(bg=self.header_bg_color)
                self.exam_info_label.configure(font=self.sub_header_font, bg=self.header_bg_color)
                self.clock_frame.configure(bg=self.clock_bg_color)
                self.clock_label.configure(font=self.clock_font, fg=self.clock_fg_color, bg=self.clock_bg_color)
                self.display_subject_info()
            except Exception as e:
                messagebox.showerror("Error", f"Error saving settings: {e}")
            settings_win.destroy()
        tk.Button(settings_win, text="Save", command=save_settings, font=self.custom_font,
                  bg="#e74c3c", fg="white", relief="flat").grid(row=len(labels), column=0, padx=10, pady=10)
        tk.Button(settings_win, text="Cancel", command=settings_win.destroy, font=self.custom_font,
                  bg="#95a5a6", fg="white", relief="flat").grid(row=len(labels), column=1, padx=10, pady=10)
    
    def open_help_window(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("Help & Tutorial")
        help_win.configure(bg="#333333")
        help_win.geometry("800x600")
        try:
            help_win.state("zoomed")
        except Exception:
            pass
        help_win.grab_set()
        help_text = (
            "Welcome to the Exam Clock Application!\n\n"
            "Features:\n"
            "• Displays the current time in a large, central clock.\n"
            "• Shows exam details (date, start time, end time) in the header.\n"
            "• A progress bar indicates exam progress with dynamic color changes.\n"
            "• Subject information is displayed in a table at the bottom (sorted by seat rows if provided).\n"
            "• Settings allow you to adjust fonts, colors, flash settings, etc.\n\n"
            "Demo Mode:\n"
            "Click the 'Toggle Demo Mode' button to simulate an exam session that lasts 2 minutes.\n\n"
            "Edit Layout:\n"
            "Click the 'Toggle Edit Layout' button to enable drag-and-drop repositioning of the main UI panels.\n\n"
            "Double-click any subject row (including on the text) to edit its details directly.\n\n"
            "Hover over icons for additional information. Enjoy!"
        )
        text_widget = tk.Text(help_win, wrap="word", font=self.custom_font, bg="#333333", fg="white")
        text_widget.insert("1.0", help_text)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        button_frame = tk.Frame(help_win, bg="#333333")
        button_frame.pack(fill="x", padx=10, pady=10)
        demo_button = tk.Button(button_frame, text="Toggle Demo Mode", font=self.custom_font,
                                bg="#3498db", fg="white", relief="flat", command=self.toggle_demo_mode)
        demo_button.pack(side="left", padx=10)
        edit_button = tk.Button(button_frame, text="Toggle Edit Layout", font=self.custom_font,
                                bg="#27ae60", fg="white", relief="flat", command=self.toggle_edit_mode)
        edit_button.pack(side="left", padx=10)
        close_button = tk.Button(button_frame, text="Close", font=self.custom_font,
                                 bg="#e74c3c", fg="white", relief="flat", command=help_win.destroy)
        close_button.pack(side="right", padx=10)
    
    def toggle_demo_mode(self):
        if not self.demo_mode:
            self.demo_mode = True
            now = datetime.now()
            self.original_exam_start_time = self.exam_start_time
            self.original_exam_end_time = self.exam_end_time
            self.exam_start_time = now.strftime("%H:%M")
            demo_end = now + timedelta(minutes=2)
            self.exam_end_time = demo_end.strftime("%H:%M")
            new_info = f"Date: {self.exam_date}    |    Exam Start: {self.exam_start_time}    |    Exam End: {self.exam_end_time} (Demo Mode)"
            self.exam_info_label.config(text=new_info)
            messagebox.showinfo("Demo Mode", "Demo Mode Activated: Exam lasts 2 minutes.")
        else:
            self.demo_mode = False
            if self.original_exam_start_time and self.original_exam_end_time:
                self.exam_start_time = self.original_exam_start_time
                self.exam_end_time = self.original_exam_end_time
            new_info = f"Date: {self.exam_date}    |    Exam Start: {self.exam_start_time}    |    Exam End: {self.exam_end_time}"
            self.exam_info_label.config(text=new_info)
            messagebox.showinfo("Demo Mode", "Demo Mode Deactivated.")
    
    def toggle_edit_mode(self):
        if not self.edit_mode:
            self.edit_mode = True
            self.enable_edit_mode()
            messagebox.showinfo("Edit Layout", "Edit mode enabled. Drag the UI elements to reposition them.")
        else:
            self.edit_mode = False
            self.disable_edit_mode()
            messagebox.showinfo("Edit Layout", "Edit mode disabled.")
    
    def enable_edit_mode(self):
        for widget in [self.header_frame, self.clock_frame, self.progress_frame, self.subject_frame]:
            widget.update_idletasks()
            x = widget.winfo_x()
            y = widget.winfo_y()
            widget.pack_forget()
            widget.place(x=x, y=y)
            self.make_draggable(widget)
    
    def disable_edit_mode(self):
        for widget in [self.header_frame, self.clock_frame, self.progress_frame, self.subject_frame]:
            widget.unbind("<ButtonPress-1>")
            widget.unbind("<B1-Motion>")
    
    def make_draggable(self, widget):
        widget.bind("<ButtonPress-1>", self.on_drag_start)
        widget.bind("<B1-Motion>", self.on_drag_motion)
    
    def on_drag_start(self, event):
        widget = event.widget
        widget._drag_start_x = event.x
        widget._drag_start_y = event.y
    
    def on_drag_motion(self, event):
        widget = event.widget
        dx = event.x - widget._drag_start_x
        dy = event.y - widget._drag_start_y
        x = widget.winfo_x() + dx
        y = widget.winfo_y() + dy
        widget.place(x=x, y=y)
    
    def load_pre_config(self):
        if not os.path.exists(PRE_CONFIG_CSV):
            with open(PRE_CONFIG_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "ExamStart", "ExamEnd", "SubjectCode1", "SubjectName1"])
            messagebox.showinfo("Pre-Config Created", f"No pre-config CSV found.\nA new file has been created at:\n{PRE_CONFIG_CSV}\nPlease populate it with data and restart the app.")
            return None
        configs = []
        try:
            with open(PRE_CONFIG_CSV, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    conf = {}
                    conf["exam_date"] = row.get("Date", "")
                    conf["exam_start_time"] = row.get("ExamStart", "")
                    conf["exam_end_time"] = row.get("ExamEnd", "")
                    subjects = []
                    for key in row:
                        if key.startswith("SubjectCode"):
                            index = key[len("SubjectCode"):]
                            code = row[key]
                            name_key = "SubjectName" + index
                            name = row.get(name_key, "")
                            if code and name:
                                subjects.append((code, name))
                    conf["subject_info"] = subjects
                    configs.append(conf)
        except Exception as e:
            messagebox.showerror("CSV Error", f"Error reading CSV file: {e}")
            return None
        if not configs:
            messagebox.showinfo("No Configs", "No configurations found in CSV.")
            return None
        select_win = tk.Toplevel(self.root)
        select_win.title("Select Pre-Config")
        select_win.configure(bg="#333333")
        select_win.geometry("600x400")
        select_win.grab_set()
        tk.Label(select_win, text="Select a Pre-Configuration:", font=self.custom_font, bg="#333333", fg="white").pack(pady=10)
        listbox = tk.Listbox(select_win, font=self.custom_font, width=80)
        listbox.pack(pady=10, padx=10, fill="both", expand=True)
        now = datetime.now()
        best_index = 0
        best_diff = None
        for idx, conf in enumerate(configs):
            try:
                conf_date = datetime.strptime(conf["exam_date"], "%d-%b-%Y")
                conf_time = datetime.strptime(conf["exam_start_time"], "%H:%M").time()
                conf_datetime = datetime.combine(conf_date, conf_time)
                diff = abs((conf_datetime - now).total_seconds())
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_index = idx
            except Exception:
                pass
        for idx, conf in enumerate(configs):
            summary = f"{conf.get('exam_date','')} | Start: {conf.get('exam_start_time','')} | End: {conf.get('exam_end_time','')}"
            listbox.insert(tk.END, summary)
        listbox.select_set(best_index)
        listbox.activate(best_index)
        listbox.see(best_index)
        choice = {"value": None}
        def select_config():
            try:
                index = listbox.curselection()[0]
            except IndexError:
                index = 0
            choice["value"] = configs[index]
            select_win.destroy()
        tk.Button(select_win, text="Load", font=self.custom_font, bg="#2ecc71", fg="white",
                  relief="flat", command=select_config).pack(pady=10)
        self.root.wait_window(select_win)
        return choice["value"]
    
    def prompt_load_configuration(self):
        if os.path.exists(LOG_FILE):
            return messagebox.askyesno("Load Configuration", "Load the last saved configuration?")
        else:
            return False
    
    def load_configuration(self):
        try:
            with open(LOG_FILE, "r") as file:
                config = json.load(file)
            return config
        except (json.JSONDecodeError, FileNotFoundError):
            messagebox.showwarning("Warning", "Could not load configuration. Starting fresh.")
            return {}
    
    def save_configuration(self):
        subject_log = {}
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as file:
                    subject_log = json.load(file).get("subject_log", {})
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        for subject_code, subject_name, _ in self.subject_info:
            if subject_code not in subject_log:
                subject_log[subject_code] = subject_name
        config = {
            "subject_info": self.subject_info,
            "subject_log": subject_log,
            "exam_start_time": self.exam_start_time,
            "exam_end_time": self.exam_end_time
        }
        with open(LOG_FILE, "w") as file:
            json.dump(config, file)
    
    def get_exam_times(self):
        exam_start = self.custom_simpledialog("Exam Time", "Enter the exam start time (HH:MM, 24-hour format):")
        exam_end = self.custom_simpledialog("Exam Time", "Enter the exam end time (HH:MM, 24-hour format):")
        return exam_start, exam_end
    
    def get_subject_info(self):
        subject_info = []
        subject_log = {}
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as file:
                    config = json.load(file)
                    subject_log = config.get("subject_log", {})
            except (json.JSONDecodeError, FileNotFoundError):
                messagebox.showwarning("Warning", "Subject log could not be loaded. Starting fresh.")
        num_subjects = self.custom_simpledialog("Input", "Enter the number of subjects (or leave blank to skip):", is_integer=True)
        if num_subjects is None or num_subjects <= 0:
            return []
        for _ in range(num_subjects):
            if subject_log:
                autocomplete_list = [f"{code} - {subject_log[code]}" for code in subject_log]
                subject_code = self.custom_autocomplete_dialog("Input", "Enter the subject code:", autocomplete_list)
            else:
                subject_code = self.custom_simpledialog("Input", "Enter the subject code:")
            if not subject_code:
                continue
            if subject_code in subject_log:
                subject_name = subject_log[subject_code]
            else:
                subject_name = self.custom_simpledialog("Input", f"Enter the subject name for {subject_code}:")
                subject_log[subject_code] = subject_name
            seat_rows_prompt = f"Enter the seat rows for {subject_code} - {subject_name} (or leave blank):"
            seat_rows = self.custom_simpledialog("Input", seat_rows_prompt)
            subject_info.append((subject_code, subject_name, seat_rows if seat_rows else "No Rows Provided"))
        return subject_info
    
    def custom_autocomplete_dialog(self, title, prompt, autocomplete_list, is_integer=False):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        width, height = 800, 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.configure(bg="#333333")
        dialog.attributes('-topmost', True)
        tk.Label(dialog, text=prompt, font=self.custom_font, bg="#333333", fg="white", wraplength=750).pack(pady=20)
        entry = AutocompleteEntry(dialog, autocomplete_list, font=self.custom_font, width=50)
        entry.pack(pady=20)
        dialog.after(10, lambda: entry.focus_set())
        def on_ok():
            dialog.result = entry.get()
            dialog.destroy()
        tk.Button(dialog, text="OK", command=on_ok, font=self.custom_font,
                  bg="#e74c3c", fg="white", relief="flat", activebackground="#c0392b").pack(pady=10)
        dialog.bind("<Return>", lambda event: on_ok())
        self.root.wait_window(dialog)
        if is_integer:
            try:
                return int(dialog.result)
            except (ValueError, TypeError):
                return None
        else:
            return dialog.result.strip() if dialog.result else None
    
    def custom_simpledialog(self, title, prompt, is_integer=False):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        width, height = 800, 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.configure(bg="#333333")
        dialog.attributes('-topmost', True)
        tk.Label(dialog, text=prompt, font=self.custom_font, bg="#333333", fg="white", wraplength=750).pack(pady=20)
        entry_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=entry_var, font=self.custom_font, width=50)
        entry.pack(pady=20)
        dialog.after(10, lambda: entry.focus_set())
        def on_ok():
            dialog.result = entry_var.get()
            dialog.destroy()
        tk.Button(dialog, text="OK", command=on_ok, font=self.custom_font,
                  bg="#e74c3c", fg="white", relief="flat", activebackground="#c0392b").pack(pady=10)
        dialog.bind("<Return>", lambda event: on_ok())
        self.root.wait_window(dialog)
        if is_integer:
            try:
                return int(dialog.result)
            except (ValueError, TypeError):
                return None
        else:
            return dialog.result.strip() if dialog.result else None
    
    def display_subject_info(self):
        self.sort_subjects_by_rows()
        for widget in self.subject_frame.winfo_children():
            widget.destroy()
        header_frame = tk.Frame(self.subject_frame, bg=self.main_bg_color)
        header_frame.pack(fill="x", pady=(0, 5))
        tk.Label(header_frame, text="Code", font=self.info_font, fg="white", bg=self.main_bg_color)\
            .grid(row=0, column=0, sticky="w", padx=10)
        tk.Label(header_frame, text="Subject", font=self.info_font, fg="white", bg=self.main_bg_color)\
            .grid(row=0, column=1, sticky="ew", padx=10)
        tk.Label(header_frame, text="Rows", font=self.info_font, fg="white", bg=self.main_bg_color)\
            .grid(row=0, column=2, sticky="e", padx=10)
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=2)
        header_frame.columnconfigure(2, weight=1)
        for index, (subject_code, subject_name, seat_rows) in enumerate(self.subject_info):
            row_frame = tk.Frame(self.subject_frame, bg="#333333", bd=1, relief="ridge")
            row_frame.pack(fill="x", padx=10, pady=2)
            # Bind double-click on the row and all its children.
            self.bind_double_click(row_frame, index)
            tk.Label(row_frame, text=subject_code, font=self.info_font, fg="white", bg="#333333")\
                .grid(row=0, column=0, sticky="w", padx=10, pady=5)
            tk.Label(row_frame, text=subject_name, font=self.info_font, fg="white", bg="#333333")\
                .grid(row=0, column=1, sticky="ew", padx=10, pady=5)
            tk.Label(row_frame, text=seat_rows, font=self.info_font, fg="white", bg="#333333")\
                .grid(row=0, column=2, sticky="e", padx=10, pady=5)
            row_frame.columnconfigure(0, weight=1)
            row_frame.columnconfigure(1, weight=2)
            row_frame.columnconfigure(2, weight=1)
    
    def edit_subject_dialog(self, row_index):
        subject = self.subject_info[row_index]
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Subject")
        dialog.configure(bg="#333333")
        dialog.geometry("600x300")
        dialog.attributes('-topmost', True)
        tk.Label(dialog, text="Edit Subject Details", font=self.custom_font, bg="#333333", fg="white").pack(pady=10)
        frame = tk.Frame(dialog, bg="#333333")
        frame.pack(pady=10)
        tk.Label(frame, text="Subject Code:", font=self.custom_font, bg="#333333", fg="white").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        code_var = tk.StringVar(value=subject[0])
        code_entry = tk.Entry(frame, textvariable=code_var, font=self.custom_font, width=25)
        code_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(frame, text="Subject Name:", font=self.custom_font, bg="#333333", fg="white").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        name_var = tk.StringVar(value=subject[1])
        name_entry = tk.Entry(frame, textvariable=name_var, font=self.custom_font, width=25)
        name_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(frame, text="Seat Rows:", font=self.custom_font, bg="#333333", fg="white").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        rows_var = tk.StringVar(value=subject[2])
        rows_entry = tk.Entry(frame, textvariable=rows_var, font=self.custom_font, width=25)
        rows_entry.grid(row=2, column=1, padx=5, pady=5)
        button_frame = tk.Frame(dialog, bg="#333333")
        button_frame.pack(pady=10)
        def save_edit():
            new_code = code_var.get().strip()
            new_name = name_var.get().strip()
            new_rows = rows_var.get().strip()
            if not new_code or not new_name:
                messagebox.showwarning("Invalid Data", "Subject code and name cannot be empty.")
                return
            self.subject_info[row_index] = (new_code, new_name, new_rows if new_rows else "No Rows Provided")
            self.save_configuration()
            self.display_subject_info()
            dialog.destroy()
        tk.Button(button_frame, text="OK", command=save_edit, font=self.custom_font,
                  bg="#e74c3c", fg="white", relief="flat", activebackground="#c0392b").grid(row=0, column=0, padx=10)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, font=self.custom_font,
                  bg="#95a5a6", fg="white", relief="flat").grid(row=0, column=1, padx=10)
        dialog.bind("<Return>", lambda event: save_edit())
    
    def sort_subjects_by_rows(self):
        def key_func(item):
            rows = item[2]
            try:
                first_number = rows.split("-")[0].strip()
                return int(first_number)
            except (ValueError, IndexError):
                return float('inf')
        self.subject_info.sort(key=key_func)
    
    def is_internet_connected(self, host="8.8.8.8", port=53, timeout=3):
        try:
            socket.create_connection((host, port), timeout)
            return True
        except OSError:
            return False
    
    def check_internet_and_time(self):
        if not self.is_internet_connected():
            prompt = ("Internet not connected.\nPlease verify your PC time.\nEnter the correct time (HH:MM:SS) if needed, or leave blank if correct:")
            correct_time_str = self.custom_simpledialog("Time Check", prompt)
            if correct_time_str:
                try:
                    h, m, s = map(int, correct_time_str.split(':'))
                    desired_seconds = h * 3600 + m * 60 + s
                    current_struct = time.localtime()
                    current_seconds = current_struct.tm_hour * 3600 + current_struct.tm_min * 60 + current_struct.tm_sec
                    self.time_offset = desired_seconds - current_seconds
                except Exception:
                    messagebox.showwarning("Invalid Time", "Time entered is invalid. Using system time.")
                    self.time_offset = 0
            else:
                self.time_offset = 0
        else:
            self.time_offset = 0
    
    def update_clock(self):
        adjusted_time = time.localtime(time.time() + self.time_offset)
        current_time_str = time.strftime("%H:%M:%S", adjusted_time)
        self.clock_label.config(text=current_time_str)
        self.update_progress_bar()
        minutes = time.strftime("%M", adjusted_time)
        seconds = time.strftime("%S", adjusted_time)
        if minutes in ["00", "30"] and seconds == "00":
            self.flash_clock()
        self.root.after(1000, self.update_clock)
    
    def update_progress_bar(self):
        try:
            today = datetime.now().date()
            exam_start = datetime.strptime(f"{today} {self.exam_start_time}", "%Y-%m-%d %H:%M")
            exam_end = datetime.strptime(f"{today} {self.exam_end_time}", "%Y-%m-%d %H:%M")
            now = datetime.fromtimestamp(time.time() + self.time_offset)
            if now < exam_start:
                progress = 0
                time_left = (exam_end - exam_start).total_seconds()
            elif now > exam_end:
                progress = 100
                time_left = 0
            else:
                total = (exam_end - exam_start).total_seconds()
                elapsed = (now - exam_start).total_seconds()
                progress = (elapsed / total) * 100
                time_left = (exam_end - now).total_seconds()
            self.progress["value"] = progress
            if time_left <= 10 * 60:
                color = "#e74c3c"
            elif time_left <= 30 * 60:
                color = "#f39c12"
            else:
                color = "#2ecc71"
            self.style.configure("custom.Horizontal.TProgressbar", background=color)
        except Exception as e:
            print("Error updating progress bar:", e)
    
    def flash_clock(self):
        for i in range(self.flash_count):
            self.root.after(self.flash_delay * i, lambda i=i: self.clock_label.config(fg='red' if i % 2 == 0 else self.clock_fg_color))
    
    def exit_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', False)
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    startup_choice = show_startup_menu(root, font=("Helvetica", 20))
    print("Startup choice:", startup_choice)
    root.deiconify()
    app = FullScreenClockApp(root, config_choice=startup_choice)
    root.mainloop()
