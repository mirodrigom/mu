import time
import logging
import os
import threading
import signal
import sys

from logger_config import setup_logging
from interface import Interface
from utils import Utils
from config import Configuration
from gameclass import GameClass
from memory import Memory
from movement import Movement
from learning_path_manually import LearningPathManually
from learning_path_automatically import LearningPathAutomatically
from grid_system import Grid

class GameBot:
    def __init__(self):
        self.config = Configuration()
        setup_logging()
        self.logging = logging.getLogger(__name__)
        self.interface = Interface(self.config)
        self.gameclass = GameClass()
        self.utils = Utils()
        self.memory = Memory(config=self.config)
        self.movement = Movement(interface=self.interface, config=self.config, memory=self.memory)
        
        self.interface.load_ocr_packages()
        
        self.running = True
        self.reference_point = None
        self.first_time = True
        self.last_reset_time = 0  # Initialize the last reset time
        self.reset_cooldown = 60  # Cooldown period in seconds
        self.logging.info("GameBot initialized")

        # Add signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C signal to stop the bot and save data."""
        self.logging.info("Ctrl+C detected. Stopping bot and saving data...")
        self.running = False

        # Stop the learner if it exists
        if hasattr(self, 'learner'):
            self.learner.stop_capturing()  # Stop the learner and save data

        # Forcefully terminate the program
        os._exit(0)  # Use os._exit(0) to ensure the program terminates immediately

    def run(self):
        self.logging.info("Running")
        if self.EXPLORE_MODE:
            self.interface.focus_application()  # Focus the target application
            
            # Initialize the learner based on the mode
            if self.EXPLORE_MANUAL_MODE:
                self.learner = LearningPathManually(map_name=self.EXPLORE_MAP, movement=self.movement)
            else:
                self.learner = LearningPathAutomatically(map_name=self.EXPLORE_MAP, movement=self.movement, interface=self.interface)

            # Initialize the grid
            grid = Grid(memory=self.memory, learner=self.learner)

            # Start the capture thread
            capture_thread = threading.Thread(target=self.learner.start_capturing)
            capture_thread.daemon = True  # Daemonize the thread to exit when the main thread exits
            capture_thread.start()

            try:
                # Run the grid
                grid.run()
            except KeyboardInterrupt:
                print("Saving data before exit...")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                # Ensure the learner stops capturing and the thread is joined
                self.learner.stop_capturing()
                if capture_thread.is_alive():
                    capture_thread.join()
                
                # Destroy the grid window if it exists
                if grid.root:
                    grid.root.destroy()

        else:
            count = 1
            while self.running:
                try:
                    if not self.running:
                        return
                    self.interface.focus_application()
                    # Primera inicialización
                    if self.first_time:
                        self.first_time = False
                        self.logging.info("1. Read stats")
                        self.read_all_stats()
                        self.logging.info("2. Assign attributes")
                        self.distribute_attributes()
                        
                        self.logging.info("3. Show last stats after add attributes")
                        self.read_all_stats()
                    else:
                        self.logging.info("1. Lets go to kill some mobs")
                        self.movement.check_abrupt_movements()
                        self.lets_kill_some_mobs()
                        self.logging.info(f"2. Wait {self.config.file['check_interval']} seconds until check and add stats")
                        time.sleep(self.config.file['check_interval'])
                        if count == 10:
                            self.read_all_stats()
                            self.distribute_attributes()
                            count = 1
                        else:
                            count += 1
                        time.sleep(2)
                except KeyboardInterrupt:
                    self.logging.info("Bot stopped by user")
                    break
                except Exception as e:
                    self.logging.error(f"Error in main loop: {e}")
                    time.sleep(1)
    
    def distribute_attributes(self):
        """Distribuye puntos de atributos disponibles según la configuración."""
        if self.SKIP_ATTRIBUTES == True:
            return
        try:
            # First read all stats
            current_state = self.config.get_game_state()

            # Check if we have read stats correctly and that available_points exists and is not None
            available_points = current_state.get('available_points')
            if available_points is None:
                self.logging.error("No available points value found in game state")
                return False
                
            # Convert to integer if not already
            try:
                available_points = int(available_points)
            except (TypeError, ValueError):
                self.logging.error(f"Invalid available points value: {available_points}")
                return False

            if available_points <= 0:
                self.logging.info("No points available to distribute")
                return False

            self.logging.info(f"Starting distribution of {available_points} available points")
            self.logging.info(f"Stat distribution config: {self.config.file['stat_distribution']}")
            
            # Process each attribute individually with defensive programming
            for attribute, ratio in self.config.file['stat_distribution'].items():
                try:
                    # Ensure ratio is a number
                    if ratio is None:
                        self.logging.info(f"Skipping {attribute} - ratio is None")
                        continue
                        
                    # Convert to float if not already
                    try:
                        ratio = float(ratio)
                    except (TypeError, ValueError):
                        self.logging.error(f"Invalid ratio for {attribute}: {ratio}")
                        continue
                    
                    points_to_allocate = int(available_points * ratio)
                    if points_to_allocate <= 0:
                        self.logging.info(f"Skipping {attribute} - no points to allocate (ratio: {ratio})")
                    else:
                        self.interface.command_add_attributes(attribute=attribute, points=points_to_allocate)
                        self.logging.info(f"Allocating {points_to_allocate} points to {attribute}")
                except Exception as e:
                    self.logging.error(f"Error distributing points for {attribute}: {e}")

        except Exception as e:
            self.logging.error(f"Error in distribute_attributes: {e}")

        # Read stats again after distribution
        self.logging.info("Distribution complete, reading final stats")
        
        return True

    def get_value_based_on_memory_address(self, address):
        points = None
        if address:
            try:
                value = self.memory.get_value_of_memory(address)
                if value is not None:
                    points = value
                    self.logging.info(f"Successfully read value {value}")
                else:
                    self.logging.info("Failed to read value, clearing address")
                    address = None
            except Exception as e:
                self.logging.info(f"Error reading memory: {str(e)}")
                address = None
        return points

    def get_attribute_points(self, current_state, attr, attr_spanish, memory_attr_name, find_memory_method, get_coords_method, get_points_method, set_coords_method):
        self.logging.info(f"memory address => {getattr(self.memory, memory_attr_name, None)}")
        try:
            if not getattr(self.memory, memory_attr_name, None):
                # Get the attribute coordinates
                coords_attr = get_coords_method(current_state)
                if len(coords_attr) == 0:
                    coords_attr = self.interface.get_text_from_screen(attr_spanish)

                # Save the attribute reference
                set_coords_method(coords_attr)

                # Get the points using OCR
                points = get_points_method(coords_attr)
                self.logging.info(f"current value => {points}")

                # Only proceed with memory scan if we have a valid value
                if points and points > 0:
                    memory_attr_addr = find_memory_method(points)

                    # Verify we found exactly one match
                    if memory_attr_addr and len(memory_attr_addr) == 1:
                        # Verify the address is stable
                        self.logging.debug("Inside memory_attr_addr")
                        if self.memory.verify_address(memory_attr_addr[0]):
                            self.memory.set_memory_addr_attr(attr, memory_attr_addr[0])
                            self.logging.info(f"Set memory address to: 0x{memory_attr_addr[0]:X}")
                    else:
                        self.logging.debug("Inside else of memory_attr_addr")
                        while memory_attr_addr and len(memory_attr_addr) != 1:
                            if(attr == "available_points"):
                                # choise a random attribute like agility
                                self.interface.command_add_attributes(attribute="agility", points=1)
                                memory_attr_addr = self.memory.another_scan(memory_attr_addr, points - 1)
                            else:
                                self.interface.command_add_attributes(attribute=attr, points=1)
                                memory_attr_addr = self.memory.another_scan(memory_attr_addr, points + 1)
                            time.sleep(1)
                        if self.memory.verify_address(memory_attr_addr[0]):
                            self.memory.set_memory_addr_attr(attr, memory_attr_addr[0])
                            self.logging.info(f"Set memory address to: 0x{memory_attr_addr[0]:X}")

            
            return self.get_value_based_on_memory_address(getattr(self.memory, memory_attr_name, None))
        except Exception as e:
            self.logging.error(f"Error reading {attr} points: {e}")
            return None

    def read_all_stats(self):
        """Read and save all character stats with improved error handling and retry logic"""
        max_retries = 3
        for retry in range(max_retries):
            try:
                if not self.memory.all_memory_is_loaded(self.gameclass.attributes):
                    self.interface.open_stats_window()
                    time.sleep(1)  # Give UI time to update
                
                current_state = self.config.get_game_state()                
                # Read all stats
                stats = {
                    'level': 0,
                    'reset': 0,
                    'strenght': 0,
                    'agility': 0,
                    'vitality': 0,
                    'energy': 0,
                    'command': 0,  # Initialize command for all classes
                    'available_points': 0
                }
                
                # Basic stats
                stats['level'] = self.memory.get_level()
                stats['reset'] = self.memory.get_reset()
                
                # Debug level and reset values
                self.logging.info(f"Current level: {stats['level']}, reset: {stats['reset']}")

                # Always try to read available points
                if self.SKIP_ATTRIBUTES == False:
                    for attempt in range(3):  # Try a few times to read available points
                        stats['available_points'] = self.get_attribute_points(
                            current_state=current_state, 
                            attr="available_points", 
                            attr_spanish="Puntos", 
                            memory_attr_name="available_points_addr", 
                            find_memory_method=self.memory.find_available_points_memory, 
                            get_coords_method=self.interface.get_available_attributes, 
                            get_points_method=self.interface.get_available_points_ocr, 
                            set_coords_method=self.interface.set_available_attributes
                        )
                        
                        if stats['available_points'] is not None:
                            break
                        
                        # Try reopening stats window if we couldn't read points
                        self.logging.warning(f"Failed to read available points, attempt {attempt+1}/3")
                        self.interface.escape()
                        time.sleep(0.5)
                        self.interface.open_stats_window()
                        time.sleep(1)
                            
                # Attributes
                if self.SKIP_ATTRIBUTES == False:
                    for attr in self.gameclass.attributes:
                        if attr == 'strenght':
                            stats[attr] = self.get_attribute_points(current_state, attr, "Fuerza", "strenght_addr", self.memory.find_str_memory, lambda state: self.interface.get_attribute_reference(state, attr), lambda coords: self.interface.get_attr_ocr(coords, attr), lambda coords: self.interface.set_attribute_reference("strenght", coords))
                        if attr == 'agility':
                            stats[attr] = self.get_attribute_points(current_state, attr, "Agilidad", "agility_addr", self.memory.find_agi_memory, lambda state: self.interface.get_attribute_reference(state, attr), lambda coords: self.interface.get_attr_ocr(coords, attr), lambda coords: self.interface.set_attribute_reference("agility", coords))
                        if attr == 'vitality':
                            stats[attr] = self.get_attribute_points(current_state, attr, "Vitalidad", "vitality_addr", self.memory.find_vit_memory, lambda state: self.interface.get_attribute_reference(state, attr), lambda coords: self.interface.get_attr_ocr(coords, attr), lambda coords: self.interface.set_attribute_reference("vitality", coords))
                        if attr == 'energy':
                            stats[attr] = self.get_attribute_points(current_state, attr, "Energía", "energy_addr", self.memory.find_ene_memory, lambda state: self.interface.get_attribute_reference(state, attr), lambda coords: self.interface.get_attr_ocr(coords, attr), lambda coords: self.interface.set_attribute_reference("energy", coords))
                        if attr == 'command':
                            stats[attr] = self.get_attribute_points(current_state, attr, "Comando", "command_addr", self.memory.find_com_memory, lambda state: self.interface.get_attribute_reference(state, attr), lambda coords: self.interface.get_attr_ocr(coords, attr), lambda coords: self.interface.set_attribute_reference("command", coords))                  
            
                # Make sure to set a default of 0 for available_points if it's None
                if stats['available_points'] is None:
                    self.logging.warning("Setting available_points to 0 as fallback")
                    stats['available_points'] = 0

                # Update state
                state = {
                    'current_level': stats['level'],
                    'current_reset': stats['reset'],
                    'current_strenght': stats['strenght'],
                    'current_agility': stats['agility'],
                    'current_vitality': stats['vitality'],
                    'current_energy': stats['energy'],
                    'current_command': stats['command'],
                    'available_points': stats['available_points']
                }
                
                self.logging.info("Final stats:")
                self.logging.info(f"Available Points: {state['available_points']}")
                self.logging.info(f"Strength: {state['current_strenght']}")
                self.logging.info(f"Agility: {state['current_agility']}")
                self.logging.info(f"Vitality: {state['current_vitality']}")
                self.logging.info(f"Energy: {state['current_energy']}")
                self.logging.info(f"Command: {state['current_command']}")

                self.config.update_game_state(state)
                return True

            except Exception as e:
                self.logging.error(f"Error reading stats (attempt {retry+1}/{max_retries}): {e}")
                if retry < max_retries - 1:
                    self.logging.info("Retrying stats reading after error...")
                    self.interface.reload_ui()  # Reset UI between attempts
                    time.sleep(1)
                else:
                    self.logging.error("Failed to read stats after multiple attempts")
                    # Set a minimal default state
                    default_state = {
                        'current_level': self.memory.get_level() or 1,
                        'current_reset': self.memory.get_reset() or 0,
                        'available_points': 0
                    }
                    self.config.update_game_state(default_state)

    def _perform_right_click_fallback(self, duration=3):
        """
        Perform a right-click fallback for the specified duration.
        This can help get unstuck in situations where normal movement fails.
        Delegates to the Movement class implementation.
        
        Args:
            duration: How long to perform right-clicks, in seconds
        """
        try:
            # Use the Movement class implementation
            self.movement.perform_right_click_fallback(duration=duration)
            
        except Exception as e:
            self.logging.error(f"Error during right-click fallback: {e}")

    def check_and_click_play(self, x, y):
        """Check play button and update location state with increased tolerance"""
        try:
            self.movement.get_current_coords_from_game()
            current_state = self.config.get_game_state()
            current_x, currenty_y = self.interface.get_current_coords(current_state=current_state)
            mu_helper_active = self.interface.get_mu_helper_status(current_state)
            
            # Increased tolerance from 10 to 20 to allow for more flexibility in position
            if abs(current_x - x) <= 20 and abs(currenty_y - y) <= 20 and not mu_helper_active:
                self.interface.start_mu_helper()
                self.interface.set_mu_helper_status(True)
                self.interface.set_current_coords([x, y])
                self.logging.info(f"Play button clicked - was inactive (green). Position: ({current_x}, {currenty_y}), Target: ({x}, {y})")
            elif mu_helper_active:
                self.logging.info("Play already active (red) - skipping click")
            else:
                self.logging.warning(f"Position too far from target. Current: ({current_x}, {currenty_y}), Target: ({x}, {y}), Difference: ({abs(current_x - x)}, {abs(currenty_y - y)})")
                
                # Try right-click fallback if we're too far from target
                self.logging.info("Attempting right-click fallback to reach target...")
                self.movement._perform_right_click_fallback(duration=3)
                
                # Check position again
                self.movement.get_current_coords_from_game()
                current_state = self.config.get_game_state()
                current_x, currenty_y = self.interface.get_current_coords(current_state=current_state)
                
                # Try again with the new position
                if abs(current_x - x) <= 20 and abs(currenty_y - y) <= 20 and not mu_helper_active:
                    self.interface.start_mu_helper()
                    self.interface.set_mu_helper_status(True)
                    self.interface.set_current_coords([x, y])
                    self.logging.info(f"Play button clicked after right-click fallback. Position: ({current_x}, {currenty_y}), Target: ({x}, {y})")

        except Exception as e:
            self.logging.error(f"Error checking play button: {e}")
   
    def reset_character(self):
        """Reset character and manage stats window"""
        self.logging.info("Attempting to reset character...")
        current_state = self.config.get_game_state()
        self.logging.info(f"Current state before reset: {current_state}")

        current_time = time.time()
        if current_time - self.last_reset_time < self.reset_cooldown:
            self.logging.info("Reset is on cooldown. Skipping reset.")
            
            # If we can't reset due to cooldown, start hunting instead
            self.check_level_kill_or_reset(level=current_state.get('current_level', 0), helper=False)
            return False
            
        # Try to reset
        self.interface.command_reset()
        self.last_reset_time = time.time()  # Update the last reset time
        
        # Wait a moment for the reset to complete
        time.sleep(3)
        
        # Update game state with new data
        new_state = self.config.get_game_state()
        new_reset_count = new_state.get('current_reset', 0) + 1
        self.config.update_game_state({
            'current_reset': new_reset_count,
            'current_level': 1,  # Reset always sets level to 1
            'current_map': self.gameclass.start_location  # Ensure this is set to character's start location
        })
        self.logging.info(f"Current state after reset: {self.config.get_game_state()}")

        # Reset memory cache
        self.memory.load_memory_addr_from_file()
        
        # Read new stats and distribute attributes
        self.read_all_stats()
        self.distribute_attributes()
        
        # Start hunting at level 1
        self.check_level_kill_or_reset(level=1, helper=False)
        
        return True

    def lets_kill_some_mobs(self):
        current_state = self.config.get_game_state()
        level = current_state.get('current_level', 0)
        reset = current_state.get('current_reset', 0)
        mu_helper_active = current_state.get('mulheper_active', False)
        
        # Use the adapter to get the reset level based on current reset count
        reset_level = self.gameclass.set_level_to_reset(reset)
        
        # Ensure reset_level has a valid value
        if reset_level is None:
            self.logging.warning("Reset level is None, using default value of 400")
            reset_level = 400  # Default fallback if for some reason reset_level is None
            
        max_level = self.config.file.get('max_level', 400)  # Use default of 400 if not specified

        # Add debug logging
        self.logging.info(f"Current values - Level: {level}, Reset Level: {reset_level}, Max Level: {max_level}, Helper Active: {mu_helper_active}")

        # Check if we're on reset cooldown
        current_time = time.time()
        reset_cooldown_active = (current_time - self.last_reset_time < self.reset_cooldown)
        
        # Reset only if not on cooldown
        if level >= reset_level and reset_level <= max_level and not reset_cooldown_active:
            self.logging.info("Attempting to reset character...")
            self.interface.set_mu_helper_status(False)
            self.reset_character()
        else:
            # Always call check_level_kill_or_reset - it will handle both cases:
            # 1. If helper not active, it will try to reach the position and activate it
            # 2. If already active but in wrong location, it will move to correct spot
            self.check_level_kill_or_reset(level=level, helper=mu_helper_active)
            
            # If we're here, verify helper is active
            if not mu_helper_active:
                # Explicitly check current position vs target position
                current_state = self.config.get_game_state()
                hunting_spot = self.config.get_hunting_spot(
                    reset_count=reset, 
                    current_level=level,
                    character_start_location=self.gameclass.start_location
                )
                
                if hunting_spot:
                    target_x, target_y = hunting_spot["location"]
                    current_x, current_y = self.movement.get_current_coords_from_game()
                    
                    # If we're close enough to target
                    if self.is_at_target_location(current_x, current_y, target_x, target_y, tolerance=20):
                        self.logging.info(f"At correct position ({current_x},{current_y}), activating helper")
                        self.interface.start_mu_helper()
                        self.interface.set_mu_helper_status(True)
                    else:
                        self.logging.warning(f"Not at correct position. Current: ({current_x},{current_y}), Target: ({target_x},{target_y})")
            
    def check_level_kill_or_reset(self, level, helper):
        """
        Determine the appropriate hunting location based on level and move there
        Uses A* pathfinding to navigate through known free spaces
        """
        try:
            # Get current reset
            current_state = self.config.get_game_state()
            reset = current_state.get('current_reset', 0)
            
            # Use the adapter to find the appropriate hunting spot
            hunting_spot = self.config.get_hunting_spot(
                reset_count=reset, 
                current_level=level,
                character_start_location=self.gameclass.start_location
            )
            
            if hunting_spot:
                # Move to the appropriate map
                map_name = hunting_spot["map"]
                location = hunting_spot["location"]
                
                self.logging.info(f"Moving to hunting spot for level {level}: {map_name} at {location}")
                # This call will ensure map_data is loaded with free_spaces
                self.movement.move_to_location(map_name=map_name, do_not_open_stats=True)
                x, y = location
                
                # Explicitly add the target location to free_spaces to ensure pathfinding works
                if self.movement.map_data and 'free_spaces' in self.movement.map_data:
                    self.movement.map_data['free_spaces'].add((x, y))
            else:
                # Fallback to start location if no hunting spot is found
                map_name = self.gameclass.start_location
                x, y = 128, 128  # Default coordinates
                self.logging.warning(f"No suitable hunting spot found for level {level}, using default location: {map_name} at ({x},{y})")
                self.movement.move_to_location(map_name=map_name, do_not_open_stats=True)
            
            # Get current coordinates
            current_x, current_y = self.movement.get_current_coords_from_game()
            
            # Check if we're at the target location - if not, try to navigate there
            # even if the helper is active
            if not self.is_at_target_location(current_x, current_y, x, y, tolerance=10) or not helper:
                self.logging.info(f"Not at target location or helper not active. Current: ({current_x},{current_y}), Target: ({x},{y})")
                
                # Reset movement tracking
                self.movement.last_movements.clear()
                
                # Attempt to walk to the target location using A* pathfinding
                max_attempts = 3
                for attempt in range(max_attempts):
                    self.logging.info(f"Attempt {attempt+1}/{max_attempts} to walk to ({x}, {y}) using A* pathfinding")
                    
                    # Use the walk_to method which implements A* pathfinding through free_spaces
                    reached_zone = self.movement.walk_to(target_x=x, target_y=y)
                    
                    if reached_zone:
                        self.logging.info(f"Successfully reached target: ({x}, {y})")
                        self.check_and_click_play(x, y)
                        break
                    elif attempt < max_attempts - 1:
                        self.logging.warning(f"Failed to reach target with A*, retrying... ({attempt+1}/{max_attempts})")
                        
                        # Try right-click fallback between attempts
                        self.movement.perform_right_click_fallback(duration=3)
                        time.sleep(1)
                    else:
                        self.logging.error(f"Failed to reach target after {max_attempts} attempts")
                        # Try to click play anyway, with higher tolerance
                        current_x, current_y = self.movement.get_current_coords_from_game()
                        if abs(current_x - x) <= 30 and abs(current_y - y) <= 30:
                            self.logging.info("Location is close enough, trying to start MU helper...")
                            self.interface.start_mu_helper()
                            self.interface.set_mu_helper_status(True)
            else:
                self.logging.info(f"Already at target location ({current_x},{current_y}) and helper is active.")
                # Ensure helper is still active by clicking it again
                if not helper:
                    self.interface.start_mu_helper()
                    self.interface.set_mu_helper_status(True)
                
        except Exception as e:
            self.logging.error(f"Error in check_level_kill_or_reset: {e}")
            # Try to start helper anyway if we had an error
            self.interface.start_mu_helper()
            self.interface.set_mu_helper_status(True)

    # Helper method to check if we're at the target location
    def is_at_target_location(self, current_x, current_y, target_x, target_y, tolerance=10):
        """Check if current position is close enough to target position"""
        return abs(current_x - target_x) <= tolerance and abs(current_y - target_y) <= tolerance