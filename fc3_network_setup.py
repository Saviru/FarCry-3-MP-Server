import tkinter as tk
from tkinter import ttk, messagebox
import socket
import requests
import configparser
import os
import threading
import time
import subprocess
import sys

# Current date and time: 2025-05-03 09:04:14
# Current user: Saviru

class NetworkSetupTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Far Cry 3 Network Setup")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
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
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # IP Address section
        ip_frame = ttk.LabelFrame(main_frame, text="IP Address", padding="5")
        ip_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(ip_frame, text="Local IP:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.local_ip_var = tk.StringVar()
        ttk.Entry(ip_frame, textvariable=self.local_ip_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(ip_frame, text="Detect", command=self.detect_local_ip).grid(row=0, column=2, padx=5)
        
        ttk.Label(ip_frame, text="Public IP:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.public_ip_var = tk.StringVar()
        ttk.Entry(ip_frame, textvariable=self.public_ip_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(ip_frame, text="Detect", command=self.detect_public_ip).grid(row=1, column=2, padx=5)
        
        ttk.Label(ip_frame, text="Server IP:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.server_ip_var = tk.StringVar(value=self.config.get('DEFAULT', 'server_ip', fallback='127.0.0.1'))
        ttk.Entry(ip_frame, textvariable=self.server_ip_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Button(ip_frame, text="Use Local", command=lambda: self.server_ip_var.set(self.local_ip_var.get())).grid(row=2, column=2, padx=5)
        
        # Port section
        port_frame = ttk.LabelFrame(main_frame, text="Port Configuration", padding="5")
        port_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(port_frame, text="Server Port:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value=self.config.get('DEFAULT', 'server_port', fallback='9201'))
        ttk.Entry(port_frame, textvariable=self.port_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(port_frame, text="Test", command=self.test_port).grid(row=0, column=2, padx=5)
        
        # Port forwarding section
        forward_frame = ttk.LabelFrame(main_frame, text="Port Forwarding", padding="5")
        forward_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(forward_frame, text="For multiplayer, you need to set up port forwarding on your router:").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(forward_frame, text="1. Forward port 9201 UDP to your local IP address").grid(row=1, column=0, columnspan=3, sticky=tk.W)
        ttk.Label(forward_frame, text="2. Make sure your firewall allows Far Cry 3 to access the network").grid(row=2, column=0, columnspan=3, sticky=tk.W)
        
        ttk.Button(forward_frame, text="Open Router Page", command=self.open_router).grid(row=3, column=0, pady=10)
        ttk.Button(forward_frame, text="Check Port Forwarding", command=self.check_port_forwarding).grid(row=3, column=1, pady=10)
        
        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Save Configuration", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=self.close).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Initialize
        self.detect_local_ip()
    
    def detect_local_ip(self):
        """Detect local IP address"""
        self.status_var.set("Detecting local IP...")
        
        try:
            # Get local IP by creating a socket connection
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            self.local_ip_var.set(local_ip)
            self.status_var.set(f"Local IP detected: {local_ip}")
        except Exception as e:
            self.status_var.set(f"Error detecting local IP: {e}")
            self.local_ip_var.set("127.0.0.1")
    
    def detect_public_ip(self):
        """Detect public IP address"""
        self.status_var.set("Detecting public IP...")
        
        def fetch_ip():
            try:
                # Use external service to get public IP
                response = requests.get("https://api.ipify.org", timeout=5)
                if response.status_code == 200:
                    self.public_ip_var.set(response.text)
                    self.status_var.set(f"Public IP detected: {response.text}")
                else:
                    self.status_var.set("Failed to detect public IP")
            except Exception as e:
                self.status_var.set(f"Error detecting public IP: {e}")
        
        # Run in a separate thread to avoid blocking UI
        threading.Thread(target=fetch_ip, daemon=True).start()
    
    def test_port(self):
        """Test if port is available"""
        port = int(self.port_var.get())
        self.status_var.set(f"Testing port {port}...")
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('0.0.0.0', port))
            s.close()
            self.status_var.set(f"Port {port} is available")
            messagebox.showinfo("Port Test", f"Port {port} is available for use.")
        except Exception as e:
            self.status_var.set(f"Port {port} is in use or unavailable")
            messagebox.warning("Port Test", f"Port {port} is already in use or unavailable.\nError: {e}")
    
    def open_router(self):
        """Open default gateway in browser for router configuration"""
        self.status_var.set("Detecting router address...")
        
        try:
            # Get default gateway
            if sys.platform == 'win32':
                output = subprocess.check_output("ipconfig | findstr /i \"Default Gateway\"", shell=True).decode()
                gateway = output.split(":")[-1].strip()
            else:
                output = subprocess.check_output("ip route | grep default", shell=True).decode()
                gateway = output.split()[2]
            
            # Open browser to the router's IP
            import webbrowser
            webbrowser.open(f"http://{gateway}")
            
            self.status_var.set(f"Opened router configuration page at {gateway}")
        except Exception as e:
            self.status_var.set(f"Failed to open router page: {e}")
            messagebox.showinfo("Router Access", 
                               "Could not automatically open your router's configuration page.\n\n"
                               "You'll need to manually access your router's configuration page to set up port forwarding.")
    
    def check_port_forwarding(self):
        """Check if port is forwarded properly"""
        self.status_var.set("Checking port forwarding...")
        
        def check_port():
            port = int(self.port_var.get())
            public_ip = self.public_ip_var.get()
            
            if not public_ip or public_ip == "127.0.0.1":
                self.status_var.set("Please detect your public IP first")
                return
            
            try:
                # Use an external service to check port forwarding
                response = requests.get(f"https://portchecker.co/check?port={port}&protocol=udp", timeout=10)
                
                if "Port open" in response.text:
                    self.status_var.set(f"Port {port} is properly forwarded")
                    messagebox.showinfo("Port Forwarding", f"Port {port} is properly forwarded!")
                else:
                    self.status_var.set(f"Port {port} is not forwarded")
                    messagebox.warning("Port Forwarding", 
                                      f"Port {port} does not appear to be forwarded correctly.\n\n"
                                      "Please check your router's port forwarding configuration.")
            except Exception as e:
                self.status_var.set(f"Error checking port forwarding: {e}")
                messagebox.error("Error", f"Failed to check port forwarding: {e}")
        
        # Run in a separate thread to avoid blocking UI
        threading.Thread(target=check_port, daemon=True).start()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Update config object
            self.config['DEFAULT']['server_ip'] = self.server_ip_var.get()
            self.config['DEFAULT']['server_port'] = self.port_var.get()
            
            # Save to file
            with open('fc3_multiplayer.ini', 'w') as f:
                self.config.write(f)
            
            self.status_var.set("Configuration saved successfully")
            messagebox.showinfo("Configuration", "Network configuration saved successfully.")
        except Exception as e:
            self.status_var.set(f"Error saving configuration: {e}")
            messagebox.error("Error", f"Failed to save configuration: {e}")
    
    def close(self):
        """Close the window"""
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkSetupTool(root)
    root.mainloop()