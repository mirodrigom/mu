import json
import logging
import time
import threading
from typing import List, Tuple, Set, Dict

class LearningPathManually:
    def __init__(self, map_name: str, movement):
        self.movement = movement
        self.logging = logging.getLogger(__name__)
        self.map_name = map_name
        self.free_spaces: Set[Tuple[int, int]] = set()  # Stores the coordinates of free spaces
        self.recorded_coords: Set[Tuple[int, int]] = set()  # Track recorded coordinates
        self.running = False
        self.lock = threading.Lock()

        # Load map data during initialization
        self.movement.load_map_data(map=self.map_name)
        with self.lock:
            # Initialize free_spaces and recorded_coords
            self.free_spaces.update(self.movement.map_data.get("free_spaces", set()))
            self.recorded_coords.update(self.free_spaces)  # Use free_spaces as the base

    def start_capturing(self):
        self.running = True
        self.logging.info(f"Starting to capture free spaces for {self.map_name}...")
        last_coords = None

        while self.running:
            current_coords = self.movement.get_current_coords_from_game()
            if current_coords and current_coords != last_coords:
                self.logging.info(f"New coordinates detected: {current_coords}. Adding to free spaces.")
                with self.lock:
                    self.free_spaces.add(current_coords)
                    self.recorded_coords.add(current_coords)  # Add to recorded coordinates
                last_coords = current_coords
            time.sleep(0.1)

    def stop_capturing(self):
        self.running = False
        with self.lock:
            # Save updated map data
            self.movement.map_data["free_spaces"] = self.free_spaces
            self.movement.save_map_data(map=self.map_name)
        self.logging.info("Stopped capturing free spaces.")

    def get_recorded_coords(self) -> Set[Tuple[int, int]]:
        """Return the set of recorded coordinates."""
        with self.lock:
            return self.recorded_coords.copy()  # Return a copy to avoid thread safety issues   