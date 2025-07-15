import tkinter as tk
from tkinter import simpledialog, messagebox
import time
import os
import sys
import json

# Set LOG_FILE to be in the same directory as the running script or .exe
if getattr(sys, 'frozen', False):
    # Running as a frozen .exe using PyInstaller
    application_path = os.path.dirname(sys.executable)
else:
    # Running as a standard Python script
    application_path = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(application_path, "subject_log.json")


class FullScreenClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Full Screen Clock with Subject Information")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')

        self.custom_font = ("Helvetica", 20)

        # Load or start new configuration based on user choice
        if self.prompt_load_configuration():
            self.subject_info = self.load_configuration()
        else:
            self.subject_info = self.get_subject_info()
            self.save_configuration()

        self.setup_ui()
        self.update_clock()
        self.root.bind("<Escape>", self.exit_fullscreen)

    def setup_ui(self):
        """Setup the UI layout with clock and subject information frames."""
        # Frame for subject info
        self.info_frame = tk.Frame(self.root, bg='black')
        self.info_frame.pack(pady=20, fill='both', expand=True)

        self.display_subject_info()

        self.clock_frame = tk.Frame(self.root, bg='black')
        self.clock_frame.pack(expand=True)

        self.clock_label = tk.Label(self.clock_frame, fg='#FFFF00', bg='black', font=("Courier", 150, "bold"))
        self.clock_label.pack()

        self.exit_button = tk.Button(self.root, text="Exit", command=self.exit_fullscreen, bg='red', fg='white', font=("Helvetica", 24, "bold"))
        self.exit_button.pack(pady=20, anchor='s')

    def prompt_load_configuration(self):
        """Ask the user if they want to load the last saved configuration or start fresh."""
        if os.path.exists(LOG_FILE):
            answer = messagebox.askyesno("Load Last Configuration", "Do you want to load the last saved configuration?")
            return answer
        else:
            messagebox.showinfo("No Configuration Found", "No previous configuration found. Starting fresh.")
            return False

    def load_configuration(self):
        """Load the configuration from the saved JSON file."""
        try:
            with open(LOG_FILE, 'r') as file:
                config = json.load(file)
            subject_info = config.get("subject_info", [])
            return subject_info
        except (json.JSONDecodeError, FileNotFoundError):
            messagebox.showwarning("Warning", "Subject log file could not be loaded. Starting fresh.")
            return []

    def save_configuration(self):
        """Save the current configuration to the JSON file."""
        # Load existing subject names to avoid overwriting
        subject_log = {}
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r') as file:
                    subject_log = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Update the log with new subject names
        for subject_code, subject_name, _ in self.subject_info:
            if subject_code not in subject_log:
                subject_log[subject_code] = subject_name

        config = {
            "subject_info": self.subject_info,
            "subject_log": subject_log
        }

        with open(LOG_FILE, 'w') as file:
            json.dump(config, file)

    def get_subject_info(self):
        """Prompt user to enter subject information."""
        subject_info = []

        # Load the log file if it exists and handle any error in reading it
        subject_log = {}
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r') as file:
                    config = json.load(file)
                    subject_log = config.get("subject_log", {})
            except (json.JSONDecodeError, FileNotFoundError):
                messagebox.showwarning("Warning", "Subject log file could not be loaded. Starting fresh.")

        num_subjects = self.custom_simpledialog("Input", "Enter the number of subjects (or leave blank to skip):", is_integer=True)

        if num_subjects is None or num_subjects <= 0:
            return []

        for _ in range(num_subjects):
            subject_code = self.custom_simpledialog("Input", "Enter the subject code:")

            # Skip empty subject codes
            if not subject_code:
                continue

            # Retrieve subject name if it already exists in the log
            if subject_code in subject_log:
                subject_name = subject_log[subject_code]
            else:
                subject_name = self.custom_simpledialog("Input", f"Enter the subject name for {subject_code}:")
                subject_log[subject_code] = subject_name

            # Mention the subject code and name in the seat rows prompt
            seat_rows_prompt = f"Enter the seat rows for {subject_code} - {subject_name} (or leave blank):"
            seat_rows = self.custom_simpledialog("Input", seat_rows_prompt)
            subject_info.append((subject_code, subject_name, seat_rows if seat_rows else "No Rows Provided"))

        return subject_info

    def custom_simpledialog(self, title, prompt, is_integer=False):
        """Custom dialog for getting user input with larger size to ensure visibility of the OK button."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("800x300")  # Increased size to ensure better usability
        dialog.configure(bg='white')
        dialog.attributes('-topmost', True)

        tk.Label(dialog, text=prompt, font=self.custom_font, bg='white', wraplength=750).pack(pady=20)

        entry_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=entry_var, font=self.custom_font, width=50)
        entry.pack(pady=20)

        def on_ok():
            dialog.result = entry_var.get()
            dialog.destroy()

        tk.Button(dialog, text="OK", command=on_ok, font=self.custom_font).pack(pady=10)

        # Bind the ENTER key to the on_ok function
        dialog.bind("<Return>", lambda event: on_ok())

        self.root.wait_window(dialog)

        if is_integer:
            try:
                return int(dialog.result)
            except ValueError:
                return None  # Return None for invalid integer input
        else:
            return dialog.result.strip() if dialog.result else None

    def display_subject_info(self):
        """Display subject information with improved readability, all in one line."""
        if not self.subject_info:
            return

        for subject_code, subject_name, seat_rows in self.subject_info:
            # Adjust font size slightly smaller to ensure everything fits in one line
            subject_text = f"{subject_code} - {subject_name} - Rows: {seat_rows}"
            subject_label = tk.Label(self.info_frame, text=subject_text, fg='white', bg='black', font=("Helvetica", 28, "bold"), anchor='w')
            subject_label.pack(padx=10, pady=5, fill='x')

    def update_clock(self):
        """Update the clock every second and trigger flash at 30-minute intervals."""
        now = time.strftime("%H:%M:%S")
        self.clock_label.config(text=now)

        # Check if it's a 30-minute interval (e.g., 11:00:00, 11:30:00)
        minutes = time.strftime("%M")
        seconds = time.strftime("%S")
        if minutes in ["00", "30"] and seconds == "00":
            self.flash_clock()

        self.root.after(1000, self.update_clock)

    def flash_clock(self, flashes=6):
        """Flash the clock label to draw attention."""
        for i in range(flashes):
            self.root.after(500 * i, lambda: self.clock_label.config(fg='red' if i % 2 == 0 else '#FFFF00'))

    def exit_fullscreen(self, event=None):
        """Exit fullscreen and close the application."""
        self.root.attributes('-fullscreen', False)
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = FullScreenClockApp(root)
    root.mainloop()
