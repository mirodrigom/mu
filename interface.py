import os
import pytesseract
import screeninfo
import numpy as np
import pyautogui
import cv2
import time
import logging

from PIL import Image, ImageGrab
from utils import Utils
from config import Configuration

class Interface:
    
    screen_width = 0
    screen_height = 0
    window_stats_open = False
    
    def __init__(self, config):
        self.config = config
        self.utils = Utils()
        self.logging = logging.getLogger(__name__)
        pyautogui.FAILSAFE = False

    def setup_screen(self):
            """Configura los parámetros de la pantalla del juego"""
            monitor = screeninfo.get_monitors()[1]
            self.screen_width = monitor.width
            self.screen_height = monitor.height
            self.logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")
            
    def ensure_stats_window_open(self):
        """Ensures the stats window stays open without image detection"""
        try:
            self.open_stats_window()
            time.sleep(0.1)
        except Exception as e:
            self.logging.error(f"Error pressing C key: {e}")
            
    def get_position_data(self):
        """
        Obtiene las coordenadas del juego mediante OCR.
        Returns:
            str: Coordenadas en formato "x,y"
        """
        try:
            adjusted_position = self.config.get_ocr_coordinates()['position']
            return self.convert_image_into_string(coords=adjusted_position, image_name="position").strip()
        except Exception as e:
            self.logging.error(f"Position fetch failed: {e}")
            raise ValueError("Position fetch failed")
        
    def load_ocr_packages(self):
        """Inicializa las variables de estado del juego (nivel, resets, coordenadas)"""
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def _preprocess_image(self, img_path):
        """Enhanced image preprocessing for better number recognition"""
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Scale the image
        scale = 2
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(scaled)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(contrast)
        
        # Thresholding
        _, binary = cv2.threshold(denoised, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def get_elemental_reference(self):
        """Localiza el punto de referencia elemental en la pantalla."""
        self.logging.debug("Attempting to locate elemental reference on the screen")
        
        image_path = os.path.join(self.config.dirs['images'], 'tofind', 'elemental_reference.png')
        self.logging.debug(image_path)
        if not os.path.exists(image_path):
            self.logging.error(f"Reference image not found at: {image_path}")
            return None
            
        for attempt in range(3):
            time.sleep(1)
            try:
                elemental_loc = pyautogui.locateOnScreen(image_path, confidence=0.7)
                if elemental_loc:
                    self.logging.debug(f"Found elemental reference at: {elemental_loc}")
                    return pyautogui.center(elemental_loc)
                self.logging.warning(f"Attempt {attempt + 1}: Reference not found")
            except Exception as e:
                self.logging.error(f"Error finding elemental reference on attempt {attempt + 1}: {str(e)}")
        return None
    
    
    def convert_image_into_string(self, coords, image_name, relative_coords=None ):
        try:
            if relative_coords:
                final_coords = self.utils.get_relative_coords(coords, relative_coords)
            else:
                final_coords = coords
            area = ImageGrab.grab(bbox=tuple(final_coords))
            path = os.path.join(self.config.dirs['images'], f'{image_name}.png')
            area.save(path)
            
            preprocessed = self._preprocess_image(path)
            text = pytesseract.image_to_string(
                preprocessed,
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            )
            
            return text
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return 0
        
    def convert_image_into_number(self, coords, image_name, relative_coords=None ):
        try:
            text = self.convert_image_into_string(coords, image_name, relative_coords)
            number = self.utils.extract_numeric_value(text)
            
            return number
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return 0
    
    def read_attribute(self, attribute_name, ref_point):
        """Read attribute with validation based on config settings"""
        try:
            attribute_coords = self.config.get_ocr_coordinates()['attributes'][attribute_name]['points']
            relative_coords = self.utils.get_relative_coords(attribute_coords, ref_point)
            
            value = self.convert_image_into_string(coords=attribute_coords, image_name=f'{attribute_name}_value', relative_coords=relative_coords,)

            # Get validation rules from config
            if 'validation' in self.config.file and attribute_name in self.config.file['validation']:
                min_val = self.config.file['validation'][attribute_name].get('min', 0)
                max_val = self.config.file['validation'][attribute_name].get('max', float('inf'))

                if not min_val <= value <= max_val:
                    self.logging.warning(f"{attribute_name} value out of range: {value}")
                    return self.read_attribute(attribute_name, ref_point)

            return value

        except Exception as e:
            self.logging.error(f"Error reading {attribute_name}: {e}")
            return 0
    
    #################################### Clicks ####################################
    
    def click_center_screen(self):
        pyautogui.click(self.screen_width // 2, self.screen_height // 2)
        
    def mouse_click(self, x, y):
        pyautogui.click(x, y)
    
    #################################### Commands ####################################
    def enter(self):
        pyautogui.press('enter')
        
    def command_reset(self):
        self.enter()
        pyautogui.write('/reset')
        self.enter()
        
    def command_add(self, attribute, points):
        self.enter()
        if attribute == "strenght":
            pyautogui.write(f'/s {points}')
        elif attribute == "agility":
            pyautogui.write(f'/a {points}')
        elif attribute == "vitality":
            pyautogui.write(f'/v {points}')
        elif attribute == "energy":
            pyautogui.write(f'/e {points}')
        elif attribute == "command":
            pyautogui.write(f'/c {points}')
        else:
            self.logging.warning("Wrong attribute to add points.")
        self.enter()
        
    def command_move_to_map(self, map_name):
        self.enter()
        pyautogui.write(f'/move {map_name}')
        self.enter()
        self.window_stats_open = False
        
    def arrow_key_up(self):
        pyautogui.keyUp('up')
        
    def arrow_key_down(self):
        pyautogui.keyUp('down')
    
    def arrow_key_left(self):
        pyautogui.keyUp('left')
        
    def arrow_key_right(self):
        pyautogui.keyUp('right')
        
    def open_stats_window(self):
        time.sleep(2)
        if not self.window_stats_open:
            pyautogui.press('c')
        else:
            self.logging("Stat window is already open.")
            
    def take_screenshot(self, image_name):
        stats_area = ImageGrab.grab()
        stats_path = os.path.join(self.config.dirs['images'], f"{image_name}.png")
        stats_area.save(stats_path)
        return stats_path
    
    def take_screenshot_with_coords(self, coords, image_name):
        image_area = ImageGrab.grab(bbox=tuple(coords))
        path = os.path.join(self.config.dirs['images'], 'play_button_area.png')
        image_area.save(path)