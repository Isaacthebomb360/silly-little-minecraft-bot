from pyautogui import *
from pymsgbox import confirm, prompt, alert
import time
import random
import pyperclip
import json
from datetime import datetime
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import threading
from queue import Queue
import re

FAILSAFE = True
screenWidth, screenHeight = size()
print(f"Screen size: {screenWidth}x{screenHeight}")

class Settings:
    def __init__(self):
        self.MaxRepeats = 5
        self.SimpleSettings = False
        self.commentary_enabled = True
        self.commentary_frequency = 0.3
        self.auto_move = True
        self.break_time_min = 300
        self.break_time_max = 900
        self.death_reaction_chance = 0.8
        self.chat_region = (int(screenWidth * 0.02), int(screenHeight * 0.7), 
                           int(screenWidth * 0.4), int(screenHeight * 0.25))
        self.ocr_confidence = 0.7
        self.monitoring_interval = 0.5
        
        # Toggleable tasks
        self.auto_eat = True
        self.auto_mine = True
        self.auto_chop = True
        self.auto_attack = True
        self.eat_interval = 120  # seconds between eating
        self.mine_duration = 60  # seconds to mine
        self.chop_duration = 60  # seconds to chop
        self.attack_duration = 30  # seconds to attack mobs
        self.hotbar_slots = {
            'food': 1,
            'pickaxe': 2,
            'axe': 3,
            'sword': 4
        }

class DeathDetector:
    def __init__(self):
        self.death_patterns = [
            r'.*died.*',
            r'.*slain by.*',
            r'.*was killed by.*',
            r'.*fell from.*',
            r'.*burned to death.*',
            r'.*drowned.*',
            r'.*blown up by.*',
            r'.*withered away.*',
            r'.*starved to death.*',
            r'.*squashed by.*',
            r'.*shot by.*',
            r'.*poked to death.*',
            r'.*tried to swim in lava.*',
            r'.*doomed to fall.*',
            r'.*blown up.*',
            r'.*fireballed.*',
            r'.*flames.*',
            r'.*fell out of the world.*',
            r'.*didn\'t want to live.*',
            r'.*discovered the floor was lava.*'
        ]
        self.recent_deaths = {}
        self.death_cooldown = 30  # seconds
        self.last_chat_hash = None
        
    def preprocess_image(self, image):
        """Enhance image for better OCR accuracy"""
        # Convert to grayscale
        gray = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(2.0)
        
        # Sharpening
        enhancer = ImageEnhance.Sharpness(gray)
        gray = enhancer.enhance(2.0)
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(gray)
        
        # Apply threshold to binary
        _, thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        return Image.fromarray(thresh)
    
    def extract_chat_text(self, chat_region):
        """Capture and extract text from chat region"""
        try:
            # Capture chat region
            screenshot = screenshot(region=chat_region)
            
            # Preprocess image
            processed_image = self.preprocess_image(screenshot)
            
            # Use pytesseract to extract text
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 :.,!?()[]_'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def is_death_message(self, text):
        """Check if text contains a death message"""
        if not text:
            return False, None
            
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                for pattern in self.death_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        return True, line
        return False, None
    
    def should_react_to_death(self, death_message):
        """Check if we should react to this death (cooldown and uniqueness)"""
        current_time = time.time()
        message_hash = hash(death_message)
        
        # Check cooldown
        if message_hash in self.recent_deaths:
            if current_time - self.recent_deaths[message_hash] < self.death_cooldown:
                return False
        
        # Update recent deaths
        self.recent_deaths[message_hash] = current_time
        
        # Clean up old entries
        old_entries = [msg for msg, timestamp in self.recent_deaths.items() 
                      if current_time - timestamp > self.death_cooldown * 2]
        for msg in old_entries:
            del self.recent_deaths[msg]
            
        return True

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
        if random.random() < currentSettings.commentary_frequency:
            if activity_type in self.messages:
                return random.choice(self.messages[activity_type])
            else:
                return random.choice(self.messages['general'])
        return None

currentSettings = Settings()
commentary_system = Commentary()
death_detector = DeathDetector()
currentRepeat = 0
start_time = time.time()

