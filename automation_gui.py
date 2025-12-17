import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import datetime
import json
import os
import pickle
import pytz
import tzlocal
import re
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Load environment variables from .env file
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
load_dotenv()

from youtube_metadata import (
    authenticate_account, list_available_accounts, get_account_info,
    get_account_token_file, TOKEN_PICKLE_FILE, get_authenticated_service,
    get_account_id_from_service, load_processed_videos_data,
    save_processed_videos_data, get_my_unscheduled_private_video_ids,
    get_video_transcript, is_transcript_duplicate, save_video_data,
    generate_metadata_with_gemini, update_and_schedule_video,
    view_processed_data_summary, cleanup_old_data, QuotaExceededError,
    get_account_promotion_config, save_promotion_config
)
from promotion_logic import PromotionEngine


class YouTubeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Shorts Automation Suite")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # Configure style
        style = ttk.Style()
        style.theme_use("clam")
        
        self.youtube_service = None
        self.selected_account = None
        self.channel_id = None
        self.processing = False
        
        self.create_main_menu()
        
    def create_main_menu(self):
        """Create the main menu interface."""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.root.title("YouTube Shorts Automation Suite - Main Menu")
        
        # Title frame
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="🎬 YouTube Shorts Automation Suite",
            font=("Arial", 18, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Schedule, manage, and automate your YouTube Shorts",
            font=("Arial", 10),
            foreground="gray"
        )
        subtitle_label.pack()
        
        # Main content frame
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Buttons frame
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Button styling
        button_style = {
            "width": 40,
            "padding": 15
        }
        
        btn_run = ttk.Button(
            button_frame,
            text="▶ Run Automation (Schedule Videos)",
            command=self.open_automation_dialog
        )
        btn_run.pack(pady=10, fill=tk.X)
        
        btn_add = ttk.Button(
            button_frame,
            text="➕ Add New Account",
            command=self.open_add_account_dialog
        )
        btn_add.pack(pady=10, fill=tk.X)
        
        btn_manage = ttk.Button(
            button_frame,
            text="⚙️  Manage Accounts",
            command=self.open_manage_accounts_dialog
        )
        btn_manage.pack(pady=10, fill=tk.X)

        btn_promote = ttk.Button(
            button_frame,
            text="📢 Promote Videos",
            command=self.open_promotion_dialog
        )
        btn_promote.pack(pady=10, fill=tk.X)
        
        btn_exit = ttk.Button(
            button_frame,
            text="❌ Exit",
            command=self.root.quit
        )
        btn_exit.pack(pady=10, fill=tk.X)
        
        # Info frame at bottom
        info_frame = ttk.LabelFrame(content_frame, text="Information", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        info_text = """
        📋 Features:
        • Fetch unscheduled private (draft) videos
        • Generate AI-powered metadata with Gemini
        • Schedule videos with custom time slots
        • Duplicate content detection
        • Multi-account support
        • Track processed videos
        
        ⚠️  Requirements:
        • client_secret.json (Google OAuth credentials)
        • GEMINI_API_KEY environment variable
        • Internet connection
        """
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(fill=tk.BOTH, expand=True)
    
    def open_automation_dialog(self):
        """Open the automation scheduling dialog."""
        # Select account first
        if not self.select_account():
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Schedule Videos")
        dialog.geometry("800x750")
        
        # Create notebook for steps
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Step 1: Review videos
        frame1 = ttk.Frame(notebook)
        notebook.add(frame1, text="Step 1: Review Videos")
        self.create_review_videos_tab(frame1, dialog)
        
        # Step 2: Scheduling settings
        frame2 = ttk.Frame(notebook)
        notebook.add(frame2, text="Step 2: Schedule Settings")
        self.create_schedule_settings_tab(frame2, dialog)
        
        # Step 3: Progress
        frame3 = ttk.Frame(notebook)
        notebook.add(frame3, text="Step 3: Processing")
        self.create_progress_tab(frame3, dialog)
    
    def create_review_videos_tab(self, parent, dialog):
        """Create tab to review videos."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instr_label = ttk.Label(
            main_frame,
            text="Fetching your unscheduled private videos...",
            font=("Arial", 10)
        )
        instr_label.pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(main_frame, mode='indeterminate')
        progress.pack(fill=tk.X, pady=10)
        progress.start()
        
        # Frame for video list (will be populated)
        list_frame = ttk.LabelFrame(main_frame, text="Unscheduled Private Videos", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Text widget with scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        video_text = tk.Text(list_frame, height=15, yscrollcommand=scrollbar.set)
        video_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=video_text.yview)
        
        # Fetch videos in background
        def fetch_videos():
            try:
                videos = get_my_unscheduled_private_video_ids(self.youtube_service)
                progress.stop()
                
                if videos:
                    video_text.config(state=tk.NORMAL)
                    video_text.delete(1.0, tk.END)
                    video_text.insert(tk.END, f"Found {len(videos)} unscheduled private videos:\n\n")
                    for vid_id in videos:
                        video_text.insert(tk.END, f"• {vid_id}\n")
                    video_text.config(state=tk.DISABLED)
                    
                    instr_label.config(
                        text=f"✓ Ready to schedule {len(videos)} videos. Proceed to Step 2."
                    )
                    # Store videos for next step
                    dialog.videos_to_schedule = videos
                else:
                    video_text.config(state=tk.NORMAL)
                    video_text.delete(1.0, tk.END)
                    video_text.insert(tk.END, "No unscheduled private videos found.")
                    video_text.config(state=tk.DISABLED)
                    instr_label.config(text="✗ No videos to schedule.")
                    messagebox.showinfo("No Videos", "No unscheduled private videos found.")
            except Exception as e:
                progress.stop()
                messagebox.showerror("Error", f"Failed to fetch videos: {e}")
                instr_label.config(text=f"✗ Error: {e}")
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=fetch_videos, daemon=True)
        thread.start()
    
    def create_schedule_settings_tab(self, parent, dialog):
        """Create tab for scheduling settings."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Start date section
        date_frame = ttk.LabelFrame(main_frame, text="Start Date", padding=10)
        date_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(date_frame, text="Select date to start scheduling (DD-MM-YYYY):").pack(anchor=tk.W)
        date_entry = ttk.Entry(date_frame, width=20)
        today = datetime.date.today()
        date_entry.insert(0, today.strftime("%d-%m-%Y"))
        date_entry.pack(anchor=tk.W, pady=5)
        
        def get_date():
            try:
                return datetime.datetime.strptime(date_entry.get(), "%d-%m-%Y").date()
            except ValueError:
                messagebox.showerror("Invalid Date", "Please enter date in DD-MM-YYYY format.")
                return None
        
        # Videos per day section
        vpd_frame = ttk.LabelFrame(main_frame, text="Videos Per Day", padding=10)
        vpd_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(vpd_frame, text="How many videos to schedule per day?").pack(anchor=tk.W)
        vpd_var = tk.IntVar(value=1)
        vpd_spinbox = ttk.Spinbox(vpd_frame, from_=1, to=10, textvariable=vpd_var, width=5)
        vpd_spinbox.pack(anchor=tk.W, pady=5)
        
        # Time slots section
        time_frame = ttk.LabelFrame(main_frame, text="Daily Time Slots", padding=10)
        time_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(time_frame, text="Set time for each video (in order):").pack(anchor=tk.W)
        
        time_entries = []
        
        def update_time_slots(*args):
            # Clear previous entries
            for widget in time_frame.winfo_children()[1:]:
                if isinstance(widget, ttk.Frame):
                    widget.destroy()
            time_entries.clear()
            
            vpd = vpd_var.get()
            for i in range(vpd):
                slot_frame = ttk.Frame(time_frame)
                slot_frame.pack(fill=tk.X, pady=5)
                
                ttk.Label(slot_frame, text=f"Time for video {i+1}:").pack(side=tk.LEFT, padx=5)
                
                time_entry = ttk.Entry(slot_frame, width=10)
                time_entry.insert(0, f"{9+i*2:02d}:00")
                time_entry.pack(side=tk.LEFT, padx=5)
                time_entries.append(time_entry)
                
                ttk.Label(slot_frame, text="(HH:MM format)", foreground="gray").pack(side=tk.LEFT)
            
            dialog.time_entries = time_entries
        
        # Use trace_add for Python 3.13+ compatibility
        try:
            vpd_var.trace_add("write", update_time_slots)
        except AttributeError:
            # Fallback for older Python versions
            vpd_var.trace("w", update_time_slots)
        update_time_slots()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        def proceed_to_processing():
            try:
                if not hasattr(dialog, 'videos_to_schedule') or not dialog.videos_to_schedule:
                    messagebox.showwarning("No Videos", "Please go back and fetch videos first.")
                    return
                
                # Validate inputs
                start_date = get_date()
                if not start_date:
                    return
                    
                vpd = vpd_var.get()
                
                times = []
                for entry in time_entries:
                    time_str = entry.get()
                    time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
                    times.append(time_obj)
                
                # Store settings in dialog
                dialog.schedule_settings = {
                    'start_date': start_date,
                    'videos_per_day': vpd,
                    'time_slots': times
                }
                
                # Move to Step 3
                notebook = dialog.nametowidget(dialog.winfo_parent())
                # Find parent notebook
                for widget in dialog.winfo_children():
                    if isinstance(widget, ttk.Notebook):
                        widget.select(2)  # Go to step 3
                        break
                
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Please enter valid times in HH:MM format: {e}")
        
        ttk.Button(button_frame, text="Proceed to Processing", command=proceed_to_processing).pack(side=tk.RIGHT, padx=5)
    
    def create_progress_tab(self, parent, dialog):
        """Create tab to show processing progress."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready to start processing", font=("Arial", 10))
        status_label.pack(pady=10)
        
        # Progress bar
        progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        progress_bar.pack(fill=tk.X, pady=10)
        
        # Output text
        output_frame = ttk.LabelFrame(main_frame, text="Processing Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        output_text = tk.Text(output_frame, height=20, yscrollcommand=scrollbar.set)
        output_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=output_text.yview)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def start_processing():
            if not hasattr(dialog, 'schedule_settings'):
                messagebox.showwarning("Missing Settings", "Please complete Step 2 first.")
                return
            
            # Disable button during processing
            start_btn.config(state=tk.DISABLED)
            output_text.config(state=tk.NORMAL)
            output_text.delete(1.0, tk.END)
            
            def run_automation():
                try:
                    output_text.insert(tk.END, "Starting automation...\n\n")
                    output_text.see(tk.END)
                    self.root.update_idletasks()
                    
                    videos = dialog.videos_to_schedule
                    settings = dialog.schedule_settings
                    
                    # Get system timezone
                    local_tz_name = tzlocal.get_localzone_name()
                    system_tz = pytz.timezone(local_tz_name) if local_tz_name else pytz.utc
                    
                    # Initialize processing
                    current_date = settings['start_date']
                    current_time_idx = 0
                    time_slots = settings['time_slots']
                    vpd = settings['videos_per_day']
                    
                    total_videos = len(videos)
                    scheduled_count = 0
                    
                    for idx, video_id in enumerate(videos):
                        if self.processing == False:
                            output_text.insert(tk.END, "\n❌ Processing cancelled by user.\n")
                            break
                        
                        progress = ((idx + 1) / total_videos) * 100
                        progress_bar['value'] = progress
                        status_label.config(text=f"Processing video {idx+1}/{total_videos}")
                        self.root.update_idletasks()
                        
                        output_text.insert(tk.END, f"\n[{idx+1}/{total_videos}] Processing {video_id}...\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        # Find next valid slot
                        slot_count = 0
                        publish_dt = None
                        iter_date = current_date
                        iter_time_idx = current_time_idx
                        
                        while publish_dt is None and slot_count < (len(time_slots) * 365 * 2):
                            slot_count += 1
                            candidate_dt_naive = datetime.datetime.combine(
                                iter_date,
                                time_slots[iter_time_idx]
                            )
                            candidate_dt = system_tz.localize(candidate_dt_naive)
                            min_valid_dt = datetime.datetime.now(system_tz) + datetime.timedelta(minutes=30)
                            
                            if candidate_dt >= min_valid_dt:
                                publish_dt = candidate_dt
                            else:
                                iter_time_idx += 1
                                if iter_time_idx >= len(time_slots):
                                    iter_time_idx = 0
                                    iter_date += datetime.timedelta(days=1)
                        
                        if not publish_dt:
                            output_text.insert(tk.END, "  ✗ Could not find valid slot. Skipping.\n")
                            output_text.see(tk.END)
                            self.root.update_idletasks()
                            continue
                        
                        output_text.insert(tk.END, f"  ⏰ Scheduled for: {publish_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        # Get transcript
                        output_text.insert(tk.END, "  📝 Fetching transcript...\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        transcript = get_video_transcript(self.youtube_service, video_id)
                        if not transcript:
                            output_text.insert(tk.END, "  ✗ No transcript found. Skipping.\n")
                            output_text.see(tk.END)
                            self.root.update_idletasks()
                            continue
                        
                        # Check for duplicates
                        if is_transcript_duplicate(self.channel_id, transcript):
                            output_text.insert(tk.END, "  ✗ Duplicate content detected. Skipping.\n")
                            output_text.see(tk.END)
                            self.root.update_idletasks()
                            continue
                        
                        # Generate metadata
                        output_text.insert(tk.END, "  🤖 Generating metadata with Gemini...\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        metadata = generate_metadata_with_gemini(transcript)
                        if not metadata or "Placeholder" in metadata.get("title", "") or "Fallback" in metadata.get("title", ""):
                            output_text.insert(tk.END, "  ✗ Metadata generation failed. Skipping.\n")
                            output_text.see(tk.END)
                            self.root.update_idletasks()
                            continue
                        
                        output_text.insert(tk.END, f"  📌 Title: {metadata['title'][:60]}...\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        # Schedule video
                        output_text.insert(tk.END, "  📤 Scheduling video...\n")
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        if update_and_schedule_video(self.youtube_service, video_id, metadata, publish_dt):
                            scheduled_count += 1
                            output_text.insert(tk.END, "  ✓ Video scheduled successfully!\n")
                            save_video_data(self.channel_id, video_id, transcript, metadata, publish_dt)
                        else:
                            output_text.insert(tk.END, "  ✗ Failed to schedule video.\n")
                            save_video_data(self.channel_id, video_id, transcript, metadata, None)
                        
                        output_text.see(tk.END)
                        self.root.update_idletasks()
                        
                        # Advance schedule
                        current_time_idx += 1
                        if current_time_idx >= len(time_slots):
                            current_time_idx = 0
                            current_date += datetime.timedelta(days=1)
                    
                    progress_bar['value'] = 100
                    output_text.insert(tk.END, f"\n\n✅ Processing complete!\n")
                    output_text.insert(tk.END, f"Successfully scheduled: {scheduled_count}/{total_videos} videos\n")
                    status_label.config(text=f"Complete: {scheduled_count}/{total_videos} videos scheduled")
                    
                except QuotaExceededError as e:
                    output_text.insert(tk.END, f"\n\n❌ YouTube API Quota Exceeded: {e}\n")
                    status_label.config(text="Error: Quota exceeded")
                except Exception as e:
                    output_text.insert(tk.END, f"\n\n❌ Error: {e}\n")
                    status_label.config(text=f"Error: {e}")
                finally:
                    start_btn.config(state=tk.NORMAL)
                    self.processing = False
                    output_text.config(state=tk.DISABLED)
            
            self.processing = True
            thread = threading.Thread(target=run_automation, daemon=True)
            thread.start()
        
        start_btn = ttk.Button(button_frame, text="Start Processing", command=start_processing)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def open_add_account_dialog(self):
        """Open dialog to add a new account."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Account")
        dialog.geometry("500x300")
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Enter Account Name", font=("Arial", 12, "bold")).pack(pady=10)
        
        name_entry = ttk.Entry(main_frame, width=30)
        name_entry.pack(pady=10)
        
        info_text = """Account name must contain only:
        • Letters (a-z, A-Z)
        • Numbers (0-9)
        • Hyphens (-) and underscores (_)
        
        Example: personal, business, channel_1"""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT, foreground="gray")
        info_label.pack(pady=20, anchor=tk.W)
        
        status_label = ttk.Label(main_frame, text="", foreground="blue")
        status_label.pack(pady=10)
        
        def add_account():
            account_name = name_entry.get().strip()
            
            if not account_name:
                messagebox.showerror("Invalid Input", "Account name cannot be empty.")
                return
            
            if account_name in list_available_accounts():
                messagebox.showerror("Duplicate", f"Account '{account_name}' already exists.")
                return
            
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
                messagebox.showerror("Invalid Name", "Account name can only contain letters, numbers, hyphens, and underscores.")
                return
            
            status_label.config(text="Opening browser for authentication...")
            dialog.update_idletasks()
            
            try:
                creds = authenticate_account(account_name)
                if creds:
                    channel_id, channel_title = get_account_info(creds)
                    if channel_title:
                        messagebox.showinfo(
                            "Success",
                            f"✓ Account added successfully!\n\nAccount: {account_name}\nChannel: {channel_title}\nID: {channel_id}"
                        )
                        dialog.destroy()
                    else:
                        messagebox.showwarning(
                            "Partial Success",
                            f"Account added but unable to verify channel information.\nSaved to: {get_account_token_file(account_name)}"
                        )
                        dialog.destroy()
                else:
                    messagebox.showerror("Failed", "Failed to authenticate. Please try again.")
                    status_label.config(text="")
            except Exception as e:
                messagebox.showerror("Error", f"Error adding account: {e}")
                status_label.config(text="")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="Add Account", command=add_account).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def open_manage_accounts_dialog(self):
        """Open dialog to manage accounts."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Accounts")
        dialog.geometry("700x600")
        
        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Manage Your Accounts", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tab 1: View Accounts
        frame1 = ttk.Frame(notebook)
        notebook.add(frame1, text="View Accounts")
        self.create_view_accounts_tab(frame1, dialog)
        
        # Tab 2: Account Operations
        frame2 = ttk.Frame(notebook)
        notebook.add(frame2, text="Account Operations")
        self.create_account_operations_tab(frame2, dialog)
        
        # Tab 3: Data Management
        frame3 = ttk.Frame(notebook)
        notebook.add(frame3, text="Data Management")
        self.create_data_management_tab(frame3, dialog)
    
    def create_view_accounts_tab(self, parent, dialog):
        """Create tab to view all accounts."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Available Accounts", font=("Arial", 11, "bold")).pack(pady=10)
        
        # Accounts list frame
        list_frame = ttk.LabelFrame(main_frame, text="Accounts", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        accounts_text = tk.Text(list_frame, height=15, yscrollcommand=scrollbar.set)
        accounts_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=accounts_text.yview)
        
        def refresh_accounts():
            accounts_text.config(state=tk.NORMAL)
            accounts_text.delete(1.0, tk.END)
            
            available_accounts = list_available_accounts()
            
            if not available_accounts:
                accounts_text.insert(tk.END, "No accounts found.")
            else:
                accounts_text.insert(tk.END, f"Found {len(available_accounts)} account(s):\n\n")
                
                for account in available_accounts:
                    try:
                        if account == "default":
                            token_file = TOKEN_PICKLE_FILE
                        else:
                            token_file = get_account_token_file(account)
                        
                        with open(token_file, "rb") as f:
                            creds = pickle.load(f)
                            if creds and creds.valid:
                                channel_id, channel_title = get_account_info(creds)
                                if channel_title:
                                    accounts_text.insert(tk.END, f"✓ {account}\n")
                                    accounts_text.insert(tk.END, f"  Channel: {channel_title}\n")
                                    accounts_text.insert(tk.END, f"  ID: {channel_id}\n\n")
                                else:
                                    accounts_text.insert(tk.END, f"⚠ {account} - Unable to get channel info\n\n")
                            else:
                                accounts_text.insert(tk.END, f"⚠ {account} - Credentials need refresh\n\n")
                    except Exception as e:
                        accounts_text.insert(tk.END, f"✗ {account} - Error: {e}\n\n")
            
            accounts_text.config(state=tk.DISABLED)
        
        refresh_accounts()
        
        ttk.Button(main_frame, text="Refresh", command=refresh_accounts).pack(pady=10)
    
    def create_account_operations_tab(self, parent, dialog):
        """Create tab for account operations."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Account Operations", font=("Arial", 11, "bold")).pack(pady=10)
        
        # Account selection
        select_frame = ttk.LabelFrame(main_frame, text="Select Account", padding=10)
        select_frame.pack(fill=tk.X, pady=10)
        
        account_var = tk.StringVar()
        available_accounts = list_available_accounts()
        
        if available_accounts:
            account_combo = ttk.Combobox(select_frame, textvariable=account_var, values=available_accounts, state="readonly")
            account_combo.pack(fill=tk.X, pady=5)
        else:
            ttk.Label(select_frame, text="No accounts available.", foreground="red").pack(pady=5)
        
        # Operations frame
        ops_frame = ttk.LabelFrame(main_frame, text="Operations", padding=10)
        ops_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        def refresh_credentials():
            if not account_var.get():
                messagebox.showwarning("No Selection", "Please select an account.")
                return
            
            account_name = account_var.get()
            try:
                creds = authenticate_account(account_name)
                if creds:
                    channel_id, channel_title = get_account_info(creds)
                    if channel_title:
                        messagebox.showinfo("Success", f"✓ Credentials refreshed!\nChannel: {channel_title}")
                    else:
                        messagebox.showwarning("Partial Success", "Credentials refreshed but unable to verify channel info.")
                else:
                    messagebox.showerror("Failed", "Failed to refresh credentials.")
            except Exception as e:
                messagebox.showerror("Error", f"Error refreshing credentials: {e}")
        
        def delete_account():
            if not account_var.get():
                messagebox.showwarning("No Selection", "Please select an account.")
                return
            
            account_name = account_var.get()
            if messagebox.askyesno("Confirm Delete", f"Delete account '{account_name}'? This cannot be undone."):
                try:
                    if account_name == "default":
                        token_file = TOKEN_PICKLE_FILE
                    else:
                        token_file = get_account_token_file(account_name)
                    
                    if os.path.exists(token_file):
                        os.remove(token_file)
                        messagebox.showinfo("Success", f"✓ Account '{account_name}' deleted.")
                        # Refresh available accounts
                        account_combo['values'] = list_available_accounts()
                        account_var.set("")
                except Exception as e:
                    messagebox.showerror("Error", f"Error deleting account: {e}")
        
        ttk.Button(ops_frame, text="Refresh Credentials", command=refresh_credentials, width=30).pack(pady=5, fill=tk.X)
        ttk.Button(ops_frame, text="Delete Account", command=delete_account, width=30).pack(pady=5, fill=tk.X)
    
    def create_data_management_tab(self, parent, dialog):
        """Create tab for data management."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Data Management", font=("Arial", 11, "bold")).pack(pady=10)
        
        # Account selection
        select_frame = ttk.LabelFrame(main_frame, text="Select Account", padding=10)
        select_frame.pack(fill=tk.X, pady=10)
        
        account_var = tk.StringVar()
        available_accounts = list_available_accounts()
        
        if available_accounts:
            account_combo = ttk.Combobox(select_frame, textvariable=account_var, values=available_accounts, state="readonly")
            account_combo.pack(fill=tk.X, pady=5)
        else:
            ttk.Label(select_frame, text="No accounts available.", foreground="red").pack(pady=5)
        
        # Data frame
        data_frame = ttk.LabelFrame(main_frame, text="Processed Videos Data", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(data_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        data_text = tk.Text(data_frame, height=12, yscrollcommand=scrollbar.set)
        data_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=data_text.yview)
        
        def view_data_summary():
            if not account_var.get():
                messagebox.showwarning("No Selection", "Please select an account.")
                return
            
            account_name = account_var.get()
            try:
                if account_name == "default":
                    token_file = TOKEN_PICKLE_FILE
                else:
                    token_file = get_account_token_file(account_name)
                
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    channel_id, _ = get_account_info(creds)
                    
                    if channel_id:
                        data = load_processed_videos_data(channel_id)
                        videos = data.get("videos", {})
                        
                        data_text.config(state=tk.NORMAL)
                        data_text.delete(1.0, tk.END)
                        
                        data_text.insert(tk.END, f"Account: {account_name}\n")
                        data_text.insert(tk.END, f"Channel ID: {channel_id}\n\n")
                        data_text.insert(tk.END, f"Total Processed Videos: {len(videos)}\n\n")
                        
                        if videos:
                            scheduled = sum(1 for v in videos.values() if v.get("status") == "scheduled")
                            duplicates = sum(1 for v in videos.values() if "Duplicate" in v.get("metadata", {}).get("title", ""))
                            errors = sum(1 for v in videos.values() if "Error" in v.get("metadata", {}).get("title", ""))
                            
                            data_text.insert(tk.END, f"Successfully Scheduled: {scheduled}\n")
                            data_text.insert(tk.END, f"Duplicates Detected: {duplicates}\n")
                            data_text.insert(tk.END, f"Processing Errors: {errors}\n\n")
                            
                            data_text.insert(tk.END, f"Last Updated: {data.get('last_updated', 'Unknown')}\n\n")
                            
                            data_text.insert(tk.END, "Recent Videos:\n")
                            recent = list(videos.items())[-5:]
                            for vid_id, vid_data in recent:
                                title = vid_data.get("metadata", {}).get("title", "No title")[:50]
                                status = vid_data.get("status", "unknown")
                                data_text.insert(tk.END, f"\n• {vid_id}\n  Title: {title}...\n  Status: {status}\n")
                        else:
                            data_text.insert(tk.END, "No processed videos found.")
                        
                        data_text.config(state=tk.DISABLED)
                    else:
                        messagebox.showerror("Error", "Could not retrieve channel ID.")
            except Exception as e:
                messagebox.showerror("Error", f"Error loading data: {e}")
        
        def cleanup_data():
            if not account_var.get():
                messagebox.showwarning("No Selection", "Please select an account.")
                return
            
            account_name = account_var.get()
            try:
                if account_name == "default":
                    token_file = TOKEN_PICKLE_FILE
                else:
                    token_file = get_account_token_file(account_name)
                
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    channel_id, _ = get_account_info(creds)
                    
                    if channel_id:
                        # Ask for days to keep
                        days_str = tk.simpledialog.askstring(
                            "Cleanup Data",
                            "Enter number of days to keep (default 30):",
                            parent=parent
                        )
                        if days_str:
                            try:
                                days = int(days_str)
                                cleanup_old_data(channel_id, days)
                                messagebox.showinfo("Success", f"✓ Cleanup complete. Kept data from last {days} days.")
                                view_data_summary()  # Refresh display
                            except ValueError:
                                messagebox.showerror("Invalid Input", "Please enter a valid number.")
            except Exception as e:
                messagebox.showerror("Error", f"Error during cleanup: {e}")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="View Summary", command=view_data_summary).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cleanup Old Data", command=cleanup_data).pack(side=tk.LEFT, padx=5)
    
    def select_account(self):
        """Select an account for automation."""
        available_accounts = list_available_accounts()
        
        if not available_accounts:
            messagebox.showerror("No Accounts", "Please add an account first.")
            return False
        
        # Create selection dialog
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("Select Account")
        select_dialog.geometry("500x400")
        
        main_frame = ttk.Frame(select_dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Select an Account", font=("Arial", 12, "bold")).pack(pady=10)
        
        # List of accounts
        list_frame = ttk.LabelFrame(main_frame, text="Available Accounts", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        accounts_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        accounts_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=accounts_listbox.yview)
        
        for account in available_accounts:
            # Just show account names without trying to validate tokens
            # Token validation happens when user selects account via authenticate_account()
            accounts_listbox.insert(tk.END, account)
        
        # Track if selection was successful
        selection_successful = [False]
        
        def confirm_selection():
            selection = accounts_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an account.")
                return
            
            selected_account = available_accounts[selection[0]]
            try:
                self.selected_account = selected_account
                
                # Authenticate and refresh if needed (matches CLI behavior)
                creds = authenticate_account(selected_account)
                
                if not creds:
                    messagebox.showerror("Error", "Failed to authenticate account.")
                    return
                
                # Verify credentials work by getting channel info
                try:
                    self.youtube_service = build("youtube", "v3", credentials=creds)
                    self.channel_id = get_account_id_from_service(self.youtube_service)
                    
                    if not self.channel_id:
                        messagebox.showerror("Error", "Could not retrieve channel ID. Token may be invalid.")
                        return
                except Exception as auth_error:
                    messagebox.showerror("Authentication Error", f"Failed to use account: {auth_error}")
                    return
                
                selection_successful[0] = True
                messagebox.showinfo("Selected", f"Using account: {selected_account}")
                select_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error authenticating account: {e}")
                print(f"Account selection error: {e}")
        
        ttk.Button(main_frame, text="Select", command=confirm_selection).pack(pady=10)
        
        # Wait for dialog to close
        self.root.wait_window(select_dialog)
        
        # Return success status
        return selection_successful[0]

    def open_promotion_dialog(self):
        """Open the promotion management dialog."""
        if not self.select_account():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Promote Videos - {self.selected_account}")
        dialog.geometry("800x700")

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Settings
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self.create_promotion_settings_tab(settings_frame, dialog)

        # Tab 2: Run Promotion
        run_frame = ttk.Frame(notebook)
        notebook.add(run_frame, text="Run Promotion")
        self.create_run_promotion_tab(run_frame, dialog)

    def create_promotion_settings_tab(self, parent, dialog):
        """Create tab for promotion settings."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Load existing config
        current_config = get_account_promotion_config(self.selected_account)
        
        # Scrollable canvas for settings
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Telegram Settings ---
        tg_frame = ttk.LabelFrame(scrollable_frame, text="Telegram Settings", padding=10)
        tg_frame.pack(fill=tk.X, pady=10)

        # Helper to get value, ignoring placeholders
        def get_conf_val(key, env_key):
            val = current_config.get(key, "")
            # If value is empty or looks like a placeholder, try env
            if not val or "<" in val or "DEFAULT" in val:
                val = os.environ.get(env_key, "")
            return val

        ttk.Label(tg_frame, text="Bot Token:").pack(anchor=tk.W)
        tg_bot_entry = ttk.Entry(tg_frame, width=50)
        tg_bot_entry.insert(0, get_conf_val("telegram_bot_token", "TELEGRAM_BOT_TOKEN"))
        tg_bot_entry.pack(fill=tk.X, pady=5)

        ttk.Label(tg_frame, text="Chat ID (for single target):").pack(anchor=tk.W)
        tg_chat_entry = ttk.Entry(tg_frame, width=50)
        tg_chat_entry.insert(0, get_conf_val("telegram_chat_id", "TELEGRAM_CHAT_ID"))
        tg_chat_entry.pack(fill=tk.X, pady=5)

        # --- OAuth Helper ---
        def capture_oauth_callback(port=5000):
            """Starts a local server to capture the OAuth callback."""
            callback_data = {"path": None}
            
            class CallbackHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    callback_data["path"] = self.path
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<h1>Authentication Successful!</h1><p>You can close this window and return to the app.</p><script>window.close()</script>")
                
                def log_message(self, format, *args):
                    pass # Silence logs

            try:
                # Allow address reuse to avoid "Address already in use" errors
                socketserver.TCPServer.allow_reuse_address = True
                with socketserver.TCPServer(("127.0.0.1", port), CallbackHandler) as httpd:
                    httpd.timeout = 120 # 2 minutes timeout
                    httpd.handle_request() # Handle one request
            except Exception as e:
                print(f"Server error: {e}")
            
            return callback_data["path"]

        # --- Twitter Settings ---
        tw_frame = ttk.LabelFrame(scrollable_frame, text="Twitter/X Settings", padding=10)
        tw_frame.pack(fill=tk.X, pady=10)

        ttk.Label(tw_frame, text="Client ID:").pack(anchor=tk.W)
        tw_client_id_entry = ttk.Entry(tw_frame, width=50)
        tw_client_id_entry.insert(0, get_conf_val("x_client_id", "X_CLIENT_ID"))
        tw_client_id_entry.pack(fill=tk.X, pady=5)

        ttk.Label(tw_frame, text="Client Secret:").pack(anchor=tk.W)
        tw_client_secret_entry = ttk.Entry(tw_frame, width=50, show="*")
        tw_client_secret_entry.insert(0, get_conf_val("x_client_secret", "X_CLIENT_SECRET"))
        tw_client_secret_entry.pack(fill=tk.X, pady=5)

        def get_twitter_token():
            client_id = tw_client_id_entry.get().strip()
            client_secret = tw_client_secret_entry.get().strip()
            if not client_id or not client_secret:
                messagebox.showerror("Missing Info", "Please enter Client ID and Client Secret.")
                return
            
            # Twitter OAuth 2.0 Flow
            redirect_uri = "http://127.0.0.1:5000/callback" 
            
            messagebox.showinfo("Info", f"This will open a browser to login with X.\n\nNOTE: Ensure '{redirect_uri}' is added to your App's Callback URLs in the Developer Portal.\n\nAlso ensure 'Type of App' is 'Confidential Client'.")

            def run_auth():
                try:
                    from requests_oauthlib import OAuth2Session
                    import hashlib
                    import base64
                    
                    # PKCE
                    code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8").rstrip("=")
                    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")

                    scope = ["tweet.read", "tweet.write", "users.read", "offline.access"]
                    
                    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
                    authorization_url, state = oauth.authorization_url(
                        "https://twitter.com/i/oauth2/authorize",
                        code_challenge=code_challenge,
                        code_challenge_method="S256"
                    )
                    
                    webbrowser.open(authorization_url)
                    
                    # Start local server to capture callback
                    path = capture_oauth_callback(port=5000)
                    
                    if path:
                        # Construct full redirect URL
                        redirect_response = f"http://127.0.0.1:5000{path}"
                        
                        token = oauth.fetch_token(
                            token_url="https://api.twitter.com/2/oauth2/token",
                            authorization_response=redirect_response,
                            client_id=client_id,
                            client_secret=client_secret,
                            code_verifier=code_verifier
                        )
                        access_token = token.get("access_token")
                        if access_token:
                            # Update UI in main thread
                            self.root.after(0, lambda: tw_token_entry.delete(0, tk.END))
                            self.root.after(0, lambda: tw_token_entry.insert(0, access_token))
                            self.root.after(0, lambda: messagebox.showinfo("Success", "Access Token retrieved automatically!"))
                        else:
                            self.root.after(0, lambda: messagebox.showerror("Error", "Could not retrieve token."))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Error", "Timeout or no callback received."))

                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Auth failed: {e}"))

            # Run in thread to avoid freezing GUI
            threading.Thread(target=run_auth, daemon=True).start()

        ttk.Button(tw_frame, text="Get Access Token (Auto)", command=get_twitter_token).pack(pady=5)

        ttk.Label(tw_frame, text="Access Token / Bearer Token:").pack(anchor=tk.W)
        tw_token_entry = ttk.Entry(tw_frame, width=50)
        tw_token_entry.insert(0, current_config.get("x_bearer_token", ""))
        tw_token_entry.pack(fill=tk.X, pady=5)

        ttk.Label(tw_frame, text="Webhook URL (optional):").pack(anchor=tk.W)
        tw_webhook_entry = ttk.Entry(tw_frame, width=50)
        tw_webhook_entry.insert(0, current_config.get("twitter_webhook", ""))
        tw_webhook_entry.pack(fill=tk.X, pady=5)

        # --- Instagram Settings ---
        ig_frame = ttk.LabelFrame(scrollable_frame, text="Instagram Settings", padding=10)
        ig_frame.pack(fill=tk.X, pady=10)

        # Method Selector
        ig_method_var = tk.StringVar(value=current_config.get("ig_method", "official"))
        
        ttk.Label(ig_frame, text="Method:").pack(anchor=tk.W)
        method_frame = ttk.Frame(ig_frame)
        method_frame.pack(fill=tk.X, pady=5)
        
        # Container frames for toggling
        official_frame = ttk.Frame(ig_frame)
        instagrapi_frame = ttk.Frame(ig_frame)

        def toggle_ig_method():
            if ig_method_var.get() == "official":
                instagrapi_frame.pack_forget()
                official_frame.pack(fill=tk.X, expand=True)
            else:
                official_frame.pack_forget()
                instagrapi_frame.pack(fill=tk.X, expand=True)

        ttk.Radiobutton(method_frame, text="Official Graph API (Safer)", variable=ig_method_var, value="official", command=toggle_ig_method).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="Instagrapi (Unofficial/Risky)", variable=ig_method_var, value="instagrapi", command=toggle_ig_method).pack(side=tk.LEFT, padx=5)

        # --- Official API UI ---
        ttk.Label(official_frame, text="App ID:").pack(anchor=tk.W)
        ig_app_id_entry = ttk.Entry(official_frame, width=50)
        ig_app_id_val = current_config.get("ig_app_id") or os.environ.get("INSTA_APP_ID", "")
        ig_app_id_entry.insert(0, ig_app_id_val)
        ig_app_id_entry.pack(fill=tk.X, pady=5)

        ttk.Label(official_frame, text="App Secret:").pack(anchor=tk.W)
        ig_app_secret_entry = ttk.Entry(official_frame, width=50, show="*")
        ig_app_secret_val = current_config.get("ig_app_secret") or os.environ.get("INSTA_APP_SECRET", "")
        ig_app_secret_entry.insert(0, ig_app_secret_val)
        ig_app_secret_entry.pack(fill=tk.X, pady=5)

        ttk.Button(official_frame, text="Get Access Token (Browser)", command=get_ig_token).pack(pady=5)

        ttk.Label(official_frame, text="IG User ID:").pack(anchor=tk.W)
        ig_user_entry = ttk.Entry(official_frame, width=50)
        ig_user_entry.insert(0, current_config.get("ig_user_id", ""))
        ig_user_entry.pack(fill=tk.X, pady=5)

        ttk.Label(official_frame, text="Access Token:").pack(anchor=tk.W)
        ig_token_entry = ttk.Entry(official_frame, width=50)
        ig_token_entry.insert(0, current_config.get("ig_access_token", ""))
        ig_token_entry.pack(fill=tk.X, pady=5)

        # --- Instagrapi UI ---
        ttk.Label(instagrapi_frame, text="Username:").pack(anchor=tk.W)
        ig_username_entry = ttk.Entry(instagrapi_frame, width=50)
        ig_username_val = current_config.get("ig_username") or os.environ.get("INSTA_USERNAME", "")
        ig_username_entry.insert(0, ig_username_val)
        ig_username_entry.pack(fill=tk.X, pady=5)

        ttk.Label(instagrapi_frame, text="Password:").pack(anchor=tk.W)
        ig_password_entry = ttk.Entry(instagrapi_frame, width=50, show="*")
        ig_password_val = current_config.get("ig_password") or os.environ.get("INSTA_PASSWORD", "")
        ig_password_entry.insert(0, ig_password_val)
        ig_password_entry.pack(fill=tk.X, pady=5)
        
        # Initial toggle
        toggle_ig_method()

        # Image Source Selection
        img_frame = ttk.LabelFrame(scrollable_frame, text="Image Generation", padding=10)
        img_frame.pack(fill=tk.X, pady=10)
        
        img_source_var = tk.StringVar(value=current_config.get("image_source", "webhook"))
        
        def toggle_img_inputs():
            if img_source_var.get() == "webhook":
                img_webhook_entry.config(state=tk.NORMAL)
            else:
                img_webhook_entry.config(state=tk.DISABLED)

        ttk.Radiobutton(img_frame, text="Use Webhook (e.g. Midjourney wrapper)", variable=img_source_var, value="webhook", command=toggle_img_inputs).pack(anchor=tk.W)
        ttk.Radiobutton(img_frame, text="Use Gemini (Imagen 3)", variable=img_source_var, value="gemini", command=toggle_img_inputs).pack(anchor=tk.W)

        ttk.Label(img_frame, text="Image Gen Webhook URL:").pack(anchor=tk.W)
        img_webhook_entry = ttk.Entry(img_frame, width=50)
        img_webhook_entry.insert(0, current_config.get("image_generation_webhook", ""))
        img_webhook_entry.pack(fill=tk.X, pady=5)
        
        toggle_img_inputs()

        # Save Button
        def save_settings():
            new_config = {
                "account_name": self.selected_account,
                "telegram_bot_token": tg_bot_entry.get().strip(),
                "telegram_chat_id": tg_chat_entry.get().strip(),
                "x_client_id": tw_client_id_entry.get().strip(),
                "x_client_secret": tw_client_secret_entry.get().strip(),
                "x_bearer_token": tw_token_entry.get().strip(),
                "twitter_webhook": tw_webhook_entry.get().strip(),
                "ig_method": ig_method_var.get(),
                "ig_app_id": ig_app_id_entry.get().strip(),
                "ig_app_secret": ig_app_secret_entry.get().strip(),
                "ig_user_id": ig_user_entry.get().strip(),
                "ig_access_token": ig_token_entry.get().strip(),
                "ig_username": ig_username_entry.get().strip(),
                "ig_password": ig_password_entry.get().strip(),
                "image_source": img_source_var.get(),
                "image_generation_webhook": img_webhook_entry.get().strip()
            }
            
            # Construct full config structure
            full_config = load_promotion_config()
            accounts = full_config.get("accounts", [])
            
            # Remove existing entry for this account if present
            accounts = [a for a in accounts if a.get("account_name") != self.selected_account]
            accounts.append(new_config)
            full_config["accounts"] = accounts
            
            if save_promotion_config(full_config):
                messagebox.showinfo("Success", "Settings saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save settings.")

        ttk.Button(scrollable_frame, text="Save Settings", command=save_settings).pack(pady=20)

    def create_run_promotion_tab(self, parent, dialog):
        """Create tab to run promotion."""
        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=10)

        dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Dry Run (Test Mode)", variable=dry_run_var).pack(side=tk.LEFT)

        # Output
        output_frame = ttk.LabelFrame(main_frame, text="Promotion Logs", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        output_text = tk.Text(output_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True)

        def log(msg):
            output_text.insert(tk.END, f"{msg}\n")
            output_text.see(tk.END)
            self.root.update_idletasks()

        def run_promotion():
            btn_run.config(state=tk.DISABLED)
            output_text.delete(1.0, tk.END)
            log("Starting promotion engine...")
            
            def _thread_target():
                try:
                    # 1. Get Config
                    config = get_account_promotion_config(self.selected_account)
                    
                    # 2. Construct Account Config for Engine
                    # The engine expects a specific structure. We map our flat config to it.
                    # Also need to get channel ID and API key from existing metadata logic
                    
                    # Get channel ID and API key (assuming API key is in env or global config for now, 
                    # or we need to add it to settings. For now, let's try to get it from env if not in config)
                    
                    # We need the channel ID. We can get it from the authenticated service.
                    if not self.youtube_service:
                         # Try to authenticate silently if service is missing
                         from youtube_metadata import authenticate_account, get_account_info
                         creds = authenticate_account(self.selected_account)
                         if creds:
                             self.youtube_service = build("youtube", "v3", credentials=creds)
                    
                    if not self.youtube_service:
                        log("Error: Could not authenticate to get Channel ID.")
                        return

                    channel_id = get_account_id_from_service(self.youtube_service)
                    
                    # Construct the config object for PromotionEngine
                    engine_config = {
                        "channel_id": channel_id,
                        "youtube_api_key": os.environ.get("YOUTUBE_API_KEY"), # Fallback
                        "telegram_targets": [],
                        "twitter_targets": [],
                        "instagram_targets": []
                    }
                    
                    # Add Telegram
                    if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
                        engine_config["telegram_targets"].append({
                            "bot_token": config.get("telegram_bot_token"),
                            "chat_id": config.get("telegram_chat_id")
                        })
                        
                    # Add Twitter
                    if config.get("x_bearer_token"):
                        engine_config["twitter_targets"].append({"x_bearer_token": config.get("x_bearer_token")})
                    if config.get("twitter_webhook"):
                        engine_config["twitter_targets"].append({"webhook": config.get("twitter_webhook")})
                        
                    # Add Instagram
                    if config.get("ig_user_id") and config.get("ig_access_token"):
                        engine_config["instagram_targets"].append({
                            "ig_user_id": config.get("ig_user_id"),
                            "access_token": config.get("ig_access_token")
                        })
                    
                    engine_config["image_generation_webhook"] = config.get("image_generation_webhook")

                    # 3. Run Engine
                    engine = PromotionEngine()
                    engine.process_account(engine_config, dry_run=dry_run_var.get(), log_callback=log)
                    
                    log("Promotion run complete.")

                except Exception as e:
                    log(f"Error: {e}")
                finally:
                    btn_run.config(state=tk.NORMAL)

            threading.Thread(target=_thread_target, daemon=True).start()

        btn_run = ttk.Button(controls_frame, text="Run Promotion Now", command=run_promotion)
        btn_run.pack(side=tk.RIGHT)

    def select_account(self):
        """Helper to ensure an account is selected."""
        if self.selected_account:
            return True
            
        # If no account selected, try to select default or ask user
        from youtube_metadata import list_available_accounts
        accounts = list_available_accounts()
        if not accounts:
            messagebox.showwarning("No Accounts", "Please add an account first.")
            return False
            
        # Simple selection dialog
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("Select Account")
        select_dialog.geometry("300x150")
        
        tk.Label(select_dialog, text="Select Account:").pack(pady=10)
        combo = ttk.Combobox(select_dialog, values=accounts, state="readonly")
        combo.pack(pady=5)
        if accounts: combo.current(0)
        
        result = [None]
        def on_select():
            result[0] = combo.get()
            select_dialog.destroy()
            
        ttk.Button(select_dialog, text="Select", command=on_select).pack(pady=10)
        self.root.wait_window(select_dialog)
        
        if result[0]:
            self.selected_account = result[0]
            # Authenticate to set service
            from youtube_metadata import authenticate_account
            creds = authenticate_account(self.selected_account)
            if creds:
                self.youtube_service = build("youtube", "v3", credentials=creds)
                return True
        return False

def main():
    root = tk.Tk()
    app = YouTubeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
