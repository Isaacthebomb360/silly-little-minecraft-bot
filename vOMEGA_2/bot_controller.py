# bot_controller.py
import subprocess
import threading
import json
import time

HOST = "localhost"
PORT = 53985
USERNAME = "IsaacsFembo(y)t"
ALLOWED_USER = "Isaacthebomb360"
COMMAND_PREFIX = "!bot"

# Start Node.js bot
proc = subprocess.Popen(
    ["node", "mineflayer_wrapper.js"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env={"HOST": HOST, "PORT": str(PORT), "USERNAME": USERNAME},
)


# Read Node stdout
def read_output():
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            event = json.loads(line.strip())
            if event.get("event") == "chat":
                user = event["user"]
                msg = event["message"]
                print(f"[{user}]: {msg}")
                handle_chat(user, msg)
            else:
                print("NODE EVENT:", event)
        except Exception:
            print("NODE RAW:", line.strip())


def handle_chat(user, msg):
    if user != ALLOWED_USER or not msg.startswith(COMMAND_PREFIX):
        return
    cmd = msg[len(COMMAND_PREFIX) :].strip().lower()
    args = cmd.split()
    if not args:
        return
    command = args[0]

    if command == "hello":
        send_command("chat", {"message": f"Hello {user}!"})
    elif command == "status":
        send_command("chat", {"message": "All systems nominal."})
    elif command == "jump":
        send_command("jump", {})
    elif command == "come":
        # Example: go to coordinates 10,64,10
        send_command("come", {"position": {"x": 10, "y": 64, "z": 10}})
    elif command == "move" and len(args) > 1:
        send_command("move", {"direction": args[1]})
    else:
        send_command("chat", {"message": f"Unknown command: {command}"})


def send_command(command, args):
    msg = json.dumps({"command": command, "args": args}) + "\n"
    proc.stdin.write(msg)
    proc.stdin.flush()


threading.Thread(target=read_output, daemon=True).start()

# Keep Python alive
try:
    while proc.poll() is None:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping bot...")
    proc.terminate()
