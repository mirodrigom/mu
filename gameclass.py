from config import Config

class GameClass:
    name = None
    start_location = None
    logging = None
    config = None

    def __init__(self):
        self.config = Configuration()
        self.logging = logging.getLogger(__name__)
        self.build_character_profile()

    def build_character_profile():
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
        self.logging.info(f"You are a {self.name} who born in {self.start_location}")
        self.logging.info("===================")

    def 
        
    def set_class(self):
        name = self.config.get_class()

    
    