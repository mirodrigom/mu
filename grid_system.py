from tkinter import *
from typing import Set, Tuple

class Grid:
    def __init__(self, memory, learner, screen_width=1920, screen_height=1080, cell_size=210):
        """
        Initialize the grid overlay.
        
        :param memory: Memory object for retrieving current coordinates.
        :param learner: LearningPathManually instance for managing recorded coordinates.
        :param screen_width: Width of the grid in pixels.
        :param screen_height: Height of the grid in pixels.
        :param cell_size: Size of each grid cell in pixels.
        """
        self.memory = memory
        self.learner = learner  # Instance of LearningPathManually
        self.width = screen_width
        self.height = screen_height
        self.cell_size = cell_size
        self.cols = self.width // cell_size
        self.rows = self.height // cell_size
        self.center_col = (self.width // (2 * cell_size))
        self.center_row = (self.height // (2 * cell_size))
        
        # Initialize Tkinter root and canvas
        self.root = Tk()
        self.root.attributes('-alpha', 0.7)  # Set transparency
        self.root.attributes('-topmost', True)  # Keep window on top
        self.root.overrideredirect(True)  # Remove window borders
        
        self.canvas = Canvas(
            self.root, 
            width=screen_width, 
            height=screen_height, 
            bg='white',
            highlightthickness=0
        )
        self.canvas.pack()
        
        self.root.wm_attributes('-transparentcolor', 'white')  # Make white background transparent
        
        # Store text items and background rectangles for each cell
        self.coordinate_texts = {}
        self.text_backgrounds = {}
        
        # Initialize current position
        self.current_x = 0
        self.current_y = 0
        
        # Draw the grid and update coordinates
        self.draw_grid()
        self.update_coordinates(0, 0)
        
        # Load recorded coordinates at startup
        self.load_recorded_coordinates()

    def draw_grid(self):
        """Draw the grid lines and initialize cell texts and backgrounds."""
        for x in range(0, self.width, self.cell_size):
            self.canvas.create_line(x, 0, x, self.height, fill='#A0A0A0', dash=(4, 4))
        for y in range(0, self.height, self.cell_size):
            self.canvas.create_line(0, y, self.width, y, fill='#A0A0A0', dash=(4, 4))
        
        # Highlight the center cell in green
        green_cells = [(self.center_col, self.center_row)]  # Center cell
        
        for col, row in green_cells:
            x = col * self.cell_size
            y = row * self.cell_size
            self.canvas.create_rectangle(
                x, y,
                x + self.cell_size, y + self.cell_size,
                fill='#00FF00',
                outline='#008000'
            )
        
        # Create text items and background rectangles for all cells
        for col in range(self.cols):
            for row in range(self.rows):
                x = col * self.cell_size + self.cell_size / 2
                y = row * self.cell_size + self.cell_size / 2
                
                # Background rectangle for text
                bg_rect = self.canvas.create_rectangle(
                    0, 0, 0, 0,
                    fill='yellow',  # Default color for unrecorded cells
                    outline=''
                )
                
                # Text item for coordinates
                text_item = self.canvas.create_text(
                    x, y,
                    text="",
                    fill='black'
                )
                
                # Store references to text and background
                self.coordinate_texts[(col, row)] = text_item
                self.text_backgrounds[(col, row)] = bg_rect

    def update_coordinates(self, base_x, base_y):
        """Update the coordinate labels for all cells based on the current position."""
        self.current_x = base_x
        self.current_y = base_y
        
        # Update the center cell's text
        center_text = self.coordinate_texts.get((self.center_col, self.center_row))
        center_bg = self.text_backgrounds.get((self.center_col, self.center_row))
        if center_text:
            self.canvas.itemconfig(
                center_text,
                text=f"({base_x}, {base_y})",
                font=('Arial', 12, 'bold'),
                fill='black'
            )
            bbox = self.canvas.bbox(center_text)
            if bbox:
                self.canvas.coords(center_bg, bbox)
        
        # Update all other cells' texts
        for col in range(self.cols):
            for row in range(self.rows):
                if col == self.center_col and row == self.center_row:
                    continue
                
                rel_x = base_x + (col - self.center_col)
                rel_y = base_y + (self.center_row - row)
                
                text_item = self.coordinate_texts.get((col, row))
                bg_rect = self.text_backgrounds.get((col, row))
                if text_item:
                    self.canvas.itemconfig(
                        text_item,
                        text=f"({rel_x}, {rel_y})",
                        font=('Arial', 10),
                        fill='#000000'
                    )
                    bbox = self.canvas.bbox(text_item)
                    if bbox:
                        self.canvas.coords(bg_rect, bbox)

    def update_background_colors(self, recorded_coords: Set[Tuple[int, int]]):
        """Update the background color of cells based on recorded coordinates."""
        for col in range(self.cols):
            for row in range(self.rows):
                rel_x = self.current_x + (col - self.center_col)
                rel_y = self.current_y + (self.center_row - row)
                
                bg_rect = self.text_backgrounds.get((col, row))
                if bg_rect:
                    if (rel_x, rel_y) in recorded_coords:
                        self.canvas.itemconfig(bg_rect, fill='#00FF00')  # Change to green
                    else:
                        self.canvas.itemconfig(bg_rect, fill='yellow')  # Reset to yellow

    def load_recorded_coordinates(self):
        """Load recorded coordinates from the learner and update the grid."""
        if hasattr(self, 'learner'):
            recorded_coords = self.learner.get_recorded_coords()
            print(f"Loaded recorded coordinates: {recorded_coords}")  # Debug log
            self.update_background_colors(recorded_coords)

    def check_surrounding_coordinates(self, recorded_coords: Set[Tuple[int, int]]):
        """Check if surrounding coordinates have been discovered."""
        surrounding_coords = [
            (self.current_x + dx, self.current_y + dy)
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            if not (dx == 0 and dy == 0)
        ]
        
        for coord in surrounding_coords:
            if coord in recorded_coords:
                print(f"Coordinate {coord} has been discovered.")
            else:
                print(f"Coordinate {coord} has not been discovered.")

    def check_coordinates(self):
        """Check and update the current coordinates from memory."""
        try:
            x, y = self.memory.get_coordinates()
            self.update_coordinates(x, y)
        except Exception as e:
            print(f"Error getting coordinates: {e}")

    def run(self):
        """Start the main loop for the grid application."""
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        self.root.bind('<Escape>', lambda e: self.root.destroy())  # Exit on Escape key
        
        def update_loop():
            """Continuous update loop for the grid."""
            self.check_coordinates()
            
            # Update background colors based on recorded coordinates
            if hasattr(self, 'learner'):
                recorded_coords = self.learner.get_recorded_coords()
                self.update_background_colors(recorded_coords)
                self.check_surrounding_coordinates(recorded_coords)
            
            self.root.after(50, update_loop)  # Schedule next update
        
        update_loop()  # Start the update loop
        self.root.mainloop()  # Start the Tkinter event loop