import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import requests
import threading
import time
from datetime import datetime

# ----------------------
# CONFIG
# ----------------------
SERVER_URL = "http://macbook.local:8942"  # Change to your server address
USERNAME = None
BROADCAST_PIN = "2016"
LOGGING_PIN = "26126"
POLL_INTERVAL = 1.5  # seconds
MAX_MESSAGES = 100

messages = []

# ----------------------
# GUI
# ----------------------
root = tk.Tk()
root.title("Family Chat")
root.geometry("400x600")
root.configure(bg="#ffffff")  # Full white background

# Chat display
chat_display = scrolledtext.ScrolledText(
    root, state='disabled', wrap='word',
    bg="#ffffff", fg="#000000", font=("Segoe UI", 11)
)
chat_display.pack(padx=10, pady=10, fill='both', expand=True)

# Message input
msg_frame = tk.Frame(root, bg="#ffffff")
msg_frame.pack(padx=10, pady=5, fill='x')
msg_entry = tk.Entry(msg_frame, font=("Segoe UI", 12), bg="#ffffff", fg="#000000")
msg_entry.pack(side='left', fill='x', expand=True, padx=(0,5))
send_btn = tk.Button(msg_frame, text="Send", font=("Segoe UI", 11), command=lambda: send_message())
send_btn.pack(side='right')

# Broadcast / Logging frame
control_frame = tk.Frame(root, bg="#ffffff")
control_frame.pack(padx=10, pady=5, fill='x')

broadcast_btn = tk.Button(control_frame, text="Broadcast", font=("Segoe UI", 11),
                          command=lambda: send_broadcast())
broadcast_btn.pack(side='left', padx=5)
logging_btn = tk.Button(control_frame, text="Toggle Logging", font=("Segoe UI", 11),
                        command=lambda: toggle_logging())
logging_btn.pack(side='left', padx=5)

# ----------------------
# HELPER FUNCTIONS
# ----------------------
def ask_username():
    global USERNAME
    USERNAME = simpledialog.askstring("Username", "Enter your name:", parent=root)
    if not USERNAME:
        messagebox.showerror("Error", "You must enter a username.")
        root.destroy()

def append_to_display(msg):
    chat_display.configure(state='normal')
    chat_display.insert(tk.END, msg + "\n")
    chat_display.configure(state='disabled')
    chat_display.yview(tk.END)

def fetch_messages():
    global messages
    while True:
        try:
            resp = requests.get(f"{SERVER_URL}/api/messages")
            if resp.status_code == 200:
                data = resp.json()[-MAX_MESSAGES:]
                # Display only new messages
                for m in data[len(messages):]:
                    display_msg = format_message(m)
                    append_to_display(display_msg)
                messages = data
        except Exception as e:
            append_to_display(f"[Error] Could not fetch messages: {e}")
        time.sleep(POLL_INTERVAL)

def format_message(msg):
    # Broadcast messages are normal text
    if msg['user'] == USERNAME:
        return f"[You] {msg['time']}: {msg['text']}"
    elif msg['user'] == "System":
        return f"[System] {msg['time']}: {msg['text']}"  # italics optional
    elif msg['user'] == "Broadcast":
        return f"[Broadcast] {msg['time']}: {msg['text']}"  # normal
    else:
        return f"[{msg['user']}] {msg['time']}: {msg['text']}"

# ----------------------
# ACTIONS
# ----------------------
def send_message():
    text = msg_entry.get().strip()
    if not text:
        return
    data = {"user": USERNAME, "text": text, "time": datetime.now().strftime("%H:%M")}
    try:
        resp = requests.post(f"{SERVER_URL}/api/send_message", json=data)
        if resp.status_code != 200:
            append_to_display("[Error] Failed to send message.")
    except Exception as e:
        append_to_display(f"[Error] {e}")
    msg_entry.delete(0, tk.END)

def send_broadcast():
    text = simpledialog.askstring("Broadcast", "Enter broadcast message:")
    if not text:
        return
    pin = simpledialog.askstring("PIN", "Enter broadcast PIN:")
    if not pin:
        return
    data = {"pin": pin, "message": text}
    try:
        resp = requests.post(f"{SERVER_URL}/api/broadcast", json=data)
        if resp.status_code == 200:
            append_to_display("[Broadcast sent successfully]")
        else:
            append_to_display(f"[Error] {resp.json().get('reason','Failed')}")
    except Exception as e:
        append_to_display(f"[Error] {e}")

def toggle_logging():
    enable_logging = messagebox.askyesno(
        "Logging", 
        "Enable logging?\n(Yes: Enable | No: Disable)"
    )
    pin = simpledialog.askstring("PIN", "Enter logging PIN:")
    if not pin:
        return
    data = {"pin": pin, "state": "true" if enable_logging else "false"}
    try:
        resp = requests.post(f"{SERVER_URL}/api/logging", json=data)
        if resp.status_code == 200:
            append_to_display(f"[Logging {'enabled' if enable_logging else 'disabled'} successfully]")
        else:
            append_to_display(f"[Error] {resp.json().get('reason','Failed')}")
    except Exception as e:
        append_to_display(f"[Error] {e}")

# ----------------------
# START
# ----------------------
ask_username()
threading.Thread(target=fetch_messages, daemon=True).start()
root.mainloop()
