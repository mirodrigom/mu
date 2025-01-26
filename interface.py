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
    
    def __init__(self, config):
        self.config = config
        self.utils = Utils()
        self.logging = logging.getLogger(__name__)

    def setup_screen(self):
            """Configura los parámetros de la pantalla del juego"""
            monitor = screeninfo.get_monitors()[1]
            self.screen_width = monitor.width
            self.screen_height = monitor.height
            self.logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")
            
    def ensure_stats_window_open(self):
        """Ensures the stats window stays open without image detection"""
        try:
            pyautogui.press('c')
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
            coord_area = ImageGrab.grab(bbox=tuple(adjusted_position))
            coord_area_path = os.path.join(self.config.dirs['images'], 'coord_area_path.png')
            coord_area.save(coord_area_path)
            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
            return pytesseract.image_to_string(coord_area, config=config).strip()
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
    
    def read_available_points(self, ref_point):
        """Read available attribute points"""
        try:
            coords = self.utils.get_relative_coords(self.config.file['ocr_coordinates']['available_points'], ref_point)
            points_area = ImageGrab.grab(bbox=tuple(coords))
            points_path = os.path.join(self.config.dirs['images'], 'available_points.png')
            points_area.save(points_path)

            points_thresh = self._preprocess_image(points_path)
            if points_thresh is not None:
                points_text = pytesseract.image_to_string(
                    Image.fromarray(points_thresh),
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789'
                )
                return self.utils._extract_numeric_value(points_text)
        except Exception as e:
            self.logging.error(f"Error reading available points: {e}")
        return 0
    

    def _read_numeric_area(self, area_name, ref_point):
        """Read numeric value from specified area"""
        coords = self.utils.get_relative_coords(self.config.get_ocr_coordinates()[area_name], ref_point)
        area = ImageGrab.grab(bbox=tuple(coords))
        path = os.path.join(self.config.dirs['images'], f'{area_name}_test.png')
        area.save(path)

        preprocessed = self._preprocess_image(path)
        text = pytesseract.image_to_string(
            preprocessed,
            config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        )
        return self.utils._extract_numeric_value(text)
    
    def click_center_screen(self):
        pyautogui.click(self.screen_width // 2, self.screen_height // 2)
        
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