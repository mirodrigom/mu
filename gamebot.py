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
        self.current_path = []  # Store coordinates for current path
        self.good_paths = {}  # Dictionary to store successful paths by destination
        

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
        return (f"[POS] Current:[{current_x},{current_y}] → Target:[{target_x},{target_y}] | " f"Δ[{dx},{dy}] | Dist:{dist}{blocked_str}{status_str}")

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
        raw_data = self.interface.get_position_data(with_comma=True)
        self.logging.debug(f"[POSITION] Raw position data: '{raw_data}'")
        
        # Try comma-separated format first
        if ',' in raw_data:
            try:
                x, y = raw_data.split(',')
                x, y = int(x.strip()), int(y.strip())
                self.logging.debug(f"[POSITION] Parsed coordinates: [{x}, {y}]")
                return x, y
            except ValueError as e:
                self.logging.debug(f"[POSITION] Failed to parse comma format: {e}")

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
                    self.logging.warning(f"Attempt {attempt + 1} failed: {e}")
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
    
    def get_current_coords_from_game(self, retries=3, delay=1):
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
                self.logging.info(f"[POSITION] Successfully got coordinates: [{x}, {y}] (attempt {attempt + 1})")
                return True
            except Exception as e:
                self.logging.warning(f"[POSITION] ⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return False
    
    def detect_wall(self, positions_history, current_pos):
        """
        Enhanced wall detection with better stuck detection
        """
        if len(positions_history) < 3:
            return False, set()
            
        # Check for complete immobility
        recent_positions = positions_history[-5:]
        if all(pos == recent_positions[0] for pos in recent_positions):
            self.logging.warning(f"[WALL] 🚫 Complete stuck detected at {current_pos}")
            return True, {'N', 'S', 'E', 'W'}  # All directions blocked
            
        x_values = [pos[0] for pos in positions_history[-5:]]
        y_values = [pos[1] for pos in positions_history[-5:]]
        
        x_movement = max(x_values) - min(x_values)
        y_movement = max(y_values) - min(y_values)
        
        blocked_directions = set()
        
        # More aggressive wall detection
        if x_movement <= 2:
            if abs(current_pos[0] - positions_history[-5][0]) < 2:
                blocked_directions.add('W')
                blocked_directions.add('E')
                self.logging.warning(f"[WALL] ⬅️➡️ X-axis movement blocked at x={current_pos[0]}")
                
        if y_movement <= 2:
            if abs(current_pos[1] - positions_history[-5][1]) < 2:
                blocked_directions.add('N')
                blocked_directions.add('S')
                self.logging.warning(f"[WALL] ⬆️⬇️ Y-axis movement blocked at y={current_pos[1]}")
                
        return len(blocked_directions) > 0, blocked_directions

    def calculate_escape_vector(self, current_pos, blocked_directions, attempt=0, target_pos=None):
        """
        Calculate escape vector when stuck, with smarter pattern selection
        """
        # If we have target position, calculate desired direction
        if target_pos:
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            target_direction = ''
            
            if dy > 0:  # Need to go up
                if dx < 0:  # Need to go left
                    primary_patterns = ['NW', 'W', 'N', 'SW', 'NE']
                else:  # Need to go right
                    primary_patterns = ['NE', 'E', 'N', 'SE', 'NW']
            else:  # Need to go down
                if dx < 0:  # Need to go left
                    primary_patterns = ['SW', 'W', 'S', 'NW', 'SE']
                else:  # Need to go right
                    primary_patterns = ['SE', 'E', 'S', 'NE', 'SW']
        else:
            # If no target, use default pattern order
            primary_patterns = ['NE', 'NW', 'SE', 'SW', 'N', 'S', 'E', 'W']

        # Get pattern based on attempt number
        pattern_index = attempt % len(primary_patterns)
        chosen_pattern = primary_patterns[pattern_index]
        
        # Define movement vectors for each pattern
        vectors = {
            'N': (0, 2),     # Strong up
            'S': (0, -2),    # Strong down
            'E': (2, 0),     # Strong right
            'W': (-2, 0),    # Strong left
            'NE': (1, 1),    # Northeast
            'NW': (-1, 1),   # Northwest
            'SE': (1, -1),   # Southeast
            'SW': (-1, -1),  # Southwest
        }
        
        # Try patterns in order until we find one that's not blocked
        for pattern in primary_patterns[pattern_index:] + primary_patterns[:pattern_index]:
            if pattern not in blocked_directions:
                self.logging.info(f"[ESCAPE] Trying escape pattern: {pattern} (attempt {attempt})")
                return vectors[pattern][0], vectors[pattern][1], f'escape_{pattern}'
        
        # If all normal patterns are blocked, try a more aggressive random movement
        random_x = (-1)**(attempt % 2) * (2 if attempt % 3 == 0 else 1)
        random_y = (-1)**((attempt + 1) % 2) * (2 if attempt % 3 != 0 else 1)
        
        self.logging.warning(f"[ESCAPE] All patterns blocked! Using random movement (attempt {attempt})")
        return random_x, random_y, 'escape_random'

    def move_to_coordinates(self, target_x: int, target_y: int):
        """Enhanced movement method with better stuck handling"""
        self.current_path = []
        positions_history = []
        stuck_count = 0
        escape_attempt = 0
        last_pos = None
        last_movement_type = None
        
        self.logging.info(f"[MOVEMENT] Starting movement to target [{target_x}, {target_y}]")
        
        if not self.get_current_coords_from_game():
            self.logging.error("[MOVEMENT] Failed to get initial position")
            return
            
        current_state = self.config.get_game_state()
        current_map = self.interface.get_current_map(current_state)
        blocked_directions = set()
        
        while True:
            # Get current position
            self.get_current_coords_from_game()
            current_x, current_y = self._fetch_position()
            positions_history.append((current_x, current_y))
            
            # Log current status with target distance
            dx = target_x - current_x
            dy = target_y - current_y
            dist = abs(dx) + abs(dy)
            self.logging.info(f"[STATUS] Pos:[{current_x},{current_y}] Target:[{target_x},{target_y}] Dist:{dist} | Last movement: {last_movement_type}")
            
            # Check if we've reached destination
            if abs(dx) <= 10 and abs(dy) <= 10:
                self.logging.info(f"[MOVEMENT] ✅ Reached destination!")
                self.check_and_click_play(target_x, target_y)
                break
                
            # Detect stuck condition
            if last_pos == (current_x, current_y):
                stuck_count += 1
                if stuck_count >= 3:  # Stuck for 3 consecutive checks
                    self.logging.warning(f"[STUCK] 🚫 Stuck for {stuck_count} moves at [{current_x},{current_y}]")
                    
                    # Try escape movement
                    move_x, move_y, move_type = self.calculate_escape_vector(
                        (current_x, current_y),
                        blocked_directions,
                        escape_attempt,
                        (target_x, target_y)  # Pass target position for smarter escapes
                    )
                    escape_attempt += 1
                    
                    # If we've tried escaping multiple times without success, reset position
                    if escape_attempt >= 8:  # Increased from 5 to 8 attempts
                        self.logging.warning(f"[RESET] 🔄 Failed to escape after {escape_attempt} attempts, resetting position")
                        self.move_to_location(map_name=current_map, stuck=True)
                        stuck_count = 0
                        escape_attempt = 0
                        positions_history.clear()
                        blocked_directions.clear()
                        continue
            else:
                stuck_count = 0
                if escape_attempt > 0:  # If we moved, reset escape attempt counter
                    escape_attempt = 0
                    blocked_directions.clear()  # Clear blocked directions if we successfully moved
                    
            last_pos = (current_x, current_y)
            
            # Keep history manageable
            if len(positions_history) > 10:
                positions_history.pop(0)
                
            # Check for walls
            is_wall, new_blocked = self.detect_wall(positions_history, (current_x, current_y))
            if is_wall:
                blocked_directions.update(new_blocked)
                
            # Calculate movement
            if stuck_count >= 3:
                move_x, move_y, move_type = self.calculate_escape_vector(
                    (current_x, current_y),
                    blocked_directions,
                    escape_attempt,
                    (target_x, target_y)  # Pass target position for smarter escapes
                )
            else:
                move_x, move_y, move_type = self.calculate_movement_vector(
                    current_x, current_y, target_x, target_y, blocked_directions
                )
                
            # Execute movement
            self.execute_movement(move_x, move_y, move_type)
            last_movement_type = move_type
            time.sleep(0.3)  # Slightly longer delay between movements

    def calculate_movement_vector(self, current_x, current_y, target_x, target_y, blocked_directions):
        """
        Calculate movement vector considering blocked directions
        Returns: tuple (dx, dy, movement_type)
        """
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Base movement vectors
        vectors = {
            'N': (0, 1),
            'S': (0, -1),
            'E': (1, 0),
            'W': (-1, 0),
            'NE': (1, 1),
            'NW': (-1, 1),
            'SE': (1, -1),
            'SW': (-1, -1)
        }
        
        # Determine primary direction needed
        primary_dir = ''
        if abs(dx) > abs(dy):
            primary_dir = 'E' if dx > 0 else 'W'
        else:
            primary_dir = 'N' if dy > 0 else 'S'
            
        # If primary direction is blocked, try alternatives
        if primary_dir in blocked_directions:
            # Try diagonal movements
            if 'N' not in blocked_directions and dy > 0:
                if 'E' not in blocked_directions and dx > 0:
                    return vectors['NE'][0], vectors['NE'][1], 'diagonal'
                elif 'W' not in blocked_directions and dx < 0:
                    return vectors['NW'][0], vectors['NW'][1], 'diagonal'
            elif 'S' not in blocked_directions and dy < 0:
                if 'E' not in blocked_directions and dx > 0:
                    return vectors['SE'][0], vectors['SE'][1], 'diagonal'
                elif 'W' not in blocked_directions and dx < 0:
                    return vectors['SW'][0], vectors['SW'][1], 'diagonal'
                    
            # If diagonals don't work, try perpendicular movement
            if primary_dir in ['E', 'W']:
                if 'N' not in blocked_directions:
                    return vectors['N'][0], vectors['N'][1], 'alternate'
                elif 'S' not in blocked_directions:
                    return vectors['S'][0], vectors['S'][1], 'alternate'
            else:
                if 'E' not in blocked_directions:
                    return vectors['E'][0], vectors['E'][1], 'alternate'
                elif 'W' not in blocked_directions:
                    return vectors['W'][0], vectors['W'][1], 'alternate'
        
        # Default to primary direction if not blocked
        return vectors[primary_dir][0], vectors[primary_dir][1], 'primary'

    def execute_movement(self, move_x, move_y, movement_type):
        """
        Execute the movement with proper delays and key release checks.
        Implements more careful key press handling to avoid input conflicts.
        """
        # Base delays
        key_press_delay = 0.1    # Time to hold a key
        between_keys_delay = 0.2  # Time between different key presses
        post_move_delay = 0.3    # Time after complete movement
        
        try:
            # Execute X movement first if any
            if move_x != 0:
                if move_x < 0:
                    self.logging.debug("[MOVEMENT] Pressing LEFT")
                    self.interface.arrow_key_left()
                    time.sleep(key_press_delay)
                elif move_x > 0:
                    self.logging.debug("[MOVEMENT] Pressing RIGHT")
                    self.interface.arrow_key_right()
                    time.sleep(key_press_delay)
                    
                # Wait between different directions
                time.sleep(between_keys_delay)
                
            # Then execute Y movement if any
            if move_y != 0:
                if move_y < 0:
                    self.logging.debug("[MOVEMENT] Pressing DOWN")
                    self.interface.arrow_key_down()
                    time.sleep(key_press_delay)
                elif move_y > 0:
                    self.logging.debug("[MOVEMENT] Pressing UP")
                    self.interface.arrow_key_up()
                    time.sleep(key_press_delay)
            
            # Log the complete movement
            self.logging.debug(
                f"[MOVEMENT] Executed {movement_type} movement: "
                f"[{'LEFT' if move_x < 0 else 'RIGHT' if move_x > 0 else ''} "
                f"{'UP' if move_y > 0 else 'DOWN' if move_y < 0 else ''}]"
            )
            
            # Wait after complete movement
            time.sleep(post_move_delay)
            
        except Exception as e:
            self.logging.error(f"[MOVEMENT] Error executing movement: {e}")
            time.sleep(post_move_delay)  # Still wait even if there's an error

    def move_to_coordinates(self, target_x: int, target_y: int):
        """Enhanced movement method with better stuck handling"""
        self.current_path = []
        positions_history = []
        stuck_count = 0
        escape_attempt = 0
        last_pos = None
        
        self.logging.info(f"[MOVEMENT] Starting movement to target [{target_x}, {target_y}]")
        
        if not self.get_current_coords_from_game():
            self.logging.error("[MOVEMENT] Failed to get initial position")
            return
            
        current_state = self.config.get_game_state()
        current_map = self.interface.get_current_map(current_state)
        blocked_directions = set()
        
        while True:
            # Get current position
            self.get_current_coords_from_game()
            current_x, current_y = self._fetch_position()
            positions_history.append((current_x, current_y))
            
            # Log current status with target distance
            dx = target_x - current_x
            dy = target_y - current_y
            dist = abs(dx) + abs(dy)
            self.logging.info(f"[STATUS] Pos:[{current_x},{current_y}] Target:[{target_x},{target_y}] Dist:{dist}")
            
            # Check if we've reached destination
            if abs(dx) <= 10 and abs(dy) <= 10:
                self.logging.info(f"[MOVEMENT] ✅ Reached destination!")
                self.check_and_click_play(target_x, target_y)
                break
                
            # Detect stuck condition
            if last_pos == (current_x, current_y):
                stuck_count += 1
                if stuck_count >= 3:  # Stuck for 3 consecutive checks
                    self.logging.warning(f"[STUCK] 🚫 Stuck for {stuck_count} moves at [{current_x},{current_y}]")
                    
                    # Try escape movement
                    move_x, move_y, move_type = self.calculate_escape_vector(
                        (current_x, current_y),
                        blocked_directions,
                        escape_attempt
                    )
                    escape_attempt += 1
                    
                    # If we've tried escaping multiple times without success, reset position
                    if escape_attempt >= 5:
                        self.logging.warning(f"[RESET] 🔄 Failed to escape after {escape_attempt} attempts, resetting position")
                        self.move_to_location(map_name=current_map, stuck=True)
                        stuck_count = 0
                        escape_attempt = 0
                        positions_history.clear()
                        blocked_directions.clear()
                        continue
            else:
                stuck_count = 0
                if escape_attempt > 0:  # If we moved, reset escape attempt counter
                    escape_attempt = 0
                    
            last_pos = (current_x, current_y)
            
            # Keep history manageable
            if len(positions_history) > 10:
                positions_history.pop(0)
                
            # Check for walls
            is_wall, new_blocked = self.detect_wall(positions_history, (current_x, current_y))
            if is_wall:
                blocked_directions.update(new_blocked)
                
            # Calculate movement
            if stuck_count >= 3:
                move_x, move_y, move_type = self.calculate_escape_vector(
                    (current_x, current_y),
                    blocked_directions,
                    escape_attempt
                )
            else:
                move_x, move_y, move_type = self.calculate_movement_vector(
                    current_x, current_y, target_x, target_y, blocked_directions
                )
                
            # Execute movement
            self.execute_movement(move_x, move_y, move_type)
            time.sleep(0.2)  # Small delay between movements

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