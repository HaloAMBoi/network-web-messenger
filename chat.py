from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory messages
messages = []
MAX_MESSAGES = 100

# Logging
log_file = "chat_log.txt"
logging_enabled = False  # Controlled by chat commands

# HTML with username prompt, cached per device
html = """
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
"""

@app.route("/")
def index():
    return render_template_string(html)

def save_message_to_file(msg):
    global logging_enabled
    if logging_enabled:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{msg['time']}] {msg['user']}: {msg['text']}\n")

@socketio.on("join")
def handle_join(username):
    emit("load_messages", messages)
    join_notice = {
        "user": "System",
        "text": f"{username} joined the chat 👋",
        "time": datetime.now().strftime("%H:%M")
    }
    messages.append(join_notice)
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)
    socketio.emit("new_message", join_notice)
    save_message_to_file(join_notice)

@socketio.on("send_message")
@socketio.on("send_message")
def handle_send(data):
    """
    Handles all incoming messages from clients.
    Supports commands:
      - 'clear' => clears chat for everyone
      - 'logging:true' => enable TXT logging
      - 'logging:false' => disable TXT logging
    Normal messages are appended and optionally logged.
    """
    global logging_enabled
    text_lower = data["text"].strip().lower()

    # ----- COMMAND: Toggle Logging -----
    if text_lower.startswith("logging:"):
        value = text_lower.split(":")[1].strip()
        if value == "true":
            logging_enabled = True
            status_msg = {
                "user": "System",
                "text": f"Logging enabled ✅ by {data['user']}",
                "time": data["time"]
            }
        elif value == "false":
            logging_enabled = False
            status_msg = {
                "user": "System",
                "text": f"Logging disabled ❌ by {data['user']}",
                "time": data["time"]
            }
        else:
            # Invalid command
            status_msg = {
                "user": "System",
                "text": f"Invalid logging command: {data['text']}",
                "time": data["time"]
            }
        # Append to memory, emit to all clients, optionally log
        messages.append(status_msg)
        if len(messages) > 100:
            messages.pop(0)
        socketio.emit("new_message", status_msg)
        if logging_enabled:
            save_message_to_file(status_msg)
        return

    # ----- COMMAND: Clear chat -----
    if text_lower == "clear":
        messages.clear()
        socketio.emit("clear_messages")
        # System feedback to all clients
        status_msg = {
            "user": "System",
            "text": f"Chat cleared ✅ by {data['user']}",
            "time": data["time"]
        }
        messages.append(status_msg)
        if len(messages) > 100:
            messages.pop(0)
        socketio.emit("new_message", status_msg)
        # Clear TXT file if logging enabled
        if logging_enabled:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"=== Chat cleared by {data['user']} at {data['time']} ===\n")
        return

    # ----- NORMAL MESSAGE -----
    messages.append(data)
    if len(messages) > 100:
        messages.pop(0)
    socketio.emit("new_message", data)
    save_message_to_file(data)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8942)
