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
            self.attributes = self.attributes.append('command')
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

        self.logging.info("===================")
        self.logging.info(f"You are a {self.name} who born in {self.start_location} with this base attributes {self.attributes}")
        self.logging.info("===================")
        
    def set_class(self):
        name = self.config.get_class()

    def set_level_to_reset(self, reset):
        if reset == 0:
            level_to_reset = 350
        elif reset > 0 and reset <= 5:
            level_to_reset = 360
        elif reset > 5 and reset <= 15:
            level_to_reset = 370
        elif reset > 15 and reset <= 25:
            level_to_reset = 380
        elif reset > 25 and reset <= 50:
            level_to_reset = 390
        elif reset > 50:
            level_to_reset = 400

        self.logging.info(f"This character will reset at level: {level_to_reset} / Number of resets {reset}")
        return level_to_reset

    
    