# Task timers
last_eat_time = 0
last_mine_time = 0
last_chop_time = 0
last_attack_time = 0

# Monitoring control
monitoring_active = True
death_queue = Queue()

def load_settings():
    global currentSettings
    try:
        with open('minecraft_settings.json', 'r') as f:
            settings_data = json.load(f)
            currentSettings.MaxRepeats = settings_data.get('MaxRepeats', 5)
            currentSettings.SimpleSettings = settings_data.get('SimpleSettings', False)
            currentSettings.commentary_enabled = settings_data.get('commentary_enabled', True)
            currentSettings.commentary_frequency = settings_data.get('commentary_frequency', 0.3)
            currentSettings.auto_move = settings_data.get('auto_move', True)
            currentSettings.break_time_min = settings_data.get('break_time_min', 300)
            currentSettings.break_time_max = settings_data.get('break_time_max', 900)
            currentSettings.death_reaction_chance = settings_data.get('death_reaction_chance', 0.8)
            currentSettings.chat_region = tuple(settings_data.get('chat_region', currentSettings.chat_region))
            currentSettings.ocr_confidence = settings_data.get('ocr_confidence', 0.7)
            currentSettings.monitoring_interval = settings_data.get('monitoring_interval', 0.5)
            
            # Load task toggles
            currentSettings.auto_eat = settings_data.get('auto_eat', True)
            currentSettings.auto_mine = settings_data.get('auto_mine', True)
            currentSettings.auto_chop = settings_data.get('auto_chop', True)
            currentSettings.auto_attack = settings_data.get('auto_attack', True)
            currentSettings.eat_interval = settings_data.get('eat_interval', 120)
            currentSettings.mine_duration = settings_data.get('mine_duration', 60)
            currentSettings.chop_duration = settings_data.get('chop_duration', 60)
            currentSettings.attack_duration = settings_data.get('attack_duration', 30)
            currentSettings.hotbar_slots = settings_data.get('hotbar_slots', currentSettings.hotbar_slots)
    except FileNotFoundError:
        save_settings()

def save_settings():
    with open('minecraft_settings.json', 'w') as f:
        settings_data = {
            'MaxRepeats': currentSettings.MaxRepeats,
            'SimpleSettings': currentSettings.SimpleSettings,
            'commentary_enabled': currentSettings.commentary_enabled,
            'commentary_frequency': currentSettings.commentary_frequency,
            'auto_move': currentSettings.auto_move,
            'break_time_min': currentSettings.break_time_min,
            'break_time_max': currentSettings.break_time_max,
            'death_reaction_chance': currentSettings.death_reaction_chance,
            'chat_region': currentSettings.chat_region,
            'ocr_confidence': currentSettings.ocr_confidence,
            'monitoring_interval': currentSettings.monitoring_interval,
            
            # Save task toggles
            'auto_eat': currentSettings.auto_eat,
            'auto_mine': currentSettings.auto_mine,
            'auto_chop': currentSettings.auto_chop,
            'auto_attack': currentSettings.auto_attack,
            'eat_interval': currentSettings.eat_interval,
            'mine_duration': currentSettings.mine_duration,
            'chop_duration': currentSettings.chop_duration,
            'attack_duration': currentSettings.attack_duration,
            'hotbar_slots': currentSettings.hotbar_slots
        }
        json.dump(settings_data, f)

load_settings()

def death_monitoring_thread():
    """Continuous death monitoring in separate thread"""
    global monitoring_active
    last_check = 0
    
    print("Death monitoring thread started")
    
    while monitoring_active:
        try:
            current_time = time.time()
            
            # Only check at specified intervals
            if current_time - last_check >= currentSettings.monitoring_interval:
                # Extract text from chat
                chat_text = death_detector.extract_chat_text(currentSettings.chat_region)
                
                if chat_text:
                    # Check for death messages
                    is_death, death_message = death_detector.is_death_message(chat_text)
                    
                    if is_death and death_detector.should_react_to_death(death_message):
                        print(f"Death detected: {death_message}")
                        death_queue.put(death_message)
                
                last_check = current_time
            
            time.sleep(0.1)  # Small sleep to prevent CPU overload
            
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(1)

