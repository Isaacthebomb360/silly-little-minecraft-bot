import lodestone
import json
import time
import random
import threading
from queue import Queue
import re
from pymsgbox import confirm, prompt, alert

class MinecraftBot:
    def __init__(self):
        self.settings = self.load_settings()
        self.bot = None
        self.running = False
        self.current_cycle = 0
        self.start_time = time.time()
        self.death_queue = Queue()
        self.commentary_system = Commentary()
        
        # Task timers
        self.last_eat_time = 0
        self.last_mine_time = 0
        self.last_chop_time = 0
        self.last_attack_time = 0
        
    def load_settings(self):
        default_settings = {
            'server_host': 'localhost',
            'server_port': 25565,
            'bot_username': 'AutoBot',
            'max_cycles': 5,
            'auto_eat': True,
            'auto_mine': True,
            'auto_chop': True,
            'auto_attack': True,
            'commentary_enabled': True,
            'commentary_frequency': 0.3,
            'death_reaction_chance': 0.8,
            'eat_interval': 120,
            'mine_duration': 60,
            'chop_duration': 60,
            'attack_duration': 30,
            'break_time_min': 300,
            'break_time_max': 900,
            'simple_settings': False
        }
        
        try:
            with open('minecraft_bot_settings.json', 'r') as f:
                loaded = json.load(f)
                # Merge with defaults
                for key in default_settings:
                    if key in loaded:
                        default_settings[key] = loaded[key]
        except FileNotFoundError:
            self.save_settings(default_settings)
            
        return default_settings
    
    def save_settings(self, settings=None):
        if settings is None:
            settings = self.settings
        with open('minecraft_bot_settings.json', 'w') as f:
            json.dump(settings, f, indent=2)
    
    def connect_bot(self):
        """Connect to Minecraft server using Lodestone"""
        try:
            print(f"Connecting to {self.settings['server_host']}:{self.settings['server_port']}...")
            
            self.bot = lodestone.createBot({
                'host': self.settings['server_host'],
                'port': self.settings['server_port'],
                'username': self.settings['bot_username'],
                'auth': 'microsoft',
                'logErrors': True,
                'hideErrors': False
            })
            
            # Set up event handlers
            self.setup_event_handlers()
            
            print("Bot connected successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def setup_event_handlers(self):
        """Set up Lodestone event handlers"""
        # Chat message handler for death detection
        @self.bot.on('messagestr')
        def handle_message(message):
            self.handle_chat_message(message)
        
        # Spawn event - bot is ready
        @self.bot.on('spawn')
        def handle_spawn():
            print("Bot has spawned in the world!")
            self.bot.chat("Auto-bot activated! Ready to work.")
        
        # Health and hunger monitoring
        @self.bot.on('health')
        def handle_health():
            if self.bot.health < 10:
                print(f"Low health! Current health: {self.bot.health}")
        
        @self.bot.on('food')
        def handle_food():
            if self.bot.food < 15:
                print(f"Low food! Current food: {self.bot.food}")
    
    def handle_chat_message(self, message):
        """Handle chat messages for death detection"""
        death_patterns = [
            r'.*died.*',
            r'.*was slain by.*', 
            r'.*was killed by.*',
            r'.*fell from.*',
            r'.*burned to death.*',
            r'.*drowned.*',
            r'.*blown up by.*',
            r'.*withered away.*'
        ]
        
        message_lower = message.lower()
        for pattern in death_patterns:
            if re.match(pattern, message_lower):
                print(f"Death detected: {message}")
                if (self.settings['commentary_enabled'] and 
                    random.random() < self.settings['death_reaction_chance']):
                    reaction = self.commentary_system.get_commentary('death_reaction')
                    if reaction:
                        self.bot.chat(reaction)
                        print(f"Reacted to death: {reaction}")
                break
    
    def find_and_equip_tool(self, tool_type):
        """Find and equip a tool from inventory"""
        try:
            tool_items = {
                'pickaxe': ['diamond_pickaxe', 'iron_pickaxe', 'stone_pickaxe', 'wooden_pickaxe'],
                'axe': ['diamond_axe', 'iron_axe', 'stone_axe', 'wooden_axe'],
                'sword': ['diamond_sword', 'iron_sword', 'stone_sword', 'wooden_sword'],
                'food': ['cooked_beef', 'cooked_porkchop', 'bread', 'apple', 'golden_carrot']
            }
            
            if tool_type not in tool_items:
                return False
            
            for item_name in tool_items[tool_type]:
                item = self.bot.inventory.findInventoryItem(item_name)
                if item:
                    self.bot.equip(item, 'hand')
                    time.sleep(1)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error equipping {tool_type}: {e}")
            return False
    
    def auto_eat(self):
        """Automatically eat when hungry"""
        if not self.settings['auto_eat']:
            return False
            
        current_time = time.time()
        if (current_time - self.last_eat_time >= self.settings['eat_interval'] or 
            (hasattr(self.bot, 'food') and self.bot.food < 18)):
            
            if self.find_and_equip_tool('food'):
                print("Eating food...")
                self.bot.activateItem()
                time.sleep(2.5)  # Eating takes time
                self.last_eat_time = current_time
                
                if random.random() < self.settings['commentary_frequency']:
                    commentary = self.commentary_system.get_commentary('eating')
                    if commentary:
                        self.bot.chat(commentary)
                return True
            else:
                print("No food found in inventory!")
                
        return False
    
    def auto_mine(self):
        """Automatically mine nearby blocks"""
        if not self.settings['auto_mine']:
            return False
            
        current_time = time.time()
        if current_time - self.last_mine_time >= self.settings['mine_duration']:
            print("Starting mining...")
            
            if self.find_and_equip_tool('pickaxe'):
                # Look for nearby blocks to mine
                blocks_to_mine = ['diamond_ore', 'iron_ore', 'coal_ore', 'gold_ore', 'stone', 'cobblestone']
                
                start_time = time.time()
                while time.time() - start_time < self.settings['mine_duration']:
                    found_block = False
                    
                    # Look for blocks in range
                    for block_name in blocks_to_mine:
                        block = self.bot.findBlock({
                            'matching': self.bot.registry.blocksByName[block_name].id,
                            'maxDistance': 5
                        })
                        
                        if block:
                            print(f"Found {block_name}, mining...")
                            try:
                                self.bot.dig(block)
                                found_block = True
                                # Random commentary chance
                                if random.random() < 0.1 and self.settings['commentary_enabled']:
                                    commentary = self.commentary_system.get_commentary('mining')
                                    if commentary:
                                        self.bot.chat(commentary)
                                break
                            except Exception as e:
                                print(f"Error mining: {e}")
                    
                    if not found_block:
                        # Move around to find more blocks
                        self.random_movement()
                        time.sleep(2)
                    
                    time.sleep(1)
                
                self.last_mine_time = current_time
                return True
                
        return False
    
    def auto_chop(self):
        """Automatically chop nearby trees"""
        if not self.settings['auto_chop']:
            return False
            
        current_time = time.time()
        if current_time - self.last_chop_time >= self.settings['chop_duration']:
            print("Starting wood cutting...")
            
            if self.find_and_equip_tool('axe'):
                # Look for trees to chop
                wood_blocks = ['oak_log', 'spruce_log', 'birch_log', 'jungle_log', 'acacia_log', 'dark_oak_log']
                
                start_time = time.time()
                while time.time() - start_time < self.settings['chop_duration']:
                    found_tree = False
                    
                    for block_name in wood_blocks:
                        block = self.bot.findBlock({
                            'matching': self.bot.registry.blocksByName[block_name].id,
                            'maxDistance': 6
                        })
                        
                        if block:
                            print(f"Found {block_name}, chopping...")
                            try:
                                self.bot.dig(block)
                                found_tree = True
                                # Random commentary chance
                                if random.random() < 0.1 and self.settings['commentary_enabled']:
                                    commentary = self.commentary_system.get_commentary('chopping')
                                    if commentary:
                                        self.bot.chat(commentary)
                                break
                            except Exception as e:
                                print(f"Error chopping: {e}")
                    
                    if not found_tree:
                        # Move around to find more trees
                        self.random_movement()
                        time.sleep(2)
                    
                    time.sleep(1)
                
                self.last_chop_time = current_time
                return True
                
        return False
    
    def auto_attack(self):
        """Automatically attack nearby hostile mobs"""
        if not self.settings['auto_attack']:
            return False
            
        current_time = time.time()
        if current_time - self.last_attack_time >= self.settings['attack_duration']:
            print("Looking for mobs to attack...")
            
            if self.find_and_equip_tool('sword'):
                # Find hostile mobs
                hostile_mobs = ['zombie', 'skeleton', 'spider', 'creeper', 'enderman']
                attacked = False
                
                start_time = time.time()
                while time.time() - start_time < self.settings['attack_duration']:
                    for entity_name in hostile_mobs:
                        entity = self.bot.nearestEntity(lambda e: e.name.lower() == entity_name and 
                                                       self.bot.entity.position.distanceTo(e.position) < 8)
                        if entity:
                            print(f"Found {entity_name}, attacking!")
                            try:
                                self.bot.attack(entity)
                                attacked = True
                                # Random commentary chance
                                if random.random() < 0.2 and self.settings['commentary_enabled']:
                                    commentary = self.commentary_system.get_commentary('attacking')
                                    if commentary:
                                        self.bot.chat(commentary)
                                time.sleep(1)
                            except Exception as e:
                                print(f"Error attacking: {e}")
                    
                    if not attacked:
                        # Move around to find mobs
                        self.random_movement()
                        time.sleep(2)
                    
                    time.sleep(1)
                
                self.last_attack_time = current_time
                return attacked
                
        return False
    
    def random_movement(self):
        """Perform random movement to explore"""
        try:
            # Random direction
            directions = ['forward', 'back', 'left', 'right']
            direction = random.choice(directions)
            
            # Set control state for random duration
            if direction == 'forward':
                self.bot.setControlState('forward', True)
            elif direction == 'back':
                self.bot.setControlState('back', True)
            elif direction == 'left':
                self.bot.setControlState('left', True)
            elif direction == 'right':
                self.bot.setControlState('right', True)
            
            # Random jump chance
            if random.random() < 0.3:
                self.bot.setControlState('jump', True)
                time.sleep(0.5)
                self.bot.setControlState('jump', False)
            
            move_time = random.uniform(2, 5)
            time.sleep(move_time)
            
            # Stop movement
            self.bot.setControlState('forward', False)
            self.bot.setControlState('back', False)
            self.bot.setControlState('left', False)
            self.bot.setControlState('right', False)
            
        except Exception as e:
            print(f"Error in random movement: {e}")
    
    def take_break(self):
        """Take a random break"""
        break_time = random.randint(
            self.settings['break_time_min'], 
            self.settings['break_time_max']
        )
        print(f"Taking a break for {break_time} seconds...")
        
        start_break = time.time()
        while time.time() - start_break < break_time and self.running:
            # Occasional small movements during break
            if random.random() < 0.1:
                self.random_movement()
            time.sleep(5)
    
    def change_settings(self):
        """Interactive settings menu"""
        options = [
            f"Server Host (current: {self.settings['server_host']})",
            f"Server Port (current: {self.settings['server_port']})",
            f"Bot Username (current: {self.settings['bot_username']})",
            f"Max Cycles (current: {self.settings['max_cycles']})",
            f"Auto Eat (current: {'ON' if self.settings['auto_eat'] else 'OFF'})",
            f"Auto Mine (current: {'ON' if self.settings['auto_mine'] else 'OFF'})",
            f"Auto Chop (current: {'ON' if self.settings['auto_chop'] else 'OFF'})",
            f"Auto Attack (current: {'ON' if self.settings['auto_attack'] else 'OFF'})",
            f"Commentary (current: {'ON' if self.settings['commentary_enabled'] else 'OFF'})",
            "Back to Main"
        ]
        
        choice = confirm("Change Settings:", buttons=options)
        
        if choice == options[0]:
            new_host = prompt("Server Host:", default=self.settings['server_host'])
            if new_host:
                self.settings['server_host'] = new_host
        elif choice == options[1]:
            try:
                new_port = int(prompt("Server Port:", default=str(self.settings['server_port'])))
                self.settings['server_port'] = new_port
            except ValueError:
                alert("Invalid port number!")
        elif choice == options[2]:
            new_username = prompt("Bot Username:", default=self.settings['bot_username'])
            if new_username:
                self.settings['bot_username'] = new_username
        elif choice == options[3]:
            try:
                new_cycles = int(prompt("Max Cycles:", default=str(self.settings['max_cycles'])))
                self.settings['max_cycles'] = new_cycles
            except ValueError:
                alert("Invalid number!")
        elif choice == options[4]:
            self.settings['auto_eat'] = not self.settings['auto_eat']
        elif choice == options[5]:
            self.settings['auto_mine'] = not self.settings['auto_mine']
        elif choice == options[6]:
            self.settings['auto_chop'] = not self.settings['auto_chop']
        elif choice == options[7]:
            self.settings['auto_attack'] = not self.settings['auto_attack']
        elif choice == options[8]:
            self.settings['commentary_enabled'] = not self.settings['commentary_enabled']
        
        self.save_settings()
    
    def run(self):
        """Main bot execution loop"""
        print("Minecraft Auto-Bot Starting...")
        
        if not self.connect_bot():
            alert("Failed to connect to Minecraft server!")
            return
        
        self.running = True
        
        try:
            while self.running and self.current_cycle < self.settings['max_cycles']:
                print(f"Cycle {self.current_cycle + 1}/{self.settings['max_cycles']}")
                
                # Perform tasks
                tasks_performed = 0
                
                if self.auto_eat():
                    tasks_performed += 1
                
                if self.auto_mine():
                    tasks_performed += 1
                
                if self.auto_chop():
                    tasks_performed += 1
                
                if self.auto_attack():
                    tasks_performed += 1
                
                # Random movement between tasks
                self.random_movement()
                
                # Random break
                if random.random() < 0.3:
                    self.take_break()
                
                self.current_cycle += 1
                time.sleep(10)  # Brief pause between cycles
            
            # Completion
            elapsed_time = time.time() - self.start_time
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            
            if self.current_cycle >= self.settings['max_cycles']:
                self.bot.chat(f"Completed {self.settings['max_cycles']} cycles! Total time: {hours}h {minutes}m")
                print(f"Session completed: {hours}h {minutes}m")
            
        except KeyboardInterrupt:
            print("\nBot stopped by user")
        except Exception as e:
            print(f"Bot error: {e}")
        finally:
            self.running = False
            if self.bot:
                self.bot.quit()
            self.save_settings()
            print("Bot stopped. Settings saved.")

class Commentary:
    def __init__(self):
        self.messages = {
            'mining': [
                "Time to get these diamonds!",
                "Mining away...",
                "This pickaxe is working hard!",
                "Found some good ore here!",
                "The mines are calling me!"
            ],
            'chopping': [
                "Timber!",
                "These trees won't chop themselves!",
                "Getting some quality wood!",
                "Forestry at its finest!",
                "Making room for new growth!"
            ],
            'attacking': [
                "Time to clear out some mobs!",
                "These monsters won't know what hit them!",
                "Protecting the area!",
                "Another mob bites the dust!",
                "Keeping things safe around here!"
            ],
            'eating': [
                "Time for a snack!",
                "Gotta keep my hunger bar full!",
                "This food really hits the spot!",
                "Refueling for more work!",
                "Mmm, tasty!"
            ],
            'death_reaction': [
                "omg you just died again to fall damage again",
                "LMAO how do you keep dying like that?",
                "Bruh... that was embarrassing",
                "Did I just witness a skill issue?",
                "You might want to avoid cliffs... just saying",
                "Another one bites the dust!",
                "Maybe try looking where you're going?",
                "That death was so bad it's almost impressive",
                "You're really testing those respawn mechanics!",
                "I've seen better survival skills from a chicken",
                "Maybe Minecraft isn't your game...",
                "You died so hard even the zombies felt bad",
                "Pro tip: The ground is not your friend",
                "That was a certified classic right there",
                "You make dying look easy!",
                "Are you trying to set a death record?",
                "That was spectacularly bad",
                "I could hear that death from here",
                "You should probably stick to creative mode",
                "That death deserves an award"
            ],
            'general': [
                "What a beautiful day in Minecraft!",
                "Automation makes life easier!",
                "Grinding those resources!",
                "Making progress!",
                "This bot is working hard!"
            ]
        }
    
    def get_commentary(self, activity_type):
        if activity_type in self.messages:
            return random.choice(self.messages[activity_type])
        return random.choice(self.messages['general'])

def main():
    bot = MinecraftBot()
    
    print("Minecraft Auto-Bot")
    print("==================")
    
    while True:
        options = [
            "Start Bot",
            "Change Settings", 
            "Exit"
        ]
        
        choice = confirm("Minecraft Auto-Bot", buttons=options)
        
        if choice == options[0]:
            bot.run()
        elif choice == options[1]:
            bot.change_settings()
        else:
            break

if __name__ == "__main__":
    main()
