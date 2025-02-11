import time
import math
import json
import random
import logging
from typing import Tuple, Optional, List
from collections import defaultdict, deque  # Add this at the top of your file

class Movement:
    """
    An improved movement class for MU Online bot with better pathfinding and obstacle avoidance.
    """
    def __init__(self, interface, config, memory):
        self.interface = interface
        self.config = config
        self.memory = memory
        self.stuck_positions = defaultdict(int)  # Track direction failure counts
        self.effective_movements = deque(maxlen=10)  # Track recent movements
        self.logging = logging.getLogger(__name__)
        self.current_target = None  # Initialize the attribute in __init__
        self.movement_will_be_with = "mouse"
        
        # Movement constants
        self.STEP_SIZE = 1  # Each movement is 3 tiles
        self.CLOSE_ENOUGH_DISTANCE = 0  # Consider arrived when within 3 tiles
        self.MAX_STUCK_COUNT = 3
        self.MOVEMENT_TIMEOUT = 60  # 1 minute timeout
        
        # Stuck detection
        self.movement_history = deque(maxlen=20)
        self.stuck_threshold = 5  # Number of steps to consider the bot stuck
        self.stuck_timeout = 300  # Time (in seconds) before resetting to Lorencia
        
        # Movement directions with their corresponding x,y changes
        self.DIRECTIONS = {
            'N': (0, self.STEP_SIZE),
            'S': (0, -self.STEP_SIZE),
            'E': (self.STEP_SIZE, 0),
            'W': (-self.STEP_SIZE, 0),
            'NE': (self.STEP_SIZE, self.STEP_SIZE),
            'NW': (-self.STEP_SIZE, self.STEP_SIZE),
            'SE': (self.STEP_SIZE, -self.STEP_SIZE),
            'SW': (-self.STEP_SIZE, -self.STEP_SIZE)
        }

        self.map_file = "map_data.json"
        self.exploration_directions = list(self.DIRECTIONS.keys())  # All possible directions
        self.exploration_step_size = self.STEP_SIZE  # Step size for exploration
        self.max_exploration_steps = 100  # Maximum steps to explore (adjust as needed)
        # Track attempts to reach specific coordinates
        self.coordinate_attempts = defaultdict(int)
        self.MAX_COORDINATE_ATTEMPTS = 3  # Max attempts before marking as unreachable
        
        self.load_map_data()
        
    def get_unexplored_coordinates(self, current_pos) -> Optional[Tuple[int, int]]:
        """Identifica y devuelve coordenadas inexploradas que sean accesibles desde free_spaces."""
        current_x, current_y = current_pos
        self.logging.info(f"Current position: ({current_x}, {current_y})")

        search_radius = 100  # Increase the search radius
        unexplored_coords = []

        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                target_x = current_x + dx
                target_y = current_y + dy

                # Skip if the coordinate is already explored or is an obstacle
                if (target_x, target_y) in self.map_data['free_spaces'] or (target_x, target_y) in self.map_data['obstacles']:
                    continue

                # Check if the unexplored coordinate is accessible from free_spaces
                if self._is_explorable(target_x, target_y):
                    unexplored_coords.append((target_x, target_y))
                    self.logging.debug(f"Found accessible unexplored coordinate: ({target_x}, {target_y})")

        if unexplored_coords:
            # Prioritize the closest unexplored coordinate
            unexplored_coords.sort(key=lambda coord: self._calculate_distance(current_x, current_y, *coord))
            self.logging.info(f"Closest accessible unexplored coordinate: {unexplored_coords[0]}")
            return unexplored_coords[0]

        self.logging.info("No accessible unexplored coordinates found within the search radius.")
        return None

    def _is_reachable_via_free_spaces(self, start_x: int, start_y: int, target_x: int, target_y: int) -> bool:
        """
        Check if the target coordinate is reachable via free_spaces.
        Allows moving through a small number of non-free_spaces tiles.
        """
        self.logging.debug(f"Checking path from ({start_x}, {start_y}) to ({target_x}, {target_y})")
        
        max_non_free_tiles = 2  # Allow moving through up to 2 non-free_spaces tiles
        non_free_count = 0
        
        # Use Bresenham's line algorithm to check for a straight-line path through free_spaces
        for x, y in self._bresenham_line(start_x, start_y, target_x, target_y):
            self.logging.debug(f"Checking coordinate ({x}, {y})")
            if (x, y) not in self.map_data['free_spaces']:
                non_free_count += 1
                if non_free_count > max_non_free_tiles:
                    self.logging.debug(f"Path blocked at ({x}, {y}). Too many non-free_spaces tiles.")
                    return False  # Path is blocked
        return True  # Path is clear
    
    def _bresenham_line(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        """
        Generate coordinates along a straight line between two points using Bresenham's line algorithm.
        """
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return points
    
    def _is_explorable(self, target_x: int, target_y: int) -> bool:
        """
        Verifica si una coordenada inexplorada es accesible desde los free_spaces.
        Devuelve True si hay al menos un free_space adyacente a la coordenada inexplorada.
        """
        # Verifica si hay al menos un free_space adyacente a la coordenada inexplorada
        for dx, dy in self.DIRECTIONS.values():
            adjacent_x = target_x + dx
            adjacent_y = target_y + dy
            if (adjacent_x, adjacent_y) in self.map_data['free_spaces']:
                return True
        return False
    
    def explore_new_area(self):
        """
        Explore a new area by moving to the closest unexplored coordinate using free spaces.
        """
        current_pos = self.get_current_coords_from_game()
        self.logging.info(f"Current position: {current_pos}")

        # Obtener la coordenada inexplorada más cercana y accesible
        unexplored_coord = self.get_unexplored_coordinates(current_pos)
        if not unexplored_coord:
            self.logging.info("No accessible unexplored coordinates found.")
            return False

        target_x, target_y = unexplored_coord
        self.logging.info(f"Target unexplored coordinate: ({target_x}, {target_y})")

        # Mover a la coordenada inexplorada
        self.logging.info(f"Attempting to move to unexplored coordinate: ({target_x}, {target_y})")
        success = self.move_to(target_x, target_y)

        if success:
            self.logging.info(f"Successfully reached unexplored coordinate: ({target_x}, {target_y})")
            # Marcar la nueva área como explorada
            self.map_data['free_spaces'].add((target_x, target_y))
            self.save_map_data()
            return True
        else:
            self.logging.warning(f"Failed to reach unexplored coordinate: ({target_x}, {target_y})")
            # Marcar la coordenada como obstáculo si no se pudo llegar
            self.map_data['obstacles'].add((target_x, target_y))
            self.save_map_data()
            return False

    def move_to_unexplored(self, current_pos) -> bool:
        """
        Move the bot to the closest unexplored coordinate using free_spaces for navigation.
        Returns True if successful, False otherwise.
        """
        unexplored_coord = self.get_unexplored_coordinates(current_pos)
        if unexplored_coord:
            self.logging.info(f"Moving to unexplored coordinate: {unexplored_coord}")
            success = self.move_to(*unexplored_coord)
            if success:
                # Once we reach the unexplored coordinate, explore the surrounding area
                self.logging.info("Reached unexplored coordinate. Exploring surrounding area.")
                #self.explore_randomly()  # Call explore_randomly here
                return True
            else:
                self.logging.warning("Failed to move to unexplored coordinate.")
                return False
        else:
            self.logging.info("No unexplored coordinates found.")
            return False
        
    def _handle_stuck_recovery(self):
        """Handle stuck recovery by trying alternative directions."""
        self.logging.warning("Bot is stuck. Attempting to recover.")
        current_x, current_y = self.get_current_coords_from_game()
        
        # Try moving in all possible directions
        for direction in self.DIRECTIONS:
            dx, dy = self.DIRECTIONS[direction]
            target_x, target_y = current_x + dx, current_y + dy
            
            # Skip if the target position is an obstacle
            if (target_x, target_y) in self.map_data['obstacles']:
                continue
            
            self.logging.info(f"Attempting to move {direction} to ({target_x}, {target_y}).")
            self.move_to(target_x, target_y)
            time.sleep(0.5)  # Wait for movement to complete
            
            # Check if the bot successfully moved
            new_x, new_y = self.get_current_coords_from_game()
            if (new_x, new_y) != (current_x, current_y):
                self.logging.info("Successfully recovered from stuck state.")
                return True
        
        self.logging.warning("Failed to recover from stuck state.")
        return False
        
    def explore_randomly(self):
        """Explore the map randomly, avoiding repetitive movements."""
        self.logging.info("Starting random exploration...")
        
        boundary_failures = defaultdict(int)  # Track failures in each direction
        original_directions = self.exploration_directions.copy()  # Save original directions
        stuck_count = 0  # Track consecutive failures
        start_time = time.time()  # Track the start time of exploration
        
        while time.time() - start_time < self.stuck_timeout:  # Use a while loop with a timeout
            current_pos = self.get_current_coords_from_game()
            self.logging.debug(f"Current position: {current_pos}")
            
            # Check if the bot is stuck (not moving for several steps)
            if len(self.movement_history) == self.movement_history.maxlen and len(set(self.movement_history)) <= 2:
                self.logging.warning("Bot is stuck in the same position. Attempting to recover.")
                self._handle_stuck_recovery()
                return  # Exit the function and restart exploration
            
            # Choose a random direction to move
            direction = random.choice(self.exploration_directions)
            dx, dy = self.DIRECTIONS[direction]
            target_pos = (current_pos[0] + dx, current_pos[1] + dy)
            
            self.logging.info(f"[TARGET] {target_pos}")
            # Attempt to move to the target position
            self.move_to(*target_pos)
            time.sleep(0.5)  # Wait for the bot to move
            
            # Check if the bot successfully moved to the target position
            new_pos = self.get_current_coords_from_game()
            if new_pos == target_pos:
                # Successfully moved: mark as free space
                self.map_data['free_spaces'].add(target_pos)
                self.map_data['obstacles'].discard(target_pos)  # Ensure it's not marked as an obstacle
                stuck_count = 0  # Reset stuck count
                self.save_map_data()
            else:
                # Failed to move: mark as obstacle
                if target_pos not in self.map_data['free_spaces']:
                    self.map_data['obstacles'].add(target_pos)
                # Also mark the current position as a potential obstacle if stuck
                if new_pos == current_pos and current_pos not in self.map_data['free_spaces']:
                    self.map_data['obstacles'].add(current_pos)
                boundary_failures[direction] += 1
                stuck_count += 1
            
            # If stuck too many times, take a break or change strategy
            if stuck_count >= self.MAX_STUCK_COUNT:
                self.logging.warning("Bot is stuck. Taking a break or changing strategy.")
                self._handle_stuck_recovery()
                return  # Exit the function and restart exploration
        
        self.logging.info("Random exploration completed.")
        self.save_map_data()

    def save_map_data(self):
        try:
            data = {
                'obstacles': list(self.map_data['obstacles']),
                'free_spaces': list(self.map_data['free_spaces']),
                'map_name': self.map_data['map_name']
            }
            with open(self.map_file, 'w') as f:
                json.dump(data, f, indent=4)
            self.logging.info(f"Map data saved with {len(data['obstacles'])} obstacles")
        except Exception as e:
            self.logging.error(f"Failed to save map data: {e}")

    def load_map_data(self):
        """Load map data from a JSON file. If the file is missing or invalid, initialize with default data."""
        default_data = {
            'obstacles': set(),  # Temporary obstacles
            'permanent_obstacles': set(),  # Permanent obstacles (unreachable coordinates)
            'free_spaces': set(),  # Free spaces
            'map_name': None
        }
        
        try:
            # Try to load the map data from the file
            with open(self.map_file, 'r') as f:
                data = json.load(f)
                self.map_data = {
                    'obstacles': set(tuple(obs) for obs in data.get('obstacles', [])),
                    'permanent_obstacles': set(tuple(obs) for obs in data.get('permanent_obstacles', [])),
                    'free_spaces': set(tuple(free) for free in data.get('free_spaces', [])),
                    'map_name': data.get('map_name', None)
                }
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is invalid, initialize with default data
            self.logging.warning(f"{self.map_file} not found or invalid. Initializing with default data.")
            self.map_data = default_data
            self.save_map_data()  # Save the default data to the file

    def _get_best_direction(self, current_x: int, current_y: int, target_x: int, target_y: int) -> str:
        """
        Determine the best direction to move based on current position and target.
        Avoids moving toward known obstacles.
        """
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Generate a list of possible directions, sorted by priority
        possible_directions = []
        
        # Diagonal movements (higher priority if both X and Y are significantly off)
        if abs(dx) >= self.STEP_SIZE and abs(dy) >= self.STEP_SIZE:
            if dx > 0 and dy > 0 and (current_x + self.STEP_SIZE, current_y + self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('NE')
            if dx < 0 and dy > 0 and (current_x - self.STEP_SIZE, current_y + self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('NW')
            if dx > 0 and dy < 0 and (current_x + self.STEP_SIZE, current_y - self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('SE')
            if dx < 0 and dy < 0 and (current_x - self.STEP_SIZE, current_y - self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('SW')
        
        # Cardinal directions (fallback if diagonals are blocked)
        if abs(dx) > abs(dy):
            if dx > 0 and (current_x + self.STEP_SIZE, current_y) not in self.map_data['obstacles']:
                possible_directions.append('E')
            elif dx < 0 and (current_x - self.STEP_SIZE, current_y) not in self.map_data['obstacles']:
                possible_directions.append('W')
        else:
            if dy > 0 and (current_x, current_y + self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('N')
            elif dy < 0 and (current_x, current_y - self.STEP_SIZE) not in self.map_data['obstacles']:
                possible_directions.append('S')
        
        # If no valid directions are found, try any direction that isn't blocked
        if not possible_directions:
            for direction, (dx, dy) in self.DIRECTIONS.items():
                target_pos = (current_x + dx, current_y + dy)
                if target_pos not in self.map_data['obstacles']:
                    possible_directions.append(direction)
        
        # If still no valid directions, return None (bot is completely blocked)
        if not possible_directions:
            self.logging.warning("No valid directions found. Bot is completely blocked.")
            return None
        
        # Choose the first valid direction (prioritizes diagonals, then cardinals)
        return possible_directions[0]

    def _verify_movement(self, start_pos) -> bool:
        """Verify if movement actually changed position."""
        self.logging.info(f"Starting position: {start_pos}")
        
        # Retry movement up to 3 times before marking as failed
        for _ in range(3):
            time.sleep(0.5)  # Wait for the bot to move
            end_pos = self.get_current_coords_from_game()
            self.logging.info(f"Ending position: {end_pos}")
            
            if start_pos != end_pos:
                self.map_data['free_spaces'].add(end_pos)
                self.map_data['obstacles'].discard(end_pos)
                self.logging.debug(f"Movement successful to {end_pos}")
                return True
        
        # If movement failed after retries, mark as obstacle
        target_pos = self.current_target
        if target_pos and target_pos not in self.map_data['free_spaces']:
            self.map_data['obstacles'].add(target_pos)
            self.logging.debug(f"Movement failed at {start_pos}. Marking target {target_pos} as obstacle.")
        else:
            self.logging.debug(f"Movement failed at {start_pos}. But is already a free space at {target_pos}.")
        
        self.save_map_data()
        return False
    
    def _find_alternative_path(self, target_x: int, target_y: int) -> bool:
        """Calculate path using A* algorithm with obstacle avoidance."""
        current_x, current_y = self.get_current_coords_from_game()
        
        # Try all possible directions in a random order
        directions = list(self.DIRECTIONS.keys())
        random.shuffle(directions)
        
        for direction in directions:
            dx, dy = self.DIRECTIONS[direction]
            target_pos = (current_x + dx, current_y + dy)
            
            # Skip if the target position is an obstacle
            if target_pos in self.map_data['obstacles']:
                continue
            
            # Attempt to move in this direction
            start_pos = self.get_current_coords_from_game()
            self._execute_movement(direction)
            
            # Verify if movement was successful
            if self._verify_movement(start_pos=start_pos):
                return self.move_to(target_x, target_y)
        
        self.logging.error("No viable path found.")
        return False


    def _find_path_bfs(self, start_x: int, start_y: int, target_x: int, target_y: int) -> Optional[List[Tuple[int, int]]]:
        """
        Use BFS to find a path from (start_x, start_y) to (target_x, target_y).
        Returns a list of coordinates representing the path, or None if no path is found.
        """
        queue = deque()
        queue.append((start_x, start_y, []))  # (x, y, path)
        visited = set()
        start_time = time.time()  # Track the start time

        while queue:
            # Check if the timeout has been reached
            if time.time() - start_time > 5:  # 5-second timeout
                self.logging.warning("Pathfinding timed out. No valid path found.")
                return None

            x, y, path = queue.popleft()
            if (x, y) == (target_x, target_y):
                return path + [(x, y)]  # Return the full path

            if (x, y) in visited:
                continue
            visited.add((x, y))

            # Explore all possible directions, sorted by proximity to target
            directions = sorted(self.DIRECTIONS.items(), key=lambda d: self._calculate_distance(x + d[1][0], y + d[1][1], target_x, target_y))
            for direction, (dx, dy) in directions:
                new_x = x + dx
                new_y = y + dy

                # Skip if the new coordinate is an obstacle or out of bounds
                if (new_x, new_y) in self.map_data['obstacles'] or (new_x, new_y) in self.map_data['permanent_obstacles']:
                    continue

                # Add the new coordinate to the queue
                queue.append((new_x, new_y, path + [(x, y)]))

        return None  # No path found

    def _execute_movement_towards(self, target_x: int, target_y: int):
        """Move the bot towards the target coordinate."""
        current_x, current_y = self.get_current_coords_from_game()
        dx = target_x - current_x
        dy = target_y - current_y

        self.logging.debug(f"Moving towards ({target_x}, {target_y}). Current position: ({current_x}, {current_y})")

        # Determine the best direction to move
        if dx > 0:
            self.interface.mouse_right()
        elif dx < 0:
            self.interface.mouse_left()
        elif dy > 0:
            self.interface.mouse_top()
        elif dy < 0:
            self.interface.mouse_down()

        time.sleep(1.0)  # Increase delay to allow the bot to move
    
    def move_to(self, target_x: int, target_y: int) -> bool:
        """Move towards the target coordinates using pathfinding."""
        self.logging.debug("==========================")
        current_x, current_y = self.get_current_coords_from_game()
        self.logging.debug(f"Current position: ({current_x}, {current_y}), Target: ({target_x}, {target_y})")
        
        if not current_x or not current_y:
            self.logging.error("Failed to retrieve current position.")
            return False

        step_y = None
        step_x = None
        # Track attempts to reach the target
        attempt_count = 0
        while attempt_count < 3:  # Allow up to 3 attempts
            self.logging.debug(f"============ Attempt {attempt_count} ============")
            # Find a path to the target using BFS
            path = self._find_path_bfs(current_x, current_y, target_x, target_y)
            if not path:
                self.logging.warning(f"No valid path found to ({target_x}, {target_y}). Marking as unreachable.")
                self.map_data['permanent_obstacles'].add((target_x, target_y))
                self.save_map_data()
                return False

            # Follow the path step by step
            for step_x, step_y in path:
                self.logging.info(f"Moving to ({step_x}, {step_y})")
                self._execute_movement_towards(step_x, step_y)
                time.sleep(0.5)  # Increase delay to allow movement to complete

                # Verify if the bot successfully moved to the target position
                new_x, new_y = self.get_current_coords_from_game()
                self.logging.debug(f"New position after movement: ({new_x}, {new_y})")
                if (new_x, new_y) != (step_x, step_y):
                    self.logging.warning(f"Failed to move to ({step_x}, {step_y}). Attempt {attempt_count + 1}.")
                    attempt_count += 1
                    self.interface.use_spell()
                    break  # Retry the entire path
                else:
                    self.logging.warning(f"Successfull reach target after {attempt_count} attempts. Marking as FREE SPACE.")
                    self.map_data['free_spaces'].add((step_x, step_y))
                    self.save_map_data()
            else:
                self.map_data['free_spaces'].add((target_x, target_y))
                self.save_map_data()
                self.logging.info(f"Successfully reached target location: ({target_x}, {target_y})")
                return True

        self.logging.warning(f"Failed to reach target after {attempt_count} attempts. Marking as obstacle.")
        self.map_data['obstacles'].add((step_x, step_y))
        # Force immediate save after marking as obstacle
        try:
            self.save_map_data()
            self.logging.info(f"Successfully saved obstacle {(step_x, step_y)} to map data")
        except Exception as e:
            self.logging.error(f"Failed to save map data: {e}")
        return False
    
    def explore_systematically(self):
        """Explore the map in a systematic pattern (e.g., spiral)."""
        self.logging.info("Starting systematic exploration...")
        
        current_x, current_y = self.get_current_coords_from_game()
        step_size = self.STEP_SIZE
        direction_index = 0
        directions = ['E', 'S', 'W', 'N']  # Clockwise spiral
        steps_in_direction = 1
        steps_taken = 0
        
        while True:
            # Move in the current direction
            direction = directions[direction_index]
            dx, dy = self.DIRECTIONS[direction]
            target_x = current_x + dx * step_size
            target_y = current_y + dy * step_size
            
            self.logging.info(f"Moving {direction} to ({target_x}, {target_y})")
            success = self.move_to(target_x, target_y)
            
            if success:
                current_x, current_y = target_x, target_y
                steps_taken += 1
                
                # Change direction if steps_in_direction are completed
                if steps_taken >= steps_in_direction:
                    direction_index = (direction_index + 1) % 4
                    if direction_index % 2 == 0:  # Increase steps after every two turns
                        steps_in_direction += 1
                    steps_taken = 0
            else:
                self.logging.warning(f"Failed to move {direction}. Trying next direction.")
                direction_index = (direction_index + 1) % 4
                steps_taken = 0

    def explore_map(self, map_name: str):
        """Explore the map to create a map of obstacles and free spaces."""
        self.map_data['map_name'] = map_name
        self.save_map_data()  # Save the map name immediately
        self.load_map_data()  # Load existing map data if available
        
        # Move to the map if not already there
        self.move_to_location(map_name, avoid_checks=True, do_not_open_stats=True)
        
        # Initialize free_spaces with the current position
        current_pos = self.get_current_coords_from_game()
        self.map_data['free_spaces'].add(current_pos)
        self.save_map_data()
        
        # Start by moving to unexplored coordinates
        self.move_to_unexplored(current_pos)
        self.logging.info("Moved to an unexplored coordinate. Continuing exploration.")
        time.sleep(0.5)  # Wait for the bot to settle
        
        # If no unexplored coordinates are found, fall back to random exploration
        self.logging.info("No more unexplored coordinates found. Starting random exploration.")
        self.explore_randomly()
        
        self.logging.info(f"Finished exploring {map_name}. Map data saved to {self.map_file}")

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(x2 - x1) + abs(y2 - y1)

    def _execute_movement(self, direction: str):
        """Execute movement in the given direction and update movement history."""
        dx, dy = self.DIRECTIONS[direction]
        
        self.logging.info(f"Moving to {direction}...")
        self.logging.debug(f"Movement history before update: {list(self.movement_history)}")
        
        if self.movement_will_be_with == "mouse":
            self.logging.debug(f"Using mouse for movement: {direction}")
            # Diagonal movements
            if direction == 'NE':
                self.interface.mouse_top_right()
            elif direction == 'NW':
                self.interface.mouse_top_left()
            elif direction == 'SE':
                self.interface.mouse_down_right()
            elif direction == 'SW':
                self.interface.mouse_down_left()
            # Cardinal directions
            elif dx > 0:
                self.interface.mouse_right()
            elif dx < 0:
                self.interface.mouse_left()
            elif dy > 0:
                self.interface.mouse_top()
            elif dy < 0:
                self.interface.mouse_down()
        else:
            self.logging.debug(f"Using keyboard for movement: {direction}")
            # Keyboard movements (unchanged)
            if dx > 0:
                self.interface.arrow_key_right(press=True)
            elif dx < 0:
                self.interface.arrow_key_left(press=True)
            if dy > 0:
                self.interface.arrow_key_up(press=True)
            elif dy < 0:
                self.interface.arrow_key_down(press=True)
            
            # Small delay to simulate natural movement
            time.sleep(0.5)
            
            # Release keys
            self.interface.release_all_keys()
        
        # Increase delay after movement to allow the game to process it
        time.sleep(0.5)  # Increased from 1.0 to 2.0 seconds

    def _handle_stuck_state(self, current_x: int, current_y: int) -> bool:
        """
        Handle stuck state by trying alternative movements.
        Returns True if unstuck, False if failed.
        """
        self.logging.warning(f"Stuck at position [{current_x}, {current_y}]. Attempting to recover.")
        
        # Try moving in a random direction
        direction = random.choice(self.exploration_directions)
        dx, dy = self.DIRECTIONS[direction]
        target_pos = (current_x + dx, current_y + dy)
        
        self.logging.info(f"Attempting to move in direction {direction} to {target_pos}.")
        self.move_to(*target_pos)
        time.sleep(1.0)  # Wait for the bot to move
        
        # Check if the bot successfully moved
        new_pos = self.get_current_coords_from_game()
        if new_pos != (current_x, current_y):
            self.logging.info("Successfully recovered from stuck state.")
            return True
        else:
            self.logging.warning("Failed to recover from stuck state.")
            return False

    def move_to_location(self, map_name: str, avoid_checks=False, stuck=False, do_not_open_stats=False):
        if not avoid_checks:
            current_state = self.config.get_game_state()
            if map_name != current_state['current_map'] or stuck is True:
                self.interface.set_mu_helper_status(False)
                self.interface.command_move_to_map(map_name=map_name)
                self.config.update_game_state({'current_map': map_name})
            else:
                self.logging.info(f"Character already in {map_name}. No need to move again")
        else:
            self.logging.info(f"Character is moving to {map_name} without checking the current map.")
            self.interface.set_mu_helper_status(False)
            self.interface.command_move_to_map(map_name=map_name)
        
        if not do_not_open_stats:
            self.interface.open_stats_window()
        
    def get_current_coords_from_game(self):
        try:
            x, y = self.memory.get_coordinates()
            self.interface.set_current_coords([x, y])
            self.logging.info(f"[POSITION] [{x}, {y}]")
            return x, y
        except Exception as e:
            self.logging.error(f"Failed to read coordinates from game memory: {e}")
            return (0, 0)  # Return a default position or handle the error appropriately