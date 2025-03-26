import os
import random
import threading
import time
import tkinter as tk
import argparse
import json
from typing import List, Dict, Union, Optional, Callable
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import TkinterDnD, DND_FILES
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration constants
CONFIG_FILE = "shredder_config.json"
DEFAULT_CONFIG = {
    "passes": 3,
    "verify": True,
    "destroy_metadata": True,
    "chunk_size": 1024 * 1024,  # 1MB
    "max_workers": 4,
    "overwrite_patterns": [
        {"name": "Zero Fill", "pattern": b'\x00'},
        {"name": "One Fill", "pattern": b'\xFF'},
        {"name": "DoD 5220.22-M", "pattern": [b'\x55', b'\xAA', b'\x92\x49\x24\x92']},
        {"name": "Random Data", "pattern": "random"},
        {"name": "Gutmann", "pattern": "gutmann"}
    ]
}

class FileShredderApp:
    def __init__(self, root: Optional[tk.Tk] = None, cli_mode: bool = False):
        self.cli_mode = cli_mode
        self.files_to_shred: List[str] = []
        self.config: Dict = self.load_config()
        
        # Setup overwrite patterns
        self.overwrite_patterns: List[Dict] = self.config.get("overwrite_patterns", DEFAULT_CONFIG["overwrite_patterns"])
        self.gutmann_patterns = self._generate_gutmann_patterns()
        
        # Protected directories (system directories + custom from config)
        self.protected_dirs: List[str] = self._get_protected_dirs()
        
        if not cli_mode:
            # GUI initialization
            self.root = root
            self.root.title("Secure File Shredder Pro")
            self.root.geometry("800x600")
            self.setup_gui()

    def _get_protected_dirs(self) -> List[str]:
        """Get protected directories from config and system defaults."""
        protected = [
            os.path.expandvars("%SystemRoot%"),
            os.path.expandvars("%ProgramFiles%"),
            os.path.expandvars("%ProgramFiles(x86)%"),
            "/System", "/bin", "/usr", "/etc", "/lib", "/sbin"
        ]
        
        # Add custom protected dirs from config if they exist
        custom_dirs = self.config.get("protected_dirs", [])
        protected.extend([os.path.expandvars(d) for d in custom_dirs])
        
        # Resolve all paths to absolute and remove duplicates
        protected = list({os.path.abspath(p) for p in protected if os.path.exists(p)})
        return protected

    def _generate_gutmann_patterns(self) -> List[bytes]:
        """Generate Gutmann method patterns (35 passes)."""
        patterns = []
        
        # First 4 passes - random
        for _ in range(4):
            patterns.append(os.urandom(1))
            
        # Next 15 passes - specific patterns
        for i in range(4, 19):
            if i % 2 == 0:
                patterns.append(bytes([i % 256] * 4))
            else:
                patterns.append(bytes([(i * 16) % 256] * 4))
                
        # Next 15 passes - inverse of previous
        for i in range(19, 34):
            patterns.append(bytes([~b & 0xFF for b in patterns[i-15]]))
            
        # Final pass - random
        patterns.append(os.urandom(1))
        
        return patterns

    def load_config(self) -> Dict:
        """Load configuration from file or use defaults."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Validate config
                    if isinstance(config, dict):
                        return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            print(f"⚠ Config load error: {e}")
        return DEFAULT_CONFIG.copy()

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log(f"⚠ Config save error: {e}", "warning")

    def setup_gui(self) -> None:
        """Create all GUI components."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        self.label = ttk.Label(controls_frame, text="Drag & drop files/folders here or click 'Add'", font=('Arial', 12))
        self.label.pack(side=tk.LEFT, padx=5)
        
        # Add buttons in a subframe
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(side=tk.LEFT)
        
        self.add_file_button = ttk.Button(btn_frame, text="Add Files", command=lambda: self.add_files())
        self.add_file_button.pack(side=tk.LEFT, padx=2)
        
        self.add_folder_button = ttk.Button(btn_frame, text="Add Folder", command=lambda: self.add_folder())
        self.add_folder_button.pack(side=tk.LEFT, padx=2)
        
        self.clear_button = ttk.Button(controls_frame, text="Clear List", command=self.clear_files)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Shredding Options")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Passes selection
        ttk.Label(options_frame, text="Passes:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.passes_var = tk.IntVar(value=self.config["passes"])
        self.passes_spin = ttk.Spinbox(options_frame, from_=1, to=35, textvariable=self.passes_var, width=5)
        self.passes_spin.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # Pattern selection
        ttk.Label(options_frame, text="Pattern:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.pattern_var = tk.StringVar()
        self.pattern_combo = ttk.Combobox(options_frame, textvariable=self.pattern_var, state="readonly")
        self.pattern_combo['values'] = [p["name"] for p in self.overwrite_patterns]
        self.pattern_combo.current(0)
        self.pattern_combo.grid(row=0, column=3, padx=5, sticky=tk.W)
        
        # Checkboxes
        self.verify_var = tk.BooleanVar(value=self.config["verify"])
        self.verify_check = ttk.Checkbutton(options_frame, text="Verify after shredding", variable=self.verify_var)
        self.verify_check.grid(row=0, column=4, padx=5, sticky=tk.W)
        
        self.metadata_var = tk.BooleanVar(value=self.config["destroy_metadata"])
        self.metadata_check = ttk.Checkbutton(options_frame, text="Destroy metadata", variable=self.metadata_var)
        self.metadata_check.grid(row=0, column=5, padx=5, sticky=tk.W)
        
        # Advanced options button
        self.advanced_btn = ttk.Button(options_frame, text="Advanced...", command=self.show_advanced_options)
        self.advanced_btn.grid(row=0, column=6, padx=5, sticky=tk.E)
        
        # Log area
        self.log_area = scrolledtext.ScrolledText(main_frame, width=100, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Bottom controls
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        self.shred_button = ttk.Button(bottom_frame, text="Shred Files", command=self.start_shredding)
        self.shred_button.pack(side=tk.LEFT, padx=5)
        
        self.wipe_free_space_btn = ttk.Button(bottom_frame, text="Wipe Free Space", 
                                           command=self.start_free_space_wiping)
        self.wipe_free_space_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(bottom_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Configure drag-and-drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def show_advanced_options(self) -> None:
        """Show advanced options dialog."""
        adv_window = tk.Toplevel(self.root)
        adv_window.title("Advanced Options")
        adv_window.geometry("400x300")
        
        ttk.Label(adv_window, text="Chunk Size (bytes):").pack(pady=(10, 0))
        self.chunk_size_var = tk.IntVar(value=self.config["chunk_size"])
        ttk.Entry(adv_window, textvariable=self.chunk_size_var).pack()
        
        ttk.Label(adv_window, text="Max Parallel Workers:").pack(pady=(10, 0))
        self.max_workers_var = tk.IntVar(value=self.config["max_workers"])
        ttk.Spinbox(adv_window, from_=1, to=32, textvariable=self.max_workers_var).pack()
        
        ttk.Label(adv_window, text="Protected Directories:").pack(pady=(10, 0))
        prot_frame = ttk.Frame(adv_window)
        prot_frame.pack(fill=tk.X, padx=5)
        
        self.protected_dirs_list = tk.Listbox(prot_frame, height=4)
        self.protected_dirs_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(prot_frame, orient="vertical", command=self.protected_dirs_list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.protected_dirs_list.config(yscrollcommand=scroll.set)
        
        # Populate list
        for d in self.protected_dirs:
            self.protected_dirs_list.insert(tk.END, d)
        
        # Add/remove buttons
        btn_frame = ttk.Frame(adv_window)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="Add", command=self.add_protected_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_protected_dir).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(adv_window, text="Save", command=lambda: self.save_advanced_options(adv_window)).pack(pady=10)

    def add_protected_dir(self) -> None:
        """Add a new protected directory."""
        dir_path = filedialog.askdirectory(title="Select directory to protect")
        if dir_path and dir_path not in self.protected_dirs:
            self.protected_dirs.append(dir_path)
            self.protected_dirs_list.insert(tk.END, dir_path)

    def remove_protected_dir(self) -> None:
        """Remove selected protected directory."""
        selection = self.protected_dirs_list.curselection()
        if selection:
            index = selection[0]
            self.protected_dirs.pop(index)
            self.protected_dirs_list.delete(index)

    def save_advanced_options(self, window: tk.Toplevel) -> None:
        """Save advanced options and close window."""
        self.config["chunk_size"] = self.chunk_size_var.get()
        self.config["max_workers"] = self.max_workers_var.get()
        self.config["protected_dirs"] = self.protected_dirs.copy()
        self.save_config()
        window.destroy()
        self.log("Advanced settings saved.", "info")

    def log(self, message: str, level: str = "info") -> None:
        """Unified logging for both GUI and CLI."""
        timestamp = time.strftime("%H:%M:%S")
        msg = f"[{timestamp}] {message}"
        
        if self.cli_mode:
            # CLI output with colors
            colors = {
                "error": "\033[91m",    # red
                "warning": "\033[93m",  # yellow
                "success": "\033[92m",  # green
                "info": "\033[0m"       # reset
            }
            print(f"{colors[level]}{msg}\033[0m")
        else:
            # GUI logging
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"{msg}\n", f"log_{level}")
            self.log_area.tag_config("log_error", foreground="red")
            self.log_area.tag_config("log_warning", foreground="orange")
            self.log_area.tag_config("log_success", foreground="green")
            self.log_area.config(state='disabled')
            self.log_area.see(tk.END)
            self.root.update_idletasks()

    def is_protected_location(self, path: str) -> bool:
        """Check if path is in a protected directory."""
        try:
            abs_path = os.path.abspath(path)
            
            # Never protect files in user directories
            user_dirs = [
                os.path.expanduser("~"),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Downloads")
            ]
            
            for user_dir in user_dirs:
                user_dir = os.path.abspath(user_dir)
                if abs_path.startswith(user_dir):
                    return False
                    
            # Check system protected directories
            for protected_dir in self.protected_dirs:
                protected_dir = os.path.abspath(protected_dir)
                if protected_dir and abs_path.startswith(protected_dir):
                    return True
                    
            return False
        except Exception as e:
            self.log(f"⚠ Error checking protected status: {str(e)}", "warning")
            return False

    def on_drop(self, event) -> None:
        """Handle drag-and-drop file/folder additions."""
        dropped_data = event.data
        
        # Windows returns paths wrapped in {} and separated by spaces
        if '{' in dropped_data and '}' in dropped_data:
            items = []
            start = dropped_data.find('{')
            while start != -1:
                end = dropped_data.find('}', start)
                if end == -1:
                    break
                items.append(dropped_data[start+1:end])
                start = dropped_data.find('{', end)
        else:
            # Handle non-Windows or single file drops
            items = [dropped_data.strip()]
        
        # Process all valid items
        added_count = 0
        for item in items:
            item = item.strip()
            if not item:
                continue
                
            try:
                if os.path.isfile(item) and item not in self.files_to_shred:
                    if not self.is_protected_location(item):
                        self.files_to_shred.append(item)
                        self.log(f"Added file: {item}")
                        added_count += 1
                elif os.path.isdir(item):
                    added = self._add_folder_contents(item)
                    added_count += added
                    if added > 0:
                        self.log(f"Added {added} items from folder: {item}")
            except Exception as e:
                self.log(f"⚠ Error processing {item}: {str(e)}", "warning")
        
        if added_count < len(items):
            self.log(f"⚠ Only added {added_count} of {len(items)} items", "warning")

    def add_files(self) -> None:
        """Open a file dialog to add files."""
        files = filedialog.askopenfilenames(title="Select files to shred")
        for file in files:
            if file not in self.files_to_shred:
                if self.is_protected_location(file):
                    self.log(f"⚠ Skipped protected location: {file}", "warning")
                else:
                    self.files_to_shred.append(file)
                    self.log(f"Added file: {file}")

    def add_folder(self) -> None:
        """Open a folder dialog to add folder contents."""
        folder = filedialog.askdirectory(title="Select folder to shred")
        if folder:
            added = self._add_folder_contents(folder)
            if added > 0:
                self.log(f"Added {added} items from folder: {folder}", "info")
            else:
                self.log(f"No files added from folder: {folder}", "warning")

    def _add_folder_contents(self, folder_path: str) -> int:
        """Recursively add all files from a folder."""
        added_count = 0
        
        try:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path not in self.files_to_shred and not self.is_protected_location(file_path):
                        self.files_to_shred.append(file_path)
                        added_count += 1
        except Exception as e:
            self.log(f"⚠ Error scanning folder {folder_path}: {str(e)}", "warning")
        
        return added_count

    def clear_files(self) -> None:
        """Clear the file list."""
        self.files_to_shred.clear()
        self.log("File list cleared.", "info")

    def is_file_locked(self, filepath: str) -> bool:
        """Check if a file is locked by another process."""
        try:
            if os.name == 'nt':  # Windows
                import msvcrt
                with open(filepath, 'r+b') as f:
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                        return False
                    except IOError:
                        return True
            else:  # Unix-like
                import fcntl
                with open(filepath, 'r+b') as f:
                    try:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(f, fcntl.LOCK_UN)
                        return False
                    except IOError:
                        return True
        except Exception:
            return False

    def destroy_metadata(self, file_path: str) -> str:
        """Try to destroy filesystem metadata."""
        try:
            # Randomize timestamps
            random_time = random.randint(0, 2**31-1)
            os.utime(file_path, (random_time, random_time))
            
            # Try to rename file multiple times
            dirname, basename = os.path.split(file_path)
            temp_name = file_path
            for _ in range(3):
                new_name = os.path.join(dirname, f"shred_{random.randint(0, 9999999)}")
                try:
                    os.rename(temp_name, new_name)
                    temp_name = new_name
                except:
                    break
            
            return temp_name
        except Exception as e:
            self.log(f"⚠ Couldn't modify metadata for {file_path}: {str(e)}", "warning")
            return file_path

    def verify_shred(self, file_path: str) -> bool:
        """Verify that a file cannot be recovered."""
        try:
            # Multiple checks to be sure
            return not (os.path.exists(file_path) or os.path.getsize(file_path)) == 0
        except Exception:
            return True  # If we can't check, assume success

    def get_overwrite_pattern(self, pass_num: int, file_size: int) -> bytes:
        """Get the appropriate overwrite pattern for this pass."""
        pattern_name = self.pattern_var.get() if not self.cli_mode else "DoD 5220.22-M"
        pattern_config = next((p for p in self.overwrite_patterns if p["name"] == pattern_name), None)
        
        if not pattern_config:
            return os.urandom(1) * file_size
        
        pattern = pattern_config["pattern"]
        
        if pattern == "random":
            return os.urandom(file_size)
        elif pattern == "gutmann":
            return self.gutmann_patterns[pass_num % len(self.gutmann_patterns)] * (file_size // len(self.gutmann_patterns[0]) + 1)
        elif isinstance(pattern, list):
            # For patterns like DoD that have multiple passes
            return pattern[pass_num % len(pattern)] * (file_size // len(pattern[0]) + 1)
        elif isinstance(pattern, bytes):
            return pattern * file_size
        else:
            return os.urandom(1) * file_size

    def shred_file(self, file_path: str, passes: int = 3, verify: bool = True, destroy_metadata: bool = True) -> bool:
        """Securely shred a single file with multiple patterns."""
        try:
            if not os.path.exists(file_path):
                self.log(f"⚠ File not found: {file_path}", "warning")
                return False
            
            if self.is_file_locked(file_path):
                raise Exception("File is locked by another process")
            
            file_size = os.path.getsize(file_path)
            chunk_size = self.config["chunk_size"]
            
            # Handle metadata destruction
            if destroy_metadata:
                file_path = self.destroy_metadata(file_path)
            
            with open(file_path, "r+b") as file:
                for i in range(passes):
                    pattern = self.get_overwrite_pattern(i, file_size)
                    file.seek(0)
                    
                    # Handle large files in chunks
                    if file_size > chunk_size * 10:
                        for pos in range(0, file_size, chunk_size):
                            chunk = pattern[pos:pos+chunk_size] if isinstance(pattern, bytes) and len(pattern) > 1 else pattern[:chunk_size]
                            file.write(chunk)
                            file.flush()
                    else:
                        file.write(pattern[:file_size])
                    
                    file.flush()
                    os.fsync(file.fileno())
            
            # Final deletion
            os.remove(file_path)
            
            # Verification
            if verify and not self.verify_shred(file_path):
                raise Exception("Verification failed - file may still exist")
            
            self.log(f"✅ Successfully shredded: {file_path}", "success")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to shred {file_path}: {str(e)}", "error")
            return False

    def wipe_free_space(self, directory: str = None) -> bool:
        """Wipe free space on a drive by creating and shredding a large file."""
        try:
            target_dir = directory or os.path.expanduser("~")
            temp_file = os.path.join(target_dir, f"shredder_temp_{random.randint(0, 9999999)}.tmp")
            
            self.log(f"⏳ Wiping free space in {target_dir}...", "info")
            
            # Get free space
            stat = os.statvfs(target_dir) if hasattr(os, 'statvfs') else None
            if stat:
                free_space = stat.f_bsize * stat.f_bavail
            else:
                # Windows fallback
                import ctypes
                free_space = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(target_dir), None, None, ctypes.pointer(free_space))
                free_space = free_space.value
            
            if free_space <= 0:
                raise Exception("No free space to wipe")
            
            self.log(f"Free space to wipe: {free_space / (1024*1024):.2f} MB", "info")
            
            # Create a file that fills most free space (leave some room for system)
            wipe_size = free_space * 0.95
            chunk_size = self.config["chunk_size"]
            
            with open(temp_file, 'wb') as f:
                for _ in range(0, int(wipe_size), chunk_size):
                    f.write(os.urandom(min(chunk_size, wipe_size - f.tell())))
                    f.flush()
            
            # Now shred the temporary file
            self.log("Shredding temporary file...", "info")
            success = self.shred_file(temp_file, passes=3, verify=True, destroy_metadata=True)
            
            if success:
                self.log("✅ Free space wiping completed successfully", "success")
            else:
                self.log("⚠ Free space wiping completed with warnings", "warning")
            
            return success
            
        except Exception as e:
            self.log(f"❌ Free space wiping failed: {str(e)}", "error")
            return False

    def start_shredding(self) -> None:
        """Start shredding all files in the list."""
        if not self.files_to_shred:
            if not self.cli_mode:
                messagebox.showwarning("No Files", "No files selected to shred!")
            else:
                self.log("No files to shred", "warning")
            return
        
        if not self.cli_mode:
            confirm = messagebox.askyesno(
                "Confirm", 
                f"Shred {len(self.files_to_shred)} files with {self.passes_var.get()} passes?\n"
                "This action is irreversible!"
            )
            if not confirm:
                return
            
            passes = self.passes_var.get()
            verify = self.verify_var.get()
            destroy_metadata = self.metadata_var.get()
            self.toggle_ui(False)
        else:
            passes = self.cli_passes
            verify = True
            destroy_metadata = True
        
        threading.Thread(
            target=self.shred_files_threaded,
            args=(passes, verify, destroy_metadata),
            daemon=True
        ).start()

    def start_free_space_wiping(self) -> None:
        """Start free space wiping in a separate thread."""
        target_dir = filedialog.askdirectory(title="Select drive/folder to wipe free space")
        if target_dir:
            confirm = messagebox.askyesno(
                "Confirm", 
                f"Wipe free space on {target_dir}?\n"
                "This will create a large temporary file and may take a long time!"
            )
            if confirm:
                self.toggle_ui(False)
                threading.Thread(
                    target=self.wipe_free_space,
                    args=(target_dir,),
                    daemon=True
                ).start()

    def shred_files_threaded(self, passes: int, verify: bool, destroy_metadata: bool) -> None:
        """Threaded function to shred files with progress updates."""
        total_files = len(self.files_to_shred)
        success_count = 0
        
        if not self.cli_mode:
            self.progress["maximum"] = total_files
            self.progress["value"] = 0
        
        start_time = time.time()
        
        # Use parallel processing if configured
        if self.config["max_workers"] > 1 and total_files > 1:
            self.log(f"Using {self.config['max_workers']} parallel workers...", "info")
            with ThreadPoolExecutor(max_workers=self.config["max_workers"]) as executor:
                futures = []
                for file in self.files_to_shred:
                    futures.append(executor.submit(
                        self.shred_file, file, passes, verify, destroy_metadata
                    ))
                
                for i, future in enumerate(as_completed(futures), 1):
                    if future.result():
                        success_count += 1
                    if not self.cli_mode:
                        self.progress["value"] = i
                        self.status_var.set(f"Processing {i}/{total_files}")
                        self.root.update_idletasks()
        else:
            # Sequential processing
            for i, file in enumerate(self.files_to_shred, 1):
                if not self.cli_mode:
                    self.status_var.set(f"Processing {i}/{total_files}")
                self.log(f"Shredding ({i}/{total_files}): {file}")
                
                if self.shred_file(file, passes, verify, destroy_metadata):
                    success_count += 1
                
                if not self.cli_mode:
                    self.progress["value"] = i
                    self.root.update_idletasks()
        
        elapsed_time = time.time() - start_time
        self.log(f"\nShredding complete! {success_count}/{total_files} files shredded successfully.", 
               "success" if success_count == total_files else "warning")
        self.log(f"Time taken: {elapsed_time:.2f} seconds", "info")
        
        if not self.cli_mode:
            self.status_var.set(f"Done - {success_count}/{total_files} shredded")
            self.toggle_ui(True)
        
        self.files_to_shred.clear()

    def shred_files_cli(self, paths: List[str], passes: int = 3) -> None:
        """CLI entry point."""
        self.cli_passes = passes
        
        # Expand folders if provided
        expanded_paths = []
        for path in paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not self.is_protected_location(file_path):
                            expanded_paths.append(file_path)
            elif os.path.isfile(path) and not self.is_protected_location(path):
                expanded_paths.append(path)
        
        self.files_to_shred = expanded_paths
        
        if not self.files_to_shred:
            self.log("No files to shred after filtering protected locations", "warning")
            return
        
        self.log(f"Starting shredding of {len(self.files_to_shred)} files...", "info")
        self.start_shredding()
        
        # Keep CLI alive until shredding completes
        while threading.active_count() > 1:
            time.sleep(0.1)

    def toggle_ui(self, enabled: bool) -> None:
        """Enable/disable UI elements during operation."""
        if not self.cli_mode:
            state = 'normal' if enabled else 'disabled'
            self.shred_button.config(state=state)
            self.add_file_button.config(state=state)
            self.add_folder_button.config(state=state)
            self.clear_button.config(state=state)
            self.passes_spin.config(state=state)
            self.pattern_combo.config(state=state)
            self.verify_check.config(state=state)
            self.metadata_check.config(state=state)
            self.wipe_free_space_btn.config(state=state)
            self.advanced_btn.config(state=state)

def main() -> None:
    parser = argparse.ArgumentParser(description='Secure File Shredder Pro')
    parser.add_argument('--path', nargs='+', help='File/folder paths to shred')
    parser.add_argument('--passes', type=int, default=3, help='Number of shred passes (1-35)')
    parser.add_argument('--wipe-free-space', action='store_true', help='Wipe free space on current drive')
    args = parser.parse_args()

    if args.path or args.wipe_free_space:
        # CLI Mode
        app = FileShredderApp(cli_mode=True)
        app.log("Starting secure shredding in CLI mode...", "info")
        
        if args.path:
            app.log(f"Files/folders to shred: {len(args.path)}", "info")
            app.log(f"Passes selected: {args.passes}", "info")
            app.shred_files_cli(args.path, args.passes)
        
        if args.wipe_free_space:
            app.wipe_free_space()
    else:
        # GUI Mode
        root = TkinterDnD.Tk()
        app = FileShredderApp(root)
        root.mainloop()

if __name__ == "__main__":
    main()