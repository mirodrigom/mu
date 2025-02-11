import time
import random
import logging

from typing import Tuple, Optional, List
from collections import defaultdict, deque


class LearningPathAutomatically:
    def __init__(self, map_name: str, movement, interface):
        self.movement = movement
        self.interface = interface
        self.logging = logging.getLogger(__name__)
        self.map_name = map_name
        self.current_target = None
        self.MAX_STUCK_COUNT = 3
        self.stuck_timeout = 300  # Time (in seconds) before resetting to Lorencia
        self.exploration_directions = list(self.movement.DIRECTIONS.keys())  # All possible directions
        self.movement.load_map_data(map=map_name)

    def move_to_unexplored(self) -> bool:
        """
        Move the bot to the closest unexplored coordinate using free_spaces for navigation.
        Returns True if successful, False otherwise.
        """
        current_pos = self.movement.get_current_coords_from_game()
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
        
    def start_capturing(self):
        """Explore the map randomly, avoiding repetitive movements."""
        self.logging.info("Starting random exploration...")
        
        boundary_failures = defaultdict(int)  # Track failures in each direction
        original_directions = self.exploration_directions.copy()  # Save original directions
        stuck_count = 0  # Track consecutive failures
        start_time = time.time()  # Track the start time of exploration
        
        while time.time() - start_time < self.stuck_timeout:  # Use a while loop with a timeout
            current_pos = self.movement.get_current_coords_from_game()
            self.logging.debug(f"Current position: {current_pos}")
            
            # Check if the bot is stuck (not moving for several steps)
            if len(self.movement.movement_history) == self.movement.movement_history.maxlen and len(set(self.movement.movement_history)) <= 2:
                self.logging.warning("Bot is stuck in the same position. Attempting to recover.")
                self._handle_stuck_recovery()
                return  # Exit the function and restart exploration
            
            # Choose a random direction to move
            direction = random.choice(self.exploration_directions)
            dx, dy = self.movement.DIRECTIONS[direction]
            target_pos = (current_pos[0] + dx, current_pos[1] + dy)
            
            self.logging.info(f"[TARGET] {target_pos}")
            # Attempt to move to the target position
            self.move_to(*target_pos)
            time.sleep(0.5)  # Wait for the bot to move
            
            # Check if the bot successfully moved to the target position
            new_pos = self.movement.get_current_coords_from_game()
            if new_pos == target_pos:
                # Successfully moved: mark as free space
                self.movement.map_data['free_spaces'].add(target_pos)
                self.movement.map_data['obstacles'].discard(target_pos)  # Ensure it's not marked as an obstacle
                stuck_count = 0  # Reset stuck count
                self.movement.save_map_data(map=self.map_name)
            else:
                # Failed to move: mark as obstacle
                if target_pos not in self.movement.map_data['free_spaces']:
                    self.movement.map_data['obstacles'].add(target_pos)
                # Also mark the current position as a potential obstacle if stuck
                if new_pos == current_pos and current_pos not in self.movement.map_data['free_spaces']:
                    self.movement.map_data['obstacles'].add(current_pos)
                boundary_failures[direction] += 1
                stuck_count += 1
            
            # If stuck too many times, take a break or change strategy
            if stuck_count >= self.MAX_STUCK_COUNT:
                self.logging.warning("Bot is stuck. Taking a break or changing strategy.")
                self._handle_stuck_recovery()
                return  # Exit the function and restart exploration
        
        self.logging.info("Random exploration completed.")
        self.movement.save_map_data(map=self.map_name)

    def _verify_movement(self, start_pos) -> bool:
        """Verify if movement actually changed position."""
        self.logging.info(f"Starting position: {start_pos}")
        
        # Retry movement up to 3 times before marking as failed
        for _ in range(3):
            time.sleep(0.5)  # Wait for the bot to move
            end_pos = self.movement.get_current_coords_from_game()
            self.logging.info(f"Ending position: {end_pos}")
            
            if start_pos != end_pos:
                self.movement.map_data['free_spaces'].add(end_pos)
                self.movement.map_data['obstacles'].discard(end_pos)
                self.logging.debug(f"Movement successful to {end_pos}")
                return True
        
        # If movement failed after retries, mark as obstacle
        target_pos = self.current_target
        if target_pos and target_pos not in self.movement.map_data['free_spaces']:
            self.movement.map_data['obstacles'].add(target_pos)
            self.logging.debug(f"Movement failed at {start_pos}. Marking target {target_pos} as obstacle.")
        else:
            self.logging.debug(f"Movement failed at {start_pos}. But is already a free space at {target_pos}.")
        
        self.movement.save_map_data(map=self.map_name)
        return False
    
    def move_to(self, target_x: int, target_y: int) -> bool:
        """Move towards the target coordinates using pathfinding."""
        self.logging.debug("==========================")
        current_x, current_y = self.movement.get_current_coords_from_game()
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
                self.movement.map_data['permanent_obstacles'].add((target_x, target_y))
                self.movement.save_map_data(map=self.map_name)
                return False

            # Follow the path step by step
            for step_x, step_y in path:
                self.logging.info(f"Moving to ({step_x}, {step_y})")
                self.movement._execute_movement_towards(step_x, step_y)
                time.sleep(0.5)  # Increase delay to allow movement to complete

                # Verify if the bot successfully moved to the target position
                new_x, new_y = self.movement.get_current_coords_from_game()
                self.logging.debug(f"New position after movement: ({new_x}, {new_y})")
                if (new_x, new_y) != (step_x, step_y):
                    self.logging.warning(f"Failed to move to ({step_x}, {step_y}). Attempt {attempt_count + 1}.")
                    attempt_count += 1
                    self.interface.use_spell()
                    break  # Retry the entire path
                else:
                    self.logging.warning(f"Successfull reach target after {attempt_count} attempts. Marking as FREE SPACE.")
                    self.movement.map_data['free_spaces'].add((step_x, step_y))
                    self.movement.save_map_data(map=self.map_name)
            else:
                self.movement.map_data['free_spaces'].add((target_x, target_y))
                self.movement.save_map_data(map=self.map_name)
                self.logging.info(f"Successfully reached target location: ({target_x}, {target_y})")
                return True

        self.logging.warning(f"Failed to reach target after {attempt_count} attempts. Marking as obstacle.")
        self.movement.map_data['obstacles'].add((step_x, step_y))
        # Force immediate save after marking as obstacle
        try:
            self.movement.save_map_data(map=self.map_name)
            self.logging.info(f"Successfully saved obstacle {(step_x, step_y)} to map data")
        except Exception as e:
            self.logging.error(f"Failed to save map data: {e}")
        return False
    
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
                if (target_x, target_y) in self.movement.map_data['free_spaces'] or (target_x, target_y) in self.movement.map_data['obstacles']:
                    continue

                # Check if the unexplored coordinate is accessible from free_spaces
                if self._is_explorable(target_x, target_y):
                    unexplored_coords.append((target_x, target_y))
                    self.logging.debug(f"Found accessible unexplored coordinate: ({target_x}, {target_y})")

        if unexplored_coords:
            # Prioritize the closest unexplored coordinate
            unexplored_coords.sort(key=lambda coord: self.movement._calculate_distance(current_x, current_y, *coord))
            self.logging.info(f"Closest accessible unexplored coordinate: {unexplored_coords[0]}")
            return unexplored_coords[0]

        self.logging.info("No accessible unexplored coordinates found within the search radius.")
        return None


    
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
            directions = sorted(self.movement.DIRECTIONS.items(), key=lambda d: self.movement._calculate_distance(x + d[1][0], y + d[1][1], target_x, target_y))
            for direction, (dx, dy) in directions:
                new_x = x + dx
                new_y = y + dy

                # Skip if the new coordinate is an obstacle or out of bounds
                if (new_x, new_y) in self.movement.map_data['obstacles'] or (new_x, new_y) in self.movement.map_data['permanent_obstacles']:
                    continue

                # Add the new coordinate to the queue
                queue.append((new_x, new_y, path + [(x, y)]))

        return None  # No path found
    
    def _handle_stuck_recovery(self):
        """Handle stuck recovery by trying alternative directions."""
        self.logging.warning("Bot is stuck. Attempting to recover.")
        current_x, current_y = self.movement.get_current_coords_from_game()
        
        # Try moving in all possible directions
        for direction in self.movement.DIRECTIONS:
            dx, dy = self.movement.DIRECTIONS[direction]
            target_x, target_y = current_x + dx, current_y + dy
            
            # Skip if the target position is an obstacle
            if (target_x, target_y) in self.movement.map_data['obstacles']:
                continue
            
            self.logging.info(f"Attempting to move {direction} to ({target_x}, {target_y}).")
            self.move_to(target_x, target_y)
            time.sleep(0.5)  # Wait for movement to complete
            
            # Check if the bot successfully moved
            new_x, new_y = self.movement.get_current_coords_from_game()
            if (new_x, new_y) != (current_x, current_y):
                self.logging.info("Successfully recovered from stuck state.")
                return True
        
        self.logging.warning("Failed to recover from stuck state.")
        return False

    def _is_explorable(self, target_x: int, target_y: int) -> bool:
        """
        Verifica si una coordenada inexplorada es accesible desde los free_spaces.
        Devuelve True si hay al menos un free_space adyacente a la coordenada inexplorada.
        """
        # Verifica si hay al menos un free_space adyacente a la coordenada inexplorada
        for dx, dy in self.movement.DIRECTIONS.values():
            adjacent_x = target_x + dx
            adjacent_y = target_y + dy
            if (adjacent_x, adjacent_y) in self.movement.map_data['free_spaces']:
                return True
        return False