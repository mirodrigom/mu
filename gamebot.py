import time
import logging
import os

from logger_config import setup_logging
from pathlearner import PathLearner
from interface import Interface
from utils import Utils
from config import Configuration
from gameclass import GameClass
from memory import Memory

class GameBot:
    
    consecutive_errors = 0
    """
    Un bot para automatizar acciones en un juego. Maneja movimientos, estadísticas y atributos del personaje.
    """
    def __init__(self):
        self.config = Configuration()
        setup_logging()
        self.logging = logging.getLogger(__name__)
        self.interface = Interface(self.config)
        self.gameclass = GameClass()
        self.utils = Utils()
        self.memory = Memory()
        
        self.interface.load_ocr_packages()
        
        self.running = True
        self.path_learner = PathLearner()
        self.record_good_path = False
        self.reference_point = None
        self.first_time = True
        self.current_path = []  # Store coordinates for current path
        self.good_paths = {}  # Dictionary to store successful paths by destination
        self.logging.info("GameBot initialized")
        

    def save_good_path(self, target_x: int, target_y: int):
        """
        Save the current path as a good path for reaching the target coordinates.
        """
        path_key = f"{target_x},{target_y}"
        if self.current_path:
            self.good_paths[path_key] = self.current_path.copy()
            self.logging.info(f"Saved good path to {path_key} with {len(self.current_path)} coordinates")
            
            # Optionally save to file for persistence
            try:
                path_file = f"good_path_{path_key}.txt"
                with open(path_file, 'w') as f:
                    for coord in self.current_path:
                        f.write(f"{coord[0]},{coord[1]}\n")
                self.logging.info(f"Saved path to file: {path_file}")
            except Exception as e:
                self.logging.error(f"Error saving path to file: {e}")
                
    def is_position_blocked(self, x: int, y: int, direction: str, history: list) -> bool:
        """
        Check if a position has been blocked recently based on movement history
        Returns True if the position appears to be blocked
        """
        for pos, dir in history[-5:]:  # Check last 5 movements
            if abs(pos[0] - x) < 3 and abs(pos[1] - y) < 3 and dir == direction:
                return True
        return False
    
    def format_movement_log(self, current_x: int, current_y: int, target_x: int, target_y: int, blocked: set = None, status: str = "") -> str:
        """Format a concise movement log string"""
        dx = target_x - current_x
        dy = target_y - current_y
        dist = abs(dx) + abs(dy)
        blocked_str = f"[Blocked: {','.join(blocked)}]" if blocked else ""
        status_str = f" | {status}" if status else ""
        return (f"[POS] Current:[{current_x},{current_y}] -> Target:[{target_x},{target_y}] | " f"D[{dx},{dy}] | Dist:{dist}{blocked_str}{status_str}")

    def find_alternative_route(self, current_x: int, current_y: int, target_x: int, target_y: int, blocked_directions: set, history: list) -> tuple:
        """
        Find an alternative route when direct path is blocked
        Returns the best available direction as (dx, dy)
        """
        possible_moves = []
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Calculate all possible 45-degree movements
        directions = [
            ('NE', 1, 1), ('NW', -1, 1), ('SE', 1, -1), ('SW', -1, -1),
            ('N', 0, 1), ('S', 0, -1), ('E', 1, 0), ('W', -1, 0)
        ]
        
        for name, move_x, move_y in directions:
            if name in blocked_directions:
                continue
                
            # Score this move based on how much closer it gets us to the target
            new_x = current_x + (move_x * 10)  # Project the position forward
            new_y = current_y + (move_y * 10)
            current_dist = abs(dx) + abs(dy)
            new_dist = abs(target_x - new_x) + abs(target_y - new_y)
            improvement = current_dist - new_dist
            
            if not self.is_position_blocked(new_x, new_y, name, history):
                possible_moves.append((improvement, move_x, move_y, name))
                self.logging.debug(f"[ROUTE] Possible move {name}: improvement={improvement}")
        
        if not possible_moves:
            self.logging.warning(f"[ROUTE] ⚠️ No valid moves found! Blocked directions: {blocked_directions}")
            return (0, 0)  # No valid moves found
            
        # Choose the best move
        possible_moves.sort(reverse=True)  # Sort by improvement
        return (possible_moves[0][1], possible_moves[0][2])



    # Update _fetch_position in GameBot class:
    def _fetch_position(self):
        """
        Obtiene la posición actual del personaje.
        Returns:
            tuple: Coordenadas actuales (x,y)
        Raises:
            ValueError: Si el formato de coordenadas es inválido
        """
        time.sleep(0.1)
        try:
            #x, y = self.interface.get_position_data_using_dashboard(with_comma=True)
            #x, y = self.interface.get_position_data(with_comma=True)        
            x, y = self.memory.get_coordinates()

            self.logging.debug(f"[POSITION] Parsed coordinates: [{x}, {y}]")
            return x, y
        except ValueError as e:
            self.logging.debug(f"[POSITION] Failed to parse comma format: {e}")
            raise e


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
                
                current_state = self.config.get_game_state()                
                # Read all stats
                stats = {
                    'level': 0,
                    'reset': 0,
                    'strenght': 0,
                    'agility': 0,
                    'vitality': 0,
                    'energy': 0,
                    'command': 0,  # Initialize command for all classes
                    'available_points': 0
                }
                
                # Basic stats
                for stat in ['level', 'reset', 'available_points']:
                    '''
                    if stat == 'level':
                        coords_level = self.interface.get_level_reference(current_state)
                        if len(coords_level) == 0:
                            coords_level = self.interface.get_text_from_screen("Nivel")
                        stats[stat] = self.interface.get_level_ocr(coords_level)
                        self.interface.set_level_reference(coords_level)
                    if stat == 'reset':
                        coords_reset = self.interface.get_reset_reference(current_state)
                        if len(coords_reset) == 0:
                            coords_reset = self.interface.get_text_from_screen("Resetear")
                        stats[stat] = self.interface.get_reset_ocr(coords_reset)
                        self.interface.set_reset_reference(coords_reset)
                    '''
                    if stat == 'available_points':
                        if not self.memory.available_points_addr:
                            coords_available_points = self.interface.get_available_attributes(current_state)
                            if len(coords_available_points) == 0:
                                coords_available_points = self.interface.get_text_from_screen("Puntos")
                            stats[stat] = self.interface.get_available_points_ocr(coords_available_points)
                            self.interface.set_available_attributes(coords_available_points)
                            
                            memory_available_points = self.memory.find_available_points_memory(stats[stat])
                            if memory_available_points and len(memory_available_points) == 1:
                                self.memory.available_points_addr = memory_available_points[0]
                                print(f"Set memory address to: 0x{self.memory.available_points_addr:X}")
                        
                        if self.memory.available_points_addr:
                            try:
                                value = self.memory.get_value_of_memory(self.memory.available_points_addr)
                                if value is not None:
                                    stats[stat] = value
                                    print(f"Successfully read value {value}")
                                else:
                                    print("Failed to read value, clearing address")
                                    self.memory.available_points_addr = None
                            except Exception as e:
                                print(f"Error reading memory: {str(e)}")
                                self.memory.available_points_addr = None
                                
                    #if not coords_available_points:
                    #    time.sleep(1)
                    #    continue
                    '''
                    if stats[stat] <= 0 and stat == 'level':  # Invalid read
                        self.logging.error(f"Invalid {stat} value: {stats[stat]}")
                        if stat == 'level':
                            self.interface.set_level_reference([])
                        raise ValueError(f"Invalid {stat} value: {stats[stat]}")
                    '''
                # Attributes
                '''
                for attr in self.gameclass.attributes:
                    if attr == 'strenght':
                        coords_attr = self.interface.get_attribute_reference(current_state, attr)
                        if len(coords_attr) == 0:
                            coords_attr = self.interface.get_text_from_screen("Fuerza")
                    if attr == 'agility':
                        coords_attr = self.interface.get_attribute_reference(current_state, attr)
                        if len(coords_attr) == 0:
                            coords_attr = self.interface.get_text_from_screen("Agilidad")
                    if attr == 'vitality':
                        coords_attr = self.interface.get_attribute_reference(current_state, attr)
                        if len(coords_attr) == 0:
                            coords_attr = self.interface.get_text_from_screen("Vitalidad")
                    if attr == 'energy':
                        coords_attr = self.interface.get_attribute_reference(current_state, attr)
                        if len(coords_attr) == 0:
                            coords_attr = self.interface.get_text_from_screen("Energia")
                    if attr == 'command':
                        coords_attr = self.interface.get_attribute_reference(current_state, attr)
                        if len(coords_attr) == 0:
                            coords_attr = self.interface.get_text_from_screen("Comando")
                        
                    self.interface.set_attribute_reference(attr, coords_attr)
                    stats[attr] = self.interface.get_attr_ocr(coords_attr, attr)
                '''
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
                continue
                time.sleep(1)

    def move_to_location(self, map_name: str, avoid_checks=False,stuck=False):
        """Modified to keep stats window consistently open"""
        
        if not avoid_checks:
            current_state = self.config.get_game_state()
            if map_name != current_state['current_map'] or stuck is True:

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
                if isinstance(obj, list):
                    location_obj = next((loc for loc in obj if loc["map"] == self.gameclass.start_location), obj[0])
                    self.move_to_location(map_name=location_obj["map"])
                    x = location_obj["location"][0]
                    y = location_obj["location"][1]
                else:
                    # Handle single location case as before
                    self.move_to_location(map_name=obj["map"])
                    x = obj["location"][0]
                    y = obj["location"][1]
                
                self.move_to_coordinates(x, y)
                self.check_and_click_play(x, y)
                break
        
    def lets_kill_some_mobs(self):
        
        current_state = self.config.get_game_state()
        level = self.interface.get_level(current_state)
        reset = self.interface.get_reset(current_state)
        mu_helper_active = self.interface.get_mu_helper_status(current_state)
        
        reset_level = self.gameclass.set_level_to_reset(reset)
        max_level = self.config.file['max_level']

        # Add debug logging
        self.logging.info(f"Current values - Level: {level}, Reset Level: {reset_level}, Max Level: {max_level}")

        # Reset
        if level >= reset_level and reset_level <= max_level:
            self.logging.info("Attempting to reset character...")
            self.interface.set_mu_helper_status(False)
            self.reset_character()
        # No esta farmeando
        elif not mu_helper_active and level < max_level:
            self.check_level_kill_or_reset(level=level)
        # Ponete a farmear
        elif mu_helper_active:
            self.check_level_kill_or_reset(level=level)
            
    def load_good_path(self, target_x: int, target_y: int):
        """
        Load a previously saved good path for the target coordinates.
        Returns None if no path exists.
        """
        path_key = f"{target_x},{target_y}"
        
        # First try memory
        if path_key in self.good_paths:
            return self.good_paths[path_key]
            
        # Then try file
        try:
            path_file = f"good_path_{path_key}.txt"
            if os.path.exists(path_file):
                path = []
                with open(path_file, 'r') as f:
                    for line in f:
                        x, y = map(int, line.strip().split(','))
                        path.append((x, y))
                self.good_paths[path_key] = path  # Cache in memory
                return path
        except Exception as e:
            self.logging.error(f"Error loading path from file: {e}")
        
        return None
    
    def get_current_coords_from_game(self, retries=5, delay=1):
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
                position = self._fetch_position()
                if position is None:
                    raise ValueError("Position returned None")
                    
                # Ensure position is in the correct format
                if isinstance(position, str):
                    # Assuming position is returned as "x,y" string
                    x, y = map(int, position.split(','))
                elif isinstance(position, (list, tuple)) and len(position) == 2:
                    x, y = position
                else:
                    raise ValueError(f"Unexpected position format: {position}")
                
                self.interface.set_current_coords([x,y])
                self.logging.info(f"[POSITION] Successfully got coordinates: [{x}, {y}] (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                self.logging.warning(f"[POSITION] ⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    self.interface.scroll(random_number=True)
                    time.sleep(delay)
        return False
    
    def detect_wall(self, positions_history, current_pos):
        """Enhanced wall detection with pattern recognition"""
        if len(positions_history) < 5:
            return False, set()
            
        # Check for complete immobility
        recent_positions = positions_history[-5:]
        if all(pos == recent_positions[0] for pos in recent_positions):
            self.logging.warning(f"[WALL] 🚫 Complete stuck detected at {current_pos}")
            return True, {'N', 'S', 'E', 'W'}
            
        # Analyze movement patterns
        x_values = [pos[0] for pos in positions_history[-7:]]
        y_values = [pos[1] for pos in positions_history[-7:]]
        
        x_movement = max(x_values) - min(x_values)
        y_movement = max(y_values) - min(y_values)
        
        blocked_directions = set()
        
        # Detect horizontal walls
        if y_movement <= 3:
            consecutive_y = sum(1 for i in range(len(y_values)-1) if abs(y_values[i] - y_values[i+1]) <= 1)
            if consecutive_y >= 4:
                if current_pos[1] >= positions_history[-5][1]:
                    blocked_directions.add('N')
                    self.logging.warning(f"[WALL] ⬆️ North movement blocked at y={current_pos[1]}")
                else:
                    blocked_directions.add('S')
                    self.logging.warning(f"[WALL] ⬇️ South movement blocked at y={current_pos[1]}")
        
        # Detect vertical walls
        if x_movement <= 3:
            consecutive_x = sum(1 for i in range(len(x_values)-1) if abs(x_values[i] - x_values[i+1]) <= 1)
            if consecutive_x >= 4:
                if current_pos[0] >= positions_history[-5][0]:
                    blocked_directions.add('E')
                    self.logging.warning(f"[WALL] ➡️ East movement blocked at x={current_pos[0]}")
                else:
                    blocked_directions.add('W')
                    self.logging.warning(f"[WALL] ⬅️ West movement blocked at x={current_pos[0]}")
        
        # Detect diagonal walls
        if len(positions_history) >= 7:
            diagonal_movement = sum(
                abs(positions_history[i+1][0] - positions_history[i][0]) +
                abs(positions_history[i+1][1] - positions_history[i][1])
                for i in range(len(positions_history)-2)
            )
            if diagonal_movement <= 5:
                self.logging.warning("[WALL] Diagonal movement appears blocked")
                blocked_directions.update({'NE', 'NW', 'SE', 'SW'})
        
        return bool(blocked_directions), blocked_directions
    
    def move_to_coordinates(self, target_x: int, target_y: int):
        """Enhanced movement method with 4-unit steps and stuck detection"""
        self.current_path = []
        positions_history = []
        stuck_count = 0
        escape_attempt = 0
        last_pos = None
        last_movement_type = None
        movement_timeout = time.time() + 300  # 5-minute timeout
        
        self.logging.info(f"[MOVEMENT] Starting movement to target [{target_x}, {target_y}]")
        
        if not self.get_current_coords_from_game():
            self.logging.error("[MOVEMENT] Failed to get initial position")
            return
            
        current_state = self.config.get_game_state()
        current_map = self.interface.get_current_map(current_state)
        mu_helper_active = self.interface.get_mu_helper_status(current_state)
        blocked_directions = set()
        last_successful_movement = time.time()
        
        while True:
            # Timeout check
            if time.time() > movement_timeout:
                self.logging.error("[MOVEMENT] Movement timeout reached. Resetting position.")
                self.move_to_location(map_name=current_map, stuck=True)
                return

            # Get current position
            if not self.get_current_coords_from_game():
                continue
            current_x, current_y = self._fetch_position()
            positions_history.append((current_x, current_y))
            
            # Calculate distance to target
            dx = target_x - current_x
            dy = target_y - current_y
            dist = abs(dx) + abs(dy)
            
            # Log current status
            self.logging.info(
                self.format_movement_log(
                    current_x, current_y, target_x, target_y,
                    blocked_directions, f"Last move: {last_movement_type}"
                )
            )
            
            if abs(dx) >= 20 and abs(dy) >= 20:
                if mu_helper_active == True:
                    self.interface.set_mu_helper_status(False)
                    self.logging.info(f"[MOVEMENT] ❌ You were killed 💀")
            else:
                if mu_helper_active == True:
                    self.logging.info(f"[MOVEMENT] ✅ No need to move he is already farming!")
                    break
            
            # Check if reached destination (within 8 units, 2x standard step size)
            if abs(dx) <= 8 and abs(dy) <= 8:
                self.logging.info(f"[MOVEMENT] ✅ Reached destination!")
                break
            
            # Stuck detection with improved logic for 4-unit steps
            if last_pos == (current_x, current_y):
                stuck_count += 1
                time_since_movement = time.time() - last_successful_movement
                
                if stuck_count >= 3 or time_since_movement > 10:
                    self.logging.warning(
                        f"[STUCK] 🚫 Stuck for {stuck_count} moves at [{current_x},{current_y}] "
                        f"Time since last movement: {time_since_movement:.1f}s"
                    )
                    self.interface.focus_application()
                    
                    # Progressive escape strategy
                    move_x, move_y, move_type = self.calculate_escape_vector(
                        (current_x, current_y),
                        blocked_directions,
                        escape_attempt,
                        (target_x, target_y)
                    )
                    escape_attempt += 1
                    
                    # Reset position if stuck for too long
                    if escape_attempt >= 8 or time_since_movement > 30:
                        self.logging.warning(
                            f"[RESET] 🔄 Failed to escape after {escape_attempt} attempts "
                            f"({time_since_movement:.1f}s), resetting position"
                        )
                        self.move_to_location(map_name=current_map, stuck=True)
                        return
            else:
                stuck_count = max(0, stuck_count - 1)  # Gradual reduction of stuck counter
                if escape_attempt > 0:
                    escape_attempt = max(0, escape_attempt - 1)
                    blocked_directions.clear()
                    last_successful_movement = time.time()
                    
            last_pos = (current_x, current_y)
            
            # Manage position history
            if len(positions_history) > 15:
                positions_history.pop(0)
                
            # Wall detection
            is_wall, new_blocked = self.detect_wall(positions_history, (current_x, current_y))
            if is_wall:
                blocked_directions.update(new_blocked)
                self.logging.warning(f"[WALL] Detected blocked directions: {blocked_directions}")
            
            # Calculate movement vector with 4-unit steps
            if stuck_count >= 3:
                move_x, move_y, move_type = self.calculate_escape_vector(
                    (current_x, current_y),
                    blocked_directions,
                    escape_attempt,
                    (target_x, target_y)
                )
            else:
                move_x, move_y, move_type = self.calculate_movement_vector(
                    current_x, current_y, target_x, target_y, blocked_directions
                )
                
            # Execute movement with dynamic delays
            success = self.execute_movement(move_x, move_y, move_type)
            if success:
                last_successful_movement = time.time()
                last_movement_type = move_type
                
            # Adaptive delay based on movement success and distance
            delay = 0.2 if dist > 50 else 0.3
            delay *= 1.5 if stuck_count > 0 else 1.0
            time.sleep(delay)

    def calculate_movement_vector(self, current_x, current_y, target_x, target_y, blocked_directions):
        """
        Calculate movement vector with 4-unit steps
        Returns: tuple (dx, dy, movement_type)
        """
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Define step size
        STEP_SIZE = 4
        
        # Calculate diagonal movements (combines two 4-unit steps)
        diagonal_moves = {
            'NE': (STEP_SIZE, STEP_SIZE),
            'NW': (-STEP_SIZE, STEP_SIZE),
            'SE': (STEP_SIZE, -STEP_SIZE),
            'SW': (-STEP_SIZE, -STEP_SIZE)
        }
        
        # First try diagonal movement if appropriate
        if abs(dx) >= STEP_SIZE and abs(dy) >= STEP_SIZE:
            if dx > 0 and dy > 0 and 'NE' not in blocked_directions:
                return diagonal_moves['NE'][0], diagonal_moves['NE'][1], 'diagonal_NE'
            elif dx < 0 and dy > 0 and 'NW' not in blocked_directions:
                return diagonal_moves['NW'][0], diagonal_moves['NW'][1], 'diagonal_NW'
            elif dx > 0 and dy < 0 and 'SE' not in blocked_directions:
                return diagonal_moves['SE'][0], diagonal_moves['SE'][1], 'diagonal_SE'
            elif dx < 0 and dy < 0 and 'SW' not in blocked_directions:
                return diagonal_moves['SW'][0], diagonal_moves['SW'][1], 'diagonal_SW'
        
        # If diagonal movement isn't appropriate, use cardinal directions
        if abs(dx) > abs(dy):
            if dx > 0 and 'E' not in blocked_directions:
                return STEP_SIZE, 0, 'cardinal_E'
            elif dx < 0 and 'W' not in blocked_directions:
                return -STEP_SIZE, 0, 'cardinal_W'
        else:
            if dy > 0 and 'N' not in blocked_directions:
                return 0, STEP_SIZE, 'cardinal_N'
            elif dy < 0 and 'S' not in blocked_directions:
                return 0, -STEP_SIZE, 'cardinal_S'
        
        # If primary direction is blocked, try alternative
        if abs(dx) >= STEP_SIZE:
            if dx > 0 and 'E' not in blocked_directions:
                return STEP_SIZE, 0, 'alternate_E'
            elif dx < 0 and 'W' not in blocked_directions:
                return -STEP_SIZE, 0, 'alternate_W'
        
        if abs(dy) >= STEP_SIZE:
            if dy > 0 and 'N' not in blocked_directions:
                return 0, STEP_SIZE, 'alternate_N'
            elif dy < 0 and 'S' not in blocked_directions:
                return 0, -STEP_SIZE, 'alternate_S'
        
        # If we're very close to target, make smaller movements
        if abs(dx) < STEP_SIZE and abs(dy) < STEP_SIZE:
            x_step = min(abs(dx), STEP_SIZE) * (1 if dx > 0 else -1)
            y_step = min(abs(dy), STEP_SIZE) * (1 if dy > 0 else -1)
            return x_step, y_step, 'fine_adjust'
        
        # Fallback movement
        return (STEP_SIZE if dx > 0 else -STEP_SIZE), (STEP_SIZE if dy > 0 else -STEP_SIZE), 'fallback'

    def calculate_escape_vector(self, current_pos, blocked_directions, attempt, target_pos=None):
        """Improved escape vector calculation with 4-unit steps"""
        STEP_SIZE = 4
        escape_patterns = []
        
        # If we have a target, prioritize movements that get us closer
        if target_pos:
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            
            # Determine primary movement direction based on target
            if abs(dx) > abs(dy):
                if dx > 0:  # Need to go right
                    escape_patterns = ['NE', 'E', 'SE', 'N', 'S', 'NW', 'SW', 'W']
                else:  # Need to go left
                    escape_patterns = ['NW', 'W', 'SW', 'N', 'S', 'NE', 'SE', 'E']
            else:
                if dy > 0:  # Need to go up
                    escape_patterns = ['NE', 'N', 'NW', 'E', 'W', 'SE', 'SW', 'S']
                else:  # Need to go down
                    escape_patterns = ['SE', 'S', 'SW', 'E', 'W', 'NE', 'NW', 'N']
        else:
            # Default escape patterns if no target
            escape_patterns = ['NE', 'NW', 'SE', 'SW', 'N', 'S', 'E', 'W']
        
        # Movement vectors with 4-unit steps
        vectors = {
            'N': (0, STEP_SIZE),      'S': (0, -STEP_SIZE),
            'E': (STEP_SIZE, 0),      'W': (-STEP_SIZE, 0),
            'NE': (STEP_SIZE, STEP_SIZE),    'NW': (-STEP_SIZE, STEP_SIZE),
            'SE': (STEP_SIZE, -STEP_SIZE),   'SW': (-STEP_SIZE, -STEP_SIZE),
            # Stronger movements for desperate situations
            'N2': (0, STEP_SIZE * 2),        'S2': (0, -STEP_SIZE * 2),
            'E2': (STEP_SIZE * 2, 0),        'W2': (-STEP_SIZE * 2, 0),
            'NE2': (STEP_SIZE * 2, STEP_SIZE * 2),
            'NW2': (-STEP_SIZE * 2, STEP_SIZE * 2),
            'SE2': (STEP_SIZE * 2, -STEP_SIZE * 2),
            'SW2': (-STEP_SIZE * 2, -STEP_SIZE * 2)
        }
        
        # Determine pattern based on attempt number and blocked directions
        available_patterns = [p for p in escape_patterns if p not in blocked_directions]
        if not available_patterns:
            # If all normal directions are blocked, try stronger movements
            available_patterns = [p + '2' for p in escape_patterns if p + '2' not in blocked_directions]
        
        if available_patterns:
            pattern = available_patterns[attempt % len(available_patterns)]
            vector = vectors[pattern]
            return vector[0], vector[1], f'escape_{pattern}'
        
        # Last resort: random movement with varying intensity
        intensity = STEP_SIZE * (1 + (attempt % 3))
        random_x = (-1)**(attempt % 2) * intensity
        random_y = (-1)**((attempt + 1) % 2) * intensity
        
        return random_x, random_y, 'escape_random'

    def execute_movement(self, move_x, move_y, movement_type):
        """
        Execute movement with simultaneous key presses for diagonal movement in MU Online
        """
        try:
            # Press both keys simultaneously for diagonal movement
            if move_x != 0 and move_y != 0:
                # Press both keys
                if move_x < 0:
                    self.interface.arrow_key_left(press=True)
                else:
                    self.interface.arrow_key_right(press=True)
                    
                if move_y < 0:
                    self.interface.arrow_key_down(press=True)
                else:
                    self.interface.arrow_key_up(press=True)
                    
                # Hold for a moment
                time.sleep(0.15)
                
                # Release both keys
                if move_x < 0:
                    self.interface.arrow_key_left(release=True)
                else:
                    self.interface.arrow_key_right(release=True)
                    
                if move_y < 0:
                    self.interface.arrow_key_down(release=True)
                else:
                    self.interface.arrow_key_up(release=True)
                    
            # Single direction movement
            else:
                if move_x != 0:
                    if move_x < 0:
                        self.interface.arrow_key_left(press=True)
                        time.sleep(0.1)
                        self.interface.arrow_key_left(release=True)
                    else:
                        self.interface.arrow_key_right(press=True)
                        time.sleep(0.1)
                        self.interface.arrow_key_right(release=True)
                        
                if move_y != 0:
                    if move_y < 0:
                        self.interface.arrow_key_down(press=True)
                        time.sleep(0.1)
                        self.interface.arrow_key_down(release=True)
                    else:
                        self.interface.arrow_key_up(press=True)
                        time.sleep(0.1)
                        self.interface.arrow_key_up(release=True)
            
            return True
            
        except Exception as e:
            self.logging.error(f"[MOVEMENT] Error executing movement: {e}")
            return False

    def check_and_click_play(self, x, y):
        """Check play button and update location state"""
        try:
            self.get_current_coords_from_game()
            current_state = self.config.get_game_state()
            current_x, currenty_y = self.interface.get_current_coords(current_state=current_state)
            mu_helper_active = self.interface.get_mu_helper_status(current_state)
            
            if abs(current_x - x) <= 10 and abs(currenty_y - y) <= 10 and not mu_helper_active:
                #self.interface.mouse_click(play_coords[0] + 5, play_coords[1] + 3)
                self.interface.start_mu_helper()
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
            'current_level': 0,
            'current_map': self.gameclass.start_location
        })
        self.interface.scroll(random_number=False, number=-10000, scroll_count=50)
        self.distribute_attributes()

    def run(self):
        """Ejecuta el bucle principal del bot"""
        while self.running:
            try:
                if not self.running:
                    return
                self.interface.focus_application()
                # Primera inicialización
                if self.first_time:
                    #self.interface.scroll(random_number=False, number=-10000, scroll_count=50)
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
    time.sleep(2)
    bot.run()