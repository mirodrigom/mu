import json
import logging
import time
from typing import List, Tuple

class LearningPathManually:
    """
    A class to manually capture and save free spaces by continuously checking for new coordinates.
    """
    def __init__(self, map_name: str, memory):
        self.map_name = map_name
        self.free_spaces = set()  # Stores the coordinates of free spaces
        self.logging = logging.getLogger(__name__)
        self.manually_file = "manually.json"
        self.memory = memory  # Memory interface to read coordinates from the game
        self.running = False  # Controls the while loop
        
        # Load existing manually saved data if available
        self.load_manually_data()

    def load_manually_data(self):
        """Load map data from a JSON file. If the file is missing or invalid, initialize with default data."""
        default_data = {
            'obstacles': set(),  # Temporary obstacles
            'free_spaces': set(),  # Free spaces
            'map_name': None
        }
        
        try:
            # Try to load the map data from the file
            with open(self.manually_file, 'r') as f:
                data = json.load(f)
                self.map_data = {
                    'obstacles': set(tuple(obs) for obs in data.get('obstacles', [])),
                    'free_spaces': set(tuple(free) for free in data.get('free_spaces', [])),
                    'map_name': data.get('map_name', None)
                }
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is invalid, initialize with default data
            self.logging.warning(f"{self.manually_file} not found or invalid. Initializing with default data.")

    def save_manually_data(self):
        """Save the manually captured free spaces to a JSON file."""
        try:
            # Load existing data to avoid overwriting other maps
            try:
                with open(self.manually_file, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}

            data = {
                'obstacles': list(self.map_data['obstacles']),
                'free_spaces': list(self.free_spaces),
                'map_name': self.map_name
            }

            # Update the data for the current map
            # Save the updated data
            with open(self.manually_file, 'w') as f:
                json.dump(data, f, indent=4)
            self.logging.info(f"Saved {len(self.free_spaces)} free spaces for {self.map_name} to {self.manually_file}.")
        except Exception as e:
            self.logging.error(f"Failed to save manually data: {e}")

    def get_current_coords(self) -> Tuple[int, int]:
        """
        Get the current coordinates from the game memory.
        Replace this with the actual method to read coordinates from the game.
        """
        try:
            x, y = self.memory.get_coordinates()
            self.logging.debug(f"Current coordinates: ({x}, {y})")
            return x, y
        except Exception as e:
            self.logging.error(f"Failed to read coordinates from game memory: {e}")
            return None

    def start_capturing(self):
        """
        Start capturing free spaces by continuously checking for new coordinates.
        """
        self.running = True
        self.logging.info(f"Starting to capture free spaces for {self.map_name}...")
        
        last_coords = None  # Track the last saved coordinates to avoid duplicates
        
        while self.running:
            current_coords = self.get_current_coords()
            
            if current_coords and current_coords != last_coords:
                self.logging.info(f"New coordinates detected: {current_coords}. Adding to free spaces.")
                self.free_spaces.add(current_coords)
                last_coords = current_coords
            
            time.sleep(0.1)  # Adjust the sleep time as needed

    def stop_capturing(self):
        """
        Stop capturing free spaces and save the data.
        """
        self.running = False
        self.save_manually_data()
        self.logging.info("Stopped capturing free spaces.")