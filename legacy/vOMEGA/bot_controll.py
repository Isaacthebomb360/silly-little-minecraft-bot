# bot_control.py
import subprocess, threading, json, queue, os, time

NODE_PATH = "node"
BOT_JS = "vOMEGA/bot.js"

class BotController:
    def __init__(self, host="localhost", port=25565, username="PyBot", auth="offline"):
        env = os.environ.copy()
        env["MC_HOST"] = host
        env["MC_PORT"] = str(port)
        env["MC_USERNAME"] = username
        env["MC_AUTH"] = auth

        self.proc = subprocess.Popen(
            [NODE_PATH, BOT_JS],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        self._events = queue.Queue()
        threading.Thread(target=self._reader_thread, daemon=True).start()

    def _reader_thread(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[node-out]", line)
                continue
            self._events.put(obj)

    def send(self, cmd):
        data = json.dumps(cmd, separators=(",", ":")) + "\n"
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def send_chat(self, msg, id=None):
        self.send({"type": "chat", "message": msg, "id": id})

    def follow(self, playername, id=None):
        self.send({"type": "follow", "player": playername, "id": id})

    def stop(self, id=None):
        self.send({"type": "stop", "id": id})

    def poll_event(self, timeout=0.1):
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()


if __name__ == "__main__":
    bot = BotController(host="localhost", port=53985, username="PythonBridgeBot")
    time.sleep(2)
    bot.send_chat("Hello from Python controller!")
    while True:
        ev = bot.poll_event()
        if ev:
            print("EVENT:", ev)
        time.sleep(0.1)
