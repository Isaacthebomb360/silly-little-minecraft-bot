import json
import threading
import time
import os
import sys
import math

try:
    import lodestone
except ImportError:
    print("Lodestone not found. Installing...")
    os.system("pip install lodestone")
    import lodestone

class MinecraftBot:
    def __init__(self, config_file="minecraft_bot_config2.json"):
        self.load_config(config_file)
        self.bot = None
        self.running = True
        self.current_task = None
        self.task_running = False
        
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
                },
                "tasks": {
                    "mining_depth": 10,
                    "woodcutting_radius": 15,
                    "safe_inventory_items": ["dirt", "cobblestone", "wooden_axe", "stone_axe", "iron_axe"]
                }
            }
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"📁 Created default config file: {config_file}")
            print("⚠️  Please edit minecraft_bot_config2.json with your server details before running!")
            sys.exit(1)
    
    def save_config(self, config_file="minecraft_bot_config2.json"):
        """Save current configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"💾 Configuration saved to {config_file}")
    
    def is_user_allowed(self, username):
        """Check if user is allowed to use commands"""
        return username in self.config["commands"]["allowed_users"] or "*" in self.config["commands"]["allowed_users"]
    
    def find_best_axe(self):
        """Find the best axe in inventory"""
        axe_priority = ['netherite_axe', 'diamond_axe', 'iron_axe', 'stone_axe', 'wooden_axe', 'golden_axe']
        for axe_type in axe_priority:
            for item in self.bot.inventory.items():
                if axe_type in item.name:
                    return item
        return None
    
    def find_best_pickaxe(self):
        """Find the best pickaxe in inventory"""
        pickaxe_priority = ['netherite_pickaxe', 'diamond_pickaxe', 'iron_pickaxe', 'stone_pickaxe', 'wooden_pickaxe', 'golden_pickaxe']
        for pick_type in pickaxe_priority:
            for item in self.bot.inventory.items():
                if pick_type in item.name:
                    return item
        return None
    
    def equip_tool(self, tool_name):
        """Equip a tool from inventory"""
        for slot, item in enumerate(self.bot.inventory.items()):
            if tool_name in item.name:
                self.bot.equip(item, "hand")
                print(f"🔧 Equipped {item.name}")
                return True
        print(f"❌ No {tool_name} found in inventory")
        return False
    
    def chop_tree(self):
        """Chop down a single tree"""
        try:
            # Look for nearby logs
            log_block = self.bot.findBlock({
                'matching': lambda block: any(log in block.name for log in ['log', 'wood']),
                'maxDistance': self.config["tasks"]["woodcutting_radius"],
                'useExtraInfo': False
            })
            
            if not log_block:
                print("🌳 No trees found nearby")
                return False
            
            print(f"🪵 Found {log_block.name} at {log_block.position}")
            
            # Equip best axe
            if not self.equip_tool("axe"):
                print("⚠️  No axe found, using bare hands")
            
            # Move to the tree
            self.bot.chat("Chopping tree...")
            self.bot.lookAt(log_block.position)
            time.sleep(1)
            
            # Break the log block
            self.bot.dig(log_block)
            
            # Look for more connected logs (the rest of the tree)
            for _ in range(20):  # Limit tree height
                time.sleep(0.5)
                next_log = self.bot.findBlock({
                    'matching': lambda block: any(log in block.name for log in ['log', 'wood']),
                    'maxDistance': 10,
                    'point': log_block.position.offset(0, 1, 0)  # Look above
                })
                
                if next_log:
                    self.bot.lookAt(next_log.position)
                    self.bot.dig(next_log)
                else:
                    break
            
            print("✅ Finished chopping tree")
            return True
            
        except Exception as e:
            print(f"❌ Error chopping tree: {e}")
            return False
    
    def woodcutting_task(self, count=5):
        """Automated woodcutting - chop multiple trees"""
        if self.task_running:
            self.bot.chat("Another task is already running!")
            return
            
        self.task_running = True
        self.current_task = "woodcutting"
        trees_chopped = 0
        
        self.bot.chat(f"Starting woodcutting task - target: {count} trees")
        
        for i in range(count):
            if not self.task_running:
                break
                
            print(f"🌳 Chopping tree {i+1}/{count}")
            if self.chop_tree():
                trees_chopped += 1
            else:
                self.bot.chat("No more trees found nearby")
                break
            
            # Short break between trees
            time.sleep(2)
        
        self.bot.chat(f"Woodcutting complete! Chopped {trees_chopped} trees")
        self.task_running = False
        self.current_task = None
    
    def strip_mine(self, length=10, direction='forward'):
        """Create a strip mine tunnel"""
        if self.task_running:
            self.bot.chat("Another task is already running!")
            return
            
        self.task_running = True
        self.current_task = "mining"
        
        try:
            # Equip best pickaxe
            if not self.equip_tool("pickaxe"):
                self.bot.chat("❌ No pickaxe found! Cannot mine.")
                self.task_running = False
                return
            
            self.bot.chat(f"Starting strip mine - length: {length} blocks")
            
            # Determine mining direction based on current facing
            yaw = self.bot.entity.yaw
            directions = {
                'forward': (0, 0),
                'back': (math.pi, 0),
                'left': (math.pi/2, 0),
                'right': (-math.pi/2, 0)
            }
            
            if direction in directions:
                target_yaw, target_pitch = directions[direction]
                self.bot.look(target_yaw, target_pitch)
            time.sleep(1)
            
            # Start mining tunnel (2x1 pattern)
            for block_num in range(length):
                if not self.task_running:
                    break
                    
                print(f"⛏️ Mining block {block_num + 1}/{length}")
                
                # Mine forward block
                forward_block = self.bot.blockAt(self.bot.entity.position.offset(1, 0, 0))
                if forward_block and forward_block.name != 'air':
                    self.bot.dig(forward_block)
                
                # Mine forward-up block (for 2-high tunnel)
                forward_up_block = self.bot.blockAt(self.bot.entity.position.offset(1, 1, 0))
                if forward_up_block and forward_up_block.name != 'air':
                    self.bot.dig(forward_up_block)
                
                # Move forward
                self.bot.setControlState('forward', True)
                time.sleep(0.5)
                self.bot.setControlState('forward', False)
                
                # Check for valuable ores in nearby blocks
                self.check_for_ores()
                
                # Place torch occasionally
                if block_num % 5 == 0 and block_num > 0:
                    self.place_torch()
            
            self.bot.chat("✅ Strip mining complete!")
            
        except Exception as e:
            print(f"❌ Error during mining: {e}")
            self.bot.chat("Mining task failed!")
        
        self.task_running = False
        self.current_task = None
    
    def check_for_ores(self):
        """Check for valuable ores around the bot"""
        ore_blocks = ['diamond_ore', 'iron_ore', 'gold_ore', 'coal_ore', 'redstone_ore', 'lapis_ore', 'emerald_ore']
        
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                for dz in [-2, -1, 0, 1, 2]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    
                    check_pos = self.bot.entity.position.offset(dx, dy, dz)
                    block = self.bot.blockAt(check_pos)
                    
                    if block and any(ore in block.name for ore in ore_blocks):
                        print(f"💎 Found {block.name} at {check_pos}!")
                        self.bot.chat(f"Found {block.name.replace('_', ' ')} nearby!")
    
    def place_torch(self):
        """Place a torch if available"""
        try:
            # Find torch in inventory
            torch_item = None
            for item in self.bot.inventory.items():
                if 'torch' in item.name:
                    torch_item = item
                    break
            
            if torch_item:
                # Look for suitable placement position
                place_pos = self.bot.entity.position.offset(0, 1, 0)
                if self.bot.blockAt(place_pos).name == 'air':
                    self.bot.equip(torch_item, "hand")
                    self.bot.placeBlock(place_pos)
                    print("🔦 Placed torch")
        except Exception as e:
            print(f"❌ Couldn't place torch: {e}")
    
    def collect_nearby_items(self, radius=10):
        """Collect nearby dropped items"""
        try:
            items_collected = 0
            for entity_id, entity in self.bot.entities.items():
                if (entity.name == 'item' and 
                    entity.position.distanceTo(self.bot.entity.position) <= radius):
                    print(f"🎁 Collecting {entity.name}")
                    self.bot.lookAt(entity.position)
                    time.sleep(0.5)
                    items_collected += 1
            
            if items_collected > 0:
                print(f"📦 Collected {items_collected} items")
            return items_collected
        except Exception as e:
            print(f"❌ Error collecting items: {e}")
            return 0
    
    def handle_chat(self, username, message):
        """Handle in-game chat commands"""
        try:
            if username == self.bot.username:
                return
                
            prefix = self.config["commands"]["prefix"]
            
            if not message.startswith(prefix):
                return
                
            if not self.is_user_allowed(username):
                self.bot.chat(f"Sorry {username}, you're not allowed to use commands.")
                return
            
            command = message[len(prefix):].split()
            cmd = command[0].lower() if command else ""
            args = command[1:] if len(command) > 1 else []
            
            print(f"🎮 Chat command from {username}: {cmd} {args}")
            
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
                self.task_running = False
                
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
                
            elif cmd == "pos" or cmd == "position":
                pos = self.bot.pos
                self.bot.chat(f"My position: x={pos.x:.1f}, y={pos.y:.1f}, z={pos.z:.1f}")
                
            # Task commands
            elif cmd == "chop" or cmd == "woodcut":
                count = int(args[0]) if args else 3
                self.bot.chat(f"Starting to chop {count} trees...")
                threading.Thread(target=self.woodcutting_task, args=(count,), daemon=True).start()
                
            elif cmd == "mine" or cmd == "strip mine":
                length = int(args[0]) if args else 10
                direction = args[1] if len(args) > 1 else 'forward'
                self.bot.chat(f"Starting strip mine {length} blocks...")
                threading.Thread(target=self.strip_mine, args=(length, direction), daemon=True).start()
                
            elif cmd == "collect":
                self.bot.chat("Collecting nearby items...")
                collected = self.collect_nearby_items()
                self.bot.chat(f"Collected {collected} items!")
                
            elif cmd == "inventory" or cmd == "inv":
                items = self.bot.inventory.items()
                if items:
                    item_counts = {}
                    for item in items:
                        item_counts[item.name] = item_counts.get(item.name, 0) + item.count
                    
                    # Send inventory in chunks to avoid chat limits
                    msg = "Inventory: "
                    for i, (name, count) in enumerate(item_counts.items()):
                        if i < 5:  # First 5 items
                            msg += f"{name}({count}) "
                    
                    self.bot.chat(msg.strip())
                    if len(item_counts) > 5:
                        self.bot.chat(f"... and {len(item_counts) - 5} more items")
                else:
                    self.bot.chat("Inventory is empty")
                    
            elif cmd == "task" or cmd == "status":
                if self.task_running:
                    self.bot.chat(f"Currently performing: {self.current_task}")
                else:
                    self.bot.chat("No active task")
                    
            elif cmd == "help":
                help_text = [
                    "Available commands:",
                    f"{prefix}come - Come to your position",
                    f"{prefix}stop - Stop moving/tasks",
                    f"{prefix}chop [number] - Chop trees",
                    f"{prefix}mine [length] - Strip mine",
                    f"{prefix}collect - Collect nearby items",
                    f"{prefix}inventory - Show inventory",
                    f"{prefix}task - Show current task",
                    f"{prefix}help - Show this help"
                ]
                for line in help_text:
                    self.bot.chat(line)
                    time.sleep(0.1)
                    
            else:
                self.bot.chat(f"Unknown command: {cmd}. Type {prefix}help for available commands.")
                
        except Exception as e:
            print(f"❌ Error handling chat command: {e}")
    
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
                elif args and args[0].lower() == "back":
                    self.bot.setControlState('back', True)
                    print("🚶 Moving back...")
                elif args and args[0].lower() == "left":
                    self.bot.setControlState('left', True)
                    print("🚶 Moving left...")
                elif args and args[0].lower() == "right":
                    self.bot.setControlState('right', True)
                    print("🚶 Moving right...")
                else:
                    self.bot.stop()
                    print("🛑 Stopped moving")
                    
            elif cmd == "jump":
                self.bot.jump()
                print("🦘 Jumped!")
                
            elif cmd == "come" and args:
                target_name = args[0]
                target = self.bot.players.get(target_name)
                if target:
                    print(f"🎯 Coming to {target_name}...")
                    self.bot.goto(target.pos)
                else:
                    print(f"❌ Player {target_name} not found")
                    
            elif cmd == "stop":
                self.bot.stop()
                self.task_running = False
                print("🛑 Stopped all actions and tasks")
                
            # Task commands
            elif cmd == "chop" or cmd == "woodcut":
                count = int(args[0]) if args else 5
                print(f"🌳 Starting woodcutting task: {count} trees")
                threading.Thread(target=self.woodcutting_task, args=(count,), daemon=True).start()
                
            elif cmd == "mine" or cmd == "strip mine":
                length = int(args[0]) if args else 10
                direction = args[1] if len(args) > 1 else 'forward'
                print(f"⛏️ Starting strip mine: {length} blocks")
                threading.Thread(target=self.strip_mine, args=(length, direction), daemon=True).start()
                
            elif cmd == "collect":
                print("🎁 Collecting nearby items...")
                collected = self.collect_nearby_items()
                print(f"📦 Collected {collected} items!")
                
            elif cmd == "inventory" or cmd == "inv":
                items = self.bot.inventory.items()
                if items:
                    print("🎒 Inventory:")
                    item_counts = {}
                    for item in items:
                        item_counts[item.name] = item_counts.get(item.name, 0) + item.count
                    
                    for name, count in item_counts.items():
                        print(f"  - {name}: {count}")
                else:
                    print("🎒 Inventory is empty")
                    
            elif cmd == "players":
                players = [name for name in self.bot.players if name != self.bot.username]
                if players:
                    print("👥 Online players:")
                    for player in players:
                        print(f"  - {player}")
                else:
                    print("👥 No other players online")
                    
            elif cmd == "position" or cmd == "pos":
                if hasattr(self.bot, 'pos'):
                    pos = self.bot.pos
                    print(f"📍 Position: x={pos.x:.1f}, y={pos.y:.1f}, z={pos.z:.1f}")
                else:
                    print("📍 Position not available yet")
                    
            elif cmd == "task" or cmd == "status":
                if self.task_running:
                    print(f"🔄 Current task: {self.current_task}")
                else:
                    print("✅ No active task")
                    
            elif cmd == "config":
                if args and args[0] == "reload":
                    self.load_config("minecraft_bot_config2.json")
                    print("🔄 Configuration reloaded!")
                elif args and args[0] == "save":
                    self.save_config()
                else:
                    print("📝 Config commands: reload, save")
                    
            elif cmd == "quit" or cmd == "exit":
                print("👋 Disconnecting...")
                self.running = False
                self.task_running = False
                if self.bot:
                    self.bot.quit()
                os._exit(0)
                
            elif cmd == "help":
                print("""
