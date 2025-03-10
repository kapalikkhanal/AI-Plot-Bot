import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, PanedWindow
import serial
from serial import SerialException
import google.generativeai as genai
import sys
import subprocess
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from PIL import Image, ImageTk
import re
import threading
import time

# Configure Gemini API
genai.configure(api_key='AIzaSy************TSrI7vgTb0aI') #Replace with you Gemini Api Key
model = genai.GenerativeModel('gemini-2.0-flash')

# Global variables
ser = None
current_gcode_path = None
printing = False
stop_flag = False
current_response_text = ""
current_figure = None

# Serial connection functions
def connect_printer():
    global ser
    port = port_entry.get()
    baud = baud_entry.get()

    try:
        ser = serial.Serial(port, baudrate=int(baud), timeout=1)
        enable_controls(True)
        messagebox.showinfo("Connected", f"Successfully connected to {port}")
    except Exception as e:
        messagebox.showerror("Connection Error",
                             f"Failed to connect: {str(e)}")
        enable_controls(False)


def disconnect_printer():
    global ser
    if ser and ser.is_open:
        ser.close()
    enable_controls(False)
    messagebox.showinfo("Disconnected", "Printer disconnected")

# G-code file handling
def send_gcode_file():
    global printing, stop_flag, ser
    if not current_gcode_path or not os.path.exists(current_gcode_path):
        messagebox.showwarning("Error", "No G-code file generated yet")
        return

    if not ser or not ser.is_open:
        messagebox.showwarning("Error", "Not connected to printer")
        return

    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        enable_print_controls(False)

        progress_label.config(text="Homing printer...")
        progress_bar['value'] = 0
        root.update()

        if not send_gcode("G28"):
            raise Exception("Homing failed")

        time.sleep(2)

        with open(current_gcode_path, 'r') as f:
            stop_flag = False
            printing = True
            lines = [line.strip() for line in f if line.strip()
                     and not line.strip().startswith(';')]
            total_lines = len(lines)

            progress_label.config(
                text=f"Starting print: 0/{total_lines} lines")
            root.update()

            for i, line in enumerate(lines):
                if stop_flag:
                    progress_label.config(text="Print stopped by user")
                    break

                progress_percent = int((i / total_lines) * 100)
                progress_bar['value'] = progress_percent
                progress_label.config(
                    text=f"Printing: {i+1}/{total_lines} lines ({progress_percent}%)")
                root.update()

                if not send_gcode(line):
                    raise Exception(f"Failed to send command: {line}")

            if not stop_flag:
                progress_label.config(text="Print completed successfully")
                progress_bar['value'] = 100

        printing = False
        if not stop_flag:
            messagebox.showinfo("Success", "Print completed successfully")
    except Exception as e:
        messagebox.showerror("Error", f"Printing failed: {str(e)}")
        progress_label.config(text=f"Error: {str(e)}")
    finally:
        enable_print_controls(True)
        printing = False
        stop_flag = False

# AI response generation
def generate_response():
    global current_response_text
    question = question_entry.get("1.0", tk.END).strip()
    if not question:
        messagebox.showwarning("Input Error", "Please enter a question")
        return

    try:
        response = model.generate_content(
            question +
            " (Answer in plain text without markdown formatting. Maintain proper line breaks and formatting.)",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=300,
                temperature=0.7
            )
        )

        generated_text = response.text.strip()

        if not generated_text:
            messagebox.showerror(
                "API Error", "Received empty response from Gemini API")
            return

        # Preserve paragraphs and formatting
        generated_text = generated_text.replace(
            '\n\n', '\n')  # Normalize double newlines
        generated_text = generated_text.replace(
            '\n', '\n\n')  # Add extra newline for paragraphs

        current_response_text = generated_text
        response_text.config(state=tk.NORMAL)
        response_text.delete(1.0, tk.END)
        response_text.insert(tk.END, generated_text)
        response_text.config(state=tk.NORMAL)  # To make ai response editable

        with open("ai_response.txt", "w", encoding="utf-8") as file:
            file.write(generated_text)

    except Exception as e:
        messagebox.showerror(
            "API Error", f"Failed to generate answer: {str(e)}")

def update_response():
    """Update the current_response_text with the edited content from the response_text widget."""
    global current_response_text
    current_response_text = response_text.get("1.0", tk.END).strip()
    messagebox.showinfo("Success", "Response updated successfully!")

