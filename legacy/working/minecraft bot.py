import json
import threading
import time
import os
import sys

try:
    import lodestone
except ImportError:
    print("Lodestone not found. Installing...")
    os.system("pip install lodestone")
    import lodestone

class MinecraftBot:
    def __init__(self, config_file="minecraft_bot_config.json"):
        self.load_config(config_file)
        self.bot = None
        self.running = True
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Configuration loaded from {config_file}")
        except FileNotFoundError:
            # Create default config
            self.config = {
                "server": {
                    "host": "localhost",
                    "port": 25565,
                    "version": "1.19.2"
                },
                "bot": {
                    "username": "PythonBot",
                    "auth": "offline"
                },
                "commands": {
                    "prefix": "!",
                    "allowed_users": ["YourUsername"]
                }
            }
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"📁 Created default config file: {config_file}")
            print("⚠️  Please edit config.json with your server details before running!")
            sys.exit(1)
    
    def save_config(self, config_file="config.json"):
        """Save current configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"💾 Configuration saved to {config_file}")
    
    def is_user_allowed(self, username):
        """Check if user is allowed to use commands"""
        return username in self.config["commands"]["allowed_users"] or "*" in self.config["commands"]["allowed_users"]
    
    def handle_chat(self, username, message):
        """Handle in-game chat commands"""
        try:
            prefix = self.config["commands"]["prefix"]
            
            if not message.startswith(prefix):
                return
                
            if not self.is_user_allowed(username):
                self.bot.chat(f"Sorry {username}, you're not allowed to use commands.")
                return
            
            command = message[len(prefix):].split()
            cmd = command[0].lower() if command else ""
            args = command[1:] if len(command) > 1 else []
            
            if cmd == "come":
                target = self.bot.players.get(username)
                if target:
                    self.bot.chat(f"Coming to you, {username}!")
                    self.bot.goto(target.pos)
                else:
                    self.bot.chat("Can't find your position!")
                    
            elif cmd == "stop":
                self.bot.chat("Stopping!")
                self.bot.stop()
                
            elif cmd == "jump":
                self.bot.chat("Jumping!")
                self.bot.jump()
                
            elif cmd == "list":
                players = [name for name in self.bot.players if name != self.bot.username]
                if players:
                    self.bot.chat(f"Online players: {', '.join(players)}")
                else:
                    self.bot.chat("No other players online")
                    
            elif cmd == "say" and args:
                message_text = " ".join(args)
                self.bot.chat(message_text)
                
            elif cmd == "help":
                help_text = [
                    "Available commands:",
                    f"{prefix}come - Come to your position",
                    f"{prefix}stop - Stop moving",
                    f"{prefix}jump - Jump once",
                    f"{prefix}list - List online players",
                    f"{prefix}say <message> - Send a message",
                    f"{prefix}help - Show this help"
                ]
                for line in help_text:
                    self.bot.chat(line)
                    
            else:
                self.bot.chat(f"Unknown command: {cmd}. Type {prefix}help for available commands.")
                
        except Exception as e:
            print(f"Error handling chat command: {e}")
    
    def handle_terminal_command(self, command_input):
        """Handle terminal input commands"""
        try:
            command = command_input.strip().split()
            if not command:
                return
                
            cmd = command[0].lower()
            args = command[1:] if len(command) > 1 else []
            
            if cmd == "say" and args:
                message = " ".join(args)
                self.bot.chat(message)
                print(f"💬 Sent: {message}")
                
            elif cmd == "move":
                if args and args[0].lower() == "forward":
                    self.bot.setControlState('forward', True)
                    print("🚶 Moving forward...")
                else:
                    self.bot.stop()
                    print("🛑 Stopped moving")
                    
            elif cmd == "jump":
                self.bot.jump()
                print("🦘 Jumped!")
                
            elif cmd == "come" and args:
                # Come to specific player
                target_name = args[0]
                target = self.bot.players.get(target_name)
                if target:
                    print(f"🎯 Coming to {target_name}...")
                    self.bot.goto(target.pos)
                else:
                    print(f"❌ Player {target_name} not found")
                    
            elif cmd == "stop":
                self.bot.stop()
                print("🛑 Stopped all actions")
                
            elif cmd == "inventory":
                try:
                    items = self.bot.inventory.items()
                    if items:
                        print("🎒 Inventory:")
                        for item in items:
                            print(f"  - {item.name} x{item.count}")
                    else:
                        print("🎒 Inventory is empty")
                except Exception as e:
                    print(f"❌ Could not access inventory: {e}")
                    
            elif cmd == "players":
                players = [name for name in self.bot.players if name != self.bot.username]
                if players:
                    print("👥 Online players:")
                    for player in players:
                        print(f"  - {player}")
                else:
                    print("👥 No other players online")
                    
            elif cmd == "config":
                if args and args[0] == "reload":
                    self.load_config("config.json")
                    print("🔄 Configuration reloaded!")
                elif args and args[0] == "save":
                    self.save_config()
                else:
                    print("📝 Config commands: reload, save")
                    
            elif cmd == "quit" or cmd == "exit":
                print("👋 Disconnecting...")
                self.running = False
                self.bot.quit()
                os._exit(0)
                
            elif cmd == "help":
                print("""