def process_death_messages():
    """Process detected death messages from the queue"""
    while not death_queue.empty():
        death_message = death_queue.get()
        
        if currentSettings.commentary_enabled:
            if random.random() < currentSettings.death_reaction_chance:
                reaction = commentary_system.get_commentary('death_reaction')
                if reaction:
                    send_chat_message(reaction)
                    print(f"Reacted to death: {reaction}")

def move_to_smart(x, y, duration=0.5):
    """Move mouse with slight randomness to appear more human"""
    target_x = x + random.randint(-5, 5)
    target_y = y + random.randint(-5, 5)
    
    target_x = max(0, min(target_x, screenWidth - 1))
    target_y = max(0, min(target_y, screenHeight - 1))
    
    moveTo(target_x, target_y, duration=duration)

def type_with_delay(text, delay_between_keys=0.05):
    """Type text with random delays between keystrokes"""
    for char in text:
        typewrite(char)
        time.sleep(random.uniform(delay_between_keys * 0.5, delay_between_keys * 1.5))

def send_chat_message(message):
    """Send a message in Minecraft chat"""
    press('t')  # Open chat
    time.sleep(random.uniform(0.2, 0.5))
    type_with_delay(message)
    time.sleep(random.uniform(0.1, 0.3))
    press('enter')
    print(f"Chat: {message}")

def perform_commentary(activity_type):
    """Potentially send commentary for the current activity"""
    if currentSettings.commentary_enabled:
        message = commentary_system.get_commentary(activity_type)
        if message:
            send_chat_message(message)

def switch_to_hotbar(slot):
    """Switch to a specific hotbar slot"""
    if 1 <= slot <= 9:
        press(str(slot))
        time.sleep(random.uniform(0.1, 0.3))

def anti_afk_movement():
    """Perform anti-AFK movements"""
    if currentSettings.auto_move:
        movements = ['w', 'a', 's', 'd', 'space']
        random_movement = random.choice(movements)
        
        keyDown(random_movement)
        time.sleep(random.uniform(0.1, 0.5))
        keyUp(random_movement)
        
        current_x, current_y = position()
        move_to_smart(current_x, current_y, 0.3)

def eat_food():
    """Automatically eat food to restore hunger"""
    global last_eat_time
    
    current_time = time.time()
    if current_time - last_eat_time >= currentSettings.eat_interval:
        print("Time to eat!")
        
        # Switch to food slot
        switch_to_hotbar(currentSettings.hotbar_slots['food'])
        time.sleep(0.5)
        
        # Hold right click to eat
        mouseDown(button='right')
        eating_time = random.uniform(2.0, 3.0)  # Time to consume food
        time.sleep(eating_time)
        mouseUp(button='right')
        
        perform_commentary('eating')
        last_eat_time = current_time
        return True
    return False

def mine_ores():
    """Automatically mine for ores"""
    global last_mine_time
    
    current_time = time.time()
    if current_time - last_mine_time >= currentSettings.mine_duration:
        print("Time to mine!")
        
        # Switch to pickaxe
        switch_to_hotbar(currentSettings.hotbar_slots['pickaxe'])
        time.sleep(0.5)
        
        # Look slightly down to mine at feet level
        moveRel(0, 200, duration=0.5)
        
        # Mine for specified duration with breaks
        start_time = time.time()
        while time.time() - start_time < currentSettings.mine_duration:
            # Hold left click to mine
            mouseDown(button='left')
            
            # Random mining bursts
            mine_burst = random.uniform(3.0, 8.0)
            time.sleep(mine_burst)
            
            # Short break
            mouseUp(button='left')
            time.sleep(random.uniform(0.5, 1.5))
            
            # Small mouse movement to simulate looking around
            moveRel(random.randint(-100, 100), random.randint(-50, 50), duration=0.3)
            
            # Anti-AFK during mining
            if random.random() < 0.2:
                anti_afk_movement()
        
        perform_commentary('mining')
        last_mine_time = current_time
        return True
    return False

