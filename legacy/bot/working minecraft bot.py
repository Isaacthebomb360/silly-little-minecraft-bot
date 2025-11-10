# bot_pycraft.py
from minecraft.networking.connection import Connection
from minecraft.networking.packets import ChatMessagePacket, JoinGamePacket, serverbound
import threading
import time

HOST = "localhost"
PORT = 53887
USERNAME = "IsaacsFembo(y)t"
ALLOWED_USER = "Isaacthebombo360"
COMMAND_PREFIX = "!bot"

conn = Connection(HOST, PORT, username=USERNAME, auth_token=None)

def on_join_game(join_packet):
    print("✅ Bot joined the game.")
    conn.write_packet(serverbound.play.ChatPacket(message="Hello world from bot!"))

def on_chat(packet):
    # packet.json_data is the raw JSON string from server
    json_data = packet.json_data  
    # We expect something like {"translate":"chat.type.text","with":[<user>,<message>]} or similar
    # We’ll extract username and message rudimentarily
    import json
    try:
        data = json.loads(json_data)
        if 'with' in data:
            user = data['with'][0]
            message = data['with'][1]
        else:
            return
    except Exception as e:
        return

    print(f"💬 Chat from {user}: {message}")
    if user == ALLOWED_USER and message.startswith(COMMAND_PREFIX):
        cmd = message[len(COMMAND_PREFIX):].strip().lower()
        if cmd == "hello":
            conn.write_packet(serverbound.play.ChatPacket(message=f"Hello {user}!"))
        elif cmd == "status":
            conn.write_packet(serverbound.play.ChatPacket(message="All systems nominal."))
        else:
            conn.write_packet(serverbound.play.ChatPacket(message=f"Unknown command: {cmd}"))

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
