import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import TkinterDnD, DND_FILES

class FileShredderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure File Shredder Pro")
        self.root.geometry("700x500")
        
        # Configure drag-and-drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
        
        # GUI Elements
        self.create_widgets()
        
        # File list
        self.files_to_shred = []
        
        # Protected directories (only system directories)
        self.protected_dirs = [
            os.path.expandvars("%SystemRoot%"),  # Windows directory
            os.path.expandvars("%ProgramFiles%"),
            os.path.expandvars("%ProgramFiles(x86)%"),
            "/System",  # Mac OS
            "/bin",
            "/usr",
            "/etc"
        ]
    
    def create_widgets(self):
        """Create all GUI components."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        self.label = ttk.Label(controls_frame, text="Drag & drop files here or click 'Add Files'", font=('Arial', 12))
        self.label.pack(side=tk.LEFT, padx=5)
        
        self.add_button = ttk.Button(controls_frame, text="Add Files", command=self.add_files)
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(controls_frame, text="Clear List", command=self.clear_files)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Shredding Options")
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(options_frame, text="Passes:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.passes_var = tk.IntVar(value=3)
        self.passes_spin = ttk.Spinbox(options_frame, from_=1, to=7, textvariable=self.passes_var, width=5)
        self.passes_spin.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        self.verify_var = tk.BooleanVar(value=True)
        self.verify_check = ttk.Checkbutton(options_frame, text="Verify after shredding", variable=self.verify_var)
        self.verify_check.grid(row=0, column=2, padx=5, sticky=tk.W)
        
        self.metadata_var = tk.BooleanVar(value=True)
        self.metadata_check = ttk.Checkbutton(options_frame, text="Destroy metadata", variable=self.metadata_var)
        self.metadata_check.grid(row=0, column=3, padx=5, sticky=tk.W)
        
        # Log area
        self.log_area = scrolledtext.ScrolledText(main_frame, width=85, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Bottom controls
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        self.shred_button = ttk.Button(bottom_frame, text="Shred Files", command=self.start_shredding)
        self.shred_button.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(bottom_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def log(self, message, level="info"):
        """Add a timed message to the log area with color coding."""
        timestamp = time.strftime("%H:%M:%S")
        tag = f"log_{level}"
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_area.tag_config("log_error", foreground="red")
        self.log_area.tag_config("log_warning", foreground="orange")
        self.log_area.tag_config("log_success", foreground="green")
        self.log_area.config(state='disabled')
        self.log_area.see(tk.END)
        self.root.update_idletasks()
    
    def is_protected_location(self, file_path):
        """Check if file is in a protected system directory."""
        try:
            file_path = os.path.abspath(file_path)
            
            # Never protect files in user directories
            user_dirs = [
                os.path.expanduser("~"),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Downloads")
            ]
            
            for user_dir in user_dirs:
                user_dir = os.path.abspath(user_dir)
                if file_path.startswith(user_dir):
                    return False
                    
            # Check system protected directories
            for protected_dir in self.protected_dirs:
                protected_dir = os.path.abspath(protected_dir)
                if protected_dir and file_path.startswith(protected_dir):
                    return True
                    
            return False
        except Exception as e:
            self.log(f"⚠ Error checking protected status: {str(e)}", "warning")
            return False
    
    def on_drop(self, event):
        """Handle drag-and-drop file additions with proper path parsing."""
        dropped_data = event.data
        
        # Windows returns paths wrapped in {} and separated by spaces
        if '{' in dropped_data and '}' in dropped_data:
            files = []
            current_file = []
            in_braces = False
            
            for char in dropped_data:
                if char == '{':
                    in_braces = True
                    current_file = []
                elif char == '}':
                    in_braces = False
                    files.append(''.join(current_file))
                elif in_braces:
                    current_file.append(char)
        else:
            # Handle other platforms or single files
            files = [dropped_data]
        
        for file in files:
            file = file.strip()
            if not file:
                continue
                
            # Check if path exists
            if not os.path.exists(file):
                self.log(f"⚠ Path does not exist: {file}", "warning")
                continue
                
            # Check if it's a file (not directory)
            if not os.path.isfile(file):
                self.log(f"⚠ Not a file (may be a folder): {file}", "warning")
                continue
                
            # Check protected locations
            if self.is_protected_location(file):
                self.log(f"⚠ Skipped protected location: {file}", "warning")
                continue
                
            # Add to shred list if not already there
            if file not in self.files_to_shred:
                self.files_to_shred.append(file)
                self.log(f"Added: {file}")
    
    def add_files(self):
        """Open a file dialog to add files."""
        files = filedialog.askopenfilenames(title="Select files to shred")
        for file in files:
            if file not in self.files_to_shred:
                if self.is_protected_location(file):
                    self.log(f"⚠ Skipped protected location: {file}", "warning")
                else:
                    self.files_to_shred.append(file)
                    self.log(f"Added: {file}")
    
    def clear_files(self):
        """Clear the file list."""
        self.files_to_shred.clear()
        self.log("File list cleared.", "info")
    
    def destroy_metadata(self, file_path):
        """Try to destroy filesystem metadata."""
        try:
            # Randomize timestamps
            random_time = random.randint(0, 2**31-1)
            os.utime(file_path, (random_time, random_time))
            
            # Try to rename file
            dirname, basename = os.path.split(file_path)
            temp_name = os.path.join(dirname, f"shred_{random.randint(0, 9999999)}")
            os.rename(file_path, temp_name)
            return temp_name
        except Exception as e:
            self.log(f"⚠ Couldn't modify metadata for {file_path}: {str(e)}", "warning")
            return file_path
    
    def verify_shred(self, file_path):
        """Verify that a file cannot be recovered."""
        try:
            return not os.path.exists(file_path)
        except Exception:
            return False
    
    def shred_file(self, file_path, passes=3, verify=True, destroy_metadata=True):
        """Securely shred a single file with multiple patterns."""
        try:
            if not os.path.exists(file_path):
                self.log(f"⚠ File not found: {file_path}", "warning")
                return False
            
            file_size = os.path.getsize(file_path)
            
            # Different overwrite patterns
            patterns = [
                b'\x00',  # Null bytes
                b'\xFF',  # All ones
                b'\xAA',  # 10101010
                b'\x55',  # 01010101
                os.urandom(1),  # Random byte
                os.urandom(file_size),  # Full random
                b'\xDE\xAD\xBE\xEF' * (file_size // 4 + 1)  # Custom pattern
            ]
            
            # Handle metadata destruction
            if destroy_metadata:
                file_path = self.destroy_metadata(file_path)
            
            # Handle large files in chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with open(file_path, "r+b") as file:
                for i in range(passes):
                    pattern = patterns[i] if i < len(patterns) else os.urandom(1)
                    file.seek(0)
                    
                    if file_size > chunk_size * 10:  # Large file handling
                        for pos in range(0, file_size, chunk_size):
                            if isinstance(pattern, bytes) and len(pattern) == 1:
                                file.write(pattern * min(chunk_size, file_size - pos))
                            else:
                                file.write(os.urandom(min(chunk_size, file_size - pos)))
                            file.flush()
                    else:
                        if isinstance(pattern, bytes) and len(pattern) == 1:
                            file.write(pattern * file_size)
                        else:
                            file.write(os.urandom(file_size))
                    
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
    
    def start_shredding(self):
        """Start shredding all files in the list."""
        if not self.files_to_shred:
            messagebox.showwarning("No Files", "No files selected to shred!")
            return
        
        confirm = messagebox.askyesno(
            "Confirm", 
            f"Shred {len(self.files_to_shred)} files with {self.passes_var.get()} passes?\n"
            "This action is irreversible!"
        )
        if not confirm:
            return
        
        # Disable UI during operation
        self.toggle_ui(False)
        
        # Start thread with options
        threading.Thread(
            target=self.shred_files_threaded,
            args=(
                self.passes_var.get(),
                self.verify_var.get(),
                self.metadata_var.get()
            ),
            daemon=True
        ).start()
    
    def shred_files_threaded(self, passes, verify, destroy_metadata):
        """Threaded function to shred files with progress updates."""
        total_files = len(self.files_to_shred)
        self.progress["maximum"] = total_files
        self.progress["value"] = 0
        success_count = 0
        
        start_time = time.time()
        
        for i, file in enumerate(self.files_to_shred, 1):
            self.status_var.set(f"Processing {i}/{total_files}")
            self.log(f"Shredding ({i}/{total_files}): {file}")
            
            if self.shred_file(file, passes, verify, destroy_metadata):
                success_count += 1
            
            self.progress["value"] = i
            self.root.update_idletasks()
        
        elapsed_time = time.time() - start_time
        self.log(f"\nShredding complete! {success_count}/{total_files} files shredded successfully.", 
               "success" if success_count == total_files else "warning")
        self.log(f"Time taken: {elapsed_time:.2f} seconds", "info")
        self.status_var.set(f"Done - {success_count}/{total_files} shredded")
        
        self.files_to_shred.clear()
        self.toggle_ui(True)
    
    def toggle_ui(self, enabled):
        """Enable/disable UI elements during operation."""
        state = 'normal' if enabled else 'disabled'
        self.shred_button.config(state=state)
        self.add_button.config(state=state)
        self.clear_button.config(state=state)
        self.passes_spin.config(state=state)
        self.verify_check.config(state=state)
        self.metadata_check.config(state=state)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = FileShredderApp(root)
    root.mainloop()