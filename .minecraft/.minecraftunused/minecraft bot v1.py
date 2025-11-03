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
            'fishing': [
                "Waiting for the big one...",
                "This is so relaxing!",
                "Hope I catch something rare!",
                "Perfect fishing weather!",
                "The fish are biting today!"
            ],
            'chopping': [
                "Timber!",
                "These trees won't chop themselves!",
                "Getting some quality wood!",
                "Forestry at its finest!",
                "Making room for new growth!"
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
            'monitoring_interval': currentSettings.monitoring_interval
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

def take_break():
    """Take a random break to appear more human"""
    break_time = random.randint(currentSettings.break_time_min, currentSettings.break_time_max)
    print(f"Taking a break for {break_time} seconds...")
    
    start_break = time.time()
    while time.time() - start_break < break_time:
        if random.random() < 0.1:
            anti_afk_movement()
        time.sleep(5)

def execute_task(command, activity_type, wait_before=2, wait_after=3):
    """Execute a Minecraft command with commentary"""
    # Process any death messages first
    process_death_messages()
    
    anti_afk_movement()
    
    time.sleep(random.uniform(wait_before * 0.8, wait_before * 1.2))
    
    press('t')
    time.sleep(random.uniform(0.2, 0.4))
    type_with_delay(command)
    time.sleep(random.uniform(0.1, 0.3))
    press('enter')
    
    print(f"Executed: {command}")
    
    perform_commentary(activity_type)
    
    anti_afk_movement()
    
    time.sleep(random.uniform(wait_after * 0.8, wait_after * 1.2))

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
            f"Commentary (current: {'ON' if currentSettings.commentary_enabled else 'OFF'})",
            f"Commentary Frequency (current: {currentSettings.commentary_frequency})",
            f"Death Reaction Chance (current: {currentSettings.death_reaction_chance})",
            f"Auto Movement (current: {'ON' if currentSettings.auto_move else 'OFF'})",
            "Calibrate Chat Region",
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
            currentSettings.commentary_enabled = not currentSettings.commentary_enabled
        elif choice == options[2]:
            try:
                new_freq = float(prompt("Commentary frequency (0-1):", default=str(currentSettings.commentary_frequency)))
                currentSettings.commentary_frequency = max(0, min(1, new_freq))
            except ValueError:
                alert("Invalid number!")
        elif choice == options[3]:
            try:
                new_chance = float(prompt("Death reaction chance (0-1):", 
                                        default=str(currentSettings.death_reaction_chance)))
                currentSettings.death_reaction_chance = max(0, min(1, new_chance))
            except ValueError:
                alert("Invalid number!")
        elif choice == options[4]:
            currentSettings.auto_move = not currentSettings.auto_move
        elif choice == options[5]:
            calibrate_chat_region()
    
    save_settings()

def calibrate_chat_region():
    """Help user calibrate the chat region for better detection"""
    alert("The chat region will be highlighted. Adjust the values in settings if needed.")
    # This would typically show a visual calibration tool
    # For now, we'll just use the default region
    print("Chat region calibration: Using default region")

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
        
        # Execute various Minecraft tasks
        execute_task('/herb', 'general')
        execute_task('/skill_fish', 'fishing')
        execute_task('/mine', 'mining', wait_before=4)
        execute_task('/chop', 'chopping')
        
        # Random break between cycles
        if random.random() < 0.3:
            take_break()

except KeyboardInterrupt:
    print("\nBot stopped by user")

finally:
    monitoring_active = False
    save_settings()
    print("Minecraft Bot stopped. Settings saved.")
