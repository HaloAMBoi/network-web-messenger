from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------------------
# CONFIG
# ------------------------
messages = []
MAX_MESSAGES = 100
logging_enabled = False
log_file = "chat_log.txt"

BROADCAST_PIN = "1234"   # Secret for /api/broadcast
LOGGING_PIN = "5678"     # Secret for /api/logging

# — NEW: password to join chat
CHAT_PASSWORD = "ChatroomCS"

# — NEW: password to clear via browser
ADMIN_CLEAR_PASSWORD = "clear"

# ------------------------
# HTML Template (your original)
# ------------------------
chat_html = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chatroom 💬</title>
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#0e0e0e; color:#fff; margin:0; display:flex; flex-direction:column; height:100vh; }
    header { background:#181818; padding:15px; text-align:center; font-weight:600; font-size:18px; border-bottom:1px solid #333; display:flex; justify-content:space-between; align-items:center; }
    #loggingStatus { font-size:14px; color:#aaa; font-weight:normal; }
    #chatbox { flex:1; overflow-y:auto; padding:15px; display:flex; flex-direction:column; gap:8px; scroll-behavior:smooth; }
    .msg { padding:10px 14px; border-radius:18px; max-width:75%; word-wrap:break-word; font-size:15px; line-height:1.3; }
    .self { background:#007aff; align-self:flex-end; }
    .other { background:#2f2f2f; align-self:flex-start; }
    .system { background:none; color:#aaa; font-style:italic; align-self:center; }
    .timestamp { font-size:11px; color:#aaa; text-align:right; margin-top:3px; }
    #sendForm { display:flex; background:#181818; padding:10px; border-top:1px solid #333; }
    #msg { flex:1; padding:10px; border:none; border-radius:20px; outline:none; font-size:16px; margin-right:10px; background:#2f2f2f; color:#fff; }
    button { background:#007aff; border:none; color:white; padding:10px 16px; border-radius:20px; font-size:16px; }
    button:hover { background:#005fcc; }

    #usernamePrompt, #passwordPrompt {
      position: fixed; inset:0; background:rgba(0,0,0,0.9);
      display:flex; flex-direction:column; justify-content:center; align-items:center; gap:15px;
    }
    #usernamePrompt input, #passwordPrompt input {
      padding:10px; font-size:16px; border-radius:8px; border:none; outline:none;
      width:220px; text-align:center;
    }
  </style>
</head>
<body>
  <header>
    <span>Chatroom 💬</span>
    <span id="loggingStatus">Logging: OFF</span>
  </header>

  <div id="usernamePrompt">
    <h2>Enter your name</h2>
    <input type="text" id="usernameInput" placeholder="Your name" maxlength="20" />
    <button id="joinBtn">Next</button>
  </div>

  <div id="passwordPrompt" style="display:none;">
    <h2>Enter chatroom password</h2>
    <input type="password" id="passwordInput" placeholder="Password" />
    <button id="passwordBtn">Join Chat</button>
  </div>

  <div id="chatbox" style="display:none;"></div>

  <form id="sendForm" onsubmit="sendMessage(event)" style="display:none;">
    <input type="text" id="msg" placeholder="Type a message..." autocomplete="off" required>
    <button type="submit">➤</button>
  </form>

  <div id="usernameStatus" style="
      background:#181818;
      padding:8px 15px;
      text-align:left;
      color:#aaa;
      font-size:14px;
      border-top:1px solid #333;
      display:none;
  ">
    Logged in as: <span id="currentUser"></span>
  </div>

  <script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
  <script>
    let username = null;
    let roomPassword = null;
    let socket = null;

    const usernamePrompt = document.getElementById("usernamePrompt");
    const passwordPrompt = document.getElementById("passwordPrompt");
    const chatbox = document.getElementById("chatbox");
    const form = document.getElementById("sendForm");
    const msgInput = document.getElementById("msg");
    const currentUser = document.getElementById("currentUser");
    const usernameStatus = document.getElementById("usernameStatus");
    const loggingStatus = document.getElementById("loggingStatus");

    document.getElementById("joinBtn").onclick = () => {
      const name = document.getElementById("usernameInput").value.trim();
      if (!name) { alert("Enter a name"); return; }
      username = name;
      usernamePrompt.style.display = "none";
      passwordPrompt.style.display = "flex";
    };

    document.getElementById("passwordBtn").onclick = () => {
      const pw = document.getElementById("passwordInput").value;
      if (!pw) { alert("Enter the password"); return; }
      roomPassword = pw;
      startChat();
    };

    function startChat() {
      passwordPrompt.style.display = "none";
      chatbox.style.display = "flex";
      form.style.display = "flex";
      usernameStatus.style.display = "block";
      currentUser.textContent = username;

      socket = io();

      socket.on("connect", () => {
        socket.emit("join", { username: username, password: roomPassword });
      });

      socket.on("join_denied", () => {
        alert("Wrong password. Reloading.");
        location.reload();
      });

      socket.on("load_messages", (data) => {
        chatbox.innerHTML = "";
        data.forEach(m => appendMessage(m));
      });

      socket.on("new_message", (m) => appendMessage(m));

      socket.on("clear_messages", () => { chatbox.innerHTML = ""; });

      socket.on("update_logging", (state) => {
        loggingStatus.textContent = state ? "Logging: ON" : "Logging: OFF";
      });
    }

    function appendMessage(m) {
      const div = document.createElement("div");
      if (m.user === "System") {
        div.className = "msg system";
        div.textContent = m.text;
      } else {
        div.className = "msg " + (m.user === username ? "self" : "other");
        div.innerHTML = "<b>" + m.user + "</b><br>" + m.text + "<div class='timestamp'>" + m.time + "</div>";
      }
      chatbox.appendChild(div);
      chatbox.scrollTop = chatbox.scrollHeight;
    }

    function sendMessage(e) {
      e.preventDefault();
      const text = msgInput.value.trim();
      if (!text) return;
      const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
      socket.emit("send_message", { user: username, text: text, time: time });
      msgInput.value = "";
    }
  </script>
</body>
</html>
"""

# ------------------------
# ROUTES
# ------------------------
@app.route("/")
def index():
    return render_template_string(chat_html)

@app.route("/api/messages")
def api_messages():
    return jsonify(messages[-MAX_MESSAGES:])

@app.route("/api/send_message", methods=["POST"])
def api_send_message():
    data = request.json
    if "user" in data and "text" in data:
        append_message(data)
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status":"error"}), 400

@app.route("/api/broadcast", methods=["POST"])
def api_broadcast():
    data = request.json or {}
    pin = data.get("pin")
    text = data.get("message", "")
    if pin != BROADCAST_PIN:
        return jsonify({"status":"error","reason":"Invalid PIN"}), 403
    msg = {"user": "Broadcast", "text": f"[Broadcast] {text}", "time": datetime.now().strftime("%H:%M")}
    append_message(msg)
    return jsonify({"status":"ok"})

@app.route("/api/logging", methods=["POST"])
def api_logging():
    data = request.json or {}
    pin = data.get("pin")
    state = data.get("state")
    global logging_enabled
    if pin != LOGGING_PIN or state not in ["true","false"]:
        return jsonify({"status":"error","reason":"Invalid"}), 403
    logging_enabled = (state == "true")
    msg = {"user": "System", "text": f"Logging {'enabled' if logging_enabled else 'disabled'}", "time": datetime.now().strftime("%H:%M")}
    append_message(msg)
    socketio.emit("update_logging", logging_enabled)
    return jsonify({"status":"ok"})

# ------------------------
# ADMIN CLEAR (browser URL)
# ------------------------
@app.route("/admin/clear")
def admin_clear():
    password = request.args.get("password")
    if password != ADMIN_CLEAR_PASSWORD:
        return "Unauthorized", 403

    # clear chat
    messages.clear()
    socketio.emit("clear_messages")

    return "Chat cleared successfully"

# ------------------------
# HELPERS
# ------------------------
def append_message(msg):
    messages.append(msg)
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)
    socketio.emit("new_message", msg)
    if logging_enabled:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{msg['time']}] {msg['user']}: {msg['text']}\n")
        except Exception:
            pass

# ------------------------
# SOCKET EVENTS
# ------------------------
@socketio.on("join")
def on_join(data):
    username = data.get("username")
    pwd = data.get("password")
    if pwd != CHAT_PASSWORD:
        emit("join_denied")
        # disconnect client
        disconnect()
        return

    emit("load_messages", messages)
    announce = {"user": "System", "text": f"{username} joined the chat 👋", "time": datetime.now().strftime("%H:%M")}
    append_message(announce)

@socketio.on("send_message")
def on_send(data):
    text = data.get("text", "")
    lower = text.strip().lower()

    if lower == "clear":
        # only allow clearing via admin URL, not chat command
        return

    if lower.startswith("logging:"):
        val = lower.split(":",1)[1].strip()
        global logging_enabled
        if val == "true":
            logging_enabled = True
            append_message({"user":"System", "text": f"Logging enabled ✅ by {data.get('user')}", "time": data["time"]})
        elif val == "false":
            logging_enabled = False
            append_message({"user":"System", "text": f"Logging disabled ❌ by {data.get('user')}", "time": data["time"]})
        else:
            append_message({"user":"System", "text": f"Invalid logging command: {text}", "time": data["time"]})
        socketio.emit("update_logging", logging_enabled)
        return

    append_message(data)

# ------------------------
# RUN SERVER
# ------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8942)

