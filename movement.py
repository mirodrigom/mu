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
        self.last_movements = deque(maxlen=10)
        self.logging = logging.getLogger(__name__)
        self.movement_will_be_with = "keyboard"
        
        # Movement constants
        self.STEP_SIZE = 3
        self.MOVEMENT_DELAY = 0.2  # Delay between movements
        self.MAX_RETRIES = 3  # Maximum retries for movement validation
        
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

    def is_close_enough(self, current, target, tolerance=1):
        """
        Check if the current position is within tolerance of the target.
        :param current: Tuple (x, y) representing the current position.
        :param target: Tuple (x, y) representing the target position.
        :param tolerance: Maximum allowed distance from the target.
        :return: True if within tolerance, False otherwise.
        """
        return abs(current[0] - target[0]) <= tolerance and abs(current[1] - target[1]) <= tolerance

    def _execute_movement(self, target_x: int, target_y: int):
        """
        Execute movement in the given direction and update movement history.
        :param target_x: Target X coordinate.
        :param target_y: Target Y coordinate.
        """
        current_x, current_y = self.get_current_coords_from_game()
        dx = target_x - current_x
        dy = target_y - current_y

        self.logging.debug(f"Moving towards ({target_x}, {target_y}). Current position: ({current_x}, {current_y})")
        
        if self.movement_will_be_with == "mouse":
            # Diagonal movements
            if dx > 0:
                self.interface.mouse_right()
            elif dx < 0:
                self.interface.mouse_left()
            elif dy > 0:
                self.interface.mouse_top()
            elif dy < 0:
                self.interface.mouse_down()
        else:
            # Keyboard movements (adjusted for STEP_SIZE)
            steps_x = abs(dx) // self.STEP_SIZE
            steps_y = abs(dy) // self.STEP_SIZE

            # Reduce step size as we approach the target
            if steps_x == 0 and abs(dx) > 0:
                steps_x = 1
            if steps_y == 0 and abs(dy) > 0:
                steps_y = 1

            if dx > 0:
                for _ in range(steps_x):
                    self.interface.arrow_key_right(press=True, release=True)
            elif dx < 0:
                for _ in range(steps_x):
                    self.interface.arrow_key_left(press=True, release=True)
            if dy > 0:
                for _ in range(steps_y):
                    self.interface.arrow_key_up(press=True, release=True)
            elif dy < 0:
                for _ in range(steps_y):
                    self.interface.arrow_key_down(press=True, release=True)
            
            time.sleep(self.MOVEMENT_DELAY)  # Adjust delay as needed


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
        if start not in self.map_data["free_spaces"] or goal not in self.map_data["free_spaces"]:
            self.logging.warning("Start or goal position is not in free_spaces.")
            return None

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

        # Ensure the goal is in free_spaces
        if goal not in self.map_data["free_spaces"]:
            self.logging.warning(f"Target position {goal} is not in free_spaces.")
            return None

        # Call A* and return the path
        path = self.astar(start, goal)
        if path:
            return path
        else:
            self.logging.warning("No valid path to the target.")
            return None
        
    def validate_movement(self, expected_x, expected_y):
        """
        Validate whether the character moved to the expected position.
        :param expected_x: Expected X coordinate.
        :param expected_y: Expected Y coordinate.
        :return: True if the character is at the expected position, False otherwise.
        """
        current_x, current_y = self.get_current_coords_from_game()
        if (current_x, current_y) != (expected_x, expected_y):
            self.logging.warning(f"Movement validation failed. Expected: ({expected_x}, {expected_y}), Actual: ({current_x}, {current_y})")
            return False
        return True

    def walk_to(self, target_x, target_y):
        """
        Move the bot to the target coordinates (x, y) using A* pathfinding and step-by-step movement.
        :param target_x: Target X coordinate.
        :param target_y: Target Y coordinate.
        :return: True if the target is reached, False otherwise.
        """
        while True:
            # Find the best path using A*
            path = self.find_best_route_to_target(target_x=target_x, target_y=target_y)
            if not path:
                self.logging.warning("No valid path to the target.")
                return False

            self.logging.info(f"Found path to target: {path}")

            # Move along the path step-by-step
            for step in path:
                step_x, step_y = step
                retries = 0
                current_x, current_y = self.get_current_coords_from_game()

                while not self.is_close_enough((current_x, current_y), (step_x, step_y), tolerance=1):
                    self.check_abrupt_movements()
                    self._execute_movement(step_x, step_y)
                    time.sleep(self.MOVEMENT_DELAY)  # Adjust delay as needed
                    current_x, current_y = self.get_current_coords_from_game()

                    if not self.validate_movement(step_x, step_y):
                        retries += 1
                        if retries >= self.MAX_RETRIES:
                            self.logging.warning("Failed to reach step. Recalculating path...")
                            break

                if retries >= self.MAX_RETRIES:
                    break  # Exit the loop and recalculate the path

            # Check if we reached the final target
            current_x, current_y = self.get_current_coords_from_game()
            if self.is_close_enough((current_x, current_y), (target_x, target_y), tolerance=1):
                self.logging.info(f"Successfully reached the target: ({target_x}, {target_y})")
                return True

            # If we didn't reach the target, recalculate the path and try again
            self.logging.info("Recalculating path to target...")

    def move_to_location(self, map_name: str, avoid_checks=False, stuck=False, do_not_open_stats=False):
        if not avoid_checks:
            current_state = self.config.get_game_state()
            if map_name != current_state['current_map'] or stuck is True:
                self.logging.info("Dentro de move to location")
                self.logging.debug(f"map_name: {map_name}  != current_state_map: {current_state} ")
                self.logging.info(current_state)
                #self.save_map_data(map=map_name)
                self.interface.set_mu_helper_status(False)
                self.interface.command_move_to_map(map_name=map_name)
                self.config.update_game_state({'current_map': map_name})
                self.load_map_data(map=map_name)
                self.save_respawn_zone()
                self.last_movements.clear()
            else:
                self.logging.info(f"Character already in {map_name}. No need to move again")
        else:
            #self.save_map_data(map=current_state['current_map'])
            self.logging.info(f"Character is moving to {map_name} without checking the current map.")
            self.interface.set_mu_helper_status(False)
            self.interface.command_move_to_map(map_name=map_name)
            self.load_map_data(map=map_name)
            self.save_respawn_zone()
            self.last_movements.clear()
        
        if not do_not_open_stats:
            self.interface.open_stats_window()
        
    def get_current_coords_from_game(self):
        try:
            x, y = self.memory.get_coordinates()
            self.last_movements.append([x,y])
            self.interface.set_current_coords([x, y])
            self.logging.info(f"[POSITION] [{x}, {y}]")
            return x, y
        except Exception as e:
            self.logging.error(f"Failed to read coordinates from game memory: {e}")
            return (0, 0)  # Return a default position or handle the error appropriately
        
    def check_abrupt_movements(self):
        if len(self.last_movements) == 10:
            last_x, last_y = self.last_movements[-1]
            
            # Iterate through all previous movements except the last one
            for prev_x, prev_y in list(self.last_movements)[:-1]:
                #self.logging.debug(f"Last_X = {last_x}  || Last_Y = {last_y}")
                #self.logging.debug(f"Prev_X = {prev_x}  || Prev_Y = {prev_y}")
                
                # Check if the difference in x and y is greater than or equal to 20
                if abs(last_x - prev_x) >= 20 and abs(last_y - prev_y) >= 20:
                    self.logging.debug(f"List: {self.last_movements}")
                    self.logging.warning("Detected abrupt movement. Change map or killed.")
                    self.get_current_coords_from_game()
                    current_state = self.config.get_game_state()
                    self.move_to_location(map_name=current_state['current_map'], avoid_checks=True, do_not_open_stats=True)
                    time.sleep(2)
                    return True
        return False