import subprocess
import threading
import json
import time
import os

HOST = "localhost"
PORT = 56546
USERNAME = "IsaacsFembo(y)t"
ALLOWED_USER = "Isaacthebomb360"
COMMAND_PREFIX = "!bot"

env = os.environ.copy()
env.update({"HOST": HOST, "PORT": str(PORT), "USERNAME": USERNAME})

proc = subprocess.Popen(
    ["node", "mineflayer_wrapper.js"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env,
)

def read_output():
    for line in proc.stdout:
        if not line:
            continue
        print("NODE OUT RAW:", line.strip())
        try:
            event = json.loads(line.strip())
            if event.get("event") == "chat":
                handle_chat(event["user"], event["message"])
            else:
                print("NODE EVENT:", event)
        except json.JSONDecodeError:
            pass

def read_error():
    for line in proc.stderr:
        if line:
            print("NODE ERR:", line.strip())

def handle_chat(user, msg):
    if user != ALLOWED_USER or not msg.startswith(COMMAND_PREFIX):
        return
    cmd = msg[len(COMMAND_PREFIX):].strip().lower()
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
        send_command("come", {"position": {"x": 10, "y": 64, "z": 10}})
    elif command == "move" and len(args) > 1:
        send_command("move", {"direction": args[1]})
    elif command == "pickup":
        send_command("pickup", {})
    elif command == "chop":
        send_command("chop", {})
    elif command == "mine" and len(args) > 6:
        send_command("mine", {
            "start": {"x": int(args[1]), "y": int(args[2]), "z": int(args[3])},
            "end": {"x": int(args[4]), "y": int(args[5]), "z": int(args[6])}
        })
    elif command == "respawn":
        send_command("respawn", {})
    elif command == "help":
        send_command("help", {})
    elif command == "chest":
        send_command("chest", {})
    elif command == "follow" and len(args) > 1:
        send_command("follow", {"player": args[1]})
    else:
        send_command("chat", {"message": f"Unknown command: {command}"})

def send_command(command, args):
    msg = json.dumps({"command": command, "args": args}) + "\n"
    proc.stdin.write(msg)
    proc.stdin.flush()

threading.Thread(target=read_output, daemon=True).start()
threading.Thread(target=read_error, daemon=True).start()

try:
    while proc.poll() is None:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping bot...")
    proc.terminate()
