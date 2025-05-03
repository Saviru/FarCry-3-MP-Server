#!/usr/bin/env python3
# FC3 DLL Injector - Injects custom DLLs into the game process
import os
import sys
import time
import ctypes
import logging
import configparser
import psutil
from ctypes import wintypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fc3_injector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FC3Injector")

# Windows API constants
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04

# Load Windows API functions
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = wintypes.LPVOID

kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
kernel32.GetProcAddress.restype = wintypes.LPVOID

kernel32.GetModuleHandleA.argtypes = [wintypes.LPCSTR]
kernel32.GetModuleHandleA.restype = wintypes.HMODULE

kernel32.CreateRemoteThread.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
kernel32.CreateRemoteThread.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


class FC3Injector:
    def __init__(self, config_path="fc3_injector.ini"):
        self.config = self._load_config(config_path)
        self.game_path = self.config.get("paths", {}).get("game_path", r"C:\Games\Far Cry 3\Far Cry 3")
        self.dll_path = self.config.get("injection", {}).get("dll_path", os.path.join(self.game_path, "bin", "fc3_mp_fix.dll"))
        
    def _load_config(self, config_path):
        config = {
            "paths": {
                "game_path": r"C:\Games\Far Cry 3\Far Cry 3"
            },
            "injection": {
                "dll_path": None
            }
        }
        
        if os.path.exists(config_path):
            try:
                parser = configparser.ConfigParser()
                parser.read(config_path)
                
                if "paths" in parser:
                    if "game_path" in parser["paths"]:
                        config["paths"]["game_path"] = parser.get("paths", "game_path")
                        
                if "injection" in parser:
                    if "dll_path" in parser["injection"]:
                        config["injection"]["dll_path"] = parser.get("injection", "dll_path")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                
        # Fill in default DLL path if not set
        if config["injection"]["dll_path"] is None:
            config["injection"]["dll_path"] = os.path.join(config["paths"]["game_path"], "bin", "fc3_mp_fix.dll")
                
        # Create default config if it doesn't exist
        if not os.path.exists(config_path):
            self._save_config(config, config_path)
                
        return config
    
    def _save_config(self, config, config_path):
        parser = configparser.ConfigParser()
        
        for section in config:
            parser[section] = {}
            for key, value in config[section].items():
                if value is not None:
                    parser[section][key] = str(value)
        
        with open(config_path, 'w') as f:
            parser.write(f)
    
    def find_game_process(self):
        """Find the Far Cry 3 process"""
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['name'].lower() == 'farcry3.exe':
                logger.info(f"Found Far Cry 3 process: PID {proc.info['pid']}")
                return proc.info['pid']
        
        logger.warning("Far Cry 3 process not found")
        return None
    
    def inject_dll(self, pid):
        """Inject DLL into the game process"""
        if not os.path.exists(self.dll_path):
            logger.error(f"DLL not found at {self.dll_path}")
            return False
        
        # Get full path to DLL
        dll_path_abs = os.path.abspath(self.dll_path)
        dll_path_bytes = dll_path_abs.encode('utf-8') + b'\0'
        
        try:
            # Open the process
            process_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not process_handle:
                error = ctypes.get_last_error()
                logger.error(f"Failed to open process (Error: {error})")
                return False
            
            logger.info(f"Opened process handle: {process_handle}")
            
            try:
                # Allocate memory for the DLL path
                path_len = len(dll_path_bytes)
                path_addr = kernel32.VirtualAllocEx(
                    process_handle, None, path_len, 
                    MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
                )
                
                if not path_addr:
                    error = ctypes.get_last_error()
                    logger.error(f"Failed to allocate memory (Error: {error})")
                    return False
                
                logger.info(f"Allocated memory at: 0x{path_addr:X}")
                
                # Write the DLL path to the process memory
                bytes_written = ctypes.c_size_t()
                result = kernel32.WriteProcessMemory(
                    process_handle, path_addr, dll_path_bytes, path_len, 
                    ctypes.byref(bytes_written)
                )
                
                if not result:
                    error = ctypes.get_last_error()
                    logger.error(f"Failed to write to process memory (Error: {error})")
                    return False
                
                logger.info(f"Wrote {bytes_written.value} bytes to process memory")
                
                # Get the address of LoadLibraryA
                kernel32_handle = kernel32.GetModuleHandleA(b"kernel32.dll")
                loadlib_addr = kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
                
                if not loadlib_addr:
                    error = ctypes.get_last_error()
                    logger.error(f"Failed to get LoadLibraryA address (Error: {error})")
                    return False
                
                logger.info(f"LoadLibraryA address: 0x{loadlib_addr:X}")
                
                # Create a remote thread to load the DLL
                thread_id = ctypes.c_ulong(0)
                thread_handle = kernel32.CreateRemoteThread(
                    process_handle, None, 0, loadlib_addr, path_addr, 0, 
                    ctypes.byref(thread_id)
                )
                
                if not thread_handle:
                    error = ctypes.get_last_error()
                    logger.error(f"Failed to create remote thread (Error: {error})")
                    return False
                
                logger.info(f"Created remote thread: ID {thread_id.value}")
                
                # Wait for thread to complete
                time.sleep(1)
                
                # Close the thread handle
                kernel32.CloseHandle(thread_handle)
                
                logger.info("DLL injection successful")
                return True
                
            finally:
                # Close the process handle
                kernel32.CloseHandle(process_handle)
                
        except Exception as e:
            logger.error(f"Error during DLL injection: {e}")
            return False
    
    def run_injection(self):
        """Find the game process and inject the DLL"""
        pid = self.find_game_process()
        if pid:
            return self.inject_dll(pid)
        else:
            logger.error("Cannot inject: game not running")
            return False


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import psutil
    except ImportError:
        print("Error: psutil module not found. Please install it using:")
        print("pip install psutil")
        sys.exit(1)
        
    injector = FC3Injector()
    injector.run_injection()