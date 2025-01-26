import os
import logging
import json

from pynput import keyboard

class Configuration:
    
    dirs = None
    file = None
    
    def __init__(self):
        self.setup_directories()
        self.load_config('config.json')
        self.setup_logging()
        
    def setup_logging(self):
        """Configura el sistema de logging y limpia logs anteriores"""
        log_file = os.path.join(self.dirs['logs'], 'bot_debug.log')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Reset root logger
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Configure file-only logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='w'
        )
        
        self.logging = logging.getLogger(__name__)

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
            return {
                "current_reset": 0,
                "current_level": 0,
                "current_map": "Lorencia",
                "current_location": [],
                "current_strenght": 0,
                "current_agility": 0,
                "current_vitality": 0,
                "current_energy": 0,
                "current_command": 0,
                "available_points": 0
            }
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
            
    def update_game_state(self, updates):
        """Update state file with validation"""
        try:
            current_state = self.get_game_state() or {}
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
        print(f"Loading config from: {config_file}")  # Debug
        with open(config_file) as f:
            self.file = json.load(f)
        print(f"Config loaded: {self.file is not None}")  # Debug
                
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
        
    def get_ocr_coordinates(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file['ocr_coordinates']

    def get_validation_rules(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file.get('validation', {})

    def get_stat_distribution(self):
        if not self.file:
            raise ValueError("Config file not loaded")
        return self.file['stat_distribution']