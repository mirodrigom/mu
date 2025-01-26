import logging

class Utils:
    
    def __init__(self):
        self.logging = logging.getLogger(__name__)

    def is_valid_coordinate(self, coordinate_str: str) -> bool:
        """
        Verifica si una cadena representa coordenadas válidas.
        Args:
            coordinate_str: Cadena de coordenadas a validar
        Returns:
            bool: True si es válida, False si no
        """
        try:
            parts = coordinate_str.strip().split(',')
            if len(parts) != 2:
                return False
            return all(part.strip().isdigit() for part in parts)
        except:
            return False
        
    def fix_7_digit_coordinate(self, coord_str: str) -> str:
        """
        Corrige coordenadas de 7 dígitos eliminando el dígito del medio.
        Args:
            coord_str: Coordenada de 7 dígitos
        Returns:
            str: Coordenada corregida de 6 dígitos
        """
        if len(coord_str) != 7:
            return coord_str
        return coord_str[:3] + coord_str[4:]

    def process_coordinates(self, coord_str: str) -> tuple[int, int]:
        """
        Procesa una cadena de coordenadas en una tupla (x,y).
        Args:
            coord_str: Cadena de coordenadas
        Returns:
            tuple: Coordenadas (x,y) o None si son inválidas
        """
        # Clean the string
        coord_str = ''.join(filter(str.isdigit, coord_str))

        # Handle 7-digit case
        if len(coord_str) == 7:
            coord_str = self.fix_7_digit_coordinate(coord_str)

        # Extract coordinates
        if len(coord_str) == 6:
            return int(coord_str[:3]), int(coord_str[3:])

        return None

    def get_relative_coords(self, base_coords, ref_point):
        """
        Calcula coordenadas relativas a un punto de referencia.
        Args:
            base_coords: Coordenadas base
            ref_point: Punto de referencia
        Returns:
            list: Coordenadas ajustadas
        """
        return [
            base_coords[0] + ref_point[0],
            base_coords[1] + ref_point[1],
            base_coords[2] + ref_point[0],
            base_coords[3] + ref_point[1]
        ]
        
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