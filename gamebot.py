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
        self.setup_screen()
        self.setup_directories()
        self.setup_keyboard_listener()
        self.setup_logging()
        self.load_config('config.json')
        self.initialize_game_state()
        pyautogui.FAILSAFE = False
        self.running = True
        self.current_location = None
        self.play = False
        self.path_learner = PathLearner()
        self.record_good_path = False
        self.reference_point = None
        self.first_time = True
        self.load_game_state()

    def setup_directories(self):
        """Creates necessary directories for organizing files"""
        self.dirs = {
            'images': 'images',
            'json': 'json',
            'logs': 'logs'
        }

        for directory in self.dirs.values():
            os.makedirs(directory, exist_ok=True)

    def load_game_state(self):
        """Loads the current game state from path_history.json"""
        state_file = os.path.join(self.dirs['json'], 'path_history.json')
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    self.game_state = json.load(f)
        except Exception as e:
            logging.error(f"Error loading game state: {e}")

    def setup_keyboard_listener(self):
        """Configura un listener para detectar la tecla F9 que detiene el bot"""
        def on_press(key):
            if key == keyboard.Key.f9:
                logging.info("Bot stopped")
                os._exit(0)  # Force exit the entire program

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def save_game_state(self):
        """Saves the current game state to path_history.json"""
        state_file = os.path.join(self.dirs['json'], 'path_history.json')
        try:
            with open(state_file, 'w') as f:
                json.dump(self.game_state, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving game state: {e}")

    def setup_logging(self):
        """Configura el sistema de logging y limpia logs anteriores"""
        log_file = os.path.join(self.dirs['logs'], 'bot_debug.log')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Reset root logger
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Configure file-only logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='w'
        )

        # Suppress PIL and Tesseract debug logs
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.WARNING)
        
    def load_config(self, config_path: str):
        """Carga la configuración del bot desde un archivo JSON"""
        config_file = os.path.join(self.dirs['json'], config_path)
        with open(config_file) as f:
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
            coord_area_path = os.path.join(self.dirs['images'], 'coord_area_path.png')
            coord_area.save(coord_area_path)
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

    def get_game_state(self):
        """Read current state from file with default values"""
        try:
            state_file = os.path.join(self.dirs['json'], 'current_status.json')
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    return json.load(f)
            return {
                "current_reset": 0,
                "current_level": 0,
                "current_map": "Lorencia",
                "current_location": [],
                "current_strenght": 0,
                "current_agility": 0,
                "current_vitality": 0,
                "current_energy": 0,
                "current_command": 0,
                "available_points": 0
            }
        except Exception as e:
            logging.error(f"Error reading game state: {e}")
            return None

    def update_game_state(self, updates):
        """Update state file with validation"""
        try:
            current_state = self.get_game_state() or {}
            current_state.update(updates)

            state_file = os.path.join(self.dirs['json'], 'current_status.json')
            with open(state_file, 'w') as f:
                json.dump(current_state, f, indent=4)
            return True
        except Exception as e:
            logging.error(f"Error writing game state: {e}")
            return False

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
        """Localiza el punto de referencia elemental en la pantalla."""
        logging.debug("Attempting to locate elemental reference on the screen")
        
        image_path = os.path.join(self.dirs['images'], 'tofind', 'elemental_reference.png')
        if not os.path.exists(image_path):
            logging.error(f"Reference image not found at: {image_path}")
            return None
            
        for attempt in range(3):
            time.sleep(1)
            try:
                elemental_loc = pyautogui.locateOnScreen(image_path, confidence=0.7)
                if elemental_loc:
                    logging.debug(f"Found elemental reference at: {elemental_loc}")
                    return pyautogui.center(elemental_loc)
                logging.warning(f"Attempt {attempt + 1}: Reference not found")
            except Exception as e:
                logging.error(f"Error finding elemental reference on attempt {attempt + 1}: {str(e)}")
        return None

        def get_toolbar_reference(self):
            """
            Localiza el punto de referencia toolbar en la pantalla.
            Returns:
                tuple: Coordenadas del punto de referencia o None
            """
            logging.debug("Attempting to locate toolbar reference on the screen")
            for attempt in range(3):  # Retry logic
                time.sleep(1)
                try:
                    toolbar_loc = pyautogui.locateOnScreen("./images/tofind/toolbar_reference.png", confidence=0.7)
                    if not toolbar_loc:
                        logging.warning(f"Attempt {attempt + 1}: toolbar reference not found")
                        continue
                    return pyautogui.center(toolbar_loc)
                except Exception as e:
                    logging.error(f"Error finding toolbar reference on attempt {attempt + 1}: {e}")
            return None

    def distribute_attributes(self):
        """Distribuye puntos de atributos disponibles según la configuración."""
        ref_point = self.get_elemental_reference()
        if not ref_point:
            logging.error("Cannot distribute attributes - reference point not found")
            return False

        logging.info(f"Reference point found at: {ref_point}")

        # First read all stats
        self.read_all_stats()
        current_state = self.get_game_state()

        # Log current state
        logging.info("Current stats:")
        logging.info(f"Available Points: {current_state['available_points']}")
        logging.info(f"Strength: {current_state['current_strenght']}")
        logging.info(f"Agility: {current_state['current_agility']}")
        logging.info(f"Vitality: {current_state['current_vitality']}")
        logging.info(f"Command: {current_state['current_command']}")

        # Take screenshot of stats area for debugging
        try:
            stats_area = ImageGrab.grab()
            stats_path = os.path.join(self.dirs['images'], 'stats_area_debug.png')
            stats_area.save(stats_path)
            logging.info(f"Saved stats area screenshot to {stats_path}")
        except Exception as e:
            logging.error(f"Failed to save debug screenshot: {e}")
        
        # Check if we have read stats correctly
        if (current_state['available_points'] == -1 or
            current_state['current_strenght'] == -1 or
            current_state['current_agility'] == -1 or
            current_state['current_vitality'] == -1 or
            current_state['current_command'] == -1):
            logging.error("Stats not properly read, values still at -1")
            return False

        available_points = current_state['available_points']
        if available_points <= 0:
            logging.info("No points available to distribute")
            return False

        logging.info(f"Starting distribution of {available_points} available points")
        logging.info(f"Stat distribution config: {self.config['stat_distribution']}")

        for stat, ratio in self.config['stat_distribution'].items():
            stat_points = int(available_points * ratio)
            if stat_points <= 0:
                logging.info(f"Skipping {stat} - no points to allocate (ratio: {ratio})")
                continue

            logging.info(f"Allocating {stat_points} points to {stat}")

            try:
                stat_coords = self.config['ocr_coordinates']['attributes'][stat]
                logging.info(f"Base coordinates for {stat}: {stat_coords}")

                if 'first_button' in stat_coords:
                    first_coords = self.get_relative_coords(stat_coords['first_button'], ref_point)
                    logging.info(f"Clicking first button at relative coords: {first_coords}")
                    pyautogui.click(first_coords[0], first_coords[1])
                    time.sleep(0.5)

                denominations = ['1000', '100', '10']
                for denom in denominations:
                    if denom in stat_coords:
                        denom_value = int(denom)
                        clicks = stat_points // denom_value
                        if clicks > 0:
                            coords = self.get_relative_coords(stat_coords[denom], ref_point)
                            logging.info(f"Will click {clicks} times on {denom} button at coords {coords}")
                            for click in range(clicks):
                                logging.debug(f"Click {click + 1}/{clicks} for {denom} on {stat}")
                                pyautogui.click(coords[0], coords[1])
                                time.sleep(0.2)
                            stat_points %= denom_value
                            time.sleep(0.5)

                    # Log remaining points after this denomination
                    logging.debug(f"Remaining points for {stat} after {denom}: {stat_points}")

                # Hide plus info
                if 'first_button' in stat_coords:
                    logging.info(f"Hiding plus info for {stat}")
                    pyautogui.click(first_coords[0], first_coords[1])
                    time.sleep(0.5)

            except Exception as e:
                logging.error(f"Error distributing points for {stat}: {e}")
                logging.error(f"Stat coordinates: {stat_coords}")
                continue

        # Read stats again after distribution
        logging.info("Distribution complete, reading final stats")
        self.read_all_stats()
        final_state = self.get_game_state()
        logging.info("Final stats:")
        logging.info(f"Available Points: {final_state['available_points']}")
        logging.info(f"Strength: {final_state['current_strenght']}")
        logging.info(f"Agility: {final_state['current_agility']}")
        logging.info(f"Vitality: {final_state['current_vitality']}")
        logging.info(f"Command: {final_state['current_command']}")
        return True

    def read_attribute(self, attribute_name, ref_point):
        """Read attribute with validation based on config settings"""
        try:
            attribute_coords = self.config['ocr_coordinates']['attributes'][attribute_name]['points']
            relative_coords = self.get_relative_coords(attribute_coords, ref_point)

            attr_area = ImageGrab.grab(bbox=tuple(relative_coords))
            attr_path = os.path.join(self.dirs['images'], f'{attribute_name}_value.png')
            attr_area.save(attr_path)

            preprocessed = self._preprocess_image(attr_path)
            text = pytesseract.image_to_string(
                preprocessed,
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            )

            value = self._extract_numeric_value(text)

            # Get validation rules from config
            if 'validation' in self.config and attribute_name in self.config['validation']:
                min_val = self.config['validation'][attribute_name].get('min', 0)
                max_val = self.config['validation'][attribute_name].get('max', float('inf'))

                if not min_val <= value <= max_val:
                    logging.warning(f"{attribute_name} value out of range: {value}")
                    return self.read_attribute(attribute_name, ref_point)

            return value

        except Exception as e:
            logging.error(f"Error reading {attribute_name}: {e}")
            return 0

    def _extract_numeric_value(self, text):
        """Enhanced numeric value extraction"""
        try:
            # Clean the text
            cleaned = ''.join(filter(str.isdigit, text.strip()))
            if not cleaned:
                return 0

            # Handle common OCR mistakes
            if len(cleaned) > 4:  # Stats shouldn't be more than 4 digits
                cleaned = cleaned[:4]

            value = int(cleaned)

            # Validate reasonable ranges
            if value > 9999:
                return 0

            return value
        except ValueError:
            return 0

    def read_available_points(self, ref_point):
        """Read available attribute points"""
        try:
            coords = self.get_relative_coords(self.config['ocr_coordinates']['available_points'], ref_point)
            points_area = ImageGrab.grab(bbox=tuple(coords))
            points_path = os.path.join(self.dirs['images'], 'available_points.png')
            points_area.save(points_path)

            points_thresh = self._preprocess_image(points_path)
            if points_thresh is not None:
                points_text = pytesseract.image_to_string(
                    Image.fromarray(points_thresh),
                    config=r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789'
                )
                return self._extract_numeric_value(points_text)
        except Exception as e:
            logging.error(f"Error reading available points: {e}")
        return 0

    def read_all_stats(self):
        """Read and save all character stats"""
        try:
            self.ensure_stats_window_open()
            
            ref_point = self.get_elemental_reference()
            if not ref_point:
                return self.read_all_stats()

            level = self._read_numeric_area('level', ref_point)
            reset = self._read_numeric_area('reset', ref_point)

            strenght = self.read_attribute('strenght', ref_point)
            agility = self.read_attribute('agility', ref_point)
            vitality = self.read_attribute('vitality', ref_point)
            energy = self.read_attribute('energy', ref_point)
            command = self.read_attribute('command', ref_point)

            available_coords = self.config['ocr_coordinates']['available_points']
            points_coords = self.get_relative_coords(available_coords, ref_point)
            points_area = ImageGrab.grab(bbox=tuple(points_coords))
            points_path = os.path.join(self.dirs['images'], 'available_points.png')
            points_area.save(points_path)

            preprocessed = self._preprocess_image(points_path)
            points_text = pytesseract.image_to_string(
                preprocessed,
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            )
            available_points = self._extract_numeric_value(points_text)

            state = {
                'current_level': level,
                'current_reset': reset,
                'current_strenght': strenght,
                'current_agility': agility,
                'current_vitality': vitality,
                'current_energy': energy,
                'current_command': command,
                'available_points': available_points
            }

            self.update_game_state(state)

            logging.info(f"======== RESET: {reset} ========")
            logging.info(f"======== LEVEL: {level} ========")
            logging.info(f"======== STATS: STR:{strenght} AGI:{agility} VIT:{vitality} ENE:{energy} CMD:{command} ========")
            logging.info(f"======== AVAILABLE POINTS: {available_points} ========")

            return level, reset

        except Exception as e:
            logging.error(f"Error reading stats: {e}")
            return self.read_all_stats()

    def _read_numeric_area(self, area_name, ref_point):
        """Read numeric value from specified area"""
        coords = self.get_relative_coords(self.config['ocr_coordinates'][area_name], ref_point)
        area = ImageGrab.grab(bbox=tuple(coords))
        path = os.path.join(self.dirs['images'], f'{area_name}_test.png')
        area.save(path)

        preprocessed = self._preprocess_image(path)
        text = pytesseract.image_to_string(
            preprocessed,
            config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        )
        return self._extract_numeric_value(text)

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

    def ensure_stats_window_open(self):
        """Ensures the stats window stays open without image detection"""
        try:
            pyautogui.press('c')
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error pressing C key: {e}")

    def move_to_location(self, command: str, avoid_checks=False):
        """Modified to keep stats window consistently open"""
        if not avoid_checks:
            location = command.replace('/move ', '')
            current_state = self.get_game_state()

            if location != current_state['current_map']:
                self.distribute_attributes()
                if current_state['current_level'] >= self.config['reset_level']:
                    time.sleep(0.1)

                self.play = False
                pyautogui.press('enter')
                pyautogui.write(command)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('c')  # Reopen stats after command

                self.update_game_state({'current_map': location})
        else:
            self.play = False
            pyautogui.press('enter')
            pyautogui.write(command)
            pyautogui.press('enter')
            time.sleep(0.5)
            pyautogui.press('c')

    def move_to_coordinates(self, target_x: int, target_y: int):
        """Movement without stats window toggling"""
        if not self.get_current_position():
            logging.error("Failed to get initial position")
            return

        last_pos = {'x': self.current_x, 'y': self.current_y}
        stuck_count = 0
        move_delay = 0.05

        while True:
            if not self.get_current_position():
                self.move_to_location(f'/move {self.current_location}')
                continue

            dx = target_x - self.current_x
            dy = target_y - self.current_y
            
            position_change = abs(self.current_x - last_pos['x']) + abs(self.current_y - last_pos['y'])
            if position_change < 5:
                stuck_count += 1
                if stuck_count >= 3:
                    self.move_to_location(f'/move {self.current_location}')
                    stuck_count = 0
                    continue
            else:
                stuck_count = 0

            if abs(dx) > 10 or abs(dy) > 10:
                if abs(dx) > 10:
                    key = 'left' if dx < 0 else 'right'
                    pyautogui.keyDown(key)
                    pyautogui.keyUp(key)
                
                if abs(dy) > 10:
                    key = 'down' if dy < 0 else 'up'
                    pyautogui.keyDown(key)
                    pyautogui.keyUp(key)

                time.sleep(move_delay)
            else:
                self.check_and_click_play(target_x, target_y)
                break

            last_pos = {'x': self.current_x, 'y': self.current_y}

    def check_and_click_play(self, x, y):
        """Check play button and update location state"""
        try:
            current_state = self.get_game_state()
            play_coords = self.config['ocr_coordinates']['play']
            play_button_area = ImageGrab.grab(bbox=tuple(play_coords))
            play_path = os.path.join(self.dirs['images'], 'play_button_area.png')
            play_button_area.save(play_path)

            if abs(self.current_x - x) <= 10 and abs(self.current_y - y) <= 10 and not self.play:
                pyautogui.click(play_coords[0] + 5, play_coords[1] + 3)
                self.play = True
                self.update_game_state({'current_location': [x, y]})
                logging.info("Play button clicked - was inactive (green)")
            elif self.play:
                logging.info("Play already active (red) - skipping click")

        except Exception as e:
            logging.error(f"Error checking play button: {e}")

    def reset_character(self):
        """Reset character and manage stats window"""
        pyautogui.press('c')  # Close stats window before reset
        time.sleep(0.5)
        pyautogui.press('enter')
        pyautogui.write('/reset')
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('c')  # Reopen stats window after reset

        current_state = self.get_game_state()
        new_reset = current_state['current_reset'] + 1
        self.update_game_state({
            'current_reset': new_reset,
            'current_level': 0
        })
        self.distribute_attributes()

    def run(self):
        """Ejecuta el bucle principal del bot"""
        while self.running:
            try:
                if not self.running:
                    return

                pyautogui.click(self.screen_width // 2, self.screen_height // 2)

                # Primera inicialización
                if self.first_time:
                    logging.info("1. Move to lorencia first")
                    self.move_to_location('/move lorencia')
                    self.first_time = False

                # Manejo de errores consecutivos
                if self.consecutive_errors > self.config['error_threshold']:
                    logging.error("Many consecutives errors")
                    self.play = False  # Reset play state
                    self.move_to_location('/move lorencia')
                    time.sleep(5)
                    self.consecutive_errors = 0

                level, resets = self.read_all_stats()

                # Resetear si alcanza el nivel configurado
                if level >= self.config['reset_level'] <= self.config['max_level']:
                    self.play = False  # Reset play state
                    self.reset_character()
                    # Después del reset, ejecutar el flujo normal una vez
                    if level < self.config['max_level']:
                        for threshold, obj in sorted(self.config['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                            if level >= int(threshold):
                                self.move_to_location(obj["command"])
                                x = obj["location"][0]
                                y = obj["location"][1]
                                self.move_to_coordinates(x,y)
                                self.check_and_click_play(x,y)
                                break

                # Si no está jugando, ejecutar el flujo normal
                elif not self.play and level < self.config['max_level']:
                    for threshold, obj in sorted(self.config['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                        if level >= int(threshold):
                            self.move_to_location(obj["command"])
                            x = obj["location"][0]
                            y = obj["location"][1]
                            self.move_to_coordinates(x,y)
                            self.check_and_click_play(x,y)
                            break
                elif self.play:
                    for threshold, obj in sorted(self.config['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
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
                logging.info("Bot stopped by user")
                break
            except Exception as e:
                self.consecutive_errors += 1
                logging.error(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    bot = GameBot()
    time.sleep(5)
    bot.run()