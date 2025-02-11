import json
import logging
import time
from typing import List, Tuple, Set, Dict

class LearningPathManually:
    """
    A class to manually capture and save free spaces by continuously checking for new coordinates.
    """
    def __init__(self, map_name: str, movement):
        self.movement = movement
        self.logging = logging.getLogger(__name__ )
        self.map_name = map_name
        self.free_spaces: Set[Tuple[int, int]] = set()  # Stores the coordinates of free spaces
        self.running = False  # Controls the while loop
        self.movement.load_map_data(map=map_name)

    def start_capturing(self):
        """
        Start capturing free spaces by continuously checking for new coordinates.
        """
        self.running = True
        self.logging.info(f"Starting to capture free spaces for {self.map_name}...")
        
        last_coords = None  # Track the last saved coordinates to avoid duplicates
        
        while self.running:
            current_coords = self.movement.get_current_coords_from_game()
            
            if current_coords and current_coords != last_coords:
                self.logging.info(f"New coordinates detected: {current_coords}. Adding to free spaces.")
                self.movement.map_data['free_spaces'].add(current_coords)
                last_coords = current_coords
            
            time.sleep(0.1)  # Adjust the sleep time as needed

    def stop_capturing(self):
        """
        Stop capturing free spaces and save the data.
        """
        self.running = False
        self.movement.save_map_data(map=self.map_name)
        self.logging.info("Stopped capturing free spaces.")