🎮 Terminal Commands:
  say <message>        - Send chat message
  move forward         - Start moving forward
  move stop            - Stop moving
  jump                 - Make the bot jump
  come <player>        - Come to specific player
  stop                 - Stop all actions
  inventory            - Show bot's inventory
  players              - List online players
  config reload        - Reload config from file
  config save          - Save current config
  quit / exit          - Disconnect the bot
  help                 - Show this help

🎮 In-Game Chat Commands (prefix: {}):
  !come, !stop, !jump, !list, !say <message>, !help
                """.format(self.config["commands"]["prefix"]))
                
            else:
                print('❌ Unknown command. Type "help" for available commands.')
                
        except Exception as e:
            print(f"❌ Error executing command: {e}")
    
    def terminal_input_loop(self):
        """Main loop for terminal input"""
        print("✅ Bot is running! Type 'help' for commands.")
        while self.running:
            try:
                user_input = input("> ")
                self.handle_terminal_command(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Shutting down...")
                self.running = False
                if self.bot:
                    self.bot.quit()
                break
            except Exception as e:
                print(f"❌ Terminal input error: {e}")
    
    def start_bot(self):
        """Start the Minecraft bot"""
        print("🚀 Starting Minecraft Bot...")
        print(f"🔗 Connecting to {self.config['server']['host']}:{self.config['server']['port']}")
        print(f"🤖 Bot username: {self.config['bot']['username']}")
        
        try:
            # Create the bot instance
            self.bot = lodestone.createBot(
                host=self.config["server"]["host"],
                port=self.config["server"]["port"],
                username=self.config["bot"]["username"],
                auth=self.config["bot"]["auth"],
                version=self.config["server"].get("version"),
                chat=self.handle_chat
            )
            
            # Set up bot event handlers
            @self.bot.on("spawn")
            def handle_spawn():
                print("✅ Bot successfully spawned in the world!")
                print(f"📍 Position: {self.bot.pos}")
                
            @self.bot.on("error")
            def handle_error(error):
                print(f"❌ Bot error: {error}")
                
            @self.bot.on("kicked")
            def handle_kicked(reason):
                print(f"🔌 Bot was kicked: {reason}")
                self.running = False
                
            @self.bot.on("end")
            def handle_end():
                print("🔌 Connection closed")
                self.running = False
                
            # Start terminal input in a separate thread
            terminal_thread = threading.Thread(target=self.terminal_input_loop, daemon=True)
            terminal_thread.start()
            
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            self.running = False

def main():
    print("🎮 Minecraft Bot with JSON Configuration")
    print("=" * 40)
    
    # Check if config file exists, if not create it
    if not os.path.exists("minecraft_bot_config.json"):
        print("📝 First-time setup: Creating minecraft_bot_config.json...")
        bot = MinecraftBot("minecraft_bot_config.json")
        return
    
    # Start the bot
    bot = MinecraftBot()
    bot.start_bot()

if __name__ == "__main__":
    main()