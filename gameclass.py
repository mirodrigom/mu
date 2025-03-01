import logging
from config import Configuration

class GameClass:
    name = None
    start_location = None
    logging = None
    config = None
    attributes = ['strenght', 'agility', 'vitality', 'energy']

    def __init__(self):
        self.config = Configuration()
        self.logging = logging.getLogger(__name__)
        self.build_character_profile()

    def build_character_profile(self):
        self.set_class()

        if self.name == "Magic Gladiator":
            self.start_location = "lorencia"
        elif self.name == "Dark Wizard":
            self.start_location = "lorencia"
        elif self.name == "Dark Knight":
            self.start_location = "lorencia"
        elif self.name == "Fairy Elf":
            self.start_location = "noria"
        elif self.name == "Dark Lord":
            self.start_location = "lorencia"
            # Ensure 'command' is included for Dark Lord
            if 'command' not in self.attributes:
                self.attributes.append('command')
        elif self.name == "Summoner":
            self.start_location = "elbeland"
        elif self.name == "Rage Fighter":
            self.start_location = "lorencia"
        elif self.name == "Grow Lancer":
            self.start_location = "lorencia"
        elif self.name == "Slayer":
            self.start_location = "lorencia"
        elif self.name == "Rune Mage":
            self.start_location = "noria"

        # Check if we have starting_locations in config (new format)
        if 'starting_locations' in self.config.file and self.start_location in self.config.file['starting_locations']:
            starting_location = self.config.file['starting_locations'][self.start_location]
            self.logging.info(f"Using custom starting location for {self.name} from config")
        else:
            # Use default start location
            starting_location = None

        self.logging.info("===================")
        self.logging.info(f"You are a {self.name} who born in {self.start_location} with these base attributes {self.attributes}")
        self.logging.info("===================")
        
    def set_class(self):
        self.name = self.config.get_class()

    def set_level_to_reset(self, reset):
        """
        Determine the level at which the character should reset based on the reset count.
        Uses config.get_reset_level for new config format, or falls back to original logic.
        Ensures a valid reset level is always returned.
        """
        try:
            # Use the config's get_reset_level method which handles both old and new formats
            level_to_reset = self.config.get_reset_level(reset)
            
            # Ensure level_to_reset is a valid number
            if level_to_reset is None:
                self.logging.warning(f"Reset level is None for reset count {reset}, using default of 400")
                level_to_reset = 400
            
            self.logging.info(f"This character will reset at level: {level_to_reset} / Number of resets {reset}")
            return level_to_reset
        except Exception as e:
            self.logging.error(f"Error determining reset level: {e}")
            # Safe fallback if anything goes wrong
            return 400