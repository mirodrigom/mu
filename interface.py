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
        self.setup_screen()
        pyautogui.FAILSAFE = False

    def setup_screen(self):
            """Configura los parámetros de la pantalla del juego"""
            monitor = screeninfo.get_monitors()[1]
            self.screen_width = monitor.width
            self.screen_height = monitor.height
            self.logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")
            
    def get_position_data(self, with_comma=False):
        """
        Obtiene las coordenadas del juego mediante OCR.
        Returns:
            str: Coordenadas en formato "x,y"
        """
        try:
            adjusted_position = self.config.get_ocr_coordinates()['position']
            return self.convert_image_into_string(coords=adjusted_position, image_name="position", with_comma=with_comma).strip()
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
            
        for attempt in range(5):
            time.sleep(1)
            try:
                elemental_loc = pyautogui.locateOnScreen(image_path, confidence=0.7)
                if elemental_loc:
                    self.logging.debug(f"Found elemental reference at: {elemental_loc}")
                    return pyautogui.center(elemental_loc)
                self.logging.warning(f"Attempt elemental {attempt + 1}: Reference not found")                
            except Exception as e:
                self.logging.error(f"Error finding elemental reference on attempt {attempt + 1}: {str(e)}")
                if attempt == 4:
                    logging.warning("Will close all popups.")
                    self.escape_multiple_times()
                    self.get_poweroff_reference()
                    self.window_stats_open = False
                    self.open_stats_window()
        return None
    
    def get_poweroff_reference(self):
        """Localiza el punto de referencia poweroff en la pantalla."""
        self.logging.debug("Attempting to locate poweroff reference on the screen")
        
        image_path = os.path.join(self.config.dirs['images'], 'tofind', 'poweroff_reference.png')
        self.logging.debug(image_path)
        if not os.path.exists(image_path):
            self.logging.error(f"Reference image not found at: {image_path}")
            return None
            
        for attempt in range(5):
            time.sleep(1)
            try:
                poweroff_loc = pyautogui.locateOnScreen(image_path, confidence=0.7)
                if poweroff_loc:
                    self.logging.debug(f"Found poweroff reference at: {poweroff_loc}")
                    self.escape()
                    break
                self.logging.warning(f"Attempt poweroff {attempt + 1}: Reference not found")                
            except Exception as e:
                self.logging.error(f"Error finding poweroff reference on attempt {attempt + 1}: {str(e)}")
        return None
    
    
    def convert_image_into_string(self, coords, image_name, relative_coords=None, with_comma=False):
        self.logging.debug(f"Converting {image_name}...")
        try:
            if relative_coords:
                final_coords = self.utils.get_relative_coords(coords, relative_coords)
            else:
                final_coords = coords
            path = self.take_screenshot_with_coords(coords=final_coords, image_name=image_name)
                
            if with_comma:
                method_ocr = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
            else:
                method_ocr = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
                
            preprocessed = self._preprocess_image(path)
            text = pytesseract.image_to_string(
                preprocessed,
                config=method_ocr
            ).strip()
            
            return text if text else "0" 
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return "0" 
        
    def convert_image_into_number(self, coords, image_name, relative_coords=None, with_comma=False):
        try:
            text = self.convert_image_into_string(coords, image_name, relative_coords, with_comma)
            return int(text) if text.isdigit() else 0
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return 0
    

    
    #################################### Clicks ####################################
    
    def click_center_screen(self):
        pyautogui.click(self.screen_width // 2, self.screen_height // 2)
        
    def mouse_click(self, x, y):
        pyautogui.click(x, y)
    
    #################################### Commands ####################################
    def enter(self):
        time.sleep(0.5)
        pyautogui.press('enter')
        
        
    def escape_multiple_times(self):
        times = 5
        for _ in range(times):
            time.sleep(0.3)
            pyautogui.press('escape')
        
    def escape(self):
        time.sleep(0.3)
        pyautogui.press('escape')
        
        
    def command_reset(self):
        self.enter()
        self.execute_command('/reset')
        self.enter()
        self.set_current_map(map_name = "lorencia")
        
    def command_add_attributes(self, attribute, points=0, str_attr=None, agi_attr=None, vit_attr=None, ene_attr=None, com_attr=None):
        if attribute == "strenght":
            self.enter()
            self.execute_command(f'/s {points}')
            self.enter()
            
        elif attribute == "agility":
            self.enter()
            self.execute_command(f'/a {points}')
            self.enter()
            
        elif attribute == "vitality":
            self.enter()
            self.execute_command(f'/v {points}')
            self.enter()
            
        elif attribute == "energy":
            self.enter()
            self.execute_command(f'/e {points}')
            self.enter()
            
        elif attribute == "command":
            self.enter()
            self.execute_command(f'/c {points}')
            self.enter()
            
        elif attribute == "allstats":
            command = self.utils.clean_stats_command(f'/s {str_attr}, /a {agi_attr}, /v {vit_attr}, /e {ene_attr}, /c {com_attr}')
            self.enter()
            self.execute_command(command)
            self.enter()
        else:
            self.logging.debug(f"attribute: {attribute}, points: {points}, str_attr: {str_attr}, agi_attr: {agi_attr}, vit_attr: {vit_attr}, ene_attr: {ene_attr}, com_attr: {com_attr}")
            self.logging.warning("Wrong attribute to add points.")
        time.sleep(0.7)
        
    def execute_command(self, command):
        self.logging.debug(f"Command {command} is executing")
        pyautogui.write(command)
        
    def press_key(self, key):
        self.logging.debug(f"Command {key} is executing")
        pyautogui.keyDown(key)
        time.sleep(0.1)  # Add small delay
        pyautogui.keyUp(key)
        
    def command_move_to_map(self, map_name):
        self.enter()
        self.execute_command(f'/move {map_name}')
        self.enter()
        self.set_current_map(map_name = map_name)
        self.window_stats_open = False
        
    def arrow_key_left(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        if press:
            pyautogui.keyDown('left')
        if release:
            pyautogui.keyUp('left')
            
    def arrow_key_right(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        if press:
            pyautogui.keyDown('right')
        if release:
            pyautogui.keyUp('right')
            
    def arrow_key_up(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        if press:
            pyautogui.keyDown('up')
        if release:
            pyautogui.keyUp('up')
            
    def arrow_key_down(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        if press:
            pyautogui.keyDown('down')
        if release:
            pyautogui.keyUp('down')
        
    def open_stats_window(self):
        time.sleep(2)
        if not self.window_stats_open:
            self.logging.info("Open stat window")
            pyautogui.press('c')
            self.window_stats_open = True
        else:
            self.logging.info("Stat window is already open.")
            
    def take_screenshot(self, image_name):
        image_area = ImageGrab.grab()
        path = os.path.join(self.config.dirs['images'], f"{image_name}.png")
        image_area.save(path)
        return path
    
    def take_screenshot_with_coords(self, coords, image_name):
        image_area = ImageGrab.grab(bbox=tuple(coords))
        path = os.path.join(self.config.dirs['images'], f'{image_name}.png')
        image_area.save(path)
        return path
    
    ############ Getters and Setters
    
    def get_mu_helper_status(self, current_state):
        return current_state["mulheper_active"]
    
    def set_mu_helper_status(self, status):
        self.config.update_game_state({'mulheper_active': status})
        
    def get_level(self, current_state):
        return current_state["current_level"]
    
    def set_level(self, level):
        self.config.update_game_state({'level': level})
        
    def get_current_map(self, current_state):
        return current_state["current_map"]
    
    def set_current_map(self, map_name):
        self.config.update_game_state({'current_map': map_name})
        
    def set_current_coords(self, coords):
        self.config.update_game_state({'current_location': coords})
        
    def get_current_coords(self, current_state):
        return current_state["current_location"][0], current_state["current_location"][1]