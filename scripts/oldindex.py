import pyautogui
import pytesseract
import time
import logging
from PIL import ImageGrab

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_debug.log'
)

class GameBot:
    def __init__(self):
        self.level = 0
        self.resets = 0
        self.current_x = 0
        self.current_y = 0
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.screen_width, self.screen_height = pyautogui.size()
        logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
    def get_current_position(self):
        try:
            coords_area = ImageGrab.grab(bbox=(255, 26, 329, 48))
            coords_area.save('coords_area.png')
            coords_text = pytesseract.image_to_string(coords_area)
            logging.debug(f"Raw coordinates text: {coords_text}")
            
            coords = [int(s) for s in coords_text.split() if s.isdigit()]
            if len(coords) >= 2:
                self.current_x = coords[0]
                self.current_y = coords[1]
                logging.info(f"Current position: ({self.current_x}, {self.current_y})")
                return True
            return False
        except Exception as e:
            logging.error(f"Error reading coordinates: {e}")
            return False

    def move_toc_coordinates(self, target_x, target_y):
        if not self.get_current_position():
            logging.error("Failed to get current position")
            return

        logging.info(f"Moving from ({self.current_x}, {self.current_y}) to ({target_x}, {target_y})")
        
        while abs(self.current_x - target_x) > 5 or abs(self.current_y - target_y) > 5:
            diff_x = target_x - self.current_x
            diff_y = target_y - self.current_y
            
            if abs(diff_x) > 5:
                pos_x = self.screen_width - 10 if diff_x > 0 else 10
                pyautogui.moveTo(pos_x, self.screen_height // 2)
                pyautogui.mouseDown(button='left')
                time.sleep(0.5)
                pyautogui.mouseUp(button='left')
                
            if abs(diff_y) > 5:
                pos_y = 10 if diff_y > 0 else self.screen_height - 10
                pyautogui.moveTo(self.screen_width // 2, pos_y)
                pyautogui.mouseDown(button='left')
                time.sleep(0.5)
                pyautogui.mouseUp(button='left')

            if not self.get_current_position():
                break

    def read_stats(self):
        pyautogui.press('c')
        time.sleep(1)
        
        # Move to primary monitor
        self.screen_width = 1920
        self.screen_height = 1080
        
        try:
            # Right side of screen where stats show
            reset_area = ImageGrab.grab(bbox=(1112, 333, 1153, 354))
            reset_area.save('reset_area.png')
            reset_text = pytesseract.image_to_string(reset_area)
            logging.debug(f"Raw reset text: {reset_text}")
            self.resets = int(''.join(filter(str.isdigit, reset_text)))
        except Exception as e:
            logging.error(f"Error reading resets: {e}")
            self.resets = 0
            
        try:
            level_area = ImageGrab.grab(bbox=(1750, 210, 1850, 240)) 
            level_area.save('level_area.png')
            level_text = pytesseract.image_to_string(level_area)
            logging.debug(f"Raw level text: {level_text}")
            self.level = int(''.join(filter(str.isdigit, level_text)))
        except Exception as e:
            logging.error(f"Error reading level: {e}")
            self.level = 0

        pyautogui.press('c')
        return self.level, self.resets

    def distribute_points(self):
        points = self.resets * 300
        logging.info(f"Distributing {points} points")
        
        distribution = {
            'agility': int(points * 0.3),
            'vitality': int(points * 0.1),
            'energy': int(points * 0.6)
        }
        logging.debug(f"Point distribution: {distribution}")
        
        pyautogui.press('c')
        time.sleep(1)

        for stat, points in distribution.items():
            logging.info(f"Adding {points} points to {stat}")
            try:
                stat_area = pyautogui.locateOnScreen(f'{stat}_text.png')
                if stat_area:
                    plus_button = (stat_area[0] + 150, stat_area[1])
                    logging.debug(f"Found {stat} button at {plus_button}")
                    self.add_points(plus_button, points)
                else:
                    logging.error(f"Could not find {stat} button")
            except Exception as e:
                logging.error(f"Error adding points to {stat}: {e}")

        pyautogui.press('c')

    def add_points(self, button_pos, points):
        logging.info(f"Adding points at position {button_pos}")
        remaining = points
        while remaining > 0:
            pyautogui.click(button_pos)
            time.sleep(0.5)
            if remaining >= 1000:
                logging.debug("Clicking +1000 button")
                pyautogui.click(button_pos[0] + 50, button_pos[1])
                remaining -= 1000
                logging.debug(f"Remaining points: {remaining}")
            else:
                break

    def move_to_location(self, command):
        logging.info(f"Moving to location: {command}")
        pyautogui.press('enter')
        pyautogui.write(command)
        pyautogui.press('enter')
        time.sleep(1)

    def check_and_click_play(self):
        try:
            play_button_area = ImageGrab.grab(bbox=(300, 65, 307, 71))
            play_button_area.save('play_button_area.png')
            pyautogui.click(1800, 255)  # Click middle of the area
            logging.info("Clicked play button")
        except Exception as e:
            logging.error(f"Error clicking play button: {e}")

    def reset_character(self):
        logging.info("Resetting character")
        pyautogui.press('enter')
        pyautogui.write('/reset')
        pyautogui.press('enter')
        time.sleep(2)
        self.distribute_points()

    def run(self):
        logging.info("Bot started")
        while True:
            try:
                level, resets = self.read_stats()
                logging.info(f"Current level: {level}, Resets: {resets}")
                
                if level >= 375:
                    logging.info("Performing reset sequence")
                    self.reset_character()
                    self.move_to_location('/move lorencia')
                    self.move_to_coordinates(128, 200)
                elif level >= 280:
                    logging.info("Moving to Lost Tower 5")
                    self.move_to_location('/move losttower5')
                    self.move_to_coordinates(231, 77)
                elif level >= 150:
                    logging.info("Moving to Lost Tower")
                    self.move_to_location('/move losttower')
                    self.move_to_coordinates(221, 77)
                else:
                    logging.info("Moving to Lorencia")
                    self.move_to_location('/move lorencia')
                    self.move_to_coordinates(128, 200)
                
                self.check_and_click_play()
                logging.info("Waiting 60 seconds before next check")
                time.sleep(60)
                
            except KeyboardInterrupt:
                logging.info("Bot stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                break

logging.info("Initializing bot")
bot = GameBot()
time.sleep(5)
bot.run()