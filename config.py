import os
import logging
import json
import sys
import psutil
import pywintypes
import win32gui
import win32process
import pygetwindow as gw

from pynput import keyboard

class Configuration:
    
    dirs = None
    file = None
    
    def __init__(self):
        self.setup_directories()
        self.load_config('config.json')
        self.logging = logging.getLogger(__name__)
        self.setup_keyboard_listener()
        self.update_game_state(updates=self.start_status())
        
    def setup_logging(self):
        """Configura el sistema de logging y limpia logs anteriores"""
        log_file = os.path.join(self.dirs['logs'], 'bot_debug.log')
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s'
        ))
        
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)
        
        self.logging = logging.getLogger(__name__)
        
        # Disable buffering
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)




    def get_pid_by_window_title(self):
        try:
            title = self.file["application_name"]
            # Get the window by title
            window = gw.getWindowsWithTitle(title)[0]
            
            # Get the window handle
            hwnd = window._hWnd
            
            # Get the PID from the window handle
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            # Use psutil to get the process object
            process = psutil.Process(pid)
            
            return process.pid
        except IndexError:
            self.logging.info(f"No window with title '{title}' found.")
            return None
        except psutil.NoSuchProcess:
            self.logging.info(f"Process with PID {pid} not found.")
            return None
        except Exception as e:
            self.logging.info(f"An error occurred: {e}")
            return None

    def get_memory_status(self):
        """Read current state from file with default values"""
        try:
            clean_object = {
                    "current_memory_available_points": None,
                    "current_memory_strenght": None,
                    "current_memory_agility": None,
                    "current_memory_vitality": None,
                    "current_memory_energy": None,
                    "current_memory_command": None,
                    "process_id": self.get_pid_by_window_title()
                }

            state_file = os.path.join(self.dirs['json'], 'memory.json')
            if os.path.exists(state_file):
                self.logging.info(f"Memory json file does exist: {state_file}")
                with open(state_file, 'r') as f:
                    file_object = json.load(f)
                
                if file_object["process_id"] == clean_object["process_id"]:
                    self.logging.debug(f"Clean object: {file_object}")
                    return file_object
            self.logging.info("Memory json file does not exist.")
            self.logging.debug(f"Clean object: {clean_object}")
            return clean_object
        except Exception as e:
            self.logging.error(f"Error reading game state: {e}")
            return None
        
    def update_memory_status(self, key=None, value=None):
        """Update a specific key/value pair in the memory status."""
        try:
            current_state = self.get_memory_status() or {}
            self.logging.debug(f"Current state: {current_state}")
            # Update only the specified key/value pair
            if key is not None and value is not None:
                current_state[key] = value

            state_file = os.path.join(self.dirs['json'], 'memory.json')
            self.logging.debug(f"Saving to: {state_file}")
            with open(state_file, 'w') as f:
                json.dump(current_state, f, indent=4)
            self.logging.info(f"Memory status updated")
            return True
        except Exception as e:
            self.logging.error(f"Error writing game state: {e}")
            return False
        
    def start_status(self):
        return {
                "current_reset": 0,
                "current_level": 0,
                "current_map": "",
                "current_strenght": 0,
                "current_agility": 0,
                "current_vitality": 0,
                "current_energy": 0,
                "current_command": 0,
                "available_points": 0,
                "mulheper_active": False,
                "current_position_available_points": [],
                "current_position_strenght": [],
                "current_position_agility": [],
                "current_position_vitality": [],
                "current_position_energy": [],
                "current_position_command": []
        }

    def setup_directories(self):
        """Creates necessary directories for organizing files"""
        self.dirs = {
            'images': 'images',
            'json': 'json',
            'logs': 'logs'
        }

        for directory in self.dirs.values():
            os.makedirs(directory, exist_ok=True)

    def get_game_state(self):
        """Read current state from file with default values"""
        try:
            state_file = os.path.join(self.dirs['json'], 'current_status.json')
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    return json.load(f)
            return self.start_status()
        except Exception as e:
            self.logging.error(f"Error reading game state: {e}")
            return None

    def load_game_state(self):
        """Loads the current game state from path_history.json"""
        state_file = os.path.join(self.dirs['json'], 'path_history.json')
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    self.game_state = json.load(f)
        except Exception as e:
            self.logging.error(f"Error loading game state: {e}")
            
    def update_game_state(self, updates=None):
        """Update state file with validation"""
        try:
            current_state = self.get_game_state() or {}
            if updates:
                current_state.update(updates)

            state_file = os.path.join(self.dirs['json'], 'current_status.json')
            with open(state_file, 'w') as f:
                json.dump(current_state, f, indent=4)
            return True
        except Exception as e:
            self.logging.error(f"Error writing game state: {e}")
            return False
            
    def save_game_state(self):
        """Saves the current game state to path_history.json"""
        state_file = os.path.join(self.dirs['json'], 'path_history.json')
        try:
            with open(state_file, 'w') as f:
                json.dump(self.game_state, f, indent=4)
        except Exception as e:
            self.logging.error(f"Error saving game state: {e}")
        
    def load_config(self, config_path: str):
        config_file = os.path.join(self.dirs['json'], config_path)
        with open(config_file) as f:
            self.file = json.load(f)
                
    def setup_keyboard_listener(self):
        """Configura un listener para detectar la tecla F9 que detiene el bot"""
        def on_press(key):
            if key == keyboard.Key.f9:
                self.logging.info("Bot stopped")
                os._exit(0)  # Force exit the entire program

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        # Suppress PIL and Tesseract debug logs
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.WARNING)

    def save_map_data(self, map_name, data):
        try:
            data_to_save = {
                'obstacles': list(data['obstacles']),
                'permanent_obstacles': list(data['permanent_obstacles']),
                'respawn_zone': list(data['respawn_zone']),
                'free_spaces': list(data['free_spaces']),
            }
            full_path = os.path.join(self.dirs['json'], "maps", map_name + ".json")
            with open(full_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            self.logging.info(f"Map data saved")
        except Exception as e:
            self.logging.error(f"Failed to save map data: {e}")

    def load_map_data(self, map_name):
        """Load map data from a JSON file. If the file is missing or invalid, initialize with default data."""
        default_data = {
            'obstacles': set(),  # Temporary obstacles
            'permanent_obstacles': set(),  # Permanent obstacles (unreachable coordinates)
            'respawn_zone': set(),
            'free_spaces': set(),  # Free spaces
            'map_name': None
        }

        full_path = os.path.join(self.dirs['json'], "maps", map_name + ".json")
        if not os.path.exists(full_path):
            self.save_map_data(map_name=map_name,data=default_data)
        try:
            # Try to load the map data from the file
            with open(full_path, 'r') as f:
                data = json.load(f)
                return {
                    'obstacles': set(tuple(obs) for obs in data.get('obstacles', [])),
                    'permanent_obstacles': set(tuple(obs) for obs in data.get('permanent_obstacles', [])),
                    'respawn_zone': set(tuple(free) for free in data.get('respawn_zone', [])),
                    'free_spaces': set(tuple(free) for free in data.get('free_spaces', [])),
                }
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is invalid, initialize with default data
            self.logging.warning(f"Map file not found or invalid. Initializing with default data.")
            self.save_map_data(map_name=map_name, data=default_data)  # Save the default data to the file
        return {}

    def get_class(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file['class']
        
    def get_ocr_coordinates(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file['ocr_coordinates']

    def get_validation_rules(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file.get('validation', {})
    
    def get_interface_scale(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file.get('interface_scale', {})

    def get_stat_distribution(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file['stat_distribution']