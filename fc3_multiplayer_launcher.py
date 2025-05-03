import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
import subprocess
import threading
import time
import configparser
import platform
import socket
import psutil
import datetime

# Current date and time: 2025-05-03 09:24:09
# Current user: Saviru

class FC3MultiplayerLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Far Cry 3 Multiplayer Launcher")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Configure colors for the dark theme
        self.bg_color = "#1e1e1e"
        self.fg_color = "#e0e0e0"
        self.accent_color = "#007acc"
        self.accent_dark = "#005a9e"
        self.highlight_color = "#264f78"
        self.error_color = "#f44336"
        self.success_color = "#4caf50"
        self.warning_color = "#ff9800"
        self.button_bg = "#333333"
        self.button_active = "#555555"
        self.button_accent = "#2b79b9"
        self.button_accent_active = "#1c5c96"
        self.button_danger = "#b33939"
        self.button_danger_active = "#8e2933"
        self.button_success = "#388e3c"
        self.button_success_active = "#2e7d32"
        
        # Configure fonts
        self.title_font = font.Font(family="Segoe UI", size=14, weight="bold")
        self.header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)
        
        # Apply dark theme to root window
        self.root.configure(bg=self.bg_color)
        
        # Create main container
        self.main_container = tk.Frame(root, bg=self.bg_color)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create header frame with title and logo
        self.create_header()
        
        # Create content frame
        self.content_frame = tk.Frame(self.main_container, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Split content into left panel (buttons and status) and right panel (logs)
        self.left_panel = tk.Frame(self.content_frame, bg=self.bg_color)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.right_panel = tk.Frame(self.content_frame, bg=self.bg_color)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create control panels in left pane
        self.create_control_panel()
        self.create_status_panel()
        
        # Create log panel in right pane
        self.create_log_panel()
        
        # Create debug panel at bottom
        self.create_debug_panel()
        
        # Status bar
        self.create_status_bar()
        
        # Server process
        self.server_process = None
        self.game_process = None
        
        # Log initial message
        self.log("Far Cry 3 Multiplayer Launcher initialized")
        self.log(f"Launcher started by Saviru")
        self.log(f"Game path: {self.config.get('DEFAULT', 'game_path', fallback='Not set')}")
        self.log("Current date and time: 2025-05-03 09:24:09")
        
        # Start debug info updater
        self.update_debug_info()
        
        # Start status updater
        self.update_status_info()
        
        # Verify game path
        self.verify_game_path()
    
    def create_dark_button(self, parent, text, command, width=15, height=1, bg=None, 
                          active_bg=None, font=None, style=None):
        """Create a custom dark-themed button"""
        if bg is None:
            bg = self.button_bg
        if active_bg is None:
            active_bg = self.button_active
        if font is None:
            font = self.normal_font
        
        button = tk.Button(parent, text=text, command=command, width=width, height=height,
                          bg=bg, fg=self.fg_color, activebackground=active_bg, 
                          activeforeground=self.fg_color, font=font, bd=1,
                          highlightbackground=bg, relief=tk.RAISED)
        
        if style == "accent":
            button.configure(bg=self.button_accent, activebackground=self.button_accent_active)
        elif style == "danger":
            button.configure(bg=self.button_danger, activebackground=self.button_danger_active)
        elif style == "success":
            button.configure(bg=self.button_success, activebackground=self.button_success_active)
        
        return button
    
    def create_dark_scrollbar(self, parent):
        """Create a custom dark-themed scrollbar"""
        scrollbar = tk.Scrollbar(parent, bg=self.button_bg, troughcolor=self.bg_color,
                               activebackground=self.button_active, bd=0,
                               highlightbackground=self.bg_color)
        return scrollbar
    
    def create_header(self):
        """Create the header with title and logo"""
        header_frame = tk.Frame(self.main_container, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo placeholder 
        logo_frame = tk.Frame(header_frame, width=50, height=50, bg=self.bg_color)
        logo_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # Draw a simple FC3 logo placeholder
        logo_canvas = tk.Canvas(logo_frame, width=50, height=50, bg=self.bg_color, 
                                highlightthickness=0)
        logo_canvas.pack()
        logo_canvas.create_oval(5, 5, 45, 45, outline=self.accent_color, width=2)
        logo_canvas.create_text(25, 25, text="FC3", fill=self.accent_color, 
                                font=self.header_font)
        
        # Title
        title_label = tk.Label(header_frame, text="Far Cry 3 Multiplayer", 
                              font=self.title_font, bg=self.bg_color, fg=self.fg_color)
        title_label.pack(side=tk.LEFT)
        
        # Version
        version_label = tk.Label(header_frame, text="v1.0.2", bg=self.bg_color,
                                fg=self.accent_color, font=self.normal_font)
        version_label.pack(side=tk.RIGHT)
        
        # Separator
        separator = tk.Frame(self.main_container, height=1, bg="#333333")
        separator.pack(fill=tk.X, pady=(0, 10))
    
    def create_control_panel(self):
        """Create the control panel with action buttons"""
        # Load configuration
        self.config = configparser.ConfigParser()
        if os.path.exists('fc3_multiplayer.ini'):
            self.config.read('fc3_multiplayer.ini')
        else:
            self.config['DEFAULT'] = {
                'server_ip': '127.0.0.1',
                'server_port': '9201',
                'max_players': '16',
                'game_name': 'FC3 Multiplayer',
                'game_path': r'C:\Games\Far Cry 3\Far Cry 3\bin\farcry3.exe'
            }
            with open('fc3_multiplayer.ini', 'w') as f:
                self.config.write(f)
                
        control_frame = tk.LabelFrame(self.left_panel, text="Controls", 
                                     font=self.normal_font, bg=self.bg_color, 
                                     fg=self.fg_color)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a grid for buttons
        button_frame = tk.Frame(control_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Network setup button
        self.network_btn = self.create_dark_button(button_frame, "Network Setup", 
                                                  self.network_setup, width=15)
        self.network_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Start server button
        self.server_btn = self.create_dark_button(button_frame, "Start Server", 
                                                 self.start_server, width=15, 
                                                 style="success")
        self.server_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Server configuration button
        self.config_btn = self.create_dark_button(button_frame, "Server Config", 
                                                 self.edit_config, width=15)
        self.config_btn.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Start game button
        self.start_btn = self.create_dark_button(button_frame, "Start Game", 
                                                self.start_game, width=15, 
                                                style="accent")
        self.start_btn.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Exit button
        self.exit_btn = self.create_dark_button(button_frame, "Exit", 
                                               self.exit_app, width=15, 
                                               style="danger")
        self.exit_btn.grid(row=2, column=1, padx=5, pady=5, sticky="e")
    
    def create_status_panel(self):
        """Create the status panel showing system and server status"""
        status_frame = tk.LabelFrame(self.left_panel, text="Status", 
                                    font=self.normal_font, bg=self.bg_color, 
                                    fg=self.fg_color)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create status grid
        status_grid = tk.Frame(status_frame, bg=self.bg_color)
        status_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Server status
        tk.Label(status_grid, text="Server Status:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=0, column=0, sticky="w", pady=2)
        self.server_status_var = tk.StringVar(value="Stopped")
        self.server_status_label = tk.Label(status_grid, textvariable=self.server_status_var, 
                                          font=self.normal_font, bg=self.bg_color, 
                                          fg=self.error_color)
        self.server_status_label.grid(row=0, column=1, sticky="w", pady=2)
        
        # Game status
        tk.Label(status_grid, text="Game Status:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=1, column=0, sticky="w", pady=2)
        self.game_status_var = tk.StringVar(value="Not Running")
        self.game_status_label = tk.Label(status_grid, textvariable=self.game_status_var, 
                                        font=self.normal_font, bg=self.bg_color, 
                                        fg=self.fg_color)
        self.game_status_label.grid(row=1, column=1, sticky="w", pady=2)
        
        # Network status
        tk.Label(status_grid, text="Network Status:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=2, column=0, sticky="w", pady=2)
        self.network_status_var = tk.StringVar(value="Unknown")
        self.network_status_label = tk.Label(status_grid, textvariable=self.network_status_var, 
                                           font=self.normal_font, bg=self.bg_color, 
                                           fg=self.warning_color)
        self.network_status_label.grid(row=2, column=1, sticky="w", pady=2)
        
        # Players online
        tk.Label(status_grid, text="Players Online:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=3, column=0, sticky="w", pady=2)
        self.players_var = tk.StringVar(value="0/16")
        tk.Label(status_grid, textvariable=self.players_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=3, column=1, sticky="w", pady=2)
        
        # Server uptime
        tk.Label(status_grid, text="Server Uptime:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=4, column=0, sticky="w", pady=2)
        self.uptime_var = tk.StringVar(value="00:00:00")
        tk.Label(status_grid, textvariable=self.uptime_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=4, column=1, sticky="w", pady=2)
        
        # Server IP
        tk.Label(status_grid, text="Server IP:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=5, column=0, sticky="w", pady=2)
        self.ip_var = tk.StringVar(value=self.config.get('DEFAULT', 'server_ip', fallback="127.0.0.1"))
        tk.Label(status_grid, textvariable=self.ip_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=5, column=1, sticky="w", pady=2)
        
        # Server port
        tk.Label(status_grid, text="Server Port:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=6, column=0, sticky="w", pady=2)
        self.port_var = tk.StringVar(value=self.config.get('DEFAULT', 'server_port', fallback="9201"))
        tk.Label(status_grid, textvariable=self.port_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=6, column=1, sticky="w", pady=2)
        
        # Memory usage
        tk.Label(status_grid, text="Server Memory:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=7, column=0, sticky="w", pady=2)
        self.memory_var = tk.StringVar(value="0 MB")
        tk.Label(status_grid, textvariable=self.memory_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=7, column=1, sticky="w", pady=2)
    
    def create_log_panel(self):
        """Create the log panel for showing application logs"""
        log_frame = tk.LabelFrame(self.right_panel, text="Log Output", 
                                 font=self.normal_font, bg=self.bg_color, 
                                 fg=self.fg_color)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create custom dark-themed text widget
        log_container = tk.Frame(log_frame, bg=self.bg_color)
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create vertical scrollbar
        v_scrollbar = self.create_dark_scrollbar(log_container)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create horizontal scrollbar
        h_scrollbar = self.create_dark_scrollbar(log_container)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        h_scrollbar.config(orient=tk.HORIZONTAL)
        
        # Create text widget with both scrollbars
        self.log_text = tk.Text(log_container, wrap=tk.NONE, 
                               bg="#252525", fg=self.fg_color,
                               font=self.normal_font,
                               insertbackground=self.fg_color,
                               selectbackground=self.accent_color,
                               selectforeground=self.fg_color,
                               padx=5, pady=5,
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbars to text widget
        v_scrollbar.config(command=self.log_text.yview)
        h_scrollbar.config(command=self.log_text.xview)
        
        # Add custom styling to log text
        self.log_text.tag_configure("timestamp", foreground="#888888")
        self.log_text.tag_configure("info", foreground="#e0e0e0")
        self.log_text.tag_configure("error", foreground="#f44336")
        self.log_text.tag_configure("warning", foreground="#ff9800")
        self.log_text.tag_configure("success", foreground="#4caf50")
        
        # Add button frame at bottom
        button_frame = tk.Frame(log_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Clear log button
        self.clear_log_btn = self.create_dark_button(button_frame, "Clear Log", 
                                                    self.clear_log, width=10, 
                                                    font=self.small_font)
        self.clear_log_btn.pack(side=tk.RIGHT)
        
        # Save log button
        self.save_log_btn = self.create_dark_button(button_frame, "Save Log", 
                                                   self.save_log, width=10, 
                                                   font=self.small_font)
        self.save_log_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_debug_panel(self):
        """Create the debug panel for system information"""
        debug_frame = tk.LabelFrame(self.main_container, text="System Information", 
                                   font=self.normal_font, bg=self.bg_color, 
                                   fg=self.fg_color)
        debug_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create debug grid in two columns
        debug_grid = tk.Frame(debug_frame, bg=self.bg_color)
        debug_grid.pack(fill=tk.X, padx=10, pady=5)
        
        # Left column
        left_column = tk.Frame(debug_grid, bg=self.bg_color)
        left_column.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # System info
        tk.Label(left_column, text="OS:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=0, column=0, sticky="w", pady=2)
        self.os_var = tk.StringVar(value=platform.system() + " " + platform.release())
        tk.Label(left_column, textvariable=self.os_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=0, column=1, sticky="w", pady=2)
        
        # Python version
        tk.Label(left_column, text="Python:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=1, column=0, sticky="w", pady=2)
        self.python_var = tk.StringVar(value=platform.python_version())
        tk.Label(left_column, textvariable=self.python_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=1, column=1, sticky="w", pady=2)
        
        # Right column
        right_column = tk.Frame(debug_grid, bg=self.bg_color)
        right_column.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # CPU usage
        tk.Label(right_column, text="CPU Usage:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=0, column=0, sticky="w", pady=2)
        self.cpu_var = tk.StringVar(value="0%")
        tk.Label(right_column, textvariable=self.cpu_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=0, column=1, sticky="w", pady=2)
        
        # Memory usage
        tk.Label(right_column, text="Memory Usage:", font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=1, column=0, sticky="w", pady=2)
        self.system_memory_var = tk.StringVar(value="0 MB / 0 MB")
        tk.Label(right_column, textvariable=self.system_memory_var, font=self.normal_font,
                bg=self.bg_color, fg=self.fg_color).grid(
            row=1, column=1, sticky="w", pady=2)
        
        # Add timestamp
        tk.Label(debug_grid, text=f"Last Updated: 2025-05-03 09:24:09 UTC", 
                font=self.small_font, bg=self.bg_color, fg="#888888").pack(
                    side=tk.BOTTOM, pady=(5,0))
    
    def create_status_bar(self):
        """Create the status bar at the bottom of the window"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, 
                                 bg="#252525", fg=self.fg_color, 
                                 anchor=tk.W, padx=5, pady=2,
                                 relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def verify_game_path(self):
        """Verify the game executable exists"""
        game_path = self.config.get('DEFAULT', 'game_path', fallback=r'C:\Games\Far Cry 3\Far Cry 3\bin\farcry3.exe')
        if not os.path.exists(game_path):
            self.log("Warning: Game executable not found at " + game_path, level="warning")
            self.status_var.set("⚠️ Game path not found - check configuration")
        else:
            self.log("Game executable found at " + game_path, level="success")
    
    def log(self, message, level="info"):
        """Add a message to the log with a timestamp and level-based formatting"""
        timestamp = time.strftime("%H:%M:%S")
        
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        if level == "error":
            self.log_text.insert(tk.END, "ERROR: ", "error")
            self.log_text.insert(tk.END, message + "\n", "error")
        elif level == "warning":
            self.log_text.insert(tk.END, "WARNING: ", "warning")
            self.log_text.insert(tk.END, message + "\n", "warning")
        elif level == "success":
            self.log_text.insert(tk.END, message + "\n", "success")
        else:
            self.log_text.insert(tk.END, message + "\n", "info")
        
        self.log_text.see(tk.END)
        print(f"[{level.upper()}] {message}")
    
    def clear_log(self):
        """Clear the log window"""
        self.log_text.delete(1.0, tk.END)
        self.log("Log cleared")
    
    def save_log(self):
        """Save the log to a file"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"fc3_launcher_log_{timestamp}.txt"
            
            with open(filename, "w") as f:
                f.write(self.log_text.get(1.0, tk.END))
            
            self.log(f"Log saved to {filename}", level="success")
            self.status_var.set(f"Log saved to {filename}")
        except Exception as e:
            self.log(f"Error saving log: {e}", level="error")
    
    def update_debug_info(self):
        """Update system information in the debug panel"""
        try:
            # Update CPU usage
            cpu_percent = psutil.cpu_percent()
            self.cpu_var.set(f"{cpu_percent:.1f}%")
            
            # Update memory usage
            mem = psutil.virtual_memory()
            total_mem_gb = mem.total / (1024**3)
            used_mem_gb = mem.used / (1024**3)
            self.system_memory_var.set(f"{used_mem_gb:.1f} GB / {total_mem_gb:.1f} GB ({mem.percent}%)")
            
            # Check server memory if running
            if self.server_process and self.server_process.poll() is None:
                try:
                    server_proc = psutil.Process(self.server_process.pid)
                    server_mem = server_proc.memory_info().rss / (1024**2)
                    self.memory_var.set(f"{server_mem:.1f} MB")
                except:
                    self.memory_var.set("N/A")
            else:
                self.memory_var.set("0 MB")
        except Exception as e:
            pass  # Silently ignore errors in the background updater
        
        # Schedule the next update
        self.root.after(2000, self.update_debug_info)
    
    def update_status_info(self):
        """Update status information"""
        # Update server status
        if self.server_process and self.server_process.poll() is None:
            self.server_status_var.set("Running")
            self.server_status_label.configure(fg=self.success_color)
            
            # Update uptime if server is running
            if hasattr(self, 'server_start_time'):
                uptime = time.time() - self.server_start_time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                self.uptime_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.server_status_var.set("Stopped")
            self.server_status_label.configure(fg=self.error_color)
            self.uptime_var.set("00:00:00")
        
        # Update game status
        game_running = False
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'farcry3' in proc.info['name'].lower():
                    game_running = True
                    break
            
            if game_running:
                self.game_status_var.set("Running")
                self.game_status_label.configure(fg=self.success_color)
            else:
                self.game_status_var.set("Not Running")
                self.game_status_label.configure(fg=self.fg_color)
        except:
            pass
        
        # Check network status
        try:
            port = int(self.config.get('DEFAULT', 'server_port', fallback='9201'))
            
            # Only check network if server is running
            if self.server_process and self.server_process.poll() is None:
                # Simple check if the port is accessible
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)
                s.connect((self.config.get('DEFAULT', 'server_ip', fallback='127.0.0.1'), port))
                s.close()
                
                self.network_status_var.set("Connected")
                self.network_status_label.configure(fg=self.success_color)
            else:
                self.network_status_var.set("Disconnected")
                self.network_status_label.configure(fg=self.fg_color)
        except:
            if self.server_process and self.server_process.poll() is None:
                self.network_status_var.set("Error")
                self.network_status_label.configure(fg=self.error_color)
        
        # Schedule the next update
        self.root.after(1000, self.update_status_info)
    
    def network_setup(self):
        """Launch the network setup tool"""
        self.log("Starting network setup...")
        self.status_var.set("Running network setup...")
        
        try:
            subprocess.Popen([sys.executable, "fc3_network_setup.py"])
            self.log("Network setup launched successfully", level="success")
        except Exception as e:
            self.log(f"Error launching network setup: {e}", level="error")
            self.status_var.set("Network setup failed")
    
    def edit_config(self):
        """Edit the server configuration"""
        try:
            # For simplicity, just open the config file in notepad
            if os.path.exists('fc3_multiplayer.ini'):
                if sys.platform == 'win32':
                    os.startfile('fc3_multiplayer.ini')
                else:
                    subprocess.Popen(['xdg-open', 'fc3_multiplayer.ini'])
                self.log("Opening configuration file for editing", level="info")
            else:
                self.log("Configuration file not found", level="warning")
        except Exception as e:
            self.log(f"Error opening configuration: {e}", level="error")
    
    def start_server(self):
        """Start the Far Cry 3 multiplayer server"""
        if self.server_process and self.server_process.poll() is None:
            self.log("Server is already running", level="warning")
            return
        
        self.log("Starting Far Cry 3 Multiplayer Server...")
        self.status_var.set("⚙️ Starting server...")
        
        try:
            # Start server as a subprocess
            self.server_process = subprocess.Popen(
                [sys.executable, "fc3_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Record start time for uptime calculation
            self.server_start_time = time.time()
            
            # Start a thread to read server output
            threading.Thread(target=self.read_server_output, daemon=True).start()
            
            self.log("Server started successfully", level="success")
            self.status_var.set("✅ Server running")
            
            # Update status immediately
            self.server_status_var.set("Running")
            self.server_status_label.configure(fg=self.success_color)
        except Exception as e:
            self.log(f"Error starting server: {e}", level="error")
            self.status_var.set("❌ Server failed to start")
    
    def read_server_output(self):
        """Read and process the server output in a separate thread"""
        for line in iter(self.server_process.stdout.readline, ''):
            line = line.strip()
            if "error" in line.lower():
                self.log(f"Server: {line}", level="error")
            elif "warning" in line.lower():
                self.log(f"Server: {line}", level="warning")
            else:
                self.log(f"Server: {line}")
            
            # Update player count if line contains player info
            if "players connected" in line.lower():
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        count = parts[1].strip().split("/")[0].strip()
                        max_players = self.config.get('DEFAULT', 'max_players', fallback='16')
                        self.players_var.set(f"{count}/{max_players}")
                except:
                    pass
        
        # When the loop exits, the server process has terminated
        if self.server_process.poll() is not None:
            exit_code = self.server_process.returncode
            if exit_code == 0:
                self.log(f"Server process exited cleanly with code {exit_code}", level="success")
            else:
                self.log(f"Server process exited with error code {exit_code}", level="error")
            
            self.status_var.set("Server stopped")
            self.server_status_var.set("Stopped")
            self.server_status_label.configure(fg=self.error_color)
            self.players_var.set(f"0/{self.config.get('DEFAULT', 'max_players', fallback='16')}")
    
    def start_game(self):
        """Start Far Cry 3 with multiplayer DLL injection"""
        self.log("Starting Far Cry 3 with multiplayer DLL...")
        self.status_var.set("🎮 Starting game...")
        
        try:
            # Start the game and inject DLL
            thread = threading.Thread(target=self.run_game_with_dll)
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.log(f"Error starting game: {e}", level="error")
            self.status_var.set("❌ Game failed to start")
    
    def run_game_with_dll(self):
        """Run the game with DLL injection in a separate thread"""
        try:
            result = subprocess.run([sys.executable, "fc3_injector.py"], 
                                    capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log("Game launched successfully with multiplayer DLL", level="success")
                self.status_var.set("✅ Game running")
            else:
                self.log(f"Error launching game: {result.stderr}", level="error")
                self.status_var.set("❌ Game launch failed")
                
                # Show detailed error in log
                for line in result.stderr.splitlines():
                    self.log(f"Injector error: {line}", level="error")
        except Exception as e:
            self.log(f"Exception during game launch: {e}", level="error")
            self.status_var.set("❌ Game launch failed")
    
    def exit_app(self):
        """Exit the application, stopping the server if it's running"""
        # Stop server if running
        if self.server_process and self.server_process.poll() is None:
            self.log("Stopping server...")
            try:
                self.server_process.terminate()
                # Wait up to 5 seconds for graceful termination
                for _ in range(10):
                    if self.server_process.poll() is not None:
                        break
                    time.sleep(0.5)
                
                # Force kill if still running
                if self.server_process.poll() is None:
                    self.server_process.kill()
                
                self.log("Server stopped", level="success")
            except Exception as e:
                self.log(f"Error stopping server: {e}", level="error")
        
        self.log("Exiting application...")
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    # Create and configure the root window
    root = tk.Tk()
    root.title("Far Cry 3 Multiplayer Launcher")
    
    # Set application icon
    try:
        root.iconbitmap("fc3_icon.ico")
    except:
        pass
    
    # Try to make window title bar dark on supported platforms
    try:
        if platform.system() == "Windows":
            root.update()
            ctypes_handle = ctypes.windll.user32.GetParent(root.winfo_id())
            root.after(10, lambda: ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes_handle, 20, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int)))
    except:
        pass  # Ignore if dark title bar isn't supported
    
    # Initialize the application
    app = FC3MultiplayerLauncher(root)
    
    # Start the main event loop
    root.mainloop()