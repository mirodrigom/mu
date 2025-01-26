import logging
import os

class Utils:
    
    def __init__(self):
        self.logging = logging.getLogger(__name__)

    def get_relative_coords(self, base_coords, ref_point):
        """
        Calcula coordenadas relativas a un punto de referencia.
        Args:
            base_coords: Coordenadas base
            ref_point: Punto de referencia
        Returns:
            list: Coordenadas ajustadas
        """
        '''
        self.logging.debug(f"Base coords: {base_coords}")
        self.logging.debug(f"Reference point: {ref_point}")
        
        self.logging.debug(f"1. {base_coords[0]} + {ref_point[0]} = {base_coords[0] + ref_point[0]}")
        self.logging.debug(f"2. {base_coords[1]} + {ref_point[1]} = {base_coords[1] + ref_point[1]}")
        self.logging.debug(f"3. {base_coords[2]} + {ref_point[0]} = {base_coords[2] + ref_point[0]}")
        self.logging.debug(f"4. {base_coords[3]} + {ref_point[1]} = {base_coords[3] + ref_point[1]}")
        '''
        try:
            return [
                base_coords[0] + ref_point[0],
                base_coords[1] + ref_point[1],
                base_coords[2] + ref_point[0],
                base_coords[3] + ref_point[1]
            ]
        except Exception as e:
            self.logging.error(f"{e}: It seems that your coordinates sucks.")
        
    def extract_numeric_value(self, text):
        """Enhanced numeric value extraction"""
        try:
            # Clean the text
            cleaned = ''.join(filter(str.isdigit, text.strip()))
            if not cleaned:
                return 0

            # Handle common OCR mistakes
            if len(cleaned) > 4:  # Stats shouldn't be more than 4 digits
                cleaned = cleaned[:4]

            value = int(cleaned)

            # Validate reasonable ranges
            if value > 9999:
                return 0

            return value
        except ValueError:
            return 0
    
    def clean_stats_command(self, command):
        splitted_command = command.split(",")
        filtered_stats = []
        
        for stat in splitted_command:
            point = stat.strip().split(" ")[1]
            if point != '0':
                filtered_stats.append(stat.strip())
        result = ', '.join(filtered_stats)
        return result