def chop_trees():
    """Automatically chop trees"""
    global last_chop_time
    
    current_time = time.time()
    if current_time - last_chop_time >= currentSettings.chop_duration:
        print("Time to chop trees!")
        
        # Switch to axe
        switch_to_hotbar(currentSettings.hotbar_slots['axe'])
        time.sleep(0.5)
        
        # Look straight ahead for trees
        moveRel(0, -100, duration=0.5)
        
        # Chop for specified duration with breaks
        start_time = time.time()
        while time.time() - start_time < currentSettings.chop_duration:
            # Hold left click to chop
            mouseDown(button='left')
            
            # Random chopping bursts
            chop_burst = random.uniform(2.0, 6.0)
            time.sleep(chop_burst)
            
            # Short break
            mouseUp(button='left')
            time.sleep(random.uniform(0.5, 1.0))
            
            # Look around for more trees
            moveRel(random.randint(-200, 200), random.randint(-100, 100), duration=0.4)
            
            # Anti-AFK during chopping
            if random.random() < 0.2:
                anti_afk_movement()
        
        perform_commentary('chopping')
        last_chop_time = current_time
        return True
    return False

def attack_mobs():
    """Automatically attack nearby mobs"""
    global last_attack_time
    
    current_time = time.time()
    if current_time - last_attack_time >= currentSettings.attack_duration:
        print("Time to attack mobs!")
        
        # Switch to sword
        switch_to_hotbar(currentSettings.hotbar_slots['sword'])
        time.sleep(0.5)
        
        # Attack for specified duration
        start_time = time.time()
        attack_count = 0
        
        while time.time() - start_time < currentSettings.attack_duration:
            # Look around for mobs
            moveRel(random.randint(-300, 300), random.randint(-150, 150), duration=0.3)
            
            # Attack if we "see" a mob (simulated)
            if random.random() < 0.3:  # 30% chance to "find" a mob
                # Rapid attacks
                for _ in range(random.randint(3, 8)):
                    click(button='left')
                    time.sleep(random.uniform(0.2, 0.5))
                attack_count += 1
            
            # Move around while fighting
            if random.random() < 0.4:
                movement_key = random.choice(['w', 'a', 's', 'd'])
                keyDown(movement_key)
                time.sleep(random.uniform(0.5, 1.5))
                keyUp(movement_key)
            
            time.sleep(1.0)
        
        if attack_count > 0:
            perform_commentary('attacking')
        
        last_attack_time = current_time
        return True
    return False

def take_break():
    """Take a random break to appear more human"""
    break_time = random.randint(currentSettings.break_time_min, currentSettings.break_time_max)
    print(f"Taking a break for {break_time} seconds...")
    
    start_break = time.time()
    while time.time() - start_break < break_time:
        if random.random() < 0.1:
            anti_afk_movement()
        time.sleep(5)

def shutdown():
    """Check if we should stop the bot"""
    time.sleep(2)
    global currentRepeat
    
    if currentRepeat >= currentSettings.MaxRepeats:
        elapsed_time = time.time() - start_time
        hours = elapsed_time // 3600
        minutes = (elapsed_time % 3600) // 60
        print(f"Session completed: {int(hours)}h {int(minutes)}m")
        
        if currentSettings.SimpleSettings:
            answer = confirm('Session complete! Exit program?', buttons=['Yes', 'No'])
            return answer == 'No'
        else:
            answer = confirm(
                f'Completed {currentSettings.MaxRepeats} cycles!\n'
                f'Run time: {int(hours)}h {int(minutes)}m\n'
                'What would you like to do?',
                buttons=['Continue', 'Change Settings', 'Exit']
            )
            
            if answer == 'Change Settings':
                change_settings()
                return True
            elif answer == 'Continue':
                currentRepeat = 0
                return True
            else:
                return False
    
    currentRepeat += 1
    return True

