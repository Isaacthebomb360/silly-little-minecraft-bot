# bot_controller.py
import json, subprocess, threading

# Launch Node.js bot as a subprocess
bot_process = subprocess.Popen(
    ["node", "mineflayer_wrapper.js"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)

def send_command(cmd, args=None):
    msg = {"command": cmd, "args": args or {}}
    bot_process.stdin.write(json.dumps(msg) + "\n")
    bot_process.stdin.flush()

def read_output():
    for line in bot_process.stdout:
        try:
            data = json.loads(line)
            print("BOT EVENT:", data)
        except:
            print("RAW:", line.strip())

threading.Thread(target=read_output, daemon=True).start()

# Example: send a chat command to the bot
send_command("chat", {"message": "Hello from Python!"})
