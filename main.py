import customtkinter as ctk
from tkinter import messagebox
import csv
import os
import sys
from datetime import datetime, timedelta

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


def resource_path(relative_path):
    """Get the correct path to a bundled file, whether running as a plain
    script or as a PyInstaller-built exe (which extracts data files to a
    temporary folder at runtime)."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# Default task list used the very first time the app runs
DEFAULT_TASKS = [
    "Admin Request",
    "Digital Signage",
    "Documentation",
    "Hardware",
    "Meeting",
    "Network",
    "Non-IT Work",
    "Other",
    "Password/2FA",
    "Programming",
    "Pupil Query",
    "Reimaging",
    "Security",
    "SharePoint Migration",
    "Social Media",
    "Software",
    "Staff Query",
    "Training",
    "Website Update"
    "Windows Update"
]

LOG_FILE = "task_log.csv"
CONFIG_FILE = "tasks_config.txt"
DAILY_LOGS_DIR = "daily_logs"
SCREENSHOTS_DIR = "daily_screenshots"

# Colours cycled through for each task's bar (matches the dark dashboard theme)
COLOR_PALETTE = [
    "#6C63FF", "#1FD1A1", "#75dff3", "#F2A93B",
    "#F2545B", "#B24BF3", "#d32299", "#22D3B5",
]

# Set up global app styling rules
ctk.set_appearance_mode("dark")        # Main background turns deep charcoal/black
ctk.set_default_color_theme("blue")    # Sets primary blue accent highlights


class TaskTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kirsty's Amazing Desktop Task Timer")
        self.root.geometry("480x700")
        self.root.resizable(False, False)

        # Timer variables
        self.running = False
        self.start_time = None
        self.elapsed_time = 0
        self.current_task = None

        # Dashboard state
        self.dashboard_window = None
        self.dashboard_view_mode = "daily"
        self.task_colors = {}

        # Load custom tasks configuration
        self.task_list = self.load_task_config()

        # Initialize CSV log file
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Start Time", "End Time", "Task", "Notes",
                                  "Duration (Seconds)", "Duration (Formatted)"])

        # Folders for end-of-day exports
        os.makedirs(DAILY_LOGS_DIR, exist_ok=True)
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

        # Attempt to load window icon logo
        try:
            icon_path = resource_path("logo.ico")
            self.root.after(200, lambda: self.root.iconbitmap(icon_path))
        except Exception:
            pass

        self.setup_ui()
        self.update_clock()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------------------------------------------------------
    # Config / task list handling
    # ---------------------------------------------------------------
    def load_task_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                tasks = [line.strip() for line in f.readlines() if line.strip()]
                if tasks:
                    return tasks
        self.save_task_config(DEFAULT_TASKS)
        return DEFAULT_TASKS

    def save_task_config(self, tasks):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for task in tasks:
                f.write(f"{task}\n")

    def toggle_always_on_top(self):
        if self.pin_var.get() == 1:
            self.root.attributes("-topmost", True)
        else:
            self.root.attributes("-topmost", False)

    # ---------------------------------------------------------------
    # Main window UI
    # ---------------------------------------------------------------
    def setup_ui(self):
        # 1. Window Controls (Pin always-on-top toggle)
        self.pin_var = ctk.IntVar(value=0)
        pin_check = ctk.CTkCheckBox(
            self.root,
            text="📌 Keep window on top of other apps",
            variable=self.pin_var,
            command=self.toggle_always_on_top,
            text_color="#A0A0A0"
        )
        pin_check.pack(anchor="w", padx=30, pady=(25, 10))

        # 2. Main Visual Card Container
        card_frame = ctk.CTkFrame(self.root, fg_color="#1E1E24", corner_radius=15)
        card_frame.pack(fill="both", expand=True, padx=25, pady=(5, 25))

        # 3. Task Selection & Management Section
        ctk.CTkLabel(card_frame, text="Select or Manage Tasks", font=("Arial", 13, "bold"),
                     text_color="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 5))

        select_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        select_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.task_combobox = ctk.CTkComboBox(select_frame, values=self.task_list,
                                              state="readonly", font=("Arial", 12))
        self.task_combobox.pack(side="left", fill="x", expand=True, padx=(0, 5))
        if self.task_list:
            self.task_combobox.set(self.task_list[0])

        self.delete_btn = ctk.CTkButton(select_frame, text="Delete", fg_color="#ff0000", corner_radius=30,
                                         hover_color="#cc0000", text_color="#FFFFFF", width=70,
                                         command=self.delete_current_task)
        self.delete_btn.pack(side="right")

        # Entry row to add completely new tasks
        add_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        add_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.new_task_entry = ctk.CTkEntry(add_frame, placeholder_text="Type new task category...",
                                            font=("Arial", 12))
        self.new_task_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        add_btn = ctk.CTkButton(add_frame, text="Add Task Type", fg_color="#2D3748",
                                 hover_color="#4A5568", text_color="#E2E8F0",
                                 command=self.add_custom_task)
        add_btn.pack(side="right")

        # 4. Description/Notes Text Box
        ctk.CTkLabel(card_frame, text="Task Description / Notes", font=("Arial", 13, "bold"),
                     text_color="#FFFFFF").pack(anchor="w", padx=20, pady=(5, 5))
        self.notes_entry = ctk.CTkEntry(
            card_frame,
            placeholder_text="Optional session details (e.g., ticket # or specific request)...",
            font=("Arial", 12)
        )
        self.notes_entry.pack(fill="x", padx=20, pady=(0, 20))

        # 5. Glowing Digital Timer Display
        self.time_label = ctk.CTkLabel(card_frame, text="00:00:00", font=("Arial", 48, "bold"),
                                        text_color="#03DAC6")
        self.time_label.pack(pady=(10, 2))

        self.status_label = ctk.CTkLabel(card_frame, text="Status: Ready", font=("Arial", 12, "italic"),
                                          text_color="#32cd32")
        self.status_label.pack(pady=(0, 20))

        # 6. Primary Action Buttons (Start / Stop)
        btn_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ Start Task", fg_color="#32cd32",
                                        hover_color="#28a428", text_color="#FFFFFF", width=140, corner_radius=15,
                                        font=("Arial", 13, "bold"), command=self.start_timer)
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(btn_frame, text="■ Stop Task", fg_color="#555555",
                                       hover_color="#239023", text_color="#AAAAAA", width=140, corner_radius=15,
                                       font=("Arial", 13, "bold"), state="disabled",
                                       command=self.stop_timer)
        self.stop_btn.pack(side="left", padx=10)

        # card_frame2 = ctk.CTkFrame(self.root, fg_color="blue", corner_radius=15)
        # card_frame2.pack(fill="both", expand=True, padx=25, pady=(5, 25))

        # 9. Summary Report Section (Brought back with better formatting)
        ctk.CTkLabel(card_frame, text="Quick Summary Reports", font=("Arial", 13, "bold"),
                     text_color="#FFFFFF").pack(anchor="w", padx=20, pady=(30, 5))

        report_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        report_frame.pack(fill="x", padx=20, pady=(0, 15))

        daily_btn = ctk.CTkButton(report_frame, text="Daily Summary", fg_color="#8282b5",
                                   hover_color="#575793", text_color="#E2E8F0",
                                   command=lambda: self.generate_report("daily"))
        daily_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        weekly_btn = ctk.CTkButton(report_frame, text="Weekly Summary", fg_color="#8282b5",
                                    hover_color="#575793", text_color="#E2E8F0",
                                    command=lambda: self.generate_report("weekly"))
        weekly_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))



        # 8. Dashboard button
        dashboard_btn = ctk.CTkButton(
            card_frame,
            text="Open Dashboard",
            fg_color="#8282b5",
            hover_color="#575793",
            text_color="#E2E8F0",
            command=self.open_dashboard
        )
        dashboard_btn.pack(fill="x", padx=20, pady=(0, 10))

        # 7. Save All Tasks Button (End of Day)
        self.save_all_btn = ctk.CTkButton(
            card_frame,
            text="Save All Tasks (End of Day)",
            fg_color="#32cd32",
            hover_color="#28a428",
            text_color="#FFFFFF",
            font=("Arial", 13, "bold"),
            command=self.end_day
        )
        self.save_all_btn.pack(fill="x", padx=20, pady=(30, 10))

    # ---------------------------------------------------------------
    # Task list management
    # ---------------------------------------------------------------
    def add_custom_task(self):
        new_task = self.new_task_entry.get().strip()
        if not new_task:
            return

        current_values = list(self.task_combobox.cget('values'))
        if new_task in current_values:
            messagebox.showinfo("Info", "This task type already exists.")
            return

        current_values.append(new_task)
        self.task_combobox.configure(values=current_values)
        self.task_combobox.set(new_task)
        self.new_task_entry.delete(0, 'end')
        self.save_task_config(current_values)

    def delete_current_task(self):
        selected_task = self.task_combobox.get()
        if not selected_task:
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to remove '{selected_task}'?"):
            current_values = list(self.task_combobox.cget('values'))
            current_values.remove(selected_task)
            self.task_combobox.configure(values=current_values)
            if current_values:
                self.task_combobox.set(current_values[0])
            else:
                self.task_combobox.set('')
            self.save_task_config(current_values)

    # ---------------------------------------------------------------
    # Timer
    # ---------------------------------------------------------------
    def start_timer(self):
        if not self.running:
            self.current_task = self.task_combobox.get()
            if not self.current_task:
                messagebox.showwarning("Warning", "Please select or add a task first!")
                return

            self.running = True
            self.start_time = datetime.now()
            self.elapsed_time = 0

            self.start_btn.configure(state="disabled", fg_color="#222222")
            self.stop_btn.configure(state="normal", fg_color="#B00020",
                                     hover_color="#CF6679", text_color="#FFFFFF")
            self.delete_btn.configure(state="disabled")
            self.task_combobox.configure(state="disabled")
            self.notes_entry.configure(state="disabled")
            self.status_label.configure(text=f"Tracking: {self.current_task}", text_color="#03DAC6")

    def stop_timer(self):
        if self.running:
            self.running = False
            end_time = datetime.now()

            duration_secs = int(self.elapsed_time)
            hours, remainder = divmod(duration_secs, 3600)
            mins, secs = divmod(remainder, 60)
            formatted_duration = f"{hours:02d}:{mins:02d}:{secs:02d}"

            task_notes = self.notes_entry.get().strip()
            if not task_notes:
                task_notes = "No description provided"

            # UK date format: DD-MM-YYYY
            date_str = self.start_time.strftime("%d-%m-%Y")

            with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    date_str,
                    self.start_time.strftime("%H:%M:%S"),
                    end_time.strftime("%H:%M:%S"),
                    self.current_task,
                    task_notes,
                    duration_secs,
                    formatted_duration
                ])

            # Show duration in hours and minutes for the success message
            if hours > 0:
                time_msg = f"{hours}h {mins}m {secs}s"
            elif mins > 0:
                time_msg = f"{mins}m {secs}s"
            else:
                time_msg = f"{secs}s"

            messagebox.showinfo("Success", f"Logged {time_msg} to {self.current_task}")


            self.start_btn.configure(state="normal", fg_color="#32cd32")
            self.stop_btn.configure(state="disabled", fg_color="#555555", text_color="#AAAAAA")
            self.delete_btn.configure(state="normal")
            self.task_combobox.configure(state="readonly")
            self.notes_entry.configure(state="normal")
            self.notes_entry.delete(0, 'end')
            self.status_label.configure(text="Status: Ready", text_color="#A0A0A0")
            self.time_label.configure(text="00:00:00")
            self.elapsed_time = 0

            # Keep an open dashboard in sync with the entry that was just logged
            if self.dashboard_window is not None and self.dashboard_window.winfo_exists():
                self.render_dashboard()

    def update_clock(self):
        if self.running:
            self.elapsed_time = (datetime.now() - self.start_time).total_seconds()
            hours, remainder = divmod(int(self.elapsed_time), 3600)
            mins, secs = divmod(remainder, 60)
            self.time_label.configure(text=f"{hours:02d}:{mins:02d}:{secs:02d}")
        self.root.after(1000, self.update_clock)

    # ---------------------------------------------------------------
    # Log reading helpers (with UK date format)
    # ---------------------------------------------------------------
    def read_log_rows(self):
        """Returns every row in the master log as a list of dicts."""
        if not os.path.exists(LOG_FILE):
            return []
        with open(LOG_FILE, mode='r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def get_daily_task_totals(self, target_date):
        """{task_name: seconds} for a single date, in first-seen order."""
        totals = {}
        for row in self.read_log_rows():
            try:
                row_date = datetime.strptime(row["Date"], "%d-%m-%Y").date()
            except (ValueError, KeyError):
                continue
            if row_date == target_date:
                totals[row["Task"]] = totals.get(row["Task"], 0) + int(row["Duration (Seconds)"])
        return totals  # Return seconds, not hours

    def get_weekly_day_totals(self):
        """[(label, seconds), ...] for the current Sunday-to-Saturday week."""
        today = datetime.now().date()
        # Monday=0 ... Sunday=6 -> days since the most recent Sunday
        days_since_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_since_sunday)
        day_secs = {week_start + timedelta(days=i): 0 for i in range(7)}
        for row in self.read_log_rows():
            try:
                row_date = datetime.strptime(row["Date"], "%d-%m-%Y").date()
            except (ValueError, KeyError):
                continue
            if row_date in day_secs:
                day_secs[row_date] += int(row["Duration (Seconds)"])
        return [(d.strftime("%a %d"), secs) for d, secs in day_secs.items()]

    def color_for_task(self, task_name):
        if task_name not in self.task_colors:
            self.task_colors[task_name] = COLOR_PALETTE[len(self.task_colors) % len(COLOR_PALETTE)]
        return self.task_colors[task_name]

    def format_time(self, seconds):
        """Format seconds into a readable string with hours, minutes, seconds."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    # ---------------------------------------------------------------
    # Dashboard window
    # ---------------------------------------------------------------
    def open_dashboard(self):
        if self.dashboard_window is not None and self.dashboard_window.winfo_exists():
            self.dashboard_window.lift()
            self.dashboard_window.focus()
            return

        win = ctk.CTkToplevel(self.root)
        win.attributes("-alpha", 0)  # hide while we build/style it, avoids white flash
        win.title("Task Dashboard")
        win.geometry("640x500")
        win.resizable(True, True)
        win.configure(fg_color="#15151A")
        if self.pin_var.get() == 1:
            win.attributes("-topmost", True)
        self.dashboard_window = win


        outer = ctk.CTkFrame(win, fg_color="#15151A", corner_radius=15)
        outer.pack(fill="both", expand=True, padx=15, pady=15)

        self.dashboard_title_label = ctk.CTkLabel(outer, text="Today's Logged Tasks",
                                                    font=("Arial", 15, "bold"), text_color="#FFFFFF")
        self.dashboard_title_label.pack(anchor="w", padx=15, pady=(15, 10))

        self.chart_canvas = ctk.CTkCanvas(outer, width=590, height=260, bg="#1E1E24",
                                           highlightthickness=0)
        self.chart_canvas.pack(padx=15, pady=(0, 15))

        # Stats row
        stats_frame = ctk.CTkFrame(outer, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.stat_logged_label = self._build_stat(stats_frame, "Logged today")
        self.stat_top_task_label = self._build_stat(stats_frame, "Top task")
        self.stat_weekly_label = self._build_stat(stats_frame, "Weekly total")

        # Daily / Weekly toggle
        self.view_toggle = ctk.CTkSegmentedButton(
            outer, values=["Daily Details", "Weekly Trend"], corner_radius=25, selected_color="#32cd32", selected_hover_color="#28a428",
            font=("Arial", 13, "bold"),
            command=self.switch_dashboard_view
        )
        self.view_toggle.set("Daily Details")
        self.view_toggle.pack(fill="x", padx=15, pady=(0, 15))

        self.render_dashboard()

        win.update_idletasks()
        win.attributes("-alpha", 1)  # now reveal the fully-styled window

    def _build_stat(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", expand=True, fill="x")
        ctk.CTkLabel(frame, text=title, font=("Arial", 11), text_color="#A0A0A0").pack()
        value_label = ctk.CTkLabel(frame, text="--", font=("Arial", 14, "bold"), text_color="#FFFFFF")
        value_label.pack()
        return value_label

    def switch_dashboard_view(self, selected_value):
        self.dashboard_view_mode = "daily" if selected_value == "Daily Details" else "weekly"
        self.render_dashboard()

    def render_dashboard(self):
        if self.dashboard_window is None or not self.dashboard_window.winfo_exists():
            return

        today = datetime.now().date()
        daily_totals = self.get_daily_task_totals(today)
        weekly_days = self.get_weekly_day_totals()

        if self.dashboard_view_mode == "daily":
            self.dashboard_title_label.configure(text="Today's Logged Tasks")
            bars = [(task, secs, self.color_for_task(task)) for task, secs in daily_totals.items()]
        else:
            self.dashboard_title_label.configure(text="This Week (Sun–Sat)")
            # Use different colours for each day in weekly view
            bars = [(label, secs, COLOR_PALETTE[i % len(COLOR_PALETTE)]) for i, (label, secs) in enumerate(weekly_days)]

        self.draw_bar_chart(bars)

        logged_today_secs = sum(daily_totals.values())
        top_task = max(daily_totals, key=daily_totals.get) if daily_totals else "--"
        weekly_total_secs = sum(secs for _, secs in weekly_days)

        self.stat_logged_label.configure(text=self.format_time(logged_today_secs))
        self.stat_top_task_label.configure(text=top_task)
        self.stat_weekly_label.configure(text=self.format_time(weekly_total_secs))

    def draw_bar_chart(self, bars):
        canvas = self.chart_canvas
        canvas.delete("all")

        left_label_width = 150
        right_margin = 80
        chart_width = 590 - left_label_width - right_margin
        row_height = 32
        top_margin = 10

        if not bars:
            canvas.create_text(295, 130, text="No data logged for this period yet",
                                fill="#A0A0A0", font=("Arial", 12))
            return

        max_seconds = max(secs for _, secs, _ in bars) or 1

        for i, (label, seconds, color) in enumerate(bars):
            y = top_margin + i * row_height
            bar_len = (seconds / max_seconds) * chart_width if max_seconds else 0

            canvas.create_text(left_label_width - 10, y + row_height / 2, text=label,
                                fill="#6C7AF2", font=("Arial", 11, "bold"), anchor="e")
            canvas.create_rectangle(left_label_width, y + 5, left_label_width + bar_len, y + row_height - 5,
                                     fill=color, outline="")
            canvas.create_text(left_label_width + bar_len + 10, y + row_height / 2,
                                text=self.format_time(seconds), fill="#FFFFFF", font=("Arial", 11), anchor="w")

        # Bottom axis ticks
        # axis_y = top_margin + len(bars) * row_height + 10
        # tick_count = 5
        # for t in range(tick_count + 1):
        #     tick_seconds = (max_seconds / tick_count) * t
        #     x = left_label_width + (chart_width / tick_count) * t
        #     canvas.create_text(x, axis_y, text=self.format_time(tick_seconds), fill="#6B7280", font=("Arial", 9))

    # ---------------------------------------------------------------
    # End of day: dated CSV export + dashboard screenshot
    # ---------------------------------------------------------------
    def end_day(self):
        date_str = datetime.now().strftime("%d-%m-%Y")
        saved_paths = []

        # 1. Export today's rows to a dated CSV so it never overwrites another day
        todays_rows = [row for row in self.read_log_rows()
                       if row.get("Date") == date_str]
        dated_log_path = os.path.join(DAILY_LOGS_DIR, f"task_log_{date_str}.csv")
        with open(dated_log_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Start Time", "End Time", "Task", "Notes",
                              "Duration (Seconds)", "Duration (Formatted)"])
            for row in todays_rows:
                writer.writerow([row.get("Date", ""), row.get("Start Time", ""), row.get("End Time", ""),
                                  row.get("Task", ""), row.get("Notes", ""),
                                  row.get("Duration (Seconds)", ""), row.get("Duration (Formatted)", "")])
        saved_paths.append(dated_log_path)

        # 2. Screenshot the dashboard window if it's open
        if self.dashboard_window is not None and self.dashboard_window.winfo_exists():
            if ImageGrab is None:
                messagebox.showwarning(
                    "Screenshot unavailable",
                    "The log was saved, but taking a screenshot needs the Pillow library.\n"
                    "Install it with: pip install pillow"
                )
            else:
                self.dashboard_window.update()
                x = self.dashboard_window.winfo_rootx()
                y = self.dashboard_window.winfo_rooty()
                w = self.dashboard_window.winfo_width()
                h = self.dashboard_window.winfo_height()
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"daily_summary_{date_str}.png")
                try:
                    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(screenshot_path)
                    saved_paths.append(screenshot_path)
                except Exception as exc:
                    messagebox.showwarning("Screenshot failed",
                                            f"The log was saved, but the screenshot could not be taken:\n{exc}")

        messagebox.showinfo("Day closed", "Saved:\n" + "\n".join(saved_paths))

    def on_closing(self):
        """Runs the same save as the End of Day button, so nothing is lost
        if the app is closed without pressing it."""
        self.end_day()
        self.root.destroy()

    # ---------------------------------------------------------------
    # Summary Reports (Brought back with better formatting)
    # ---------------------------------------------------------------
    def generate_report(self, report_type):
        if not os.path.exists(LOG_FILE):
            messagebox.showerror("Error", "No log file found. Start tracking tasks first!")
            return

        today = datetime.now().date()
        days_since_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_since_sunday)
        target_date = today if report_type == "daily" else week_start
        summary = {}

        with open(LOG_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_date = datetime.strptime(row["Date"], "%d-%m-%Y").date()
                    if report_type == "daily" and row_date == today:
                        summary[row["Task"]] = summary.get(row["Task"], 0) + int(row["Duration (Seconds)"])
                    elif report_type == "weekly" and row_date >= target_date:
                        summary[row["Task"]] = summary.get(row["Task"], 0) + int(row["Duration (Seconds)"])
                except (ValueError, KeyError):
                    continue

        if not summary:
            messagebox.showinfo("Report", f"No data found for this {'day' if report_type == 'daily' else 'week'}.")
            return

        # Build the report text with better formatting
        report_text = f"{'📅 DAILY' if report_type == 'daily' else '📊 WEEKLY'} SUMMARY\n"
        report_text += f"{'=' * 35}\n"
        if report_type == "daily":
            date_range_text = today.strftime('%d-%m-%Y')
        else:
            date_range_text = f"{week_start.strftime('%d-%m-%Y')} to {today.strftime('%d-%m-%Y')}"
        report_text += f"Date: {date_range_text}\n\n"

        total_all_tasks = 0
        # Sort tasks by duration (descending)
        sorted_tasks = sorted(summary.items(), key=lambda x: x[1], reverse=True)

        for task, secs in sorted_tasks:
            total_all_tasks += secs
            report_text += f"  • {task}: {self.format_time(secs)}\n"

        report_text += f"\n{'─' * 35}\n"
        report_text += f"TOTAL TIME: {self.format_time(total_all_tasks)}\n"

        if sorted_tasks and total_all_tasks > 0:
            top_task, top_time = sorted_tasks[0]
            percentage = (top_time / total_all_tasks) * 100
            report_text += f"TOP TASK: {top_task} ({percentage:.1f}%)"

               # Create a nice popup window
        report_window = ctk.CTkToplevel(self.root)

        # 🟢 PREVENT MIGRAINE FLASH: Force the OS to map the frame canvas as Dark
        # BEFORE displaying a single pixel to your monitor.
        report_window.withdraw()
        report_window.configure(fg_color="#15151A")

        report_window.title(f"{report_type.capitalize()} Report")
        report_window.geometry("420x450")
        report_window.resizable(False, False)

        # 🟢 THE HEADER ICON OVERRIDE:
        # Bypasses CustomTkinter's default blue square icon by using the window manager handle.
        try:
            icon_path = resource_path("logo.ico")
            report_window.wm_iconbitmap(icon_path)
        except Exception:
            pass

        if self.pin_var.get() == 1:
            report_window.attributes("-topmost", True)

        # Main container with dark theme
        container = ctk.CTkFrame(report_window, fg_color="#15151A", corner_radius=15)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        title_label = ctk.CTkLabel(
            container,
            text=f"{'📅 Daily' if report_type == 'daily' else '📊 Weekly'} Report",
            font=("Arial", 16, "bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(pady=(15, 5))

        date_label = ctk.CTkLabel(
            container,
            text=date_range_text,
            font=("Arial", 12),
            text_color="#A0A0A0"
        )
        date_label.pack(pady=(0, 15))

        # Text output box
        txt = ctk.CTkTextbox(
            container,
            font=("Arial", 13),
            fg_color="#1E1E24",
            text_color="#E2E8F0",
            corner_radius=10
        )
        txt.insert("0.0", report_text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # The window was withdrawn earlier to avoid a white flash while it was
        # being styled — bring it back now that it's fully built.
        report_window.deiconify()

if __name__ == "__main__":
    root = ctk.CTk()
    app = TaskTimerApp(root)
    root.mainloop()