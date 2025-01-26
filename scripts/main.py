import os
import pyautogui
import pytesseract
import time
import logging
import json
import screeninfo
import cv2
import numpy as np
from PIL import Image, ImageGrab
from pynput import keyboard
from dataclasses import dataclass
from typing import Dict, List, Tuple


class GameBot:
    def __init__(self):
        pyautogui.FAILSAFE = False  # Add this line
        self.running = True
        self.current_location = None
        self.play = False
        self.setup_keyboard_listener()
        self.setup_logging()
        self.load_config('config.json')
        self.initialize_game_state()
        self.setup_screen()
        
    def setup_keyboard_listener(self):
        def on_press(key):
            if key == keyboard.Key.f9:
                print("Bot stopped")
                os._exit(0)  # Force exit the entire program
                    
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='bot_debug.log'
        )
        
    def load_config(self, config_path: str):
        with open(config_path) as f:
            self.config = json.load(f)
            
    def initialize_game_state(self):
        self.level = 0
        self.resets = 0
        self.current_x = 0
        self.current_y = 0
        self.consecutive_errors = 0
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def setup_screen(self):
        monitor = screeninfo.get_monitors()[1]
        self.screen_width = monitor.width
        self.screen_height = monitor.height
        logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
    def get_position_data(self):
        """Gets game coordinates (x,y) via OCR"""
        try:
            x1, y1, x2, y2 = self.config['ocr_coordinates']['position']
            coord_area = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
            return pytesseract.image_to_string(coord_area, config=config).strip()
        except Exception as e:
            logging.error(f"Position fetch failed: {e}")
            raise ValueError("Position fetch failed")

    '''
    def move_with_mouse(self, target_x: int, target_y: int):
        """Moves character using mouse clicks based on relative position"""
        char_center_x = self.screen_width // 2 
        char_center_y = self.screen_height // 2

        # Calculate direction
        dx = target_x - self.current_x
        dy = target_y - self.current_y
        
        # Click offset from character center
        click_x = char_center_x + (50 if dx > 0 else -50 if dx < 0 else 0)
        click_y = char_center_y + (50 if dy > 0 else -50 if dy < 0 else 0)
        
        pyautogui.click(click_x, click_y)
        time.sleep(0.5)
    '''
        
    def is_valid_coordinate(self, coordinate_str: str) -> bool:
        """
        Validates coordinate string format (x,y).
        """
        try:
            x, y = coordinate_str.split(',')
            return x.strip().isdigit() and y.strip().isdigit()
        except ValueError:
            return False

        
    def _fetch_position(self):
        """
        Simulated method to fetch the current position. Replace with actual implementation.
        Returns:
            tuple: A tuple of (current_x, current_y)
        Raises:
            ValueError: If position data is invalid.
        """
        # Simulate fetching the position; replace with actual logic
        raw_data = self.get_position_data()
        if not self.is_valid_coordinate(raw_data):
            raise ValueError(f"Invalid coordinate format: '{raw_data}'")
        return map(int, raw_data.split(','))

    def get_current_position(self, retries=10, delay=1):
        """
        Attempts to retrieve the current position of the bot, retrying if necessary.
        Args:
            retries (int): Number of times to retry fetching the position.
            delay (int): Delay between retries in seconds.
        Returns:
            bool: True if the position was successfully fetched, False otherwise.
        """
        for attempt in range(retries):
            try:
                # Replace this with the actual logic to fetch current position
                self.current_x, self.current_y = self._fetch_position()
                logging.info(f"Current position fetched: ({self.current_x}, {self.current_y})")
                return True
            except ValueError as e:
                logging.warning(f"Attempt {attempt + 1} failed to get current position: {e}")
                time.sleep(delay)

        logging.error(f"Failed to fetch current position after {retries} retries.")
        return False

    def _preprocess_image(self, img_path):
        try:
            os.makedirs('ocr_images/raw', exist_ok=True)
            os.makedirs('ocr_images/processed', exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            img = Image.open(img_path)
            img_array = np.array(img)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            return thresh
        except Exception as e:
            logging.error(f"Image preprocessing error: {e}")
            return None

    def extract_numeric_value(self, text):
        try:
            return int(''.join(filter(str.isdigit, text.strip())))
        except ValueError:
            logging.warning(f"Failed to extract numeric value from text: '{text}'")
            return 0

    def read_stats(self):
        stats_check = ImageGrab.grab(bbox=self.config['ocr_coordinates']['level'])
        if stats_check.getpixel((0, 0))[0] < 100:
            pyautogui.press('c')
            time.sleep(1)

        try:
            # Process reset
            reset_coords = self.config['ocr_coordinates']['reset']
            reset_area = ImageGrab.grab(bbox=tuple(reset_coords))
            reset_path = 'reset_test.png'
            reset_area.save(reset_path)
            
            reset_thresh = self._preprocess_image(reset_path)
            if reset_thresh is not None:
                reset_text = pytesseract.image_to_string(Image.fromarray(reset_thresh), config=r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789')
                reset_numeric_value = self.extract_numeric_value(reset_text)
                
                logging.info(f"Reset got from image: {reset_numeric_value}")
                
                if reset_numeric_value < self.resets:
                    logging.error("Probably bad read.")
                    return self.read_stats()
                self.resets = reset_numeric_value

        except Exception as e:
            logging.error(f"Error reading resets: {e}")

        try:
            # Process level
            level_coords = self.config['ocr_coordinates']['level']
            level_area = ImageGrab.grab(bbox=tuple(level_coords))
            level_path = 'level_test.png'
            level_area.save(level_path)
            
            level_thresh = self._preprocess_image(level_path)
            if level_thresh is not None:
                level_text = pytesseract.image_to_string(Image.fromarray(level_thresh), config=r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789')
                level_numeric_value = self.extract_numeric_value(level_text)
                
                logging.info(f"Level got from image: {level_numeric_value}")
                
                if level_numeric_value < self.level or level_numeric_value > self.config['max_level']:
                    logging.error("Probably bad read.")
                    return self.read_stats()
                self.level = level_numeric_value

        except Exception as e:
            logging.error(f"Error reading level: {e}")

        if self.level == 0 and self.resets == 0:
            return self.read_stats()

        pyautogui.press('c')
        return self.level, self.resets
    
    def move_with_keys(self, target_x: int, target_y: int):
        diff_x = target_x - self.current_x
        diff_y = target_y - self.current_y
        
        # Use AWSD keys to nudge around
        while abs(diff_x) > 5 or abs(diff_y) > 5:
            if diff_x > 0:
                pyautogui.press('d')  # Move right
            elif diff_x < 0:
                pyautogui.press('a')  # Move left

            if diff_y > 0:
                pyautogui.press('s')  # Move down
            elif diff_y < 0:
                pyautogui.press('w')  # Move up
            
            time.sleep(0.5)
            if not self.get_current_position():
                break

            diff_x = target_x - self.current_x
            diff_y = target_y - self.current_y
            
    def move_with_mouse(self, move_x: int, move_y: int):
        """
        Simulates movement relative to character position
        """
        # Get character's current screen position (center)
        char_x = self.screen_width // 2
        char_y = self.screen_height // 2
        
        # Calculate click position relative to character
        click_x = char_x + (move_x * 50)  # Adjust multiplier as needed
        click_y = char_y + (move_y * 50)
        
        # Ensure clicks stay within screen bounds
        click_x = max(0, min(click_x, self.screen_width))
        click_y = max(0, min(click_y, self.screen_height))
        
        pyautogui.click(int(click_x), int(click_y))

    '''
    # This code make a simulation, not real awsd or move keyboard
    def move_to_coordinates(self, target_x: int, target_y: int):
        if not self.get_current_position():
            return
            
        while True:
            dx = abs(self.current_x - target_x)
            dy = abs(self.current_y - target_y)
            
            if dx <= 20 and dy <= 20:
                self.check_and_click_play(target_x, target_y)
                break
                
            active_window = pyautogui.getActiveWindow()
            game_window = None
            
            # Find game window on second monitor
            for window in pyautogui.getAllWindows():
                if "your_game_title" in window.title.lower():  # Replace with your game's window title
                    game_window = window
                    break
                    
            if game_window:
                game_window.activate()
                
                if dx > 20 and dy > 20:
                    if self.current_x < target_x and self.current_y < target_y:
                        pyautogui.write(['right', 'down'])
                    elif self.current_x < target_x and self.current_y > target_y:
                        pyautogui.write(['right', 'up'])
                    elif self.current_x > target_x and self.current_y < target_y:
                        pyautogui.write(['left', 'down'])
                    elif self.current_x > target_x and self.current_y > target_y:
                        pyautogui.write(['left', 'up'])
                else:
                    if dx > 20:
                        pyautogui.write('right' if self.current_x < target_x else 'left')
                    if dy > 20:
                        pyautogui.write('down' if self.current_y < target_y else 'up')
                
                if active_window:
                    active_window.activate()
                    
            time.sleep(0.2)
            
            if not self.get_current_position():
                break
    '''

    def move_to_coordinates(self, target_x: int, target_y: int):
        if not self.get_current_position():
            return
                
        last_pos = {'x': self.current_x, 'y': self.current_y}
        stuck_count = 0
        
        while True:
            if not self.get_current_position():
                time.sleep(0.5)
                continue
                
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            
            if abs(dx) <= 20 and abs(dy) <= 20:
                self.check_and_click_play(target_x, target_y)
                break
                
            # Check if stuck
            if abs(self.current_x - last_pos['x']) < 5 and abs(self.current_y - last_pos['y']) < 5:
                stuck_count += 1
                if stuck_count > 3:
                    # Try to move away from obstacle
                    for _ in range(3):
                        pyautogui.press('right' if dx < 0 else 'left')  # Move opposite direction
                        time.sleep(0.3)
                    stuck_count = 0
                    continue
                    
            last_pos = {'x': self.current_x, 'y': self.current_y}
            
            if abs(dx) > 20:
                pyautogui.press('left' if dx < 0 else 'right')
                time.sleep(0.3)
                
            if abs(dy) > 20:
                pyautogui.press('up' if dy > 0 else 'down')
                time.sleep(0.3)

    def avoid_obstacle(self, target_x, target_y, last_position):
        directions = [
            ['up'], ['right'], ['down'], ['left'],
            ['up', 'right'], ['up', 'left'],
            ['down', 'right'], ['down', 'left']
        ]
        
        for direction in directions:
            pyautogui.press(direction)
            time.sleep(0.3)
            if self.get_current_position():
                if abs(self.current_x - last_position['x']) > 5 or abs(self.current_y - last_position['y']) > 5:
                    break
                    
    def calculate_and_move(self, target_x, target_y):
        dx = target_x - self.current_x
        dy = target_y - self.current_y
        
        if abs(dx) > abs(dy):
            pyautogui.press('left' if dx < 0 else 'right')
            time.sleep(0.1)
            if dy != 0:
                pyautogui.press('up' if dy < 0 else 'down')
        else:
            pyautogui.press('up' if dy < 0 else 'down')
            time.sleep(0.1)
            if dx != 0:
                pyautogui.press('left' if dx < 0 else 'right')


    def distribute_points(self):
        points = self.resets * 300
        
        for stat, ratio in self.config['stat_distribution'].items():
            stat_points = int(points * ratio)
            try:
                stat_area = pyautogui.locateOnScreen(f'{stat}_text.png')
                if stat_area:
                    plus_button = (stat_area[0] + 150, stat_area[1])
                    self.add_points(plus_button, stat_points)
            except Exception as e:
                logging.error(f"Error adding points to {stat}: {e}")

    def add_points(self, button_pos: Tuple[int, int], points: int):
        remaining = points
        while remaining > 0:
            pyautogui.click(button_pos)
            time.sleep(0.5)
            if remaining >= 1000:
                pyautogui.click(button_pos[0] + 50, button_pos[1])
                remaining -= 1000
            else:
                break

    def move_to_location(self, command: str):
        location = command.replace('/move ', '')
        if location != self.current_location:
            pyautogui.press('enter')
            pyautogui.write(command)
            pyautogui.press('enter')
            time.sleep(1)
            self.current_location = location

    def check_and_click_play(self, x, y):
        try:
            play_coords = self.config['ocr_coordinates']['play']
            play_button_area = ImageGrab.grab(bbox=tuple(play_coords))
            play_button_area.save('play_button_area.png')
            
            if abs(self.current_x - x) <= 20 and abs(self.current_y - y) <= 20 and not self.play:
                pyautogui.click(play_coords[0] + 5, play_coords[1] + 3)
                self.play = True
                logging.info("Play button clicked - was inactive (green)")
            elif self.play:
                logging.info("Play already active (red) - skipping click")
                
        except Exception as e:
            logging.error(f"Error checking play button: {e}")


    def reset_character(self):
        pyautogui.press('enter')
        pyautogui.write('/reset')
        self.level = 0
        self.resets = 0
        pyautogui.press('enter')
        time.sleep(2)
        self.distribute_points()

    def run(self):
        while self.running:  # Changed from while True
            try:
                if not self.running:
                    return
                
                pyautogui.click(self.screen_width // 2, self.screen_height // 2)  # Focus game at the center
                time.sleep(0.5)
                
                if self.consecutive_errors > self.config['error_threshold']:
                    self.move_to_location('/move lorencia')
                    time.sleep(5)
                    self.consecutive_errors = 0
                    
                level, resets = self.read_stats()
                
                if level >= self.config['reset_level'] <= self.config['max_level']:
                    self.reset_character()

                if level < self.config['max_level']:
                    for threshold, obj in sorted(self.config['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                        logging.info(f"Treshold: {threshold}")
                        logging.info(f"Location: {obj}")
                        if level >= int(threshold):
                            self.move_to_location(obj["command"])
                            x = obj["location"][0]
                            y = obj["location"][1]
                            self.move_to_coordinates(x,y)
                            self.check_and_click_play(x,y)
                            break
                
                self.consecutive_errors = 0
                time.sleep(self.config['check_interval'])
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.consecutive_errors += 1
                logging.error(f"Error: {e}")

if __name__ == "__main__":
    bot = GameBot()
    time.sleep(5)
    bot.run()