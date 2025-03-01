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
        
    

    def _convert_new_config_format(self, new_config):
        """
        Convert the new config format to the format expected by the existing code.
        """
        old_format = {
            "class": new_config.get("class", "Fairy Elf"),
            "interface_scale": new_config.get("interface_scale", 100),
            "application_name": new_config.get("application_name", "MEGAMU"),
            "dashboard_name": new_config.get("dashboard_name", "MU-Dashboard"),
            "stat_distribution": new_config.get("stat_distribution", {}),
            "max_level": new_config.get("max_level", 400),
            "check_interval": new_config.get("check_interval", 5),
            # Create level thresholds from hunting spots
            "level_thresholds": self._generate_level_thresholds(new_config),
            # Add validation rules
            "validation": {
                "strenght": {"min": 1, "max": 32767},
                "agility": {"min": 1, "max": 32767},
                "vitality": {"min": 1, "max": 32767},
                "energy": {"min": 1, "max": 32767},
                "command": {"min": 1, "max": 32767}
            }
        }
        
        return old_format
    
    def _generate_level_thresholds(self, new_config):
        """
        Generate level thresholds from hunting spots in new config format.
        """
        thresholds = {}
        
        # Get the first reset config (for initial setup)
        if not new_config.get("reset_config"):
            return {}
            
        reset_config = new_config["reset_config"][0]
        hunting_spots = reset_config.get("hunting_spots", {})
        
        # Sort spots by level_range
        sorted_spots = sorted(
            hunting_spots.items(), 
            key=lambda x: x[1].get("level_range", [0, 0])[0]
        )
        
        # Starting location (lowest level range)
        # For level 0, we need to handle multiple maps
        if sorted_spots and sorted_spots[0][1].get("maps"):
            maps = sorted_spots[0][1]["maps"]
            map_list = []
            
            for map_name, map_data in maps.items():
                map_list.append({
                    "map": map_data["map"],
                    "location": map_data["location"]
                })
                
            thresholds["0"] = map_list
        elif sorted_spots:
            # Fallback if no maps specified
            first_spot = sorted_spots[0][1]
            thresholds["0"] = {
                "map": first_spot.get("map", "lorencia"),
                "location": first_spot.get("location", [128, 128])
            }
        
        # Process other hunting spots
        for spot_id, spot_data in sorted_spots:
            if "level_range" in spot_data and len(spot_data["level_range"]) >= 2:
                min_level = str(spot_data["level_range"][0])
                
                # Skip level 0 as we handled it specially
                if min_level == "0" or min_level == "1":
                    continue
                    
                if "map" in spot_data:
                    thresholds[min_level] = {
                        "map": spot_data["map"],
                        "location": spot_data["location"]
                    }
                elif "maps" in spot_data:
                    # If multiple maps, include them all as a list
                    map_list = []
                    for map_name, map_data in spot_data["maps"].items():
                        map_list.append({
                            "map": map_data["map"],
                            "location": map_data["location"]
                        })
                    thresholds[min_level] = map_list
        
        return thresholds
                
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
                  
    def get_hunting_spot(self, reset_count, current_level, character_start_location):
        """
        Get the appropriate hunting spot based on reset count and level.
        
        Returns: dict with 'map' and 'location' keys.
        """
        # Check if we're using the new config format
        if not self.file or 'reset_config' not in self.file:
            # Use original level threshold logic
            for threshold, obj in sorted(self.file.get('level_thresholds', {}).items(), key=lambda x: int(x[0]), reverse=True):
                if current_level >= int(threshold):
                    if isinstance(obj, list):
                        # Find location matching character start location or use first
                        location_obj = next((loc for loc in obj if loc["map"] == character_start_location), obj[0])
                        return {
                            'map': location_obj["map"],
                            'location': location_obj["location"]
                        }
                    else:
                        return {
                            'map': obj["map"],
                            'location': obj["location"]
                        }
            # Default fallback
            return {'map': character_start_location, 'location': [128, 128]}
        
        # Find the applicable reset config
        reset_config = None
        for rc in self.file.get('reset_config', []):
            reset_range = rc.get('reset_range', [0, 999])
            if reset_range[0] <= reset_count <= reset_range[1]:
                reset_config = rc
                break
                
        if not reset_config and self.file.get('reset_config'):
            reset_config = self.file['reset_config'][0]
            
        if not reset_config:
            return {'map': character_start_location, 'location': [128, 128]}
            
        # Find the appropriate hunting spot based on level
        hunting_spots = reset_config.get('hunting_spots', {})
        appropriate_spot = None
        
        # Sort by level range and find appropriate spot
        for spot_id, spot_data in sorted(
            hunting_spots.items(), 
            key=lambda x: x[1].get('level_range', [0, 0])[0]
        ):
            level_range = spot_data.get('level_range', [0, 999])
            if level_range[0] <= current_level <= level_range[1]:
                appropriate_spot = spot_data
                break
                
        if not appropriate_spot:
            return {'map': character_start_location, 'location': [128, 128]}
            
        # If spot has a specific map
        if 'map' in appropriate_spot and 'location' in appropriate_spot:
            return {
                'map': appropriate_spot['map'],
                'location': appropriate_spot['location']
            }
            
        # If spot has multiple maps, try to match the character's start location
        if 'maps' in appropriate_spot:
            # Try to find the map matching the character's start location
            if character_start_location in appropriate_spot['maps']:
                map_data = appropriate_spot['maps'][character_start_location]
                return {
                    'map': map_data['map'],
                    'location': map_data['location']
                }
                
            # If no match, use the first map
            if appropriate_spot['maps']:
                first_map = next(iter(appropriate_spot['maps'].values()))
                return {
                    'map': first_map['map'],
                    'location': first_map['location']
                }
                
        # Fallback
        return {'map': character_start_location, 'location': [128, 128]}
    
    def load_config(self, config_path: str):
        """
        Load configuration file and convert it to the expected format.
        Supports both old and new config formats.
        """
        config_file = os.path.join(self.dirs['json'], config_path)
        try:
            with open(config_file) as f:
                config_data = json.load(f)
            
            # Store the original config data for direct access
            self.original_config = config_data
                
            # Check if this is the new config format (has reset_config key)
            if 'reset_config' in config_data:
                # Convert for backwards compatibility
                self.file = self._convert_new_config_format(config_data)
                
                # Add the reset_config directly to ensure it's accessible
                # This ensures we can directly access it in get_reset_level
                self.file['reset_config'] = config_data.get('reset_config', [])
                
                if hasattr(self, 'logging'):
                    self.logging.info("Loaded new config format with reset_config")
            else:
                # Old format - use as is
                self.file = config_data
                if hasattr(self, 'logging'):
                    self.logging.info("Loaded legacy config format")
                    
        except Exception as e:
            if hasattr(self, 'logging'):
                self.logging.error(f"Error loading config: {e}")
            else:
                print(f"Error loading config: {e}")
            raise
            
    def get_reset_level(self, reset_count):
        """
        Get the reset level based on current reset count using the new config format.
        Falls back to default values if using old config format.
        """
        try:
            # Log the request
            if hasattr(self, 'logging'):
                self.logging.debug(f"Getting reset level for reset count: {reset_count}")
            
            # Check if the original config data is directly accessible
            if hasattr(self, 'original_config') and self.original_config and 'reset_config' in self.original_config:
                # Direct access to original config data
                for reset_config in self.original_config.get('reset_config', []):
                    reset_range = reset_config.get('reset_range', [0, 999])
                    if len(reset_range) >= 2 and reset_range[0] <= reset_count <= reset_range[1]:
                        level = reset_config.get('reset_level')
                        if level is not None:
                            if hasattr(self, 'logging'):
                                self.logging.debug(f"Found reset level {level} for reset count {reset_count} in range {reset_range}")
                            return level
            
            # Check if we have the file loaded with reset_config included
            if self.file and 'reset_config' in self.file:
                # New config format - find the applicable reset config
                for reset_config in self.file.get('reset_config', []):
                    reset_range = reset_config.get('reset_range', [0, 999])
                    if len(reset_range) >= 2 and reset_range[0] <= reset_count <= reset_range[1]:
                        level = reset_config.get('reset_level')
                        if level is not None:
                            if hasattr(self, 'logging'):
                                self.logging.debug(f"Found reset level {level} for reset count {reset_count} in range {reset_range}")
                            return level
                        
                # If no range matches, but we have reset_config data, reload the config file
                # This is a fallback in case the conversion process changed the data structure
                try:
                    config_file = os.path.join(self.dirs['json'], 'config.json')
                    with open(config_file) as f:
                        direct_config = json.load(f)
                    
                    if 'reset_config' in direct_config:
                        for reset_config in direct_config.get('reset_config', []):
                            reset_range = reset_config.get('reset_range', [0, 999])
                            if len(reset_range) >= 2 and reset_range[0] <= reset_count <= reset_range[1]:
                                level = reset_config.get('reset_level')
                                if level is not None:
                                    if hasattr(self, 'logging'):
                                        self.logging.debug(f"Found reset level {level} for reset count {reset_count} in direct config")
                                    return level
                except Exception as e:
                    if hasattr(self, 'logging'):
                        self.logging.error(f"Error reading direct config: {e}")
            
            # Default fallback based on common values
            if hasattr(self, 'logging'):
                self.logging.warning(f"No specific reset level found for reset count {reset_count}, using fallback")
                
            if reset_count <= 5:
                return 380
            elif reset_count <= 15:
                return 385
            elif reset_count <= 50:
                return 390
            elif reset_count < 75:
                return 395
            else:
                return 400
                
        except Exception as e:
            if hasattr(self, 'logging'):
                self.logging.error(f"Error in get_reset_level: {e}")
            return 390  # Safe fallback if anything goes wrong