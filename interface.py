import os
import pytesseract
import numpy as np
import cv2
import time
import random
import logging
import keyboard
import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32ui
import win32api

from ctypes import windll
from PIL import Image, ImageGrab
from utils import Utils
from config import Configuration

class Interface:
    
    screen_width = 0
    screen_height = 0
    
    dashboard_height = 0
    dashboard_width = 0
    dashboard_x = 0
    dashboard_y = 0
    
    window_stats_open = False
    center_screen = None
    
    def __init__(self, config: Configuration):
        self.config = config
        self.utils = Utils()
        self.logging = logging.getLogger(__name__)
        #self.setup_dashboard_coordinate()
        self.setup_screen()
        
    def get_character_center(self):
        self.logging.info(f"Center character screen: {self.center_screen}")
        return self.center_screen
        
    def setup_dashboard_coordinate(self):
        try:
            app_name = self.config.file["dashboard_name"]
            # Get the window by title
            while True:
                window = gw.getWindowsWithTitle(app_name)[0]
                self.dashboard_width = window.width
                self.dashboard_height = window.height
                
                if self.dashboard_width == 375 and self.dashboard_height == 432:
                    break
                # Move window to desired x,y coordinates
                desired_x = 5
                desired_y = 100
                window.moveTo(desired_x, desired_y)
                
                self.dashboard_x = window.left
                self.dashboard_y = window.top
                self.logging.info(window)
                self.expand_dashboard()
            
            return True
        except Exception as e:
            self.logging.error("YOU MUST OPEN FIRST MU-DASHBOARD")
            exit(0)

    def expand_dashboard(self):
        expand_button_x = self.dashboard_x + self.dashboard_width - 5
        expand_button_y = self.dashboard_y + self.dashboard_height - 5
        self.mouse_click(x = expand_button_x, y= expand_button_y)

    def setup_screen(self):
        """Configura los parámetros de la pantalla del juego"""
        try:            
            app_name = self.config.file["application_name"]
            # Get the window by title
            window = gw.getWindowsWithTitle(app_name)[0]
            
            # Get window dimensions
            self.screen_width = window.width
            self.screen_height = window.height
            self.center_screen = self.screen_width // 2, self.screen_height // 2
            self.logging.info(f"Window size: {self.screen_width}x{self.screen_height}")
            self.check_points = self._initialize_check_points()
            
            return True
        except Exception as e:
            self.logging.error(f"Error getting window info: {e}")
            return False
        
    def _initialize_check_points(self):
        """Inicializa el área de búsqueda"""
        # Área específica donde puede estar la imagen
        self.search_area = {
            'left': 849,
            'top': 427,
            'right': 1083,
            'bottom': 638
        }
        
        # Calculamos el centro del área
        center_x = (self.search_area['left'] + self.search_area['right']) // 2
        center_y = (self.search_area['top'] + self.search_area['bottom']) // 2
        
        return {
            'center': (center_x, center_y),
            'top': (center_x, self.search_area['top'] + 50),
            'down': (center_x, self.search_area['bottom'] - 50),
            'left': (self.search_area['left'] + 50, center_y),
            'right': (self.search_area['right'] - 50, center_y)
        }
        


    def preprocess_image(self, image_path):
        """Optimize PNG image with transparency for comparison"""
        try:
            # Load image if it's a path
            if isinstance(image_path, str):
                print(f"Loading image from path: {image_path}")
                image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                if image is None:
                    print(f"Failed to load image from: {image_path}")
                    return None
            else:
                image = image_path

            # Convert BGR to RGB if necessary
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Handle alpha channel if present
            if len(image.shape) == 3 and image.shape[2] == 4:
                # Split alpha channel
                bgr = image[:,:,:3]
                alpha = image[:,:,3]
                
                # Create white background
                white_bg = np.ones_like(bgr, dtype=np.uint8) * 255
                
                # Blend using alpha channel
                alpha_norm = alpha[:,:,np.newaxis] / 255.0
                blended = (bgr * alpha_norm + white_bg * (1 - alpha_norm)).astype(np.uint8)
            else:
                blended = image

            # Convert to grayscale
            gray = cv2.cvtColor(blended, cv2.COLOR_BGR2GRAY) if len(blended.shape) == 3 else blended
            
            return gray

        except Exception as e:
            print(f"Error in preprocess_image: {str(e)}")
            return None

    def capture_region(self):
        """Captura la región completa de búsqueda"""
        try:
            region = (
                self.search_area['left'],
                self.search_area['top'],
                self.search_area['right'],
                self.search_area['bottom']
            )
            # Asegurarse que la ruta existe
            import os
            screenshot_dir = "images"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
                
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{region[0]}_{region[1]}.png")
            screenshot = self.take_screenshot(region)
            
            if isinstance(screenshot, str):  # Si ya es una ruta
                return screenshot
            else:  # Si es un objeto de imagen
                screenshot.save(screenshot_path)
                return screenshot_path
                
        except Exception as e:
            print(f"Error in capture_region: {str(e)}")
            return None
        
    def take_screenshot_with_cursor_using_coords(self, coords, image_name):
        """
        Toma una screenshot de una región específica incluyendo el cursor
        """
        try:
            # Crear un DC para toda la pantalla
            hwin = win32gui.GetDesktopWindow()
            width = coords[2] - coords[0]
            height = coords[3] - coords[1]
            
            hwndDC = win32gui.GetWindowDC(hwin)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Crear el mapa de bits para guardar la imagen
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Copiar la pantalla al mapa de bits
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (coords[0], coords[1]), win32con.SRCCOPY)
            
            # Obtener información del cursor
            cursor = win32gui.GetCursorInfo()
            
            # Dibujar el cursor en la imagen si está visible
            if cursor[1]:  # cursor[1] es True si el cursor está visible
                hcursor = win32gui.LoadImage(0, win32con.IDC_ARROW, win32con.IMAGE_CURSOR, 0, 0, win32con.LR_SHARED)
                cursor_pos = win32gui.GetCursorPos()
                cursor_x = cursor_pos[0] - coords[0]  # Ajustar posición relativa
                cursor_y = cursor_pos[1] - coords[1]
                
                # Dibujar el cursor en la posición correcta
                windll.user32.DrawIcon(saveDC.GetHandleOutput(), cursor_x, cursor_y, cursor[1])
            
            # Guardar la imagen
            path = os.path.join(self.config.dirs['images'], f'{image_name}.png')
            saveBitMap.SaveBitmapFile(saveDC, path)
            
            # Limpieza
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwin, hwndDC)
            
            return path
            
        except Exception as e:
            print(f"Error taking screenshot: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        

    def check_for_image(self, target_image_path):
        """Busca la imagen en el área específica"""
        try:
            # Ensure we're using the correct target image
            target_image_path = "images/mouse_click.png"  # Force correct path
            
            # Region to search
            region = (849, 427, 1083, 638)
            
            # Take screenshot and get the path
            screenshot_path = self.take_screenshot_with_cursor_using_coords(coords=region, image_name="search_area.png")
            
            print(f"Searching in region: {region}")
            print(f"Looking for image: {target_image_path}")
            
            # Load both images using OpenCV with regular imread since there's no transparency
            screenshot_cv = cv2.imread(screenshot_path, cv2.IMREAD_COLOR)
            target = cv2.imread(target_image_path, cv2.IMREAD_COLOR)
            
            if target is None:
                print(f"Could not load target image: {target_image_path}")
                return False, (0, 0)
                
            if screenshot_cv is None:
                print(f"Could not load screenshot: {screenshot_path}")
                return False, (0, 0)
            
            # Convert both to grayscale
            screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
            target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
            
            # Find matches with a slightly lower threshold since the image is simple
            result = cv2.matchTemplate(screenshot_gray, target_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            # Lower the threshold since the image is simple and might have slight variations
            threshold = 1
            found = max_val >= threshold
            
            print(f"Best match value: {max_val:.3f}")
            
            if found:
                # Calculate absolute coordinates
                abs_x = region[0] + max_loc[0] + target.shape[1]//2
                abs_y = region[1] + max_loc[1] + target.shape[0]//2
                print(f"Found at: ({abs_x}, {abs_y})")
                return True, (abs_x, abs_y)
                
            return False, (0, 0)
            
        except Exception as e:
            print(f"Error in check_for_image: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, (0, 0)

    def find_cursor_image(self):
        found, coords = self.check_for_image("mouse_click.png")
        if found:
            return True
        return False
    
    def get_position_data_using_dashboard(self, with_comma=False):
        try:
            coordinates = [222, 263, 280, 285]
            string_converted = self.convert_image_into_string(coords=coordinates, image_name="position", with_comma=with_comma).strip()
            self.logging.debug(f"[POSITION] Raw position data: '{string_converted}'")
            return self.utils.clean_coordinates(string_converted)
            #return self.convert_image_into_string(coords=coordinates, image_name="position", with_comma=with_comma).strip()
        except Exception as e:
                self.logging.error(f"Position fetch failed: {e}")
                raise ValueError("Position fetch failed")
            
    def calculate_position_offset(self, base_offset, base_scale, scale_rate):
        """
        Calculate coordinate offset based on scale.
        """
        current_scale = self.config.get_interface_scale()
        scale_diff = current_scale - base_scale
        offset_adjustment = scale_diff * scale_rate
        return int(base_offset + offset_adjustment)

    def get_position_data(self, with_comma=False):
        """
        Obtiene las coordenadas del juego mediante OCR.
        Returns:
            str: Coordenadas en formato "x,y"
        """
        try:
            # Base values at 100% scale
            BASE_SCALE = 100
            
            # Base coordinates at 100%
            BASE_X1 = 201
            BASE_X2 = 261
            BASE_Y1 = 18
            BASE_Y2 = 40
            
            # Rate of change (pixels per 1% scale)
            X1_RATE = 2.16   # (255 - 201) / (125 - 100)
            X2_RATE = 2.72   # (329 - 261) / (125 - 100)
            Y1_RATE = 0.32   # (26 - 18) / (125 - 100)
            Y2_RATE = 0.32   # (48 - 40) / (125 - 100)
            
            # Calculate scaled coordinates
            x1 = self.calculate_position_offset(BASE_X1, BASE_SCALE, X1_RATE)
            x2 = self.calculate_position_offset(BASE_X2, BASE_SCALE, X2_RATE)
            y1 = self.calculate_position_offset(BASE_Y1, BASE_SCALE, Y1_RATE)
            y2 = self.calculate_position_offset(BASE_Y2, BASE_SCALE, Y2_RATE)
            
            adjusted_position = [x1, y1, x2, y2]
            
            self.logging.debug(f"Scale: {self.config.get_interface_scale()}%")
            self.logging.debug(f"Adjusted position coords: {adjusted_position}")
            
            string_converted = self.convert_image_into_string(coords=adjusted_position, image_name="position", with_comma=with_comma).strip()
            self.logging.debug(string_converted)
            coordinates = self.utils.clean_coordinates(string_converted)
            self.logging.debug(string_converted)
            if coordinates[0] is None or coordinates[1] is None:
                raise ValueError("Invalid coordinates returned")
            return coordinates
            
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

    def normalize_text(self, text):
        """
        Normalize text by removing accents and converting to lowercase
        """
        import unicodedata
        
        if not text:
            return ""
            
        # Convert to lowercase and strip
        text = text.lower().strip()
        
        # Remove accents
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                    if unicodedata.category(c) != 'Mn')
        
        return text

    def get_text_from_screen(self, text_to_catch):
        self.logging.debug(f"Attempting to locate {text_to_catch} text on screen")
        try:
            for attempt in range(10):
                time.sleep(1)
                try:
                    # Capture screen with DPI awareness already set
                    screen = ImageGrab.grab()
                    screen_np = np.array(screen)
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
                    
                    # Apply multiple preprocessing techniques
                    # 1. Increase contrast
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    contrast = clahe.apply(gray)
                    
                    # 2. Denoise
                    denoised = cv2.fastNlMeansDenoising(contrast)
                    
                    # 3. Multiple threshold attempts
                    preprocessing_methods = [
                        # Original binary threshold
                        lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                        # Adaptive threshold
                        lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
                        # Different binary threshold
                        lambda img: cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)[1]
                    ]
                    
                    # Try each preprocessing method
                    for preprocess in preprocessing_methods:
                        binary = preprocess(denoised)
                        
                        # Scale up the image for better OCR (2x)
                        binary = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        
                        # Add custom configuration for tesseract (removed language specification)
                        custom_config = r'--oem 3 --psm 6'
                        
                        # Perform OCR with default language
                        data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT, config=custom_config)
                        
                        for i, text in enumerate(data['text']):
                            # Make the comparison case-insensitive and accent-insensitive
                            normalized_text = self.normalize_text(text)
                            normalized_target = self.normalize_text(text_to_catch)
                            
                            if normalized_target in normalized_text:
                                # Scale back the coordinates (divide by 2 because we scaled up)
                                x = int(data['left'][i] / 2)
                                y = int(data['top'][i] / 2)
                                w = int(data['width'][i] / 2)
                                h = int(data['height'][i] / 2)
                                
                                rectangle = [x, y, x+w, y+h]
                                
                                self.logging.debug(f"Found '{text_to_catch}' at rectangle: {rectangle}")
                                return rectangle
                    
                    self.logging.warning(f"Attempt {attempt + 1}: '{text_to_catch}' text not found")
                    
                except Exception as e:
                    self.logging.error(f"Error finding '{text_to_catch}' text on attempt {attempt + 1}: {str(e)}")
            
            return None
        
        except ImportError:
            self.logging.error("pytesseract is not installed. Please install it using: pip install pytesseract")
            return None

    def get_available_points_ocr(self, coords):
        self.logging.debug("-----Starting get_available_points-----")        
        try:
            # Validate coords
            if coords is None or len(coords) < 4:
                self.logging.error(f"Invalid coords: {coords}")
                return None
                
            # Base values at 100% scale
            BASE_SCALE = 100
            BASE_X1_OFFSET = 200  # x1 offset at 100%
            BASE_X2_OFFSET = 270  # x2 offset at 100%
            
            # Rate of change (pixels per 1% scale)
            X1_RATE = 2.8    # (270 - 200) / (125 - 100)
            X2_RATE = 2.4    # (330 - 270) / (125 - 100)
            
            # Calculate scaled offsets
            x1_offset = self.calculate_offset(BASE_X1_OFFSET, BASE_SCALE, X1_RATE)
            x2_offset = self.calculate_offset(BASE_X2_OFFSET, BASE_SCALE, X2_RATE)
            
            # Apply offsets to base coordinates
            x1 = coords[2] + x1_offset
            x2 = coords[2] + x2_offset
            y1 = coords[1] - 4
            y2 = coords[3] + 4
            
            new_coords = [x1, y1, x2, y2]
            self.logging.debug(f"Created new_coords: {new_coords}")
            
            result = self.convert_image_into_number(new_coords, 'available_points')
            self.logging.debug(f"Result from convert_image_into_number: {result}")
            
            return result
                
        except Exception as e:
            self.logging.error(f"Error in get_available_points_ocr: {e}")
            self.logging.error(f"Error type: {type(e)}")
            self.logging.error(f"Coords value: {coords}")
            self.reload_ui()
            raise

    def get_level_ocr(self, coords):
        self.logging.debug("-----Starting get_level-----")        
        try:
            # First, ensure coords are integers
            coords = [int(coord) for coord in coords]  # Convert all coordinates to integers
            
            # Base values at 100% scale
            BASE_SCALE = 100
            BASE_X1_OFFSET = 200  # x1 offset at 100%
            BASE_X2_OFFSET = 280  # x2 offset at 100%
            
            # Rate of change (pixels per 1% scale)
            X1_RATE = 0      # No change for x1
            X2_RATE = 2.8    # (350 - 280) / (125 - 100)
            
            # Calculate scaled offsets
            x1_offset = self.calculate_offset(BASE_X1_OFFSET, BASE_SCALE, X1_RATE)
            x2_offset = self.calculate_offset(BASE_X2_OFFSET, BASE_SCALE, X2_RATE)
            
            # Apply offsets to base coordinates
            x1 = coords[2] + x1_offset
            x2 = coords[2] + x2_offset
            y1 = coords[1] - 2  # Y offsets remain constant
            y2 = coords[3] + 2
            
            new_coords = [x1, y1, x2, y2]
            self.logging.debug(f"Created new_coords: {new_coords}")
            
            result = self.convert_image_into_number(new_coords, 'level')
            self.logging.debug(f"Result from convert_image_into_number: {result}")
            
            return result
            
        except Exception as e:
            self.logging.error(f"Error in get_level_ocr: {e}")
            self.logging.error(f"Error type: {type(e)}")
            self.reload_ui()
            raise

    def calculate_offset(self, base_offset, base_scale, scale_rate):

        try:
            current_scale = self.config.get_interface_scale()
            if isinstance(current_scale, str):
                current_scale = int(current_scale)
            scale_diff = current_scale - base_scale
            offset_adjustment = scale_diff * scale_rate
            return int(base_offset + offset_adjustment)
        except Exception as e:
            self.logging.error(e)

    def get_reset_ocr(self, coords):
        self.logging.debug("-----Starting get_reset-----")        
        try:
                        
            # Base values at 100% scale
            BASE_SCALE = 100
            BASE_X1_OFFSET = 150  # x1 offset at 100%
            BASE_X2_OFFSET = 220  # x2 offset at 100%
            
            # Rate of change (pixels per 1% scale)
            X1_RATE = 2.0    # (200 - 150) / (125 - 100)
            X2_RATE = 2.4    # (280 - 220) / (125 - 100)
            
            # Calculate scaled offsets
            x1_offset = self.calculate_offset(BASE_X1_OFFSET, BASE_SCALE, X1_RATE)
            x2_offset = self.calculate_offset(BASE_X2_OFFSET, BASE_SCALE, X2_RATE)
            
            # Apply offsets to base coordinates
            x1 = coords[2] + x1_offset
            x2 = coords[2] + x2_offset
            y1 = coords[1] - 4
            y2 = coords[3] + 4
            
            scaled_coords = [x1, y1, x2, y2]
            
            result = self.convert_image_into_number(scaled_coords, 'reset')
            self.logging.debug(f"Result from convert_image_into_number: {result}")
            
            return result
                
        except Exception as e:
            self.logging.error(f"Error in get_reset_ocr: {e}")
            self.logging.error(f"Error type: {type(e)}")
            self.reload_ui()
            raise
        
    def get_attr_ocr(self, coords, attr):
        self.logging.debug("-----Starting get_attributes-----")        
        try:
            # Base values at 100% scale
            BASE_SCALE = 100
            BASE_X1_OFFSET = 100  # x1 offset at 100%
            BASE_X2_OFFSET = 180  # x2 offset at 100%
            
            # Rate of change (pixels per 1% scale)
            X1_RATE = 0      # No change for x1
            X2_RATE = 1.6    # (220 - 180) / (125 - 100)
            
            # Calculate scaled offsets
            x1_offset = self.calculate_offset(BASE_X1_OFFSET, BASE_SCALE, X1_RATE)
            x2_offset = self.calculate_offset(BASE_X2_OFFSET, BASE_SCALE, X2_RATE)
            
            # Apply offsets to base coordinates
            x1 = coords[2] + x1_offset
            x2 = coords[2] + x2_offset
            y1 = coords[1] - 4
            y2 = coords[3] + 4
            
            new_coords = [x1, y1, x2, y2]
            self.logging.debug(f"Created new_coords: {new_coords}")
            
            result = self.convert_image_into_number(new_coords, attr)
            self.logging.debug(f"Result from convert_image_into_number: {result}")
            
            return result
                
        except Exception as e:
            self.logging.error(f"Error in get_reset_ocr: {e}")
            self.logging.error(f"Error type: {type(e)}")
            self.reload_ui()
            raise
        
    def get_attribute_from_screen(self, attribute):
        self.logging.debug(f"Attempting to locate {attribute} text on screen")
        try:
            for attempt in range(5):
                time.sleep(1)
                try:
                    # Capture screen
                    screen = ImageGrab.grab()
                    screen_np = np.array(screen)
                    
                    # Convert to grayscale (optional but can improve OCR accuracy)
                    gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
                    
                    # Apply thresholding to get better text recognition (optional)
                    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    # Perform OCR
                    data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
                    
                    # Search for "TEXT" in the recognized text
                    for i, text in enumerate(data['text']):
                        if attribute in text:
                            # Get the coordinates of the found text
                            x = data['left'][i]
                            y = data['top'][i]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            # Calculate center point
                            center_x = x + w // 2
                            center_y = y + h // 2
                            center_point = (center_x, center_y)
                            
                            self.logging.debug(f"Found {attribute} at: {center_point}")
                            return center_point
                    
                    self.logging.warning(f"Attempt {attempt + 1}: '{attribute}' text not found")
                    
                        
                except Exception as e:
                    self.logging.error(f"Error finding '{attribute}' text on attempt {attempt + 1}: {str(e)}")
            
            return None
            
        except ImportError:
            self.logging.error("pytesseract is not installed. Please install it using: pip install pytesseract")
            return None

    def get_elemental_reference(self):
        """Localizes the word 'ELEMENTAL' on the screen using OCR."""
        self.logging.debug("Attempting to locate 'ELEMENTAL' text on screen")
        
        try:
            
            for attempt in range(5):
                time.sleep(1)
                try:
                    # Capture screen
                    screen = ImageGrab.grab()
                    screen_np = np.array(screen)
                    
                    # Convert to grayscale (optional but can improve OCR accuracy)
                    gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
                    
                    # Apply thresholding to get better text recognition (optional)
                    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    # Perform OCR
                    data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
                    
                    # Search for "ELEMENTAL" in the recognized text
                    for i, text in enumerate(data['text']):
                        if 'ELEMENTAL' in text.upper():
                            # Get the coordinates of the found text
                            x = data['left'][i]
                            y = data['top'][i]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            # Calculate center point
                            center_x = x + w // 2
                            center_y = y + h // 2
                            center_point = (center_x, center_y)
                            
                            self.logging.debug(f"Found 'ELEMENTAL' at: {center_point}")
                            return center_point
                    
                    self.logging.warning(f"Attempt {attempt + 1}: 'ELEMENTAL' text not found")
                    
                    # Handle the last attempt failure
                    if attempt == 4:
                        self.logging.warning("Will close all popups.")
                        self.escape_multiple_times()
                        #self.get_poweroff_reference()
                        self.window_stats_open = False
                        self.open_stats_window()
                        
                except Exception as e:
                    self.logging.error(f"Error finding 'ELEMENTAL' text on attempt {attempt + 1}: {str(e)}")
                    # Error handling
                    if attempt == 4:
                        self.logging.warning("Will close all popups.")
                        self.escape_multiple_times()
                        self.get_poweroff_reference()
                        self.window_stats_open = False
                        self.open_stats_window()
            
            return None
            
        except ImportError:
            self.logging.error("pytesseract is not installed. Please install it using: pip install pytesseract")
            return None
    
    def get_poweroff_reference(self):
        """Localiza el punto de referencia poweroff en la pantalla usando OpenCV."""
        self.logging.debug("Attempting to locate poweroff reference on the screen")
        
        image_path = os.path.join(self.config.dirs['images'], 'tofind', 'poweroff_reference.png')
        self.logging.debug(image_path)
        if not os.path.exists(image_path):
            self.logging.error(f"Reference image not found at: {image_path}")
            return None
        
        # Load the template image
        template = cv2.imread(image_path)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        for attempt in range(5):
            time.sleep(1)
            try:
                # Capture screen
                # Option 1: Using PIL
                screen = np.array(ImageGrab.grab())
                screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
                
                # Option 2: Using mss (faster)
                # with mss() as sct:
                #     screen = np.array(sct.grab(sct.monitors[1]))
                #     screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
                
                screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
                
                # Template matching
                result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # If confidence is high enough (similar to pyautogui's confidence)
                if max_val > 0.7:
                    # Get the position of the match
                    top_left = max_loc
                    h, w = template_gray.shape
                    bottom_right = (top_left[0] + w, top_left[1] + h)
                    
                    # Convert to format similar to pyautogui.locateOnScreen
                    poweroff_loc = (top_left[0], top_left[1], w, h)
                    self.logging.debug(f"Found poweroff reference at: {poweroff_loc}")
                    self.escape()
                    return poweroff_loc
                    
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
            
            return text if text else ("0,0" if with_comma else "0")
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return "0,0" if with_comma else "0"
        
    def convert_image_into_number(self, coords, image_name, relative_coords=None, with_comma=False):
        try:
            text = self.convert_image_into_string(coords, image_name, relative_coords, with_comma)
            return int(text) if text.isdigit() else 0
        except Exception as e:
            self.logging.error(f"Error reading {image_name}: {e}")
            return 0
    
    def focus_application(self):
        #self.mouse_click(1780, 672)
        try:
            # Find and focus MEGAMU window
            app_name = self.config.file["application_name"]
            megamu_window = gw.getWindowsWithTitle(app_name)[0]
            megamu_window.activate()
            return True
        except IndexError:
            self.logging.error("{app_name} window not found")
            return False
        except Exception as e:
            self.logging.error(f"Error focusing {app_name}: {e}")
            return False
    
    def reload_ui(self):
        self.logging.warning("Will close all popups.")
        self.escape_multiple_times()
        
        message_salir_is_active = self.get_text_from_screen("Salir")
        if message_salir_is_active:
            self.escape()
        #self.get_poweroff_reference()
        self.window_stats_open = False
        self.open_stats_window()
    
    #################################### Clicks ####################################
    
    def click_center_screen(self):
        # Using virtual click instead of physical mouse movement
        pyautogui.click(self.center_screen)

    def mouse_click(self, x, y):
        pyautogui.click(x, y)

    def scroll(self, random_number=True, number=0, scroll_count=5):

        if random_number:
            # Generate a random scroll amount between -1000 and 1000
            scroll_amount = random.randint(-1000, 1000)

            # Scroll 5 times with the random amount
            for _ in range(scroll_count):
                pyautogui.scroll(scroll_amount)  # Scroll by the random amount
                time.sleep(0.5)  # Add a small delay between scrolls

            # Log the scroll amount
            self.logging.info(f"Scrolled by: {scroll_amount} units (random)")

        else:
            if number != 0:
                # Scroll 5 times with the specified amount
                for _ in range(scroll_count):
                    pyautogui.scroll(number)  # Scroll by the specified amount
                    time.sleep(0.01)  # Add a small delay between scrolls

                # Log the scroll amount
                self.logging.info(f"Scrolled by: {number} units (fixed)")
            else:
                self.logging.warning("Number is 0. No scrolling performed.")
                
    #################################### Commands ####################################
    def enter(self):
        time.sleep(0.5)
        keyboard.press('enter')
        time.sleep(0.1)  # Small delay between press and release
        keyboard.release('enter')
        
    def start_mu_helper(self):
        keyboard.press_and_release('home')
        
    def escape_multiple_times(self):
        times = 5
        for _ in range(times):
            time.sleep(0.3)
            keyboard.press('esc')
            time.sleep(0.1)
            keyboard.release('esc')
        
    def escape(self):
        time.sleep(0.3)
        time.sleep(0.3)
        keyboard.press('esc')
        time.sleep(0.1)
        keyboard.release('esc')
        
    def command_reset(self):
        self.enter()
        self.execute_command('/reset')
        self.enter()
        
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
        keyboard.write(command, delay=0.1)  # Add a small delay between characters
        
    def press_key(self, key):
        self.logging.debug(f"Command {key} is executing")
        keyboard.press(key)
        time.sleep(0.4)  # Add small delay between press and release
        keyboard.release(key)
        
    def command_move_to_map(self, map_name):
        time.sleep(0.5)
        self.enter()
        self.execute_command(f'/move {map_name}')
        self.enter()
        self.set_current_map(map_name = map_name)
        self.window_stats_open = False
        
    def move_mouse_to_coords_without_click(self, x, y):
        pyautogui.moveTo(x, y)
        time.sleep(1)
        
    def check_npc_in_cursor(self, x, y):
        in_any_npc = False
        self.move_mouse_to_coords_without_click(x, y)
        for _ in range(2):
            in_any_npc = self.find_cursor_image()
            time.sleep(0.1)
            if in_any_npc is True:
                break
            
        if in_any_npc is True:
            self.logging.info("In that coordinate, there is an NPC. So, we will not move to that coordinate.")
            return True
        return False
    
    #Horizontal/Vertical
    def mouse_top(self):
        x, y = self.get_character_center()
        y = y - 50
        self.logging.info(f"Top mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_down(self):
        x, y = self.get_character_center()
        y = y + 50
        self.logging.info(f"Down mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_left(self):
        x, y = self.get_character_center()
        x = x - 50
        self.logging.info(f"Left mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_right(self):
        x, y = self.get_character_center()
        x = x + 50
        self.logging.info(f"Right mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    #Diagonal
    def mouse_top_right(self):
        x, y = self.get_character_center()
        x = x + 50
        y = y - 50
        self.logging.info(f"Top/Right mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_top_left(self):
        x, y = self.get_character_center()
        x = x - 50
        y = y - 50
        self.logging.info(f"Top/Left mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_down_right(self):
        x, y = self.get_character_center()
        x = x + 50
        y = y + 50
        self.logging.info(f"Down/Right mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)
        
    def mouse_down_left(self):
        x, y = self.get_character_center()
        x = x - 50
        y = y + 50
        self.logging.info(f"Down/Left mouse click on these coords: ({x},{y})")
        if not self.check_npc_in_cursor(x,y):
            self.mouse_click(x,y)

        
    def _release_all_keys(self):
        """Release all movement keys."""
        self.arrow_key_up(release=True)
        self.arrow_key_down(release=True)
        self.arrow_key_left(release=True)
        self.arrow_key_right(release=True)
    
    def arrow_key_left(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        key = 'left'
        if press:
            keyboard.press(key) 
        if release:
            keyboard.release(key)
            
    def arrow_key_right(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        key = 'right'
        if press:
            keyboard.press(key) 
        if release:
            keyboard.release(key)
            
    def arrow_key_up(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        key = 'up'
        if press:
            keyboard.press(key) 
        if release:
            keyboard.release(key)
            
    def arrow_key_down(self, press=True, release=False):
        """Enhanced arrow key control with press/release options"""
        key = 'down'
        if press:
            keyboard.press(key) 
        if release:
            keyboard.release(key)
        
    def open_stats_window(self):
        time.sleep(2)
        if not self.window_stats_open:
            self.logging.info("Open stat window")
            keyboard.press('c')
            time.sleep(0.1)
            keyboard.release('c')
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
    
    def get_reset(self, current_state):
        return current_state["current_reset"]
    
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
        
    def set_available_attributes(self, coords):
        self.config.update_game_state({'current_position_available_points': coords})
        
    def set_attribute_reference(self, attr, coords):
        if attr == "strenght":
            self.config.update_game_state({'current_position_strenght': coords})
        if attr == "agility":
            self.config.update_game_state({'current_position_agility': coords})
        if attr == "vitality":
            self.config.update_game_state({'current_position_vitality': coords})
        if attr == "energy":
            self.config.update_game_state({'current_position_energy': coords})
        if attr == "command":
            self.config.update_game_state({'current_position_command': coords})
        
    def get_available_attributes(self, current_state):
        return current_state["current_position_available_points"]
        
    def get_attribute_reference(self, current_state, attr):
        if attr == "strenght":
            return current_state["current_position_strenght"]
        if attr == "agility":
            return current_state["current_position_agility"]
        if attr == "vitality":
            return current_state["current_position_vitality"]
        if attr == "energy":
            return current_state["current_position_energy"]
        if attr == "command":
            return current_state["current_position_command"]
    
    def get_attribute_value(self, current_state, attr):
        if attr == "strenght":
            return current_state["current_strenght"]
        if attr == "agility":
            return current_state["current_agility"]
        if attr == "vitality":
            return current_state["current_vitality"]
        if attr == "energy":
            return current_state["current_energy"]
        if attr == "command":
            return current_state["current_command"]