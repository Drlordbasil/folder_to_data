import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk  # Correctly import ttk from tkinter
import threading

def get_all_py_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                py_files.append(full_path)
    return py_files

def create_dataset(root_dir, output_file, overwrite=False, progress_callback=None):
    if os.path.exists(output_file) and not overwrite:
        mode = 'a'
        already_exists = True
    else:
        mode = 'w'
        already_exists = False

    py_files = get_all_py_files(root_dir)
    total_files = len(py_files)

    if total_files == 0:
        messagebox.showinfo("No Files Found", "No Python files were found in the selected directory.")
        return

    with open(output_file, mode, encoding='utf-8') as dataset:
        for idx, file_path in enumerate(py_files, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                relative_path = os.path.relpath(file_path, root_dir)
                entry = {
                    "file_path": relative_path,
                    "code": code
                }
                dataset.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

            # Update progress
            if progress_callback:
                progress_callback(idx, total_files)

    if already_exists:
        message = f"Dataset appended successfully.\nOutput file: {output_file}"
    else:
        message = f"Dataset created successfully.\nOutput file: {output_file}"
    messagebox.showinfo("Success", message)

def browse_root_dir():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        root_dir_var.set(folder_selected)

def browse_output_file():
    file_selected = filedialog.asksaveasfilename(
        defaultextension=".jsonl",
        filetypes=[("JSON Lines", "*.jsonl"), ("All Files", "*.*")]
    )
    if file_selected:
        output_file_var.set(file_selected)

def start_processing():
    root_dir = root_dir_var.get()
    output_file = output_file_var.get()
    overwrite = overwrite_var.get()

    if not root_dir:
        messagebox.showerror("Input Error", "Please select a root directory.")
        return
    if not output_file:
        messagebox.showerror("Input Error", "Please select an output file location.")
        return

    # Disable the start button to prevent multiple clicks
    start_button.config(state='disabled')

    # Start processing in a separate thread to keep the GUI responsive
    threading.Thread(target=process_files, args=(root_dir, output_file, overwrite), daemon=True).start()

def process_files(root_dir, output_file, overwrite):
    py_files = get_all_py_files(root_dir)
    total_files = len(py_files)

    if total_files == 0:
        messagebox.showinfo("No Files Found", "No Python files were found in the selected directory.")
        start_button.config(state='normal')
        return

    progress_bar['maximum'] = total_files
    progress_bar['value'] = 0

    def update_progress(current, total):
        progress_bar['value'] = current
        progress_label.config(text=f"Processing {current}/{total} files...")

    create_dataset(root_dir, output_file, overwrite, progress_callback=update_progress)

    # Reset progress bar after completion
    progress_label.config(text="Processing complete.")
    progress_bar['value'] = 0
    start_button.config(state='normal')

# Initialize the main application window
root = tk.Tk()
root.title("Python Scripts to Dataset Creator")
root.geometry("600x250")
root.resizable(False, False)

# Variables to store user inputs
root_dir_var = tk.StringVar()
output_file_var = tk.StringVar()
overwrite_var = tk.BooleanVar()

# Styling options
padding_options = {'padx': 10, 'pady': 10}

# Root Directory Selection
root_dir_frame = tk.Frame(root)
root_dir_frame.pack(fill='x', **padding_options)

root_dir_label = tk.Label(root_dir_frame, text="Root Directory:")
root_dir_label.pack(side='left')

root_dir_entry = tk.Entry(root_dir_frame, textvariable=root_dir_var, width=50)
root_dir_entry.pack(side='left', padx=5)

browse_root_button = tk.Button(root_dir_frame, text="Browse", command=browse_root_dir)
browse_root_button.pack(side='left')

# Output File Selection
output_file_frame = tk.Frame(root)
output_file_frame.pack(fill='x', **padding_options)

output_file_label = tk.Label(output_file_frame, text="Output File:")
output_file_label.pack(side='left')

output_file_entry = tk.Entry(output_file_frame, textvariable=output_file_var, width=50)
output_file_entry.pack(side='left', padx=5)

browse_output_button = tk.Button(output_file_frame, text="Browse", command=browse_output_file)
browse_output_button.pack(side='left')

# Overwrite Option
overwrite_frame = tk.Frame(root)
overwrite_frame.pack(fill='x', **padding_options)

overwrite_check = tk.Checkbutton(overwrite_frame, text="Overwrite if file exists", variable=overwrite_var)
overwrite_check.pack(side='left')

# Start Button
start_button = tk.Button(root, text="Start Creating Dataset", command=start_processing, bg='green', fg='white')
start_button.pack(pady=10)

# Progress Bar and Label
progress_frame = tk.Frame(root)
progress_frame.pack(fill='x', **padding_options)

progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=400, mode='determinate')
progress_bar.pack(side='left', padx=5)

progress_label = tk.Label(progress_frame, text="Ready to start.")
progress_label.pack(side='left')

# Start the GUI event loop
root.mainloop()
