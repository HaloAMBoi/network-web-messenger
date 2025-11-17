import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import requests
import threading
import time
from datetime import datetime

# ----------------------
# CONFIG
# ----------------------
SERVER_URL = "http://macbook.local:8942"  # change to your server
USERNAME = None
BROADCAST_PIN = "1234"
LOGGING_PIN = "5678"
CLEAR_PIN = "1256"         # Must match CLEAR_PIN in chat.py
POLL_INTERVAL = 1.5
MAX_MESSAGES = 100

messages = []

# ----------------------
# GUI
# ----------------------
root = tk.Tk()
root.title("Family Chat Admin")
root.geometry("400x600")
root.configure(bg="#ffffff")

chat_display = scrolledtext.ScrolledText(
    root, state='disabled', wrap='word',
    bg="#ffffff", fg="#000000", font=("Segoe UI", 11)
)
chat_display.pack(padx=10, pady=10, fill='both', expand=True)

msg_frame = tk.Frame(root, bg="#ffffff")
msg_frame.pack(padx=10, pady=5, fill='x')
msg_entry = tk.Entry(msg_frame, font=("Segoe UI", 12), bg="#ffffff", fg="#000000")
msg_entry.pack(side='left', fill='x', expand=True, padx=(0,5))
send_btn = tk.Button(msg_frame, text="Send", font=("Segoe UI", 11),
                     command=lambda: send_message())
send_btn.pack(side='right')

control_frame = tk.Frame(root, bg="#ffffff")
control_frame.pack(padx=10, pady=5, fill='x')
broadcast_btn = tk.Button(control_frame, text="Broadcast", font=("Segoe UI", 11),
                          command=lambda: send_broadcast())
broadcast_btn.pack(side='left', padx=5)
logging_btn = tk.Button(control_frame, text="Toggle Logging", font=("Segoe UI", 11),
                        command=lambda: toggle_logging())
logging_btn.pack(side='left', padx=5)
clear_btn = tk.Button(control_frame, text="Clear Chat", font=("Segoe UI", 11),
                      command=lambda: clear_chat())
clear_btn.pack(side='left', padx=5)

# ----------------------
# FUNCTIONS
# ----------------------
def ask_username():
    global USERNAME
    USERNAME = simpledialog.askstring("Username", "Enter your admin name:", parent=root)
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
            resp = requests.get(f"{SERVER_URL}/api/messages", timeout=5)
            if resp.status_code == 200:
                data = resp.json()[-MAX_MESSAGES:]
                for m in data[len(messages):]:
                    append_to_display(format_message(m))
                messages = data
        except Exception as e:
            append_to_display(f"[Error fetching] {e}")
        time.sleep(POLL_INTERVAL)

def format_message(msg):
    user = msg.get("user")
    t = msg.get("time")
    text = msg.get("text")
    if user == "System":
        return f"[System] {t}: {text}"
    if user == USERNAME:
        return f"[You] {t}: {text}"
    if user == "Broadcast":
        return f"[Broadcast] {t}: {text}"
    return f"[{user}] {t}: {text}"

def send_message():
    text = msg_entry.get().strip()
    if not text:
        return
    data = {"user": USERNAME, "text": text, "time": datetime.now().strftime("%H:%M")}
    try:
        resp = requests.post(f"{SERVER_URL}/api/send_message", json=data, timeout=5)
        if resp.status_code != 200:
            append_to_display(f"[Error] send failed: {resp.status_code}")
    except Exception as e:
        append_to_display(f"[Error] {e}")
    msg_entry.delete(0, tk.END)

def send_broadcast():
    text = simpledialog.askstring("Broadcast", "Enter message to broadcast:")
    if not text:
        return
    pin = simpledialog.askstring("PIN", "Enter broadcast PIN:")
    if not pin:
        return
    data = {"pin": pin, "message": text}
    try:
        resp = requests.post(f"{SERVER_URL}/api/broadcast", json=data, timeout=5)
        if resp.status_code == 200:
            append_to_display("[Broadcast sent]")
        else:
            append_to_display(f"[Error broadcast] {resp.json().get('reason')}")
    except Exception as e:
        append_to_display(f"[Error] {e}")

def toggle_logging():
    enable = messagebox.askyesno("Logging", "Enable logging?")
    pin = simpledialog.askstring("PIN", "Enter logging PIN:")
    if not pin:
        return
    data = {"pin": pin, "state": "true" if enable else "false"}
    try:
        resp = requests.post(f"{SERVER_URL}/api/logging", json=data, timeout=5)
        if resp.status_code == 200:
            append_to_display(f"[Logging {'enabled' if enable else 'disabled'}]")
        else:
            append_to_display(f"[Error logging] {resp.json().get('reason')}")
    except Exception as e:
        append_to_display(f"[Error] {e}")

def clear_chat():
    # Admin uses clear endpoint
    pin = simpledialog.askstring("Clear Chat", "Enter clear PIN:")
    if not pin:
        return
    data = {"pin": pin, "user": USERNAME}
    try:
        resp = requests.post(f"{SERVER_URL}/api/clear", json=data, timeout=5)
        if resp.status_code == 200:
            append_to_display("[Chat cleared]")
        else:
            append_to_display(f"[Error clear] {resp.json().get('reason')}")
    except Exception as e:
        append_to_display(f"[Error] {e}")

# ----------------------
# START
# ----------------------
ask_username()
threading.Thread(target=fetch_messages, daemon=True).start()
root.mainloop()
