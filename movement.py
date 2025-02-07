import time
import math
import logging
from typing import Tuple, Optional

class Movement:
    """
    A simplified and efficient movement class for MU Online bot.
    Focuses on smooth pathfinding and practical movement execution.
    """
    def __init__(self, interface, config, memory):
        self.interface = interface
        self.config = config
        self.memory = memory
        self.logging = logging.getLogger(__name__)
        
        # Movement constants
        self.STEP_SIZE = 3  # Each movement is 3 tiles
        self.CLOSE_ENOUGH_DISTANCE = 3  # Consider arrived when within 3 tiles
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

    def move_to(self, target_x: int, target_y: int) -> bool:
        """
        Main movement method that handles pathfinding to target coordinates.
        Returns True if destination reached, False otherwise.
        """
        start_time = time.time()
        stuck_count = 0
        last_position = None
        last_distance = float('inf')
        
        self.logging.info(f"Starting movement to target [{target_x}, {target_y}]")
        
        while True:
            # Check timeout
            if time.time() - start_time > self.MOVEMENT_TIMEOUT:
                self.logging.error("Movement timeout reached")
                return False
            
            # Get current position and calculate distance
            current_x, current_y = self.get_current_coords_from_game()
            if current_x is None or current_y is None:
                continue
                
            distance = self._calculate_distance(current_x, current_y, target_x, target_y)
            
            # Check if we've reached the destination
            if distance <= self.CLOSE_ENOUGH_DISTANCE:
                self.logging.info("Reached destination")
                self._release_all_keys()
                return True
            
            # Stuck detection
            current_pos = (current_x, current_y)
            if current_pos == last_position:
                stuck_count += 1
                if stuck_count >= self.MAX_STUCK_COUNT:
                    if not self._handle_stuck_state(current_x, current_y, target_x, target_y):
                        return False
                    stuck_count = 0
            else:
                stuck_count = 0
            
            # Movement logic
            direction = self._get_best_direction(current_x, current_y, target_x, target_y)
            if direction:
                self._execute_movement(direction)
            
            # Update state for next iteration
            last_position = current_pos
            last_distance = distance
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(x2 - x1) + abs(y2 - y1)

    def _get_best_direction(self, current_x: int, current_y: int, target_x: int, target_y: int) -> str:
        """
        Determine the best direction to move based on current position and target.
        Returns direction key from self.DIRECTIONS.
        """
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

    def _execute_movement(self, direction: str):
        """Execute movement in the given direction."""
        dx, dy = self.DIRECTIONS[direction]
        
        # Press appropriate keys based on direction
        if dx > 0:
            self.interface.arrow_key_right(press=True)
        elif dx < 0:
            self.interface.arrow_key_left(press=True)
            
        if dy > 0:
            self.interface.arrow_key_up(press=True)
        elif dy < 0:
            self.interface.arrow_key_down(press=True)

    def _release_all_keys(self):
        """Release all movement keys."""
        self.interface.arrow_key_up(release=True)
        self.interface.arrow_key_down(release=True)
        self.interface.arrow_key_left(release=True)
        self.interface.arrow_key_right(release=True)

    def _handle_stuck_state(self, current_x: int, current_y: int, target_x: int, target_y: int) -> bool:
        """
        Handle stuck state by trying alternative movements.
        Returns True if unstuck, False if failed.
        """
        self.logging.warning(f"Stuck at position [{current_x}, {current_y}]")
        
        # Release all keys first
        self._release_all_keys()
        
        # Try moving in perpendicular direction briefly
        dx = target_x - current_x
        dy = target_y - current_y
        
        if abs(dx) > abs(dy):
            # If mainly moving horizontally, try vertical movement
            self.interface.arrow_key_up(press=True)
            time.sleep(0.5)
            self.interface.arrow_key_up(release=True)
        else:
            # If mainly moving vertically, try horizontal movement
            self.interface.arrow_key_right(press=True)
            time.sleep(0.5)
            self.interface.arrow_key_right(release=True)
        
        return True
    
    def move_to_location(self, map_name: str, avoid_checks=False,stuck=False):
        
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
        x, y = self.memory.get_coordinates()
        self.interface.set_current_coords([x,y])
        self.logging.info(f"[POSITION] [{x}, {y}]")
        return x, y