🎮 Terminal Commands:
  say <message>        - Send chat message
  move <direction>     - Move (forward/back/left/right/stop)
  jump                 - Make the bot jump
  come <player>        - Come to specific player
  stop                 - Stop all actions and tasks
  
🛠️ Task Commands:
  chop [number]        - Chop trees (default: 5)
  mine [length]        - Strip mine (default: 10 blocks)
  collect              - Collect nearby items
  inventory / inv      - Show bot's inventory
  task / status        - Show current task status
  
📊 Info Commands:
  players              - List online players
  position / pos       - Show bot's position
  config reload/save   - Manage configuration
  quit / exit          - Disconnect the bot
  help                 - Show this help

🎮 In-Game Chat Commands (prefix: {}):
  !chop, !mine, !collect, !inventory, !task, !stop, etc.
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
                self.task_running = False
                if self.bot:
                    self.bot.quit()
                break
            except Exception as e:
                print(f"❌ Terminal input error: {e}")
    
    def setup_bot_events(self):
        """Set up all the bot event handlers"""
        @self.bot.on("spawn")
        def handle_spawn():
            print("✅ Bot successfully spawned in the world!")
            if hasattr(self.bot, 'pos'):
                print(f"📍 Position: {self.bot.pos}")
            
        @self.bot.on("chat")
        def handle_chat(username, message):
            self.handle_chat(username, message)
            
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
            
        @self.bot.on("message")
        def handle_message(json_msg, position):
            """Handle server messages"""
            if position == "system" or position == "game_info":
                print(f"📢 Server: {json_msg}")
    
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
                version=self.config["server"].get("version")
            )
            
            # Set up all event handlers
            self.setup_bot_events()
            
            # Wait a moment for bot to initialize
            time.sleep(2)
            
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
    print("🎮 Advanced Minecraft Bot with Tasks")
    print("=" * 45)
    
    # Check if config file exists, if not create it
    if not os.path.exists("minecraft_bot_config2.json"):
        print("📝 First-time setup: Creating minecraft_bot_config2.json...")
        bot = MinecraftBot("minecraft_bot_config2.json")
        return
    
    # Start the bot
    bot = MinecraftBot()
    bot.start_bot()

if __name__ == "__main__":
    main()
