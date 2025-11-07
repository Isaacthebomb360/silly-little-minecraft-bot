# bot_pycraft_advanced.py
from minecraft.networking.connection import Connection
from minecraft.networking.packets import ChatMessagePacket, JoinGamePacket, serverbound
import threading, time, json, math

HOST = "localhost"
PORT = 62220
USERNAME = "IsaacsFembo(y)t"
ALLOWED_USER = "Isaacthebomb360"
COMMAND_PREFIX = "!bot"

conn = Connection(HOST, PORT, username=USERNAME, auth_token=None)

# Track the bot's position (rudimentary, needs server packets to update)
bot_pos = {"x": 0, "y": 0, "z": 0}

def update_position(packet):
    """Update bot position on join (rudimentary, only on spawn for now)"""
    if hasattr(packet, 'entity_id'):
        # For now just print entity ID
        print(f"Bot entity ID: {packet.entity_id}")

def move_bot(dx=0, dy=0, dz=0):
    """Send relative movement packets to server (basic simulation)"""
    # pyCraft does not provide high-level pathfinding, so this is very basic
    bot_pos['x'] += dx
    bot_pos['y'] += dy
    bot_pos['z'] += dz
    # Note: movement packets not implemented here, would require full protocol
    print(f"Moved bot to {bot_pos}")

def path_to(target_x, target_y, target_z):
    """Rudimentary straight-line pathing (no obstacles)"""
    steps = 10
    dx = (target_x - bot_pos['x']) / steps
    dy = (target_y - bot_pos['y']) / steps
    dz = (target_z - bot_pos['z']) / steps
    for i in range(steps):
        move_bot(dx, dy, dz)
        time.sleep(0.5)

def on_join_game(join_packet):
    print("✅ Bot joined the game.")
    conn.write_packet(serverbound.play.ChatPacket(message="Hello world from bot!"))

def on_chat(packet):
    try:
        data = json.loads(packet.json_data)
        if 'with' not in data:
            return
        user = data['with'][0]
        message = data['with'][1]
    except Exception:
        return

    print(f"💬 Chat from {user}: {message}")
    if user != ALLOWED_USER or not message.startswith(COMMAND_PREFIX):
        return

    cmd = message[len(COMMAND_PREFIX):].strip().lower()
    args = cmd.split()

    if not args:
        return

    command = args[0]

    if command == "hello":
        conn.write_packet(serverbound.play.ChatPacket(message=f"Hello {user}!"))
    elif command == "status":
        conn.write_packet(serverbound.play.ChatPacket(message="All systems nominal."))
    elif command == "jump":
        move_bot(dy=1)
        conn.write_packet(serverbound.play.ChatPacket(message="🦘 Jumped!"))
    elif command == "move":
        if len(args) < 2:
            conn.write_packet(serverbound.play.ChatPacket(message="Usage: !bot move <forward/back/left/right>"))
        else:
            dir = args[1]
            if dir == "forward":
                move_bot(dx=1)
            elif dir == "back":
                move_bot(dx=-1)
            elif dir == "left":
                move_bot(dz=-1)
            elif dir == "right":
                move_bot(dz=1)
            conn.write_packet(serverbound.play.ChatPacket(message=f"Moved {dir}"))
    elif command == "come":
        # rudimentary placeholder coordinates for target
        target_x, target_y, target_z = 10, bot_pos['y'], 10
        threading.Thread(target=path_to, args=(target_x, target_y, target_z), daemon=True).start()
        conn.write_packet(serverbound.play.ChatPacket(message=f"Coming to {ALLOWED_USER}!"))
    else:
        conn.write_packet(serverbound.play.ChatPacket(message=f"Unknown command: {command}"))

def keep_alive():
    while conn.connected:
        time.sleep(30)
        conn.write_packet(serverbound.play.ChatPacket(message="...still alive"))

conn.register_packet_listener(on_join_game, JoinGamePacket)
conn.register_packet_listener(on_chat, ChatMessagePacket)

conn.connect()
threading.Thread(target=keep_alive, daemon=True).start()

print("Bot running. Waiting for chat commands...")
try:
    while conn.connected:
        time.sleep(1)
except KeyboardInterrupt:
    print("👋 Shutting down bot.")
    conn.disconnect()
