import tkinter as tk
from tkinter import ttk
import cv2
from cv2 import QRCodeDetector
import requests
from PIL import Image, ImageTk
from threading import Thread
import time

# Define the Django API endpoint
API_URL = "http://192.168.85.234:8000/api/validate_ticket/"

# List of ticket types
TICKET_TYPES = [
    "entry_in", "entry_out", "dinosaur_show_in", "dinosaur_show_out",
    "ancient_statues_in", "ancient_statues_out", "ice_age_show_in", "ice_age_show_out",
    "photography",
]

# Globals
selected_ticket_type = None
cap = None
is_camera_initialized = False

# Function to initialize the camera (runs in the background)
def initialize_camera():
    """Initialize the camera with retries."""
    global cap, is_camera_initialized
    for attempt in range(3):  # Retry up to 3 times
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            is_camera_initialized = True
            print("Camera initialized successfully.")
            return
        else:
            print(f"Camera initialization failed (Attempt {attempt + 1}/3). Retrying...")
            time.sleep(1)

    print("Error: Unable to access the camera after retries.")
    cap = None
    is_camera_initialized = False

# Function to validate a ticket via the Django API
def validate_ticket(qr_code_uuid):
    if not qr_code_uuid or not selected_ticket_type:
        validation_label.config(text="Please scan a QR code.", fg="black")
        return

    data = {"qr_code_uuid": qr_code_uuid, "ticket_type": selected_ticket_type}

    try:
        response = requests.post(API_URL, json=data, timeout=5)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("status") == "success":
            door_open(True, response_data.get("message"))
        else:
            door_open(False, response_data.get("message"))
    except requests.exceptions.RequestException as e:
        validation_label.config(text=f"Failed to connect to server: {e}", fg="red")

# Function to handle door status
def door_open(status, message):
    if status:
        root.config(bg="#28a745")
        validation_label.config(text=f"Door Opened: {message}", fg="white", bg="#28a745", font=("Arial", 16, "bold"))
    else:
        root.config(bg="#dc3545")
        validation_label.config(text=f"Access Denied: {message}", fg="white", bg="#dc3545", font=("Arial", 16, "bold"))

# Function to update the camera feed
def update_frame():
    global cap
    if cap is None or not is_camera_initialized:
        validation_label.config(text="Camera not initialized or accessible.", fg="red")
        return

    ret, frame = cap.read()
    if ret:
        frame = cv2.resize(frame, (800, 600))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img_tk = ImageTk.PhotoImage(img)

        camera_label.img_tk = img_tk
        camera_label.config(image=img_tk)

        detector = QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(frame)
        if data:
            validate_ticket(data)

    root.after(10, update_frame)

# Function to display the camera page
def show_camera_page(ticket_type):
    global selected_ticket_type
    selected_ticket_type = ticket_type

    # Clear the main window
    for widget in root.winfo_children():
        widget.destroy()

    # Camera Feed Label
    tk.Label(root, text=f"Ticket Type: {ticket_type}", font=("Arial", 16, "bold"), bg="#f8f9fa").pack(pady=10)

    global camera_label
    camera_label = tk.Label(root, bg="#6c757d", relief=tk.SUNKEN, width=800, height=600)
    camera_label.pack(pady=20)

    # Validation Label
    global validation_label
    validation_label = tk.Label(
        root, text="", font=("Arial", 14), width=50, height=3, anchor="center", bg="#f8f9fa", relief=tk.FLAT
    )
    validation_label.pack(pady=20)

    # Footer
    footer_frame = tk.Frame(root, bg="#007bff", height=40)
    footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
    footer_label = tk.Label(
        footer_frame, text="\u00a9 2024 National Museum. All Rights Reserved.", font=("Arial", 10), fg="white", bg="#007bff"
    )
    footer_label.pack(pady=5)

    # Start the camera feed
    update_frame()

# Function to display the front page
def show_front_page():
    root.config(bg="#f8f9fa")
    for widget in root.winfo_children():
        widget.destroy()

    tk.Label(root, text="Select Ticket Type", font=("Arial", 20, "bold"), bg="#f8f9fa").pack(pady=20)

    button_frame = tk.Frame(root, bg="#f8f9fa")
    button_frame.pack(pady=20)

    for ticket_type in TICKET_TYPES:
        tk.Button(
            button_frame,
            text=ticket_type.replace("_", " ").title(),
            font=("Arial", 12),
            bg="#007bff",
            fg="white",
            width=20,
            command=lambda t=ticket_type: show_camera_page(t),
        ).pack(pady=5)

    footer_frame = tk.Frame(root, bg="#007bff", height=40)
    footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
    footer_label = tk.Label(
        footer_frame, text="\u00a9 2024 National Museum. All Rights Reserved.", font=("Arial", 10), fg="white", bg="#007bff"
    )
    footer_label.pack(pady=5)

# Main Program Execution
if __name__ == "__main__":
    root = tk.Tk()
    root.title("National Museum Ticket Validator")
    root.geometry("1024x768")

    # Initialize the camera in the background
    Thread(target=initialize_camera, daemon=True).start()

    # Show the front page
    show_front_page()

    # Run the application
    root.mainloop()