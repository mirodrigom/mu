import time
import math
import json
import random
import logging
from typing import Tuple, Optional
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
        self.load_map_data()
        
    def get_unexplored_coordinates(self) -> Optional[Tuple[int, int]]:
        """
        Identify and return unexplored coordinates from the map.
        Returns None if all coordinates are explored.
        """
        current_x, current_y = self.get_current_coords_from_game()
        
        # Define a search radius around the current position
        search_radius = 10  # Adjust as needed
        unexplored_coords = []
        
        # Iterate over a grid around the current position
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                target_x = current_x + dx
                target_y = current_y + dy
                
                # Check if the coordinate is unexplored
                if (target_x, target_y) not in self.map_data['free_spaces'] and \
                (target_x, target_y) not in self.map_data['obstacles']:
                    unexplored_coords.append((target_x, target_y))
        
        if unexplored_coords:
            # Prioritize the closest unexplored coordinate
            unexplored_coords.sort(key=lambda coord: self._calculate_distance(current_x, current_y, *coord))
            return unexplored_coords[0]
        
        return None
    
    def move_to_unexplored(self) -> bool:
        """
        Move the bot to the closest unexplored coordinate.
        Returns True if successful, False otherwise.
        """
        unexplored_coord = self.get_unexplored_coordinates()
        if unexplored_coord:
            self.logging.info(f"Moving to unexplored coordinate: {unexplored_coord}")
            success = self.move_to(*unexplored_coord)
            if success:
                # Once we reach the unexplored coordinate, explore the surrounding area
                self.logging.info("Reached unexplored coordinate. Exploring surrounding area.")
                self.explore_randomly()  # Call explore_randomly here
                return True
            else:
                self.logging.warning("Failed to move to unexplored coordinate.")
                return False
        else:
            self.logging.info("No unexplored coordinates found.")
            return False

    def explore_randomly(self):
        """Explore the map randomly, prioritizing unexplored coordinates."""
        self.logging.info("Starting random exploration...")
        
        boundary_failures = defaultdict(int)  # Track failures in each direction
        original_directions = self.exploration_directions.copy()  # Save original directions
        stuck_count = 0  # Track consecutive failures
        last_positions = deque(maxlen=5)  # Track the last few positions to detect being stuck
        
        for step in range(self.max_exploration_steps):
            current_pos = self.get_current_coords_from_game()
            self.logging.debug(f"Step {step + 1}: Current position: {current_pos}")
            
            # Record current position as a free space
            self.map_data['free_spaces'].add(current_pos)
            self.map_data['obstacles'].discard(current_pos)  # Ensure it's not marked as an obstacle
            
            # Check if the bot is stuck (not moving for several steps)
            last_positions.append(current_pos)
            if len(last_positions) == last_positions.maxlen and len(set(last_positions)) <= 2:
                self.logging.warning("Bot is stuck in the same position. Attempting to recover.")
                self._handle_stuck_state(current_pos[0], current_pos[1])
                last_positions.clear()  # Reset the position history
                continue  # Skip the rest of the loop and try again
            
            # Check for unexplored coordinates
            unexplored_coord = self.get_unexplored_coordinates()
            if unexplored_coord:
                self.logging.info(f"Found unexplored coordinate: {unexplored_coord}. Moving there.")
                success = self.move_to(*unexplored_coord)
                if success:
                    # Once we reach the unexplored coordinate, continue exploring
                    time.sleep(1)  # Wait for the bot to move
                    continue  # Skip the rest of the loop and continue exploration
                else:
                    self.logging.warning("Failed to move to unexplored coordinate. Continuing random exploration.")
            
            # If no unexplored coordinates, proceed with random exploration
            available_directions = [
                dir for dir in self.exploration_directions
                if boundary_failures[dir] <= 3  # Allow up to 3 failures per direction
            ]
            
            if not available_directions:
                self.logging.warning("All directions have failed too many times. Resetting.")
                boundary_failures.clear()
                available_directions = original_directions.copy()
            
            # Choose a random direction to move
            direction = random.choice(available_directions)
            dx, dy = self.DIRECTIONS[direction]
            target_pos = (current_pos[0] + dx, current_pos[1] + dy)
            
            self.logging.info(f"[TARGET] {target_pos}")
            # Attempt to move to the target position
            self.move_to(*target_pos)
            time.sleep(1)  # Wait for the bot to move
            
            # Check if the bot successfully moved to the target position
            new_pos = self.get_current_coords_from_game()
            if new_pos == target_pos:
                # Successfully moved: mark as free space
                self.map_data['free_spaces'].add(target_pos)
                self.map_data['obstacles'].discard(target_pos)  # Ensure it's not marked as an obstacle
                stuck_count = 0  # Reset stuck count
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
                self._handle_stuck_state(current_pos[0], current_pos[1])
                time.sleep(5)
                stuck_count = 0
        
        self.logging.info("Random exploration completed.")
        self.save_map_data()

    def save_map_data(self):
        """Save the current map data to a JSON file."""
        try:
            with open(self.map_file, 'w') as f:
                data = {
                    'obstacles': list(self.map_data['obstacles']),  # Convert to list
                    'free_spaces': list(self.map_data['free_spaces']),  # Convert to list
                    'map_name': self.map_data['map_name']  # Ensure map_name is included
                }
                json.dump(data, f, indent=4)
            self.logging.info(f"Map data saved successfully to {self.map_file}")
        except Exception as e:
            self.logging.error(f"Failed to save map data: {e}")

    def load_map_data(self):
        """Load map data from a JSON file. If the file is missing or invalid, initialize with default data."""
        default_data = {
            'obstacles': set(),  # Initialize as a set
            'free_spaces': set(),  # Initialize as a set
            'map_name': None
        }
        
        try:
            # Try to load the map data from the file
            with open(self.map_file, 'r') as f:
                data = json.load(f)
                self.map_data = {
                    'obstacles': set(tuple(obs) for obs in data['obstacles']),  # Convert to set
                    'free_spaces': set(tuple(free) for free in data['free_spaces']),  # Convert to set
                    'map_name': data.get('map_name', None)  # Use .get() to handle missing key
                }
            self.logging.info(f"Map data loaded successfully from {self.map_file}")
        except FileNotFoundError:
            # If the file doesn't exist, create it with default data
            self.logging.warning(f"{self.map_file} not found. Creating with default data.")
            self.map_data = default_data
            self.save_map_data()  # Save the default data to the file
        except json.JSONDecodeError:
            # If the file is empty or contains invalid JSON, initialize with default data
            self.logging.warning(f"{self.map_file} is empty or contains invalid JSON. Initializing with default data.")
            self.map_data = default_data
            self.save_map_data()  # Overwrite the file with default data

    def _get_best_direction(self, current_x: int, current_y: int, target_x: int, target_y: int) -> str:
        """Determine the best direction to move based on current position and target."""
        dx = target_x - current_x
        dy = target_y - current_y
        
        # If we're significantly off in both X and Y, use diagonal movement
        if abs(dx) >= self.STEP_SIZE and abs(dy) >= self.STEP_SIZE:
            if dx > 0:
                return 'NE' if dy > 0 else 'SE'
            else:
                return 'NW' if dy > 0 else 'SW'
        
        # Otherwise, use cardinal directions
        if abs(dx) > abs(dy):
            return 'E' if dx > 0 else 'W'
        else:
            return 'N' if dy > 0 else 'S'
    
    def _verify_movement(self,start_pos) -> bool:
        """Verify if movement actually changed position."""
        
        self.logging.info(f"Starting position: {start_pos}")
        
        end_pos = self.get_current_coords_from_game()
        self.logging.info(f"Ending position: {end_pos}")
        
        # Record movement effectiveness
        moved = start_pos != end_pos
        self.effective_movements.append(moved)
        
        if moved:
            # Only add to free_spaces if not already an obstacle
            self.map_data['free_spaces'].add(end_pos)
            self.logging.debug(f"Movement successful to {end_pos}")
            #if he could move, we will remove it from obstacle.
            self.map_data['obstacles'].discard(end_pos)
        else:
            target_pos = self.current_target
            # Only add to obstacles if not already a free space
            if target_pos and target_pos not in self.map_data['free_spaces']:
                self.map_data['obstacles'].add(target_pos)
                self.logging.debug(f"Movement failed at {start_pos}. Marking target {target_pos} as obstacle.")
            else:
                self.logging.debug(f"Movement failed at {start_pos}. But is already a free space at {target_pos}. Maybe there is a character on that position")
            # Save updated map data immediately
            self.save_map_data()
        
        return moved
    
    def _find_alternative_path(self, target_x: int, target_y: int) -> bool:
        """Calculate path using A* algorithm with obstacle avoidance"""
        # This would need a proper implementation of A* with obstacle awareness
        # Here's a simplified version:
        
        current_x, current_y = self.get_current_coords_from_game()
        
        # Try clockwise movement pattern
        for dir_order in ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']:
            if dir_order not in self.obstacle_locations:
                start_pos = self.get_current_coords_from_game()
                self._execute_movement(dir_order)
                if self._verify_movement(start_pos=start_pos):
                    return self.move_to(target_x, target_y)
        
        self.logging.error("No viable path found")
        return False

    def move_to(self, target_x: int, target_y: int) -> bool:
        """Move towards the target coordinates while handling obstacles."""
        self.current_target = (target_x, target_y)
        self.path_history = []
        self.obstacle_locations = set()

        while True:
            current_pos = self.get_current_coords_from_game()
            if not current_pos:
                self.logging.error("Failed to retrieve current position.")
                return False
            
            self.path_history.append(current_pos)
            self.map_data['free_spaces'].add(current_pos)
            self.map_data['obstacles'].discard(current_pos)  # Ensure it's not marked as an obstacle

            # Check if the bot has reached the target
            if self._calculate_distance(*current_pos, target_x, target_y) <= self.CLOSE_ENOUGH_DISTANCE:
                self.logging.info(f"Reached target location: {target_x}, {target_y}")
                return True

            # Detect circular path (bot getting stuck)
            if len(self.path_history) > 10 and len(set(self.path_history[-5:])) < 2:
                self.logging.warning("Circular path detected, marking as obstacle.")
                self.obstacle_locations.add(current_pos)
                self.map_data['obstacles'].add(current_pos)
                return self._find_alternative_path(target_x, target_y)

            # Determine the best movement direction
            direction = self._get_best_direction(*current_pos, target_x, target_y)

            start_pos = self.get_current_coords_from_game()
            # Try moving in the chosen direction
            self._execute_movement(direction)

            # Verify if movement was successful
            if not self._verify_movement(start_pos=start_pos):
                self.logging.warning(f"Movement failed in direction {direction}, searching for alternative path.")
                if current_pos not in self.map_data['free_spaces']:
                    self.map_data['obstacles'].add(current_pos)
                return self._find_alternative_path(target_x, target_y)
            else:
                # Successfully moved: mark as free space
                new_pos = self.get_current_coords_from_game()
                self.map_data['free_spaces'].add(new_pos)
                self.map_data['obstacles'].discard(new_pos)  # Ensure it's not marked as an obstacle
                return True
            

    def explore_map(self, map_name: str):
        """Explore the map to create a map of obstacles and free spaces."""
        self.map_data['map_name'] = map_name
        self.save_map_data()  # Save the map name immediately
        self.load_map_data()  # Load existing map data if available
        
        # Move to the map if not already there
        self.move_to_location(map_name, avoid_checks=True)
        
        # Start by moving to unexplored coordinates
        while self.move_to_unexplored():
            self.logging.info("Moved to an unexplored coordinate. Continuing exploration.")
            time.sleep(1)  # Wait for the bot to settle
        
        # If no more unexplored coordinates are found, log completion
        self.logging.info("No more unexplored coordinates found. Exploration complete.")
        
        # Save the final map data
        self.save_map_data()
        self.logging.info(f"Finished exploring {map_name}. Map data saved to {self.map_file}")

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(x2 - x1) + abs(y2 - y1)

    def _execute_movement(self, direction: str):
        """Execute movement in the given direction."""
        dx, dy = self.DIRECTIONS[direction]
        
        self.logging.info(f"Moving to {direction}...")
        
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
        time.sleep(1)  # Wait for the bot to move
        
        # Check if the bot successfully moved
        new_pos = self.get_current_coords_from_game()
        if new_pos != (current_x, current_y):
            self.logging.info("Successfully recovered from stuck state.")
            return True
        else:
            self.logging.warning("Failed to recover from stuck state.")
            return False
    
    def move_to_location(self, map_name: str, avoid_checks=False, stuck=False):
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
        
    def get_current_coords_from_game(self):
        try:
            x, y = self.memory.get_coordinates()
            self.interface.set_current_coords([x, y])
            self.logging.info(f"[POSITION] [{x}, {y}]")
            return x, y
        except Exception as e:
            self.logging.error(f"Failed to read coordinates from game memory: {e}")
            return (0, 0)  # Return a default position or handle the error appropriately