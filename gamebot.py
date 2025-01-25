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
from pathlearner import PathLearner

class GameBot:
    """
    Un bot para automatizar acciones en un juego. Maneja movimientos, estadísticas y atributos del personaje.
    """
    def __init__(self):
        pyautogui.FAILSAFE = False
        self.running = True
        self.current_location = None
        self.play = False
        self.setup_keyboard_listener()
        self.setup_logging()
        self.load_config('config.json')
        self.initialize_game_state()
        self.setup_screen()
        self.path_learner = PathLearner()
        self.record_good_path = False
        self.reference_point = None
        self.first_time = True

    def setup_keyboard_listener(self):
        """Configura un listener para detectar la tecla F9 que detiene el bot"""
        def on_press(key):
            if key == keyboard.Key.f9:
                logging.info("Bot stopped")
                os._exit(0)  # Force exit the entire program
                    
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def setup_logging(self):
        """Configura el sistema de logging y limpia logs anteriores"""
        with open('bot_debug.log', 'w') as f:
            f.write('')
            
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='bot_debug.log'
        )
        
        # Suppress PIL and Tesseract debug logs
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.WARNING)

    def load_config(self, config_path: str):
        """Carga la configuración del bot desde un archivo JSON"""
        with open(config_path) as f:
            self.config = json.load(f)

    def initialize_game_state(self):
        """Inicializa las variables de estado del juego (nivel, resets, coordenadas)"""
        self.level = 0
        self.resets = 0
        self.current_x = 0
        self.current_y = 0
        self.consecutive_errors = 0
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def setup_screen(self):
        """Configura los parámetros de la pantalla del juego"""
        monitor = screeninfo.get_monitors()[1]
        self.screen_width = monitor.width
        self.screen_height = monitor.height
        logging.info(f"Screen size: {self.screen_width}x{self.screen_height}")

    def get_position_data(self):
        """
        Obtiene las coordenadas del juego mediante OCR.
        Returns:
            str: Coordenadas en formato "x,y"
        """
        try:
            adjusted_position = self.adjust_coordinates(self.config['ocr_coordinates']['position'])
            coord_area = ImageGrab.grab(bbox=tuple(adjusted_position))
            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
            return pytesseract.image_to_string(coord_area, config=config).strip()
        except Exception as e:
            logging.error(f"Position fetch failed: {e}")
            raise ValueError("Position fetch failed")

    def is_valid_coordinate(self, coordinate_str: str) -> bool:
        """
        Verifica si una cadena representa coordenadas válidas.
        Args:
            coordinate_str: Cadena de coordenadas a validar
        Returns:
            bool: True si es válida, False si no
        """
        try:
            parts = coordinate_str.strip().split(',')
            if len(parts) != 2:
                return False
            return all(part.strip().isdigit() for part in parts)
        except:
            return False

    def fix_7_digit_coordinate(self, coord_str: str) -> str:
        """
        Corrige coordenadas de 7 dígitos eliminando el dígito del medio.
        Args:
            coord_str: Coordenada de 7 dígitos
        Returns:
            str: Coordenada corregida de 6 dígitos
        """
        if len(coord_str) != 7:
            return coord_str
        return coord_str[:3] + coord_str[4:]

    def process_coordinates(self, coord_str: str) -> tuple[int, int]:
        """
        Procesa una cadena de coordenadas en una tupla (x,y).
        Args:
            coord_str: Cadena de coordenadas
        Returns:
            tuple: Coordenadas (x,y) o None si son inválidas
        """
        # Clean the string
        coord_str = ''.join(filter(str.isdigit, coord_str))
        
        # Handle 7-digit case
        if len(coord_str) == 7:
            coord_str = self.fix_7_digit_coordinate(coord_str)
        
        # Extract coordinates
        if len(coord_str) == 6:
            return int(coord_str[:3]), int(coord_str[3:])
        
        return None

    # Update _fetch_position in GameBot class:
    def _fetch_position(self):
        """
        Obtiene la posición actual del personaje.
        Returns:
            tuple: Coordenadas actuales (x,y)
        Raises:
            ValueError: Si el formato de coordenadas es inválido
        """
        raw_data = self.get_position_data()
        if not self.is_valid_coordinate(raw_data):
            # Try processing as single string of digits
            coords = self.process_coordinates(raw_data)
            if coords:
                return coords
            raise ValueError(f"Invalid coordinate format: '{raw_data}'")
        return map(int, raw_data.split(','))

    def get_current_position(self, retries=900, delay=1):
        """
        Intenta obtener la posición actual con reintentos.
        Args:
            retries: Número máximo de intentos
            delay: Tiempo entre intentos
        Returns:
            bool: True si tuvo éxito, False si no
        """
        for attempt in range(retries):
            try:
                self.current_x, self.current_y = self._fetch_position()
                return True
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed to get current position: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return False

    def _preprocess_image(self, img_path):
        """
        Preprocesa una imagen para mejorar el OCR.
        Args:
            img_path: Ruta de la imagen
        Returns:
            np.array: Imagen procesada o None si hay error
        """
        try:
            # Open image
            img = Image.open(img_path)
            img_array = np.array(img)

            # Convert to grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # Apply Gaussian Blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Apply adaptive thresholding for better contrast
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Refine image with morphological operations
            kernel = np.ones((2, 2), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            return thresh
        except Exception as e:
            logging.error(f"Image preprocessing error: {e}")
            return None

    def _extract_numeric_value(self, text):
        """
        Extrae valores numéricos de un texto.
        Args:
            text: Texto a procesar
        Returns:
            int: Valor numérico o 0 si hay error
        """
        try:
            return int(''.join(filter(str.isdigit, text.strip())))
        except ValueError:
            logging.warning(f"Failed to extract numeric value from text: '{text}'")
            return 0

    def get_relative_coords(self, base_coords, ref_point):
        """
        Calcula coordenadas relativas a un punto de referencia.
        Args:
            base_coords: Coordenadas base
            ref_point: Punto de referencia
        Returns:
            list: Coordenadas ajustadas
        """
        return [
            base_coords[0] + ref_point[0],
            base_coords[1] + ref_point[1],
            base_coords[2] + ref_point[0],
            base_coords[3] + ref_point[1]
        ]

    def get_elemental_reference(self):
        """
        Localiza el punto de referencia elemental en la pantalla.
        Returns:
            tuple: Coordenadas del punto de referencia o None
        """
        logging.debug("Attempting to locate elemental reference on the screen")
        for attempt in range(3):  # Retry logic
            time.sleep(1)
            try:
                elemental_loc = pyautogui.locateOnScreen("elemental_reference.png", confidence=0.7)
                if not elemental_loc:
                    logging.warning(f"Attempt {attempt + 1}: Elemental reference not found")
                    continue
                return pyautogui.center(elemental_loc)
            except Exception as e:
                logging.error(f"Error finding elemental reference on attempt {attempt + 1}: {e}")
        return None

    def distribute_attributes(self):
        """
        Distribuye puntos de atributos según la configuración.
        Returns:
            bool: True si tuvo éxito, False si no
        """
        ref_point = self.get_elemental_reference()
        if not ref_point:
            logging.error("Cannot distribute attributes - reference point not found")
            return False
                
        points = self.resets * 430
        logging.info(f"Distributing {points} total points")

        for stat, ratio in self.config['stat_distribution'].items():
            stat_points = int(points * ratio)
            logging.info(f"Allocating {stat_points} points to {stat}")
            
            try:
                stat_coords = self.config['ocr_coordinates']['attributes'][stat]
                
                if 'first_button' in stat_coords:
                    first_coords = self.get_relative_coords(stat_coords['first_button'], ref_point)
                    logging.info(f"Relative coords for button PlusPlus of {stat}: {first_coords[0]}, {first_coords[1]}")
                    pyautogui.click(first_coords[0], first_coords[1])
                    time.sleep(0.5)
                
                denominations = ['1000', '100', '10']
                for denom in denominations:
                    if denom in stat_coords:
                        denom_value = int(denom)
                        clicks = stat_points // denom_value
                        if clicks > 0:
                            coords = self.get_relative_coords(stat_coords[denom], ref_point)
                            logging.debug(f"Need {clicks} clicks on {denom} button for {stat}")
                            logging.debug(f"Click position: X={coords[0]} Y={coords[1]}")
                            
                            for click in range(clicks):
                                pyautogui.click(coords[0], coords[1])
                                logging.debug(f"Click {click + 1}/{clicks} for {denom}")
                                time.sleep(0.2)
                                
                            stat_points %= denom_value
                            time.sleep(0.5)
                            
                # Hide plus info after completing attribute
                pyautogui.click(first_coords[0], first_coords[1])
                time.sleep(0.5)
                                
            except Exception as e:
                logging.error(f"Error distributing points for {stat}: {e}")
                continue
        
        return True

    def read_stats(self, max_retries=1000):
        """
        Lee las estadísticas del personaje (nivel y resets).
        Args:
            max_retries: Máximo número de reintentos
        Returns:
            tuple: (nivel, resets)
        """
        if max_retries <= 0:
            logging.error("Failed to read stats after maximum retries")
            return self.level, self.resets

        try:
            ref_point = self.get_elemental_reference()
            if not ref_point:
                return self.read_stats(max_retries - 1)

            # Get relative coordinates
            level_coords = self.get_relative_coords(self.config['ocr_coordinates']['level'], ref_point)
            reset_coords = self.get_relative_coords(self.config['ocr_coordinates']['reset'], ref_point)

            # Level read
            level_area = ImageGrab.grab(bbox=tuple(level_coords))
            level_path = 'level_test.png'
            level_area.save(level_path)
            
            level_thresh = self._preprocess_image(level_path)
            if level_thresh is not None:
                level_text = pytesseract.image_to_string(Image.fromarray(level_thresh), 
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789')
                level_numeric_value = self._extract_numeric_value(level_text)
                
                if level_numeric_value > 0:
                    # Additional validation to prevent unnecessary recursion
                    if (level_numeric_value < self.level or 
                        level_numeric_value > self.config['max_level']):
                        return self.read_stats(max_retries - 1)
                    self.level = level_numeric_value
                else:
                    return self.read_stats(max_retries - 1)

            # Reset read
            reset_area = ImageGrab.grab(bbox=tuple(reset_coords))
            reset_path = 'reset_test.png'
            reset_area.save(reset_path)
            
            reset_thresh = self._preprocess_image(reset_path)
            if reset_thresh is not None:
                reset_text = pytesseract.image_to_string(Image.fromarray(reset_thresh), 
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789')
                reset_numeric_value = self._extract_numeric_value(reset_text)
                
                if reset_numeric_value > 0:
                    # Additional validation to prevent unnecessary recursion
                    if reset_numeric_value < self.resets:
                        return self.read_stats(max_retries - 1)
                    self.resets = reset_numeric_value
                else:
                    return self.read_stats(max_retries - 1)

            logging.info(f"======== RESET: {self.resets} ========")
            logging.info(f"======== LEVEL: {self.level} ========")
            return self.level, self.resets

        except Exception as e:
            logging.error(f"Error reading stats: {e}")
            return self.read_stats(max_retries - 1)

    def adjust_coordinates(self, coordinates):
        """
        Ajusta coordenadas basadas en punto de referencia.
        Args:
            coordinates: Coordenadas a ajustar
        Returns:
            list: Coordenadas ajustadas
        """

        if not self.reference_point:
            return coordinates
            
        try:
            # Your config uses absolute coordinates, so we'll adjust based on the reference point directly
            offset_x = self.reference_point[0] - coordinates[0]
            offset_y = self.reference_point[1] - coordinates[1]
            
            adjusted_coordinates = [
                coordinates[0] + offset_x,
                coordinates[1] + offset_y,
                coordinates[2] + offset_x,
                coordinates[3] + offset_y
            ]
            
            logging.debug(f"Original coordinates: {coordinates}")
            logging.debug(f"Adjusted coordinates: {adjusted_coordinates}")
            return adjusted_coordinates
            
        except Exception as e:
            logging.error(f"Error adjusting coordinates: {e}")
            return coordinates

    def read_stats(self):
        """
        Lee las estadísticas del personaje (nivel y resets).
        Args:
            max_retries: Máximo número de reintentos
        Returns:
            tuple: (nivel, resets)
        """
        try:
            ref_point = self.get_elemental_reference()
            if not ref_point:
                return self.read_stats()

            # Get relative coordinates
            level_coords = self.get_relative_coords(self.config['ocr_coordinates']['level'], ref_point)
            reset_coords = self.get_relative_coords(self.config['ocr_coordinates']['reset'], ref_point)

            # Level read
            level_area = ImageGrab.grab(bbox=tuple(level_coords))
            level_path = 'level_test.png'
            level_area.save(level_path)
            
            level_thresh = self._preprocess_image(level_path)
            if level_thresh is not None:
                level_text = pytesseract.image_to_string(Image.fromarray(level_thresh), 
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789')
                level_numeric_value = self._extract_numeric_value(level_text)
                
                if level_numeric_value > 0:
                    if level_numeric_value < self.level or level_numeric_value > self.config['max_level']:
                        return self.read_stats()
                    self.level = level_numeric_value
                else:
                    return self.read_stats()

            # Reset read
            reset_area = ImageGrab.grab(bbox=tuple(reset_coords))
            reset_path = 'reset_test.png'
            reset_area.save(reset_path)
            
            reset_thresh = self._preprocess_image(reset_path)
            if reset_thresh is not None:
                reset_text = pytesseract.image_to_string(Image.fromarray(reset_thresh), 
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789')
                reset_numeric_value = self._extract_numeric_value(reset_text)
                
                if reset_numeric_value > 0:
                    if reset_numeric_value < self.resets:
                        return self.read_stats()
                    self.resets = reset_numeric_value
                else:
                    return self.read_stats()

            logging.info(f"======== RESET: {self.resets} ========")
            logging.info(f"======== LEVEL: {self.level} ========")
            return self.level, self.resets

        except Exception as e:
            logging.error(f"Error reading stats: {e}")
            return self.read_stats()

    def move_to_coordinates(self, target_x: int, target_y: int):
        """
        Mueve el personaje a las coordenadas especificadas.
        Args:
            target_x: Coordenada X objetivo
            target_y: Coordenada Y objetivo
        """
        if not self.get_current_position():
            logging.error("Failed to get initial position")
            return
            
        start_time = time.time()
        stuck_count = 0
        last_pos = {'x': self.current_x, 'y': self.current_y}
        movement_history = []
        
        while True:
            current_time = time.time()
            if not self.get_current_position():
                logging.warning("Lost position tracking, resetting to location")
                self.move_to_location(f'/move {self.current_location}')
                time.sleep(2)
                continue
                
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            distance = (dx**2 + dy**2)**0.5
            
            movement = {
                'time': current_time - start_time,
                'position': (self.current_x, self.current_y),
                'target': (target_x, target_y),
                'stuck_count': stuck_count,
                'dx': dx,
                'dy': dy
            }
            movement_history.append(movement)
            logging.debug(f"Movement detail: {movement}")
            logging.info(f"Current: ({self.current_x}, {self.current_y}), Target: ({target_x}, {target_y}), Distance: {distance:.2f}, dx: {dx}, dy: {dy}")
            
            position_change = abs(self.current_x - last_pos['x']) + abs(self.current_y - last_pos['y'])
            if position_change < 5:
                stuck_count += 1
                logging.warning(f"Potential stuck detection: count={stuck_count}, position_change={position_change}")
                if stuck_count >= 3:
                    logging.error(f"Stuck detected! Last movements: {movement_history[-5:]}")
                    self.move_to_location(f'/move {self.current_location}')
                    time.sleep(2)
                    stuck_count = 0
                    continue
            else:
                stuck_count = 0
                
            if abs(dx) > 10:
                key = 'left' if dx < 0 else 'right'
                logging.debug(f"Pressing {key} key (dx={dx})")
                pyautogui.keyDown(key)
                pyautogui.keyUp(key)
                
            if abs(dy) > 10:
                key = 'down' if dy < 0 else 'up'  # Fixed direction logic here
                logging.debug(f"Pressing {key} key (dy={dy})")
                pyautogui.keyDown(key)
                pyautogui.keyUp(key)
                
            time.sleep(0.1)
            
            if abs(dx) <= 10 and abs(dy) <= 10:
                logging.info(f"Target reached: ({self.current_x}, {self.current_y})")
                self.check_and_click_play(target_x, target_y)
                break
                
            last_pos = {'x': self.current_x, 'y': self.current_y}

    def move_to_location(self, command: str):
        """
        Mueve el personaje a una ubicación usando un comando.
        Args:
            command: Comando de movimiento
        """
        location = command.replace('/move ', '')
        if location != self.current_location:
            self.distribute_attributes()
            if self.level >= self.config['reset_level']:
                time.sleep(1)
                
            self.play = False
            pyautogui.press('enter')
            pyautogui.write(command)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.press('c')
            self.current_location = location

    def check_and_click_play(self, x, y):
        """
        Verifica y activa el botón de play si es necesario.
        Args:
            x: Coordenada X actual
            y: Coordenada Y actual
        """
        try:
            play_coords = self.config['ocr_coordinates']['play']
            play_button_area = ImageGrab.grab(bbox=tuple(play_coords))
            play_button_area.save('play_button_area.png')
            
            if abs(self.current_x - x) <= 10 and abs(self.current_y - y) <= 10 and not self.play:
                pyautogui.click(play_coords[0] + 5, play_coords[1] + 3)
                self.play = True
                logging.info("Play button clicked - was inactive (green)")
            elif self.play:
                logging.info("Play already active (red) - skipping click")
                
        except Exception as e:
            logging.error(f"Error checking play button: {e}")

    def reset_character(self):
        """Reinicia el personaje y distribuye atributos"""
        pyautogui.press('enter')
        pyautogui.write('/reset')
        self.level = 0
        self.resets = 0
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('c')
        self.distribute_attributes()

    def run(self):
        """Ejecuta el bucle principal del bot"""
        while self.running:  # Changed from while True
            try:
                if not self.running:
                    return
                
                pyautogui.click(self.screen_width // 2, self.screen_height // 2)  # Focus game at the center
                time.sleep(1)
                
                if self.first_time:
                    logging.info("Open Stats")
                    pyautogui.press('c')
                    self.first_time = False
                if self.consecutive_errors > self.config['error_threshold']:
                    logging.error("Many consecutives errors")
                    self.move_to_location('/move lorencia')
                    time.sleep(5)
                    self.consecutive_errors = 0
                    
                #if self.record_good_path:
                #    self.path_learner.record_good_path(self, self.current_location, duration=30, interval=1)
                    
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