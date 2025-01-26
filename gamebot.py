import time
import logging
import os

from pathlearner import PathLearner
from interface import Interface
from utils import Utils
from config import Configuration

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
        
        self.running = True
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
        raw_data = self.interface.get_position_data(with_comma=True)
        
        if ',' in raw_data:
            x, y = raw_data.split(',')
            return int(x), int(y)
            
        raise ValueError(f"Invalid coordinate format: '{raw_data}'")

    def get_current_coords_from_game(self, retries=900, delay=1):
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
                x, y = self._fetch_position()
                self.interface.set_current_coords([x,y])
                return True
            except Exception as e:
                self.logging.warning(f"Attempt {attempt + 1} failed to get current position: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return False

    def distribute_attributes(self):
        """Distribuye puntos de atributos disponibles según la configuración."""
        str_attr_to_add = 0
        agi_attr_to_add = 0
        vit_attr_to_add = 0
        ene_attr_to_add = 0
        com_attr_to_add = 0
        
        try:
            # First read all stats
            current_state = self.config.get_game_state()

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
            
            # Old Way

            for stat, ratio in self.config.file['stat_distribution'].items():
                stat_points = int(available_points * ratio)
                if stat_points <= 0:
                    self.logging.info(f"Skipping {stat} - no points to allocate (ratio: {ratio})")
                else:
                    self.interface.command_add_attributes(attribute=stat, points=stat_points)
                    self.logging.info(f"Allocating {stat_points} points to {stat}")

            # New way
            """
            for stat, ratio in self.config.file['stat_distribution'].items():
                if stat == "strenght":
                    str_attr_to_add = int(available_points * ratio)
                if stat == "agility":
                    agi_attr_to_add = int(available_points * ratio)
                if stat == "vitality":
                    vit_attr_to_add = int(available_points * ratio)
                if stat == "energy":
                    ene_attr_to_add = int(available_points * ratio)
                if stat == "command":
                    com_attr_to_add =  int(available_points * ratio)
                    
            self.interface.command_add_attributes(attribute="allstats", points=0, str_attr=str_attr_to_add, agi_attr=agi_attr_to_add, vit_attr=vit_attr_to_add, ene_attr=ene_attr_to_add, com_attr=com_attr_to_add)
            """
        except Exception as e:
            self.logging.error(f"Error distributing points for {stat}: {e}")

        # Read stats again after distribution
        self.logging.info("Distribution complete, reading final stats")
        
        return True

    def read_all_stats(self):
        """Read and save all character stats"""
        while True:
            try:
                self.interface.open_stats_window()
                ref_point = self.interface.get_elemental_reference()
                if not ref_point:
                    time.sleep(1)
                    continue
                
                # Read all stats
                stats = {}
                coords = self.config.get_ocr_coordinates()
                
                # Basic stats
                for stat in ['level', 'reset']:
                    stats[stat] = self.interface.convert_image_into_number(
                        coords=coords[stat], 
                        image_name=stat, 
                        relative_coords=ref_point
                    )
                    if stats[stat] <= 0:  # Invalid read
                        self.logging.error(f"Invalid {stat} value: {stats[stat]}")
                        raise ValueError(f"Invalid {stat} value: {stats[stat]}")

                # Attributes
                for attr in ['strenght', 'agility', 'vitality', 'energy', 'command']:
                    stats[attr] = self.interface.convert_image_into_number(
                        coords=coords['attributes'][attr]['points'],
                        image_name=attr,
                        relative_coords=ref_point
                    )
                    if stats[attr] < 0:  # Invalid read
                        self.logging.error(f"Invalid {attr} value: {stats[attr]}")
                        raise ValueError(f"Invalid {attr} value: {stats[attr]}")

                # Available points
                available_coords = coords['available_points']
                stats['available_points'] = self.interface.convert_image_into_number(
                    coords=available_coords,
                    image_name="available_points",
                    relative_coords=ref_point
                )
                if stats['available_points'] < 0:
                    self.logging.error(f"Invalid available points: {stats['available_points']}")
                    raise ValueError(f"Invalid available points: {stats['available_points']}")

                # Update state
                state = {
                    ''
                    'current_level': stats['level'],
                    'current_reset': stats['reset'],
                    'current_strenght': stats['strenght'],
                    'current_agility': stats['agility'],
                    'current_vitality': stats['vitality'],
                    'current_energy': stats['energy'],
                    'current_command': stats['command'],
                    'available_points': stats['available_points']
                }
                
                self.config.update_game_state(state)
                
                self.logging.info("Final stats:")
                self.logging.info(f"Available Points: {state['available_points']}")
                self.logging.info(f"Strength: {state['current_strenght']}")
                self.logging.info(f"Agility: {state['current_agility']}")
                self.logging.info(f"Vitality: {state['current_vitality']}")
                self.logging.info(f"Command: {state['current_command']}")
                return stats['level'], stats['reset']

            except Exception as e:
                self.logging.error(f"Error reading stats: {e}")
                time.sleep(1)

    def move_to_location(self, map_name: str, avoid_checks=False,stuck=False):
        """Modified to keep stats window consistently open"""
        
        if not avoid_checks:
            current_state = self.config.get_game_state()
            if map_name != current_state['current_map'] or stuck is True:
                if current_state['current_level'] >= self.config.file['reset_level']:
                    time.sleep(0.1)

                self.interface.set_mu_helper_status(False)
                self.interface.command_move_to_map(map_name=map_name)

                self.config.update_game_state({'current_map': map_name})
            else:
                self.logging.info(f"Character already in {map_name}. No need to move again")
        else:
            self.interface.set_mu_helper_status(False)
            self.interface.command_move_to_map(map_name=map_name)
            
        self.interface.open_stats_window()
        
    def check_level_kill_or_reset(self, level):
        for threshold, obj in sorted(self.config.file['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
            if level >= int(threshold):
                self.move_to_location(map_name=obj["map"])
                x = obj["location"][0]
                y = obj["location"][1]
                self.move_to_coordinates(x,y)
                self.check_and_click_play(x,y)
                break
        
    def lets_kill_some_mobs(self):
        
        current_state = self.config.get_game_state()
        level = self.interface.get_level(current_state)
        mu_helper_active = self.interface.get_mu_helper_status(current_state)
        
        reset_level = self.config.file['reset_level']
        max_level = self.config.file['max_level']
        
        # Reset
        if level >= reset_level <= max_level:
            self.interface.set_mu_helper_status(False)
            self.reset_character()
            # Después del reset, ejecutar el flujo normal una vez
            if level < max_level:
                self.check_level_kill_or_reset(level=level)
        # No esta farmeando
        elif not mu_helper_active and level < max_level:
            self.check_level_kill_or_reset(level=level)
        # Ponete a farmear
        elif mu_helper_active:
            self.check_level_kill_or_reset(level=level)

    def move_to_coordinates(self, target_x: int, target_y: int):
        """Movement without stats window toggling"""
        
        if not self.get_current_coords_from_game():
            self.logging.error("Failed to get initial position")
            return
        
        stuck_count = 0
        move_delay = 0.2
        current_state = self.config.get_game_state()
        current_map = self.interface.get_current_map(current_state)

        while True:
            
            # Store previous coordinates
            current_state = self.config.get_game_state()
            logging.debug("BEFORE LASTSS")
            logging.debug(self.interface.get_current_coords(current_state))
            last_x, last_y = self.interface.get_current_coords(current_state)
            logging.debug(f"X: {last_x}")
            logging.debug(f"Y: {last_y}")
            dx = target_x - last_x
            dy = target_y - last_y
            
            self.logging.debug(f"DX -> {dx}")
            self.logging.debug(f"DY -> {dy}")
            
            # Get new coordinates
            self.get_current_coords_from_game()
            current_state = self.config.get_game_state()
            now_x, now_y = self.interface.get_current_coords(current_state)
            
            # Compare with previous position
            position_change = abs(now_x - last_x) + abs(now_y - last_y)
            self.logging.debug(f"POSITION change -> {position_change}")
            if position_change < 2:
                stuck_count += 1
                if stuck_count >= 3:
                    self.logging.debug(f"Character it got stuck in some place, will move to {current_map}")
                    self.move_to_location(map_name=current_map, stuck=True)
                    stuck_count = 0
                    continue
            else:
                stuck_count = 0

            if abs(dx) > 10 or abs(dy) > 10:
                if abs(dx) > 10:
                    if dx < 0:
                        self.interface.arrow_key_left()
                        
                    else:
                        self.interface.arrow_key_right()
                
                if abs(dy) > 10:
                    if dy < 0:
                        self.interface.arrow_key_down()
                    else:
                        self.interface.arrow_key_up()

                self.get_current_coords_from_game()
                self.logging.debug(f"Actual position: [{last_x},{last_y}]")
                time.sleep(move_delay)
            else:
                self.check_and_click_play(target_x, target_y)
                break

    def check_and_click_play(self, x, y):
        """Check play button and update location state"""
        try:
            #current_state = self.config.get_game_state()
            play_coords = self.config.file['ocr_coordinates']['play']
            self.interface.take_screenshot_with_coords(coords=play_coords, image_name="play_button_area")

            self.get_current_coords_from_game()
            current_state = self.config.get_game_state()
            current_x, currenty_y = self.interface.get_current_coords(current_state=current_state)
            mu_helper_active = self.interface.get_mu_helper_status(current_state)
            
            if abs(current_x - x) <= 10 and abs(currenty_y - y) <= 10 and not mu_helper_active:
                self.interface.mouse_click(play_coords[0] + 5, play_coords[1] + 3)
                self.interface.set_mu_helper_status(True)
                self.interface.set_current_coords([x, y])
                self.logging.info("Play button clicked - was inactive (green)")
            elif mu_helper_active:
                self.logging.info("Play already active (red) - skipping click")

        except Exception as e:
            self.logging.error(f"Error checking play button: {e}")

    def reset_character(self):
        """Reset character and manage stats window"""
        self.interface.open_stats_window()
        self.interface.command_reset()
        self.interface.open_stats_window()

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
                    self.first_time = False
                    self.logging.info("1. Read stats")
                    self.read_all_stats()
                    self.logging.info("2. Assign attributes")
                    self.distribute_attributes()
                    
                    self.logging.info("3. Show last stats after add attributes")
                    self.read_all_stats()
                    
                else:
                    self.logging.info("1. Lets go to kill some mobs")
                    self.lets_kill_some_mobs()
                    self.logging.info(f"2. Wait {self.config.file['check_interval']} seconds until check and add stats")
                    time.sleep(self.config.file['check_interval'])
                    self.read_all_stats()
                    self.distribute_attributes()

            except KeyboardInterrupt:
                self.logging.info("Bot stopped by user")
                break
            except Exception as e:
                self.logging.error(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    bot = GameBot()
    time.sleep(5)
    bot.run()