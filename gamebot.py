import os
import pyautogui
import time
import logging
import pytesseract

from pathlearner import PathLearner
from interface import Interface
from utils import Utils
from config import Configuration
from PIL import Image, ImageGrab

class GameBot:
    
    consecutive_errors = 0
    """
    Un bot para automatizar acciones en un juego. Maneja movimientos, estadísticas y atributos del personaje.
    """
    def __init__(self):
        self.config = Configuration()
        self.logging = logging.getLogger(__name__)
        self.interface = Interface(self.config)
        self.utils = Utils()
        self.interface.load_ocr_packages()
        pyautogui.FAILSAFE = False
        self.running = True
        self.current_location = None
        self.play = False
        self.path_learner = PathLearner()
        self.record_good_path = False
        self.reference_point = None
        self.first_time = True
        

    # Update _fetch_position in GameBot class:
    def _fetch_position(self):
        """
        Obtiene la posición actual del personaje.
        Returns:
            tuple: Coordenadas actuales (x,y)
        Raises:
            ValueError: Si el formato de coordenadas es inválido
        """
        raw_data = self.interface.get_position_data()
        if not self.utils.is_valid_coordinate(raw_data):
            # Try processing as single string of digits
            coords = self.utils.process_coordinates(raw_data)
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
                self.logging.warning(f"Attempt {attempt + 1} failed to get current position: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return False

    def distribute_attributes(self):
        """Distribuye puntos de atributos disponibles según la configuración."""
        ref_point = self.interface.get_elemental_reference()
        if not ref_point:
            self.logging.error("Cannot distribute attributes - reference point not found")
            return False

        self.logging.info(f"Reference point found at: {ref_point}")

        # First read all stats
        self.read_all_stats()
        current_state = self.config.get_game_state()

        # Log current state
        self.logging.info("Current stats:")
        self.logging.info(f"Available Points: {current_state['available_points']}")
        self.logging.info(f"Strength: {current_state['current_strenght']}")
        self.logging.info(f"Agility: {current_state['current_agility']}")
        self.logging.info(f"Vitality: {current_state['current_vitality']}")
        self.logging.info(f"Command: {current_state['current_command']}")

        # Take screenshot of stats area for debugging
        try:
            stats_area = ImageGrab.grab()
            stats_path = os.path.join(self.config.dirs['images'], 'stats_area_debug.png')
            stats_area.save(stats_path)
            self.logging.info(f"Saved stats area screenshot to {stats_path}")
        except Exception as e:
            self.logging.error(f"Failed to save debug screenshot: {e}")
        
        # Check if we have read stats correctly
        if (current_state['available_points'] == -1 or
            current_state['current_strenght'] == -1 or
            current_state['current_agility'] == -1 or
            current_state['current_vitality'] == -1 or
            current_state['current_command'] == -1):
            self.logging.error("Stats not properly read, values still at -1")
            return False

        available_points = current_state['available_points']
        if available_points <= 0:
            self.logging.info("No points available to distribute")
            return False

        self.logging.info(f"Starting distribution of {available_points} available points")
        self.logging.info(f"Stat distribution config: {self.config.file['stat_distribution']}")

        for stat, ratio in self.config.file['stat_distribution'].items():
            stat_points = int(available_points * ratio)
            if stat_points <= 0:
                self.logging.info(f"Skipping {stat} - no points to allocate (ratio: {ratio})")
                continue

            self.logging.info(f"Allocating {stat_points} points to {stat}")

            try:
                stat_coords = self.config.file['ocr_coordinates']['attributes'][stat]
                self.logging.info(f"Base coordinates for {stat}: {stat_coords}")

                if 'first_button' in stat_coords:
                    first_coords = self.utils.get_relative_coords(stat_coords['first_button'], ref_point)
                    self.logging.info(f"Clicking first button at relative coords: {first_coords}")
                    self.interface.mouse_click(x=first_coords[0], y=first_coords[1])
                    time.sleep(0.5)

                denominations = ['1000', '100', '10']
                for denom in denominations:
                    if denom in stat_coords:
                        denom_value = int(denom)
                        clicks = stat_points // denom_value
                        if clicks > 0:
                            coords = self.utils.get_relative_coords(stat_coords[denom], ref_point)
                            self.logging.info(f"Will click {clicks} times on {denom} button at coords {coords}")
                            for click in range(clicks):
                                self.logging.debug(f"Click {click + 1}/{clicks} for {denom} on {stat}")
                                self.interface.mouse_click(x=coords[0], y=coords[1])
                                time.sleep(0.2)
                            stat_points %= denom_value
                            time.sleep(0.5)

                    # Log remaining points after this denomination
                    self.logging.debug(f"Remaining points for {stat} after {denom}: {stat_points}")

                # Hide plus info
                if 'first_button' in stat_coords:
                    self.logging.info(f"Hiding plus info for {stat}")
                    self.interface.mouse_click(x=first_coords[0], y=first_coords[1])
                    time.sleep(0.5)

            except Exception as e:
                self.logging.error(f"Error distributing points for {stat}: {e}")
                self.logging.error(f"Stat coordinates: {stat_coords}")
                continue

        # Read stats again after distribution
        self.logging.info("Distribution complete, reading final stats")
        self.read_all_stats()
        final_state = self.config.get_game_state()
        self.logging.info("Final stats:")
        self.logging.info(f"Available Points: {final_state['available_points']}")
        self.logging.info(f"Strength: {final_state['current_strenght']}")
        self.logging.info(f"Agility: {final_state['current_agility']}")
        self.logging.info(f"Vitality: {final_state['current_vitality']}")
        self.logging.info(f"Command: {final_state['current_command']}")
        return True

    def read_all_stats(self):
        """Read and save all character stats"""
        try:
            self.interface.ensure_stats_window_open()
            
            ref_point = self.interface.get_elemental_reference()
            if not ref_point:
                return self.read_all_stats()

            level = self.interface.convert_image_into_number('level', ref_point, 'level')
            reset = self.interface.convert_image_into_number('reset', ref_point, 'reset')

            strenght = self.interface.read_attribute('strenght', ref_point)
            agility = self.interface.read_attribute('agility', ref_point)
            vitality = self.interface.read_attribute('vitality', ref_point)
            energy = self.interface.read_attribute('energy', ref_point)
            command = self.interface.read_attribute('command', ref_point)
            
            available_coords = self.config.get_ocr_coordinates()['available_points']
            points_coords = self.utils.get_relative_coords(available_coords, ref_point)
            points_area = ImageGrab.grab(bbox=tuple(points_coords))
            points_path = os.path.join(self.config.dirs['images'], 'available_points.png')
            points_area.save(points_path)

            preprocessed = self.interface._preprocess_image(points_path)
            points_text = pytesseract.image_to_string(
                preprocessed,
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            )
            available_points = self.utils.extract_numeric_value(points_text)

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

            self.config.update_game_state(state)

            self.logging.info(f"======== RESET: {reset} ========")
            self.logging.info(f"======== LEVEL: {level} ========")
            self.logging.info(f"======== STATS: STR:{strenght} AGI:{agility} VIT:{vitality} ENE:{energy} CMD:{command} ========")
            self.logging.info(f"======== AVAILABLE POINTS: {available_points} ========")

            return level, reset

        except Exception as e:
            self.logging.error(f"Error reading stats: {e}")
            return self.read_all_stats()

    def move_to_location(self, command: str, avoid_checks=False):
        """Modified to keep stats window consistently open"""
        if not avoid_checks:
            location = command.replace('/move ', '')
            current_state = self.config.get_game_state()

            if location != current_state['current_map']:
                self.distribute_attributes()
                if current_state['current_level'] >= self.config.file['reset_level']:
                    time.sleep(0.1)

                self.play = False
                pyautogui.press('enter')
                pyautogui.write(command)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('c')  # Reopen stats after command

                self.config.update_game_state({'current_map': location})
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
            self.logging.error("Failed to get initial position")
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
            current_state = self.config.get_game_state()
            play_coords = self.config.file['ocr_coordinates']['play']
            play_button_area = ImageGrab.grab(bbox=tuple(play_coords))
            play_path = os.path.join(self.config.dirs['images'], 'play_button_area.png')
            play_button_area.save(play_path)

            if abs(self.current_x - x) <= 10 and abs(self.current_y - y) <= 10 and not self.play:
                pyautogui.click(play_coords[0] + 5, play_coords[1] + 3)
                self.play = True
                self.config.update_game_state({'current_location': [x, y]})
                self.logging.info("Play button clicked - was inactive (green)")
            elif self.play:
                self.logging.info("Play already active (red) - skipping click")

        except Exception as e:
            self.logging.error(f"Error checking play button: {e}")

    def reset_character(self):
        """Reset character and manage stats window"""
        pyautogui.press('c')  # Close stats window before reset
        time.sleep(0.5)
        pyautogui.press('enter')
        pyautogui.write('/reset')
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('c')  # Reopen stats window after reset

        current_state = self.config.get_game_state()
        new_reset = current_state['current_reset'] + 1
        self.config.update_game_state({
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

                self.interface.click_center_screen()

                # Primera inicialización
                if self.first_time:
                    self.logging.info("1. Move to lorencia first")
                    self.move_to_location('/move lorencia')
                    self.first_time = False

                # Manejo de errores consecutivos
                if self.consecutive_errors > self.config.file['error_threshold']:
                    self.logging.error("Many consecutives errors")
                    self.play = False  # Reset play state
                    self.move_to_location('/move lorencia')
                    time.sleep(5)
                    self.consecutive_errors = 0

                level, resets = self.read_all_stats()

                # Resetear si alcanza el nivel configurado
                if level >= self.config.file['reset_level'] <= self.config.file['max_level']:
                    self.play = False  # Reset play state
                    self.reset_character()
                    # Después del reset, ejecutar el flujo normal una vez
                    if level < self.config.file['max_level']:
                        for threshold, obj in sorted(self.config.file['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                            if level >= int(threshold):
                                self.move_to_location(obj["command"])
                                x = obj["location"][0]
                                y = obj["location"][1]
                                self.move_to_coordinates(x,y)
                                self.check_and_click_play(x,y)
                                break

                # Si no está jugando, ejecutar el flujo normal
                elif not self.play and level < self.config.file['max_level']:
                    for threshold, obj in sorted(self.config.file['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                        if level >= int(threshold):
                            self.move_to_location(obj["command"])
                            x = obj["location"][0]
                            y = obj["location"][1]
                            self.move_to_coordinates(x,y)
                            self.check_and_click_play(x,y)
                            break
                elif self.play:
                    for threshold, obj in sorted(self.config.file['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
                        if level >= int(threshold):
                            self.move_to_location(obj["command"])
                            x = obj["location"][0]
                            y = obj["location"][1]
                            self.move_to_coordinates(x,y)
                            self.check_and_click_play(x,y)
                            break

                self.consecutive_errors = 0
                time.sleep(self.config.file['check_interval'])

            except KeyboardInterrupt:
                self.logging.info("Bot stopped by user")
                break
            except Exception as e:
                self.consecutive_errors += 1
                self.logging.error(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    bot = GameBot()
    time.sleep(5)
    bot.run()