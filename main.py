import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import threading
import queue
import traceback
from datetime import datetime

# Attempt to import chardet for encoding detection
try:
    import chardet
except ImportError:
    import subprocess
    import sys
    # Initialize a temporary Tkinter root to show messagebox
    temp_root = tk.Tk()
    temp_root.withdraw()
    response = messagebox.askyesno(
        "Dependency Missing",
        "The 'chardet' library is required for encoding detection but is not installed.\n"
        "Do you want to install it now?"
    )
    if response:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "chardet"])
        import chardet
    else:
        messagebox.showerror(
            "Dependency Missing",
            "Cannot proceed without the 'chardet' library. Exiting application."
        )
        sys.exit(1)


class DatasetCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Scripts to Dataset Creator")
        self.root.geometry("900x600")
        self.root.resizable(True, True)

        # Variables to store user inputs
        self.root_dir_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.overwrite_var = tk.BooleanVar()

        # Queue for thread-safe communication
        self.queue = queue.Queue()
        self.cancel_event = threading.Event()

        self.create_widgets()
        self.poll_queue()

    def create_widgets(self):
        padding_options = {'padx': 10, 'pady': 5}

        # Root Directory Selection
        root_dir_frame = tk.Frame(self.root)
        root_dir_frame.pack(fill='x', **padding_options)

        root_dir_label = tk.Label(root_dir_frame, text="Root Directory:")
        root_dir_label.pack(side='left')

        root_dir_entry = tk.Entry(root_dir_frame, textvariable=self.root_dir_var, width=60)
        root_dir_entry.pack(side='left', padx=5)

        browse_root_button = tk.Button(root_dir_frame, text="Browse", command=self.browse_root_dir)
        browse_root_button.pack(side='left')

        # Tooltip for Root Directory
        self.create_tooltip(browse_root_button, "Select the root directory containing Python scripts.")

        # Output File Selection
        output_file_frame = tk.Frame(self.root)
        output_file_frame.pack(fill='x', **padding_options)

        output_file_label = tk.Label(output_file_frame, text="Output File:")
        output_file_label.pack(side='left')

        output_file_entry = tk.Entry(output_file_frame, textvariable=self.output_file_var, width=60)
        output_file_entry.pack(side='left', padx=5)

        browse_output_button = tk.Button(output_file_frame, text="Browse", command=self.browse_output_file)
        browse_output_button.pack(side='left')

        # Tooltip for Output File
        self.create_tooltip(browse_output_button, "Select the location to save the JSON Lines dataset.")

        # Overwrite Option
        overwrite_frame = tk.Frame(self.root)
        overwrite_frame.pack(fill='x', **padding_options)

        overwrite_check = tk.Checkbutton(overwrite_frame, text="Overwrite if file exists", variable=self.overwrite_var)
        overwrite_check.pack(side='left')

        # Tooltip for Overwrite Option
        self.create_tooltip(overwrite_check, "Check to overwrite the output file if it already exists.")

        # Start and Cancel Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill='x', pady=10)

        self.start_button = tk.Button(
            button_frame,
            text="Start Creating Dataset",
            command=self.start_processing,
            bg='green',
            fg='white',
            width=20
        )
        self.start_button.pack(side='left', padx=10)

        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_processing,
            bg='red',
            fg='white',
            state='disabled',
            width=10
        )
        self.cancel_button.pack(side='left', padx=10)

        # Tooltip for Start and Cancel Buttons
        self.create_tooltip(self.start_button, "Begin processing the selected Python scripts.")
        self.create_tooltip(self.cancel_button, "Cancel the ongoing processing.")

        # Progress Bar and Label
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill='x', **padding_options)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            length=700,
            mode='determinate'
        )
        self.progress_bar.pack(side='left', padx=5)

        self.progress_label = tk.Label(progress_frame, text="Ready to start.")
        self.progress_label.pack(side='left', padx=5)

        # Tooltip for Progress Bar
        self.create_tooltip(self.progress_bar, "Shows the progress of the dataset creation process.")

        # Log Area
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)

        log_label = tk.Label(log_frame, text="Log:")
        log_label.pack(anchor='w')

        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=20, wrap='word')
        self.log_text.pack(fill='both', expand=True)

        # Tooltip for Log Area
        self.create_tooltip(self.log_text, "Displays real-time logs of the processing status.")

        # Summary Section
        summary_frame = tk.Frame(self.root)
        summary_frame.pack(fill='x', padx=10, pady=5)

        summary_label = tk.Label(summary_frame, text="Summary:")
        summary_label.pack(anchor='w')

        self.summary_text = tk.Text(summary_frame, state='disabled', height=5, wrap='word')
        self.summary_text.pack(fill='x')

        # Tooltip for Summary Section
        self.create_tooltip(self.summary_text, "Displays a summary of the processing results.")

        # Export Log Button
        export_log_frame = tk.Frame(self.root)
        export_log_frame.pack(fill='x', padx=10, pady=5)

        export_log_button = tk.Button(export_log_frame, text="Export Log", command=self.export_log, width=15)
        export_log_button.pack(side='left')

        # Tooltip for Export Log Button
        self.create_tooltip(export_log_button, "Export the current log to a text file.")

    def create_tooltip(self, widget, text):
        tooltip = ToolTip(widget, text)

    def browse_root_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.root_dir_var.set(folder_selected)

    def browse_output_file(self):
        file_selected = filedialog.asksaveasfilename(
            defaultextension=".jsonl",
            filetypes=[("JSON Lines", "*.jsonl"), ("All Files", "*.*")]
        )
        if file_selected:
            self.output_file_var.set(file_selected)

    def log(self, message, msg_type='info'):
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if msg_type == 'info':
            tag = 'info'
        elif msg_type == 'error':
            tag = 'error'
        elif msg_type == 'success':
            tag = 'success'
        else:
            tag = 'info'
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def setup_tags(self):
        self.log_text.tag_config('info', foreground='black')
        self.log_text.tag_config('error', foreground='red')
        self.log_text.tag_config('success', foreground='green')

    def start_processing(self):
        root_dir = self.root_dir_var.get()
        output_file = self.output_file_var.get()
        overwrite = self.overwrite_var.get()

        if not root_dir:
            messagebox.showerror("Input Error", "Please select a root directory.")
            return
        if not os.path.isdir(root_dir):
            messagebox.showerror("Input Error", "The selected root directory does not exist.")
            return
        if not output_file:
            messagebox.showerror("Input Error", "Please select an output file location.")
            return
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            messagebox.showerror("Input Error", "The directory for the output file does not exist.")
            return

        # Disable the start button and enable the cancel button
        self.start_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.cancel_event.clear()

        # Clear previous logs and summary
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.config(state='disabled')

        # Initialize progress bar
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Starting processing...")

        # Setup log tags
        self.setup_tags()

        # Start processing in a separate thread
        threading.Thread(
            target=self.process_files,
            args=(root_dir, output_file, overwrite),
            daemon=True
        ).start()

    def cancel_processing(self):
        if messagebox.askyesno("Cancel", "Are you sure you want to cancel the processing?"):
            self.cancel_event.set()
            self.log("Cancellation requested. Waiting for the process to terminate...", msg_type='error')

    def poll_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                if message['type'] == 'log':
                    self.log(message['content'], msg_type=message.get('msg_type', 'info'))
                elif message['type'] == 'progress':
                    current = message['current']
                    total = message['total']
                    self.progress_bar['maximum'] = total
                    self.progress_bar['value'] = current
                    percentage = (current / total) * 100
                    self.progress_label.config(text=f"Processing {current}/{total} files ({percentage:.2f}%)")
                elif message['type'] == 'done':
                    summary = message['content']
                    self.progress_label.config(text="Processing complete.")
                    self.log(summary, msg_type='success')
                    self.display_summary(summary)
                    self.start_button.config(state='normal')
                    self.cancel_button.config(state='disabled')
                elif message['type'] == 'error':
                    error_msg = message['content']
                    self.log(error_msg, msg_type='error')
                    self.start_button.config(state='normal')
                    self.cancel_button.config(state='disabled')
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def display_summary(self, summary):
        self.summary_text.config(state='normal')
        self.summary_text.insert(tk.END, summary)
        self.summary_text.see(tk.END)
        self.summary_text.config(state='disabled')

    def export_log(self):
        log_content = self.log_text.get(1.0, tk.END)
        if not log_content.strip():
            messagebox.showinfo("Export Log", "No logs to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("Export Log", f"Log exported successfully to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Log", f"Failed to export log: {e}")

    def process_files(self, root_dir, output_file, overwrite):
        try:
            py_files = self.get_all_py_files(root_dir)
            total_files = len(py_files)

            if total_files == 0:
                self.queue.put({'type': 'log', 'content': "No Python files were found in the selected directory.", 'msg_type': 'info'})
                self.queue.put({'type': 'done', 'content': "No files to process."})
                return

            mode = 'a' if os.path.exists(output_file) and not overwrite else 'w'
            already_exists = os.path.exists(output_file) and not overwrite

            if already_exists:
                summary = f"Appending to existing dataset.\nOutput file: {output_file}"
                self.queue.put({'type': 'log', 'content': summary, 'msg_type': 'info'})
            else:
                summary = f"Creating new dataset.\nOutput file: {output_file}"
                self.queue.put({'type': 'log', 'content': summary, 'msg_type': 'info'})

            processed = 0
            skipped = 0
            skipped_files = []

            with open(output_file, mode, encoding='utf-8') as dataset:
                for idx, file_path in enumerate(py_files, 1):
                    if self.cancel_event.is_set():
                        self.queue.put({'type': 'log', 'content': "Processing cancelled by user.", 'msg_type': 'error'})
                        break
                    try:
                        # Attempt to read the file with UTF-8 encoding first
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                code = f.read()
                            encoding_used = 'utf-8'
                        except UnicodeDecodeError:
                            # If UTF-8 fails, detect encoding
                            with open(file_path, 'rb') as f:
                                raw_data = f.read()
                            result = chardet.detect(raw_data)
                            encoding_used = result['encoding']
                            confidence = result['confidence']
                            if encoding_used and confidence > 0.5:
                                try:
                                    code = raw_data.decode(encoding_used)
                                    self.queue.put({'type': 'log', 'content': f"Detected encoding '{encoding_used}' for file: {os.path.relpath(file_path, root_dir)} (Confidence: {confidence*100:.2f}%)", 'msg_type': 'info'})
                                except Exception as e:
                                    raise UnicodeDecodeError(f"Failed to decode with detected encoding '{encoding_used}': {e}")
                            else:
                                raise UnicodeDecodeError("Unable to detect encoding with sufficient confidence.")

                        relative_path = os.path.relpath(file_path, root_dir)
                        entry = {
                            "file_path": relative_path,
                            "code": code
                        }
                        dataset.write(json.dumps(entry) + "\n")
                        processed += 1
                        self.queue.put({'type': 'log', 'content': f"Processed: {relative_path} (Encoding: {encoding_used})", 'msg_type': 'success'})
                    except Exception as e:
                        skipped += 1
                        skipped_files.append(os.path.relpath(file_path, root_dir))
                        error_info = traceback.format_exc()
                        self.queue.put({'type': 'log', 'content': f"Error processing file {file_path}: {e}", 'msg_type': 'error'})
                        self.queue.put({'type': 'log', 'content': error_info, 'msg_type': 'error'})

                    # Update progress
                    self.queue.put({'type': 'progress', 'current': idx, 'total': total_files})

            # Prepare summary
            summary_lines = [
                "Processing complete.",
                f"Total files found: {total_files}",
                f"Processed successfully: {processed}",
                f"Skipped due to errors: {skipped}"
            ]
            if skipped_files:
                summary_lines.append("\nSkipped Files:")
                for file in skipped_files:
                    summary_lines.append(f" - {file}")
            summary = "\n".join(summary_lines)
            self.queue.put({'type': 'done', 'content': summary})

        except Exception as e:
            error_info = traceback.format_exc()
            self.queue.put({'type': 'error', 'content': f"An unexpected error occurred: {e}\n{error_info}", 'msg_type': 'error'})

    def get_all_py_files(self, root_dir):
        py_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = os.path.join(dirpath, filename)
                    py_files.append(full_path)
        return py_files


class ToolTip:
    """
    It creates a tooltip for a given widget as the mouse goes on it.
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # miliseconds
        self.wraplength = 300   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.show_tip)

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def show_tip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hide_tip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


def main():
    root = tk.Tk()
    app = DatasetCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
