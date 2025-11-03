from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------------------
# CONFIG
# ------------------------
messages = []
MAX_MESSAGES = 100
logging_enabled = False
log_file = "chat_log.txt"

# Secrets for API
BROADCAST_PIN = "1234"   # Secret for /api/broadcast
LOGGING_PIN = "5678"     # Secret for /api/logging

# ------------------------
# HTML Template (use your previous chat HTML)
# ------------------------
chat_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Family Chat 💬</title>
<style>
body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#0e0e0e; color:#fff; margin:0; display:flex; flex-direction:column; height:100vh;}
header { background:#181818; padding:15px; text-align:center; font-weight:600; font-size:18px; border-bottom:1px solid #333; display:flex; justify-content:space-between; align-items:center;}
#loggingStatus { font-size:14px; color:#aaa; font-weight:normal;}
#chatbox { flex:1; overflow-y:auto; padding:15px; display:flex; flex-direction:column; gap:8px; scroll-behavior:smooth;}
.msg { padding:10px 14px; border-radius:18px; max-width:75%; word-wrap:break-word; font-size:15px; line-height:1.3;}
.self { background:#007aff; align-self:flex-end;}
.other { background:#2f2f2f; align-self:flex-start;}
.system { background:none; color:#aaa; font-style:italic; align-self:center;}
.timestamp { font-size:11px; color:#aaa; text-align:right; margin-top:3px;}
#sendForm { display:flex; background:#181818; padding:10px; border-top:1px solid #333;}
#msg { flex:1; padding:10px; border:none; border-radius:20px; outline:none; font-size:16px; margin-right:10px; background:#2f2f2f; color:#fff;}
button { background:#007aff; border:none; color:white; padding:10px 16px; border-radius:20px; font-size:16px;}
button:hover { background:#005fcc; }

#usernamePrompt { position:fixed; inset:0; background:rgba(0,0,0,0.9); display:flex; flex-direction:column; justify-content:center; align-items:center; gap:15px;}
#usernamePrompt input { padding:10px; font-size:16px; border-radius:8px; border:none; outline:none; width:200px; text-align:center;}
</style>
</head>
<body>
<header>
  <span>Family Chat 💬</span>
  <span id="loggingStatus">Logging: OFF</span>
</header>

<div id="usernamePrompt">
  <h2>Enter your name</h2>
  <input type="text" id="usernameInput" placeholder="Your name" maxlength="20" />
  <button id="joinBtn">Join Chat</button>
</div>

<div id="chatbox" style="display:none;"></div>

<form id="sendForm" onsubmit="sendMessage(event)" style="display:none;">
  <input type="text" id="msg" placeholder="Type a message..." autocomplete="off" required>
  <button type="submit">➤</button>
</form>

<!-- Username status below the form -->
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
let username = localStorage.getItem("chat_username");
let logging = false;

const promptBox = document.getElementById("usernamePrompt");
const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const form = document.getElementById("sendForm");
const loggingStatus = document.getElementById("loggingStatus");

function startChat() {
  promptBox.style.display = "none";
  chatbox.style.display = "flex";
  form.style.display = "flex";

  const socket = io();

  function appendMessage(user, text, time) {
    const msgDiv = document.createElement("div");
    if (user === "System") {
      msgDiv.className = "msg system";
      msgDiv.textContent = text;
    } else {
      msgDiv.className = "msg " + (user === username ? "self" : "other");
      msgDiv.innerHTML = "<b>" + user + "</b><br>" + text +
                         "<div class='timestamp'>" + time + "</div>";
    }
    chatbox.appendChild(msgDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
  }

  socket.on("connect", () => {
    socket.emit("join", username);
  });

  socket.on("load_messages", (data) => {
    chatbox.innerHTML = "";
    data.forEach(m => appendMessage(m.user, m.text, m.time));
  });

  socket.on("new_message", (m) => {
    // Function to append messages
    const msgDiv = document.createElement("div");

    // System messages (commands, joins, logging toggles, clears)
    if (m.user === "System") {
        msgDiv.className = "msg system";
        msgDiv.textContent = m.text;

        // Update logging header if this is a logging command
        if (m.text.toLowerCase().includes("logging enabled")) {
            loggingStatus.textContent = "Logging: ON";
        } else if (m.text.toLowerCase().includes("logging disabled")) {
            loggingStatus.textContent = "Logging: OFF";
        }

    } else {
        // Normal messages
        msgDiv.className = "msg " + (m.user === username ? "self" : "other");
        msgDiv.innerHTML = "<b>" + m.user + "</b><br>" + m.text +
                           "<div class='timestamp'>" + m.time + "</div>";
    }

    chatbox.appendChild(msgDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
  });


  socket.on("clear_messages", () => {
    chatbox.innerHTML = "";
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = msgInput.value.trim();
    if (!text) return;
    const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    socket.emit("send_message", {user: username, text: text, time: time});
    msgInput.value = "";
  });
}

// Username prompt
document.getElementById("joinBtn").onclick = () => {
  const nameInput = document.getElementById("usernameInput");
  const name = nameInput.value.trim();
  if (!name) return alert("Please enter a name");
  username = name;
  localStorage.setItem("chat_username", username);
  startChat();
};

if (username) startChat();
</script>
</body>
</html>
"""  # Keep the full HTML from your previous version with username prompt + web chat

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
        return jsonify({"status":"ok"})
    return jsonify({"status":"error"}), 400

# ------------------------
# BROADCAST API
# ------------------------
@app.route("/api/broadcast", methods=["POST"])
def api_broadcast():
    data = request.json
    pin = data.get("pin")
    text = data.get("message")
    if pin != BROADCAST_PIN:
        return jsonify({"status":"error", "reason":"Invalid PIN"}), 403
    msg = {
        "user": "Broadcast",
        "text": f"[Broadcast] {text}",
        "time": datetime.now().strftime("%H:%M")
    }
    append_message(msg)
    return jsonify({"status":"ok"})

# ------------------------
# LOGGING API
# ------------------------
@app.route("/api/logging", methods=["POST"])
def api_logging():
    data = request.json
    pin = data.get("pin")
    state = data.get("state")
    global logging_enabled

    if pin != LOGGING_PIN:
        return jsonify({"status":"error","reason":"Invalid PIN"}), 403
    if state not in ["true","false"]:
        return jsonify({"status":"error","reason":"Invalid state"}), 400

    logging_enabled = True if state == "true" else False
    status_text = f"Logging {'enabled ✅' if logging_enabled else 'disabled ❌'} via API"

    msg = {
        "user": "System",
        "text": status_text,
        "time": datetime.now().strftime("%H:%M")
    }
    append_message(msg)
    return jsonify({"status":"ok", "logging":logging_enabled})

# ------------------------
# HELPER
# ------------------------
def append_message(msg):
    messages.append(msg)
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)
    socketio.emit("new_message", msg)
    # Save to log if enabled or if msg is logging toggle itself
    if logging_enabled or ("Logging enabled" in msg["text"] or "Logging disabled" in msg["text"]):
        with open(log_file,"a",encoding="utf-8") as f:
            f.write(f"[{msg['time']}] {msg['user']}: {msg['text']}\n")

# ------------------------
# SOCKET.IO EVENTS
# ------------------------
@socketio.on("join")
def handle_join(username):
    emit("load_messages", messages)
    join_notice = {
        "user": "System",
        "text": f"{username} joined the chat 👋",
        "time": datetime.now().strftime("%H:%M")
    }
    append_message(join_notice)

@socketio.on("send_message")
def handle_send(data):
    text_lower = data["text"].strip().lower()

    # Command: logging:true/false
    if text_lower.startswith("logging:"):
        value = text_lower.split(":")[1].strip()
        global logging_enabled
        if value == "true":
            logging_enabled = True
            msg_text = f"Logging enabled ✅ by {data['user']}"
        elif value == "false":
            logging_enabled = False
            msg_text = f"Logging disabled ❌ by {data['user']}"
        else:
            msg_text = f"Invalid logging command: {data['text']}"
        append_message({"user":"System","text":msg_text,"time":data["time"]})
        return

    # Command: clear
    if text_lower == "clear":
        messages.clear()
        socketio.emit("clear_messages")
        msg_text = f"Chat cleared ✅ by {data['user']}"
        append_message({"user":"System","text":msg_text,"time":data["time"]})
        if logging_enabled:
            with open(log_file,"w",encoding="utf-8") as f:
                f.write(f"=== Chat cleared by {data['user']} at {data['time']} ===\n")
        return

    # Normal message
    append_message(data)

# ------------------------
# RUN
# ------------------------
if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=8942)
