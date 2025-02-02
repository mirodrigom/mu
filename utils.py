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
        
    def clean_coordinates(self,coord_str):
        try:
            # Split the string by comma
            x_str, y_str = coord_str.split(',')
            
            # If x is more than 3 digits, remove first digit(s)
            if len(x_str) > 3:
                x_str = x_str[-3:]
                
            # Convert to integers
            x = int(x_str.strip())
            y = int(y_str.strip())
            
            return x, y
        except Exception as e:
            print(f"Error parsing coordinates: {e}")
            return None, None