def change_settings():
    """Change bot settings"""
    global currentSettings
    
    if currentSettings.SimpleSettings:
        new_repeats = prompt('Max repeats:', default=str(currentSettings.MaxRepeats))
        if new_repeats:
            try:
                currentSettings.MaxRepeats = int(new_repeats)
            except ValueError:
                alert("Invalid number!")
    else:
        options = [
            f"Max Repeats (current: {currentSettings.MaxRepeats})",
            f"Auto Eat (current: {'ON' if currentSettings.auto_eat else 'OFF'})",
            f"Auto Mine (current: {'ON' if currentSettings.auto_mine else 'OFF'})",
            f"Auto Chop (current: {'ON' if currentSettings.auto_chop else 'OFF'})",
            f"Auto Attack (current: {'ON' if currentSettings.auto_attack else 'OFF'})",
            f"Commentary (current: {'ON' if currentSettings.commentary_enabled else 'OFF'})",
            f"Death Reaction (current: {'ON' if currentSettings.death_reaction_chance > 0 else 'OFF'})",
            f"Auto Movement (current: {'ON' if currentSettings.auto_move else 'OFF'})",
            "Task Timers",
            "Back to Main"
        ]
        
        choice = confirm("Change Settings:", buttons=options)
        
        if choice == options[0]:
            try:
                new_repeats = int(prompt("Max repeats:", default=str(currentSettings.MaxRepeats)))
                currentSettings.MaxRepeats = new_repeats
            except ValueError:
                alert("Invalid number!")
        elif choice == options[1]:
            currentSettings.auto_eat = not currentSettings.auto_eat
        elif choice == options[2]:
            currentSettings.auto_mine = not currentSettings.auto_mine
        elif choice == options[3]:
            currentSettings.auto_chop = not currentSettings.auto_chop
        elif choice == options[4]:
            currentSettings.auto_attack = not currentSettings.auto_attack
        elif choice == options[5]:
            currentSettings.commentary_enabled = not currentSettings.commentary_enabled
        elif choice == options[6]:
            currentSettings.death_reaction_chance = 0.8 if currentSettings.death_reaction_chance == 0 else 0
        elif choice == options[7]:
            currentSettings.auto_move = not currentSettings.auto_move
        elif choice == options[8]:
            change_task_timers()
    
    save_settings()

def change_task_timers():
    """Change timing settings for tasks"""
    try:
        new_eat = int(prompt("Eat interval (seconds):", default=str(currentSettings.eat_interval)))
        new_mine = int(prompt("Mine duration (seconds):", default=str(currentSettings.mine_duration)))
        new_chop = int(prompt("Chop duration (seconds):", default=str(currentSettings.chop_duration)))
        new_attack = int(prompt("Attack duration (seconds):", default=str(currentSettings.attack_duration)))
        
        currentSettings.eat_interval = max(10, new_eat)
        currentSettings.mine_duration = max(10, new_mine)
        currentSettings.chop_duration = max(10, new_chop)
        currentSettings.attack_duration = max(10, new_attack)
    except ValueError:
        alert("Invalid number entered!")

# Start death monitoring thread
monitor_thread = threading.Thread(target=death_monitoring_thread, daemon=True)
monitor_thread.start()

# Main bot execution
print("Minecraft Bot starting in 5 seconds... Switch to Minecraft!")
time.sleep(5)

try:
    while shutdown():
        print(f"Cycle {currentRepeat}/{currentSettings.MaxRepeats}")
        
        # Process death messages
        process_death_messages()
        
        # Perform automated tasks based on settings
        tasks_performed = 0
        
        if currentSettings.auto_eat:
            if eat_food():
                tasks_performed += 1
        
        if currentSettings.auto_mine:
            if mine_ores():
                tasks_performed += 1
        
        if currentSettings.auto_chop:
            if chop_trees():
                tasks_performed += 1
        
        if currentSettings.auto_attack:
            if attack_mobs():
                tasks_performed += 1
        
        # Anti-AFK between tasks
        anti_afk_movement()
        
        # If no tasks were performed this cycle, take a short break
        if tasks_performed == 0:
            time.sleep(10)
        
        # Random break between cycles
        if random.random() < 0.3:
            take_break()

except KeyboardInterrupt:
    print("\nBot stopped by user")

finally:
    monitoring_active = False
    save_settings()
    print("Minecraft Bot stopped. Settings saved.")
