import os
import sys
import subprocess
import time
import configparser
import ctypes
from ctypes import wintypes
import traceback
import platform

# Current date and time: 2025-05-03 09:55:57
# Current user: Saviru

def inject_dll():
    """Inject the DLL into Far Cry 3 process"""
    # Load configuration
    config = configparser.ConfigParser()
    if os.path.exists('fc3_multiplayer.ini'):
        config.read('fc3_multiplayer.ini')
    
    # Use the game path from config or default to the provided path
    game_path = config.get('DEFAULT', 'game_path', fallback=r'C:\Games\Far Cry 3\Far Cry 3\bin\farcry3.exe')
    game_dir = os.path.dirname(game_path)
    
    # Get the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.abspath(os.path.join(current_dir, 'fc3_multiplayer.dll'))
    
    # Log the injection attempt
    with open("injection_log.txt", "a") as log:
        log.write(f"[2025-05-03 09:55:57] User Saviru attempting to inject {dll_path} into {game_path}\n")
    
    # Check if DLL exists
    if not os.path.exists(dll_path):
        error_msg = f"Error: DLL not found at {dll_path}"
        print(error_msg)
        with open("injection_log.txt", "a") as log:
            log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
        return False
    
    # Check if game executable exists
    if not os.path.exists(game_path):
        error_msg = f"Error: Game executable not found at {game_path}"
        print(error_msg)
        with open("injection_log.txt", "a") as log:
            log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
        return False
    
    # Check if game is already running
    game_running = False
    game_pid = None
    try:
        result = subprocess.run(['tasklist', '/fi', 'imagename eq farcry3.exe', '/fo', 'csv', '/nh'], 
                               capture_output=True, text=True)
        if 'farcry3.exe' in result.stdout:
            game_running = True
            try:
                game_pid = int(result.stdout.split(',')[1].strip('"'))
                print(f"Found running Far Cry 3 with PID: {game_pid}")
            except:
                pass
    except Exception as e:
        print(f"Error checking if game is running: {e}")
    
    # If game is not running, start it
    if not game_running:
        try:
            print(f"Starting Far Cry 3 from {game_path}")
            
            # Create the process with CREATE_SUSPENDED flag to inject before it fully starts
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = 1  # SW_SHOWNORMAL
            
            # Start the game process
            process = subprocess.Popen([game_path], 
                                      cwd=game_dir, 
                                      startupinfo=startup_info,
                                      creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            game_pid = process.pid
            print(f"Started Far Cry 3 with PID: {game_pid}")
            
            # Wait a bit for the process to initialize
            time.sleep(2)
            
            # Verify the process is still running
            if process.poll() is not None:
                error_msg = f"Error: Game process terminated with code {process.returncode}"
                print(error_msg)
                with open("injection_log.txt", "a") as log:
                    log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
                return False
            
        except Exception as e:
            error_msg = f"Error starting game: {e}"
            print(error_msg)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
                log.write(f"Traceback: {traceback.format_exc()}\n")
            return False
    else:
        print("Far Cry 3 is already running")
    
    # Now inject the DLL - Fixed for 64-bit compatibility
    try:
        if game_pid is None:
            error_msg = "Error: Cannot determine Far Cry 3 process ID"
            print(error_msg)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        print(f"Injecting DLL into process {game_pid}")
        
        # ---- NEW CODE: Alternative Injection Method using Windows API Directly ----
        is_64bit = platform.architecture()[0] == '64bit'
        print(f"Python architecture: {'64-bit' if is_64bit else '32-bit'}")
        
        # Create fixed function prototypes to handle addresses correctly
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # Define correct argument types
        OpenProcess = kernel32.OpenProcess
        OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        OpenProcess.restype = wintypes.HANDLE
        
        VirtualAllocEx = kernel32.VirtualAllocEx
        VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, 
                                  wintypes.DWORD, wintypes.DWORD]
        VirtualAllocEx.restype = wintypes.LPVOID
        
        WriteProcessMemory = kernel32.WriteProcessMemory
        WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, 
                                      ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        WriteProcessMemory.restype = wintypes.BOOL
        
        # Fix for CreateRemoteThread - explicitly define argument types
        CreateRemoteThread = kernel32.CreateRemoteThread
        CreateRemoteThread.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, 
                                      wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, 
                                      wintypes.LPDWORD]
        CreateRemoteThread.restype = wintypes.HANDLE
        
        WaitForSingleObject = kernel32.WaitForSingleObject
        WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        WaitForSingleObject.restype = wintypes.DWORD
        
        CloseHandle = kernel32.CloseHandle
        CloseHandle.argtypes = [wintypes.HANDLE]
        CloseHandle.restype = wintypes.BOOL
        
        GetProcAddress = kernel32.GetProcAddress
        GetProcAddress.argtypes = [wintypes.HANDLE, ctypes.c_char_p]
        GetProcAddress.restype = wintypes.LPVOID
        
        GetModuleHandleA = kernel32.GetModuleHandleA
        GetModuleHandleA.argtypes = [ctypes.c_char_p]
        GetModuleHandleA.restype = wintypes.HANDLE
        
        # Windows API constants
        PROCESS_ALL_ACCESS = 0x1F0FFF
        MEM_COMMIT = 0x1000
        PAGE_READWRITE = 0x04
        
        # Get a handle to the process
        h_process = OpenProcess(PROCESS_ALL_ACCESS, False, game_pid)
        if not h_process:
            error_msg = f"Error: Failed to open process (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Allocate memory in the process for the DLL path
        dll_path_bytes = (dll_path + '\0').encode('ascii')
        dll_len = len(dll_path_bytes)
        
        dll_addr = VirtualAllocEx(h_process, None, dll_len, MEM_COMMIT, PAGE_READWRITE)
        if not dll_addr:
            error_msg = f"Error: Failed to allocate memory (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Write the DLL path to the allocated memory
        bytes_written = ctypes.c_size_t(0)
        result = WriteProcessMemory(h_process, dll_addr, dll_path_bytes, dll_len, 
                                   ctypes.byref(bytes_written))
        if not result or bytes_written.value != dll_len:
            error_msg = f"Error: Failed to write to process memory (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Find LoadLibraryA address - using proper method for 64-bit compatibility
        h_kernel32 = GetModuleHandleA(b"kernel32.dll")
        if not h_kernel32:
            error_msg = f"Error: Failed to get kernel32 handle (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
            
        load_library_addr = GetProcAddress(h_kernel32, b"LoadLibraryA")
        if not load_library_addr:
            error_msg = f"Error: Failed to get LoadLibraryA address (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Create a remote thread that calls LoadLibraryA with our DLL path
        thread_id = wintypes.DWORD(0)
        thread_h = CreateRemoteThread(h_process, None, 0, load_library_addr, dll_addr, 0, 
                                     ctypes.byref(thread_id))
        
        if not thread_h:
            error_msg = f"Error: Failed to create remote thread (Error code: {ctypes.get_last_error()})"
            print(error_msg)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Wait for the thread to finish
        wait_result = WaitForSingleObject(thread_h, 10000)  # 10 second timeout
        if wait_result != 0:  # WAIT_OBJECT_0
            error_msg = f"Error: Thread execution timed out or failed (Code: {wait_result})"
            print(error_msg)
            CloseHandle(thread_h)
            CloseHandle(h_process)
            with open("injection_log.txt", "a") as log:
                log.write(f"[2025-05-03 09:55:57] ERROR: {error_msg}\n")
            return False
        
        # Clean up
        CloseHandle(thread_h)
        CloseHandle(h_process)
        
        print(f"DLL successfully injected: {dll_path}")
        
        # Log the successful injection
        with open("injection_log.txt", "a") as log:
            log.write(f"[2025-05-03 09:55:57] User Saviru successfully injected {dll_path} into process {game_pid}\n")
        
        return True
    
    except Exception as e:
        error_msg = f"Exception during injection: {e}"
        print(error_msg)
        # Log the error with full traceback
        with open("injection_log.txt", "a") as log:
            log.write(f"[2025-05-03 09:55:57] User Saviru injection error: {str(e)}\n")
            log.write(f"Traceback: {traceback.format_exc()}\n")
        return False

if __name__ == "__main__":
    success = inject_dll()
    sys.exit(0 if success else 1)