# G-code generation
def update_gcode():
    if not current_response_text:
        messagebox.showwarning("Error", "Generate a response first")
        return

    try:
        # Get the updated response from the text widget
        updated_response = response_text.get("1.0", tk.END).strip()
        if not updated_response:
            messagebox.showwarning("Error", "Response is empty")
            return

        # Save the updated response to the file
        with open("ai_response.txt", "w", encoding="utf-8") as file:
            file.write(updated_response)

        params = {
            "line_length": line_length_entry.get(),
            "line_spacing": line_spacing_entry.get(),
            "padding": padding_entry.get(),
            "paper_width": paper_width_entry.get(),
            "paper_height": paper_height_entry.get(),
            "font_size": font_size_entry.get(),
            "z_height": z_height_entry.get(),
            "z_speed": z_speed_entry.get(),
            "travel_speed": travel_speed_entry.get(),
            "write_speed": write_speed_entry.get(),
        }

        for key, value in params.items():
            if not value.replace('.', '', 1).isdigit():
                raise ValueError(f"Invalid value for {key.replace('_', ' ')}")
            params[key] = float(value)

        global current_gcode_path
        current_gcode_path = os.path.join(os.getcwd(), "output.nc")
        venv_python = sys.executable

        command = [
            venv_python, "text_to_gcode.py",
            "--input", "ai_response.txt",
            "--output", current_gcode_path,
            "--line-length", str(params["line_length"]),
            "--line-spacing", str(params["line_spacing"]),
            "--padding", str(params["padding"]),
            "--paper-width", str(params["paper_width"]),
            "--paper-height", str(params["paper_height"]),
            "--font-size", str(params["font_size"]),
            "--z-height", str(params["z_height"]),
            "--z-speed", str(params["z_speed"]),
            "--travel-speed", str(params["travel_speed"]),
            "--write-speed", str(params["write_speed"]),
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            plot_gcode(current_gcode_path,
                       params["paper_width"], params["paper_height"])
        else:
            messagebox.showerror(
                "G-code Error", f"Error generating G-code:\n{result.stderr}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to update G-code: {str(e)}")

# Visualization functions
def plot_gcode(gcode_path, paper_width, paper_height):
    global current_figure
    if current_figure:
        plt.close(current_figure)

    current_figure = plt.figure(figsize=(6, 4))
    ax = current_figure.add_subplot(111)

    # Set background color to off-white
    ax.set_facecolor('#F2F0EF')  # Off-white background
    current_figure.patch.set_facecolor('#F2F0EF')  # Match figure background

    ax.add_patch(Rectangle((0, 0), paper_width, paper_height+5,
                 edgecolor='black', facecolor='none', linewidth=1.5))

    x, y = [], []
    try:
        with open(gcode_path, 'r') as f:
            for line in f:
                if line.startswith(('G0', 'G1')):
                    x_match = re.search(r'X([\d.]+)', line)
                    y_match = re.search(r'Y([\d.]+)', line)
                    if x_match and y_match:
                        x.append(float(x_match.group(1)))
                        y.append(float(y_match.group(1)))
                    elif len(x) > 0 and len(y) > 0:
                        x.append(x[-1])
                        y.append(y[-1])
    except Exception as e:
        messagebox.showerror("Plot Error", f"Failed to parse G-code: {str(e)}")
        return

    ax.plot(x, y, 'b-', linewidth=1)
    ax.set_xlim(-5, paper_width + 10)
    ax.set_ylim(-5, paper_height + 10)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title("G-code Visualization")
    ax.set_xlabel("X Axis")
    ax.set_ylabel("Y Axis")

    for widget in viz_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(current_figure, master=viz_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    fullscreen_btn = ttk.Button(viz_frame, text="Full Screen",
                                command=show_fullscreen_plot)
    fullscreen_btn.pack(side=tk.BOTTOM, pady=5)


def show_fullscreen_plot():
    top = tk.Toplevel()
    top.title("G-code Visualization - Full Screen")
    top.state('zoomed')

    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_subplot(111)

    with open(current_gcode_path, 'r') as f:
        x, y = [], []
        for line in f:
            if line.startswith(('G0', 'G1')):
                x_match = re.search(r'X([\d.]+)', line)
                y_match = re.search(r'Y([\d.]+)', line)
                if x_match and y_match:
                    x.append(float(x_match.group(1)))
                    y.append(float(y_match.group(1)))
                elif len(x) > 0 and len(y) > 0:
                    x.append(x[-1])
                    y.append(y[-1])

    ax.plot(x, y, 'b-', linewidth=1)
    paper_width = float(paper_width_entry.get())
    paper_height = float(paper_height_entry.get())
    ax.add_patch(Rectangle((0, 0), paper_width, paper_height,
                 edgecolor='black', facecolor='none', linewidth=2))
    ax.set_xlim(-5, paper_width + 10)
    ax.set_ylim(-5, paper_height + 10)
    ax.set_aspect('equal', adjustable='box')

    canvas = FigureCanvasTkAgg(fig, master=top)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    close_btn = ttk.Button(top, text="Close", command=top.destroy)
    close_btn.pack(side=tk.BOTTOM, pady=10)

# Control function
def enable_controls(state):
    state = tk.NORMAL if state else tk.DISABLED
    home_btn.config(state=state)
    for btn in [x_plus_btn, x_minus_btn, y_plus_btn, y_minus_btn, z_plus_btn, z_minus_btn]:
        btn.config(state=state)

def enable_print_controls(state):
    send_btn.config(state=tk.NORMAL if state else tk.DISABLED)
    stop_btn.config(state=tk.NORMAL if not state else tk.DISABLED)

def send_gcode(command):
    if ser and ser.is_open:
        try:
            command = command.strip()
            if not command or command.startswith(';'):
                return True

            ser.write(f"{command}\n".encode())

            response = ""
            timeout = 30
            start_time = time.time()

            while "ok" not in response.lower():
                if ser.in_waiting:
                    new_data = ser.read(ser.in_waiting).decode(
                        'utf-8', errors='ignore')
                    response += new_data
                    print(f"Received: {new_data}")

                if time.time() - start_time > timeout:
                    print(
                        f"Timeout while waiting for 'ok' after command: {command}")
                    return False

                time.sleep(0.01)

            return True

        except SerialException as e:
            messagebox.showerror("Error", f"Connection lost: {str(e)}")
            return False
    return False

def home_all():
    send_gcode("G28")

def move_axis(axis, distance):
    send_gcode(f"G91\nG0 {axis}{distance}\nG90")

def stop_printing():
    global stop_flag
    stop_flag = True
    try:
        send_gcode("M0")
    except Exception as e:
        pass
    messagebox.showinfo("Stopped", "Printing stopped")

def create_axis_control(parent, axis, col):
    """Create axis control in a single row format."""
    ttk.Label(parent, text=f"{axis}:", font=(
        "Arial", 10, "bold")).grid(row=0, column=col, padx=5)

    distance = tk.DoubleVar(value=10.0)
    entry = ttk.Entry(parent, textvariable=distance, width=5)
    entry.grid(row=0, column=col + 1, padx=2)

    plus_btn = ttk.Button(parent, text="+",
                          command=lambda: move_axis(axis, distance.get()))
    plus_btn.grid(row=0, column=col + 2, padx=2)

    minus_btn = ttk.Button(parent, text="-",
                           command=lambda: move_axis(axis, -distance.get()))
    minus_btn.grid(row=0, column=col + 3, padx=2)

    return plus_btn, minus_btn

# UI setup
def create_ui():
    global root, port_entry, baud_entry, question_entry, response_text
    global line_length_entry, line_spacing_entry, padding_entry, paper_width_entry
    global paper_height_entry, font_size_entry, z_height_entry, z_speed_entry
    global travel_speed_entry, write_speed_entry, progress_label, progress_bar
    global home_btn, send_btn, stop_btn, x_plus_btn, x_minus_btn, y_plus_btn
    global y_minus_btn, z_plus_btn, z_minus_btn, viz_frame

    root = tk.Tk()
    root.title("AI Plot Bot")
    root.geometry("1200x800")

    try:
        root.iconbitmap("logo.ico")
    except Exception as e:
        print(f"Error loading .ico file: {e}")

    # Main paned window
    main_pane = PanedWindow(root, orient=tk.HORIZONTAL)
    main_pane.pack(fill=tk.BOTH, expand=True)

    # Left panel
    left_frame = ttk.Frame(main_pane, width=400)
    main_pane.add(left_frame)

    # Right panel
    right_frame = ttk.Frame(main_pane)
    main_pane.add(right_frame)

    # Connection frame
    conn_frame = ttk.Frame(left_frame, padding=10)
    conn_frame.pack(fill=tk.X, pady=5)

    ttk.Label(conn_frame, text="Port:").grid(row=0, column=0)
    port_entry = ttk.Entry(conn_frame)
    port_entry.grid(row=0, column=1, padx=5)
    port_entry.insert(0, "COM3")

    ttk.Label(conn_frame, text="Baud Rate:").grid(row=0, column=2)
    baud_entry = ttk.Entry(conn_frame, width=10)
    baud_entry.grid(row=0, column=3, padx=5)
    baud_entry.insert(0, "115200")

    connect_btn = ttk.Button(
        conn_frame, text="Connect", command=connect_printer)
    connect_btn.grid(row=0, column=4, padx=5)
    disconnect_btn = ttk.Button(
        conn_frame, text="Disconnect", command=disconnect_printer)
    disconnect_btn.grid(row=0, column=5, padx=5)

    # Home and Axis Controls in a single row
    control_frame = ttk.Frame(left_frame, padding=10)
    control_frame.pack(fill=tk.X, pady=5)

    # Home All button (First in row)
    home_btn = ttk.Button(control_frame, text="Home All",
                        command=home_all, state=tk.DISABLED)
    home_btn.grid(row=0, column=0, padx=5, pady=5)

    # X, Y, Z Axis Controls (Same Row)
    x_plus_btn, x_minus_btn = create_axis_control(control_frame, "X", 1)
    y_plus_btn, y_minus_btn = create_axis_control(control_frame, "Y", 5)
    z_plus_btn, z_minus_btn = create_axis_control(control_frame, "Z", 9)


    # AI Input Section
    ai_frame = ttk.LabelFrame(left_frame, text="AI Assistant", padding=10)
    ai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    ttk.Label(ai_frame, text="Enter your question:").pack(anchor=tk.W)
    question_entry = scrolledtext.ScrolledText(
        ai_frame, height=4, wrap=tk.WORD)
    question_entry.pack(fill=tk.X, pady=5)

    # Response buttons
    btn_frame = ttk.Frame(ai_frame)
    btn_frame.pack(pady=5)
    generate_btn = ttk.Button(
        btn_frame, text="Generate Response", command=generate_response)
    generate_btn.pack(side=tk.LEFT, padx=5)

    update_response_btn = ttk.Button(
        btn_frame, text="Update AI Response", command=update_response)
    update_response_btn.pack(side=tk.LEFT, padx=5)

    update_btn = ttk.Button(
        btn_frame, text="Update G-code", command=update_gcode)
    update_btn.pack(side=tk.LEFT, padx=5)

    # AI Response Display
    response_frame = ttk.Frame(ai_frame)
    response_frame.pack(fill=tk.BOTH, expand=True)
    ttk.Label(response_frame, text="AI Response:").pack(anchor=tk.W)
    response_text = scrolledtext.ScrolledText(
        response_frame, wrap=tk.WORD, height=10)
    response_text.pack(fill=tk.BOTH, expand=True)
    response_text.config(state=tk.NORMAL)

    # Parameters Grid
    param_frame = ttk.LabelFrame(
        left_frame, text="G-code Parameters", padding=10)
    param_frame.pack(fill=tk.X, pady=5)

    entries = []
    row = 0
    parameters = [
        ("Line Length:", "line_length", "300", 0, 0),
        ("Line Spacing:", "line_spacing", "10", 0, 2),
        ("Padding:", "padding", "2", 0, 4),
        ("Paper Width:", "paper_width", "150", 0, 6),
        ("Paper Height:", "paper_height", "150", 0, 8),
        ("Font Size:", "font_size", "0.58", 2, 0),
        ("Z Height:", "z_height", "1.5", 2, 2),
        ("Z Speed:", "z_speed", "5000", 2, 4),
        ("Travel Speed:", "travel_speed", "12000", 2, 6),
        ("Write Speed:", "write_speed", "4000", 2, 8),
    ]

    # for label_text, var_name, default, row in parameters:
    #     ttk.Label(param_frame, text=label_text).grid(
    #         row=row, column=0, sticky=tk.W, padx=5)
    #     entry = ttk.Entry(param_frame, width=8)
    #     entry.grid(row=row, column=1, padx=5)
    #     entry.insert(0, default)
    #     entries.append(entry)

    for label_text, var_name, default, row, col in parameters:
        ttk.Label(param_frame, text=label_text).grid(
            row=row, column=col, sticky=tk.W, padx=5, pady=2)
        entry = ttk.Entry(param_frame, width=8)
        entry.grid(row=row, column=col + 1, padx=5, pady=2)
        entry.insert(0, default)
        globals()[var_name + "_entry"] = entry

    # Progress indicators
    progress_frame = ttk.Frame(left_frame)
    progress_frame.pack(fill=tk.X, pady=5)

    progress_label = ttk.Label(progress_frame, text="Ready", anchor=tk.CENTER)
    progress_label.pack(fill=tk.X)

    progress_bar = ttk.Progressbar(
        progress_frame, orient=tk.HORIZONTAL, mode='determinate')
    progress_bar.pack(fill=tk.X, pady=5)

    # Print controls
    print_btn_frame = ttk.Frame(left_frame)
    print_btn_frame.pack(pady=5)
    send_btn = ttk.Button(print_btn_frame, text="Start Print",
                          command=lambda: threading.Thread(target=send_gcode_file).start())
    send_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(print_btn_frame, text="STOP",
                          command=stop_printing, state=tk.DISABLED)
    stop_btn.pack(side=tk.LEFT, padx=5)

    # Visualization Frame
    viz_frame = ttk.LabelFrame(
        right_frame, text="G-code Visualization", padding=10)
    viz_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    root.mainloop()


if __name__ == "__main__":
    create_ui()
