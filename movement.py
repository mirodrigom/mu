import time
import logging

from heapq import heappush, heappop
from collections import defaultdict, deque

class Movement:
    """
    An improved movement class for MU Online bot with better pathfinding and obstacle avoidance.
    """
    map_data = None

    def __init__(self, interface, config, memory):
        self.interface = interface
        self.config = config
        self.memory = memory
        self.stuck_positions = defaultdict(int)  # Track direction failure counts
        self.effective_movements = deque(maxlen=10)  # Track recent movements
        self.logging = logging.getLogger(__name__)
        self.movement_will_be_with = "mouse"
        
        # Movement constants
        self.STEP_SIZE = 1
        
        # Stuck detection
        self.movement_history = deque(maxlen=20)
        
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

    def load_map_data(self, map="lorencia"):
        self.map_data = self.config.load_map_data(map_name=map)

    def save_map_data(self, map="lorencia"):
        self.config.save_map_data(map_name=map, data=self.map_data)


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

    def save_respawn_zone(self):
        x, y = self.get_current_coords_from_game()
        self.map_data['respawn_zone'].add((x,y))
        self.map_data['free_spaces'].discard((x,y))
        self.map_data['obstacles'].discard((x,y))

    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(x2 - x1) + abs(y2 - y1)

    def heuristic(self, a, b):
        """Heuristic function for A* algorithm (uses Manhattan distance)."""
        return self._calculate_distance(a[0], a[1], b[0], b[1])

    def get_neighbors(self, node):
        """Get valid neighbors (adjacent coordinates in free_spaces)."""
        x, y = node
        neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]  # 4-directional movement
        return [n for n in neighbors if n in self.map_data["free_spaces"]]

    def astar(self, start, goal):
        """A* algorithm to find the shortest path from start to goal."""
        open_set = []
        heappush(open_set, (0, start))  # Priority queue: (priority, node)
        came_from = {}  # To reconstruct the path
        g_score = {start: 0}  # Cost from start to node
        f_score = {start: self.heuristic(start, goal)}  # Estimated total cost from start to goal through node

        while open_set:
            _, current = heappop(open_set)

            if current == goal:
                # Reconstruct the path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]  # Return reversed path

            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + 1  # Assuming each step has a cost of 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
                    heappush(open_set, (f_score[neighbor], neighbor))

        return None  # No path found
    
    def find_best_route_to_target(self, target_x, target_y):
        """Find the best path to the target (x, y) using A* algorithm."""
        start = self.get_current_coords_from_game()
        goal = (target_x, target_y)  # Target position

        # Call A* and return the path
        path = self.astar(start, goal)
        if path:
            return path
        else:
            self.logging.warning("No valid path to the target.")
            return None

    def walk_to(self, target_x, target_y):
        """Move the bot to the target coordinates (x, y) using A* pathfinding and step-by-step movement."""

        # Find the best path using A*
        path = self.find_best_route_to_target(target_x=target_x, target_y=target_y)
        if not path:
            self.logging.warning("No valid path to the target.")
            return False

        self.logging.info(f"Found path to target: {path}")

        # Move along the path step-by-step
        for step in path:
            step_x, step_y = step
            self._execute_movement_towards(step_x, step_y)

            # Wait for the bot to reach the target step
            time.sleep(1.0)  # Adjust delay as needed

            # Update current coordinates after movement
            current_x, current_y = self.get_current_coords_from_game()
            self.logging.debug(f"Current position after movement: ({current_x}, {current_y})")

            # Check if the bot reached the target step
            if (current_x, current_y) == (step_x, step_y):
                self.logging.debug(f"Reached step: ({step_x}, {step_y})")
            else:
                self.logging.warning(f"Failed to reach step: ({step_x}, {step_y})")
                return False

        self.logging.info(f"Successfully reached the target: ({target_x}, {target_y})")
        return True
        

    def move_to_location(self, map_name: str, avoid_checks=False, stuck=False, do_not_open_stats=False):
        if not avoid_checks:
            current_state = self.config.get_game_state()
            if map_name != current_state['current_map'] or stuck is True:
                self.logging.info("Dentro de move to location")
                self.logging.info(current_state)
                self.save_map_data(map=current_state['current_map'])
                self.interface.set_mu_helper_status(False)
                self.interface.command_move_to_map(map_name=map_name)
                self.config.update_game_state({'current_map': map_name})
                self.load_map_data(map=map_name)
                self.save_respawn_zone()
            else:
                self.logging.info(f"Character already in {map_name}. No need to move again")
        else:
            self.save_map_data(map=current_state['current_map'])
            self.logging.info(f"Character is moving to {map_name} without checking the current map.")
            self.interface.set_mu_helper_status(False)
            self.interface.command_move_to_map(map_name=map_name)
            self.load_map_data(map=map_name)
            self.save_respawn_zone()
        
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