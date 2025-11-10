from minecraft.networking.connection import Connection
from minecraft.networking.packets import ChatMessagePacket, serverbound, JoinGamePacket
from threading import Thread
import time

# === CONFIG ===
HOST = "localhost"
PORT = 42069
USERNAME = "PythonBot"

# === Setup connection ===
conn = Connection(HOST, PORT, username=USERNAME)

def on_join_game(join_game_packet):
    print("✅ Bot joined the game!")
    conn.write_packet(serverbound.play.ChatPacket(message="Hello from PythonBot!"))

def on_chat(packet):
    msg = packet.json_data
    print("💬 Chat:", msg)

    # Simple command handling
    if "come" in msg.lower():
        conn.write_packet(serverbound.play.ChatPacket(message="I'm here!"))
    if "jump" in msg.lower():
        conn.write_packet(serverbound.play.ChatPacket(message="Boing! 🐸"))

def keep_alive():
    """Keeps the connection open and alive"""
    while True:
        time.sleep(10)
        try:
            conn.write_packet(serverbound.play.ChatPacket(message="...still alive"))
        except:
            break

# === Register events ===
#conn.register_packet_listener(on_join_game, "join_game")
conn.register_packet_listener(on_join_game, JoinGamePacket)
conn.register_packet_listener(on_chat, ChatMessagePacket)

# === Start connection ===
conn.connect()
Thread(target=keep_alive, daemon=True).start()

print("🤖 Bot connected, waiting for packets...")
try:
    # This keeps the script alive and processes incoming packets
    while conn.connected:
        conn.networking_thread.join(1)
except KeyboardInterrupt:
    print("\n👋 Shutting down bot...")
    conn.disconnect()
