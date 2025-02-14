import time
import logging
import os

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
    
    consecutive_errors = 0
    EXPLORE_MAP = "dungeon3"
    EXPLORE_MODE = False
    EXPLORE_MANUAL_MODE = False
    SKIP_ATTRIBUTES = False
    """
    Un bot para automatizar acciones en un juego. Maneja movimientos, estadísticas y atributos del personaje.
    """
    def __init__(self):
        self.config = Configuration()
        setup_logging()
        self.logging = logging.getLogger(__name__)
        self.interface = Interface(self.config)
        self.gameclass = GameClass()
        self.utils = Utils()
        self.memory = Memory()
        self.movement = Movement(interface=self.interface, config=self.config, memory=self.memory)
        
        self.interface.load_ocr_packages()
        
        self.running = True
        self.reference_point = None
        self.first_time = True
        
        self.logging.info("GameBot initialized")
    
    def distribute_attributes(self):
        """Distribuye puntos de atributos disponibles según la configuración."""
        if self.SKIP_ATTRIBUTES == True:
            return
        try:
            # First read all stats
            current_state = self.config.get_game_state()

            # Check if we have read stats correctly
            if (current_state['available_points'] == -1 or
                current_state['current_strenght'] == -1 or
                current_state['current_agility'] == -1 or
                current_state['current_vitality'] == -1 or
                current_state['current_command'] == -1):
                self.logging.error("Stats not properly read, values still at -1")
                return False

            available_points = current_state['available_points']
            if available_points <= 0:
                self.logging.info("No points available to distribute")
                return False

            self.logging.info(f"Starting distribution of {available_points} available points")
            self.logging.info(f"Stat distribution config: {self.config.file['stat_distribution']}")
            
            # Old Way

            for stat, ratio in self.config.file['stat_distribution'].items():
                stat_points = int(available_points * ratio)
                if stat_points <= 0:
                    self.logging.info(f"Skipping {stat} - no points to allocate (ratio: {ratio})")
                else:
                    self.interface.command_add_attributes(attribute=stat, points=stat_points)
                    self.logging.info(f"Allocating {stat_points} points to {stat}")

        except Exception as e:
            self.logging.error(f"Error distributing points for {stat}: {e}")

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
                    if self.memory.verify_address(memory_attr_addr[0]):
                        setattr(self.memory, memory_attr_name, memory_attr_addr[0])
                        self.logging.info(f"Set memory address to: 0x{memory_attr_addr[0]:X}")
                else:
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
                        setattr(self.memory, memory_attr_name, memory_attr_addr[0])
                        self.logging.info(f"Set memory address to: 0x{memory_attr_addr[0]:X}")

        
        return self.get_value_based_on_memory_address(getattr(self.memory, memory_attr_name, None))

    def read_all_stats(self):
        """Read and save all character stats"""
        while True:
            try:
                if not self.memory.all_memory_is_loaded(self.gameclass.attributes):
                    self.interface.open_stats_window()
                
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
                for stat in ['level', 'reset', 'available_points']:

                    if stat == 'level':
                        stats[stat] = self.memory.get_level()
                    if stat == 'reset':
                        stats[stat] = self.memory.get_reset()
                    if self.SKIP_ATTRIBUTES == False:
                        if stat == 'available_points':
                            stats[stat] = self.get_attribute_points(current_state=current_state, attr="available_points", attr_spanish="Puntos", memory_attr_name="available_points_addr", find_memory_method=self.memory.find_available_points_memory, get_coords_method=self.interface.get_available_attributes, get_points_method=self.interface.get_available_points_ocr, set_coords_method=self.interface.set_available_attributes)
                                
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
                
                # Update state
                state = {
                    ''
                    'current_level': stats['level'],
                    'current_reset': stats['reset'],
                    'current_strenght': stats['strenght'],
                    'current_agility': stats['agility'],
                    'current_vitality': stats['vitality'],
                    'current_energy': stats['energy'],
                    'current_command': stats['command'],
                    'available_points': stats['available_points']
                }
                self.config.update_game_state(state)
                
                self.logging.info("Final stats:")
                self.logging.info(f"Available Points: {state['available_points']}")
                self.logging.info(f"Strength: {state['current_strenght']}")
                self.logging.info(f"Agility: {state['current_agility']}")
                self.logging.info(f"Vitality: {state['current_vitality']}")
                self.logging.info(f"Energy: {state['current_energy']}")
                self.logging.info(f"Command: {state['current_command']}")
                return stats['level'], stats['reset']

            except Exception as e:
                self.logging.error(f"Error reading stats: {e}")
                time.sleep(1)
                continue

    def check_level_kill_or_reset(self, level, helper):
        for threshold, obj in sorted(self.config.file['level_thresholds'].items(), key=lambda x: int(x[0]), reverse=True):
            if level >= int(threshold):
                if isinstance(obj, list):
                    location_obj = next((loc for loc in obj if loc["map"] == self.gameclass.start_location), obj[0])
                    self.movement.move_to_location(map_name=location_obj["map"], do_not_open_stats=True)
                    x = location_obj["location"][0]
                    y = location_obj["location"][1]
                else:
                    # Handle single location case as before
                    self.movement.move_to_location(map_name=obj["map"], do_not_open_stats=True)
                    x = obj["location"][0]
                    y = obj["location"][1]
                
                # Break the loop after moving to the first valid location
                break
        if not helper:
            self.movement.walk_to(target_x=x, target_y=y)
            self.check_and_click_play(x, y)

    def abrupt_coordinates_change(self):
        abrupt_change = self.movement.check_abrupt_movements()
        if abrupt_change:
            self.logging.info("Coordinates abrupt changed")
            current_state = self.config.get_game_state()
            self.movement.move_to_location(map_name=current_state['current_map'], avoid_checks=True, do_not_open_stats=True)
        
    def lets_kill_some_mobs(self):
        current_state = self.config.get_game_state()
        level = self.interface.get_level(current_state)
        reset = self.interface.get_reset(current_state)
        mu_helper_active = self.interface.get_mu_helper_status(current_state)
        
        reset_level = self.gameclass.set_level_to_reset(reset)
        max_level = self.config.file['max_level']

        # Add debug logging
        self.logging.info(f"Current values - Level: {level}, Reset Level: {reset_level}, Max Level: {max_level}")

        # Reset
        if level >= reset_level and reset_level <= max_level:
            self.logging.info("Attempting to reset character...")
            self.interface.set_mu_helper_status(False)
            self.reset_character()
        # No esta farmeando
        elif not mu_helper_active and level < max_level:
            self.check_level_kill_or_reset(level=level, helper=mu_helper_active)
        # Ponete a farmear
        elif mu_helper_active:
            self.check_level_kill_or_reset(level=level, helper=mu_helper_active)
    
    def check_and_click_play(self, x, y):
        """Check play button and update location state"""
        try:
            self.movement.get_current_coords_from_game()
            current_state = self.config.get_game_state()
            current_x, currenty_y = self.interface.get_current_coords(current_state=current_state)
            mu_helper_active = self.interface.get_mu_helper_status(current_state)
            
            if abs(current_x - x) <= 10 and abs(currenty_y - y) <= 10 and not mu_helper_active:
                #self.interface.mouse_click(play_coords[0] + 5, play_coords[1] + 3)
                self.interface.start_mu_helper()
                self.interface.set_mu_helper_status(True)
                self.interface.set_current_coords([x, y])
                self.logging.info("Play button clicked - was inactive (green)")
            elif mu_helper_active:
                self.logging.info("Play already active (red) - skipping click")

        except Exception as e:
            self.logging.error(f"Error checking play button: {e}")

    def reset_character(self):
        """Reset character and manage stats window"""
        #self.interface.open_stats_window()
        self.interface.command_reset()
        #self.interface.open_stats_window()

        current_state = self.config.get_game_state()
        new_reset = current_state['current_reset'] + 1
        self.config.update_game_state({
            'current_reset': new_reset,
            'current_level': 0,
            'current_map': self.gameclass.start_location
        })
        #self.interface.scroll(random_number=False, number=-10000, scroll_count=50)
        self.distribute_attributes()

    def run(self):
        """Ejecuta el bucle principal del bot"""
        
        if self.EXPLORE_MODE:
            self.interface.focus_application()            
            # Create grid object
            grid = Grid(memory=self.memory)
            
            # Create learner before starting grid
            if self.EXPLORE_MANUAL_MODE:
                learner = LearningPathManually(map_name=self.EXPLORE_MAP, movement=self.movement)   
            else:
                learner = LearningPathAutomatically(map_name=self.EXPLORE_MAP, movement=self.movement, interface=self.interface)

            try:
                # Start capturing in a separate thread
                import threading
                capture_thread = threading.Thread(target=learner.start_capturing)
                capture_thread.daemon = True
                capture_thread.start()
                
                # Run grid
                grid.run()
                
            except KeyboardInterrupt:
                print("Saving data before exit...")
                
                # Stop the learner
                learner.stop_capturing()

                
            finally:
                if grid.root:
                    grid.root.destroy()

        else:
            while self.running:
                try:
                    if not self.running:
                        return
                    self.interface.focus_application()
                    # Primera inicialización
                    if self.first_time:
                        #self.interface.scroll(random_number=False, number=-10000, scroll_count=50)
                        self.first_time = False
                        self.logging.info("1. Read stats")
                        self.read_all_stats()
                        self.logging.info("2. Assign attributes")
                        self.distribute_attributes()
                        
                        self.logging.info("3. Show last stats after add attributes")
                        self.read_all_stats()
                    else:
                        self.logging.info("1. Lets go to kill some mobs")
                        self.lets_kill_some_mobs()
                        self.logging.info(f"2. Wait {self.config.file['check_interval']} seconds until check and add stats")
                        time.sleep(self.config.file['check_interval'])
                        self.read_all_stats()
                        self.distribute_attributes()
                except KeyboardInterrupt:
                    self.logging.info("Bot stopped by user")
                    break
                except Exception as e:
                    self.logging.error(f"Error in main loop: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    bot = GameBot()
    time.sleep(2)
    bot.run()