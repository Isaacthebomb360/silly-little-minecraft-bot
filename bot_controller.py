import subprocess
import threading
import json
import time
import os

HOST = "localhost"
PORT = 52387
USERNAME = "IsaacsFembo(y)t"
ALLOWED_USER = "Isaacthebomb360"
COMMAND_PREFIX = "!"

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
    
    match command:
        case "hello":
            send_command("chat", {"message": f"Hello {user}!"})
        case "status":
            send_command("chat", {"message": "All systems nominal."})
        case "time":
            send_command("chat", {"message": f"Current time is {time.strftime('%H:%M:%S')}"})
        case "date":
            send_command("chat", {"message": f"Today's date is {time.strftime('%Y-%m-%d')}"})
        case "report":
            send_command("chat", {"message": f"Status report for {time.strftime('%Y-%m-%d %H:%M:%S')}: All systems nominal."})
            
        case "jump":
            send_command("jump", {})
        case "come":
            send_command("come", {"player": user})
        case "respawn":
            send_command("respawn", {})
        case "help":
            send_command("help", {})
        case "chest":
            send_command("chest", {})
        case "follow":
            target = args[1] if len(args) > 1 else user
            send_command("follow", {"player": target})
        case "stop":
            send_command("stop", {})
        case "deforest":
            send_command("deforest", {})
        case "farm":
            send_command("farm", {})
        case "stripmine":
            if len(args) > 6:
                send_command("stripmine", {
                    "start": {"x": int(args[1]), "y": int(args[2]), "z": int(args[3])},
                    "end": {"x": int(args[4]), "y": int(args[5]), "z": int(args[6])}
                })
            else:
                send_command("chat", {"message": "Usage: !stripmine x1 y1 z1 x2 y2 z2"})
        case "equip":
            send_command("equip", {})
        case "defend":
            send_command("defend", {})
        case "sethome":
            send_command("sethome", {})
        case "home":
            send_command("home", {})
        case "auto":
            if len(args) > 1:
                if args[1] == "on":
                    send_command("auto", {"state": True})
                elif args[1] == "off":
                    send_command("auto", {"state": False})
                else:
                    send_command("chat", {"message": "Usage: !auto <on/off>"})
            else:
                send_command("auto", {})
        case _:
            send_command("chat", {"message": f"Unknown command: {command}"})
'''
        case "move":
            if len(args) > 1:
                send_command("move", {"direction": args[1]})
            else :
                send_command("chat", {"message": "Usage: !move <direction>"})
        case "pickup":
            send_command("pickup", {})
        case "chop":
            send_command("chop", {})
        case "follow-me":
            send_command("follow-me", {"player": user})
'''

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
