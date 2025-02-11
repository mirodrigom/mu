from tkinter import *
from memory import Memory

class Grid:

    #148 queda muy bien
    def __init__(self, memory, screen_width=1920, screen_height=1080, cell_size=210):
        self.memory = memory
        self.width = screen_width
        self.height = screen_height
        self.cell_size = cell_size
        self.cols = self.width // cell_size
        self.rows = self.height // cell_size
        
        # Calculate center indices
        # Calculate center indices
        self.center_col = (self.width // (2 * cell_size))  # Added +1 to adjust center
        self.center_row = (self.height // (2 * cell_size))  # Added +1 to adjust center
        
        # Create window
        self.root = Tk()
        self.root.attributes('-alpha', 0.7)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Create canvas
        self.canvas = Canvas(
            self.root, 
            width=screen_width, 
            height=screen_height, 
            bg='white',
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Make window transparent
        self.root.wm_attributes('-transparentcolor', 'white')
        
        # Store text items and their background rectangles in a dictionary
        self.coordinate_texts = {}
        self.text_backgrounds = {}
        
        # Initial coordinates
        self.current_x = 0
        self.current_y = 0
        
        # Draw initial grid
        self.draw_grid()
        self.update_coordinates(0, 0)  # Start at (0,0)
        
    def draw_grid(self):
        # Draw vertical and horizontal lines
        for x in range(0, self.width, self.cell_size):
            self.canvas.create_line(x, 0, x, self.height, fill='#A0A0A0', dash=(4,4))
        for y in range(0, self.height, self.cell_size):
            self.canvas.create_line(0, y, self.width, y, fill='#A0A0A0', dash=(4,4))
        
        # Define the cells to be made [''''''=/'''''']
        green_cells = [
            (self.center_col, self.center_row),  # Center cell
            #(self.center_col -1, self.center_row),  # Right cell
            #(self.center_col, self.center_row - 1),  # Left cell
            #(self.center_col -1,  self.center_row -1)   # Bottom cell
        ]
        
        # Create green squares for the specified cells
        for col, row in green_cells:
            x = col * self.cell_size
            y = row * self.cell_size
            self.canvas.create_rectangle(
                x, y,
                x + self.cell_size, y + self.cell_size,
                fill='#00FF00',
                outline='#008000'
            )
        
        # Create text items for each cell
        for col in range(self.cols):
            for row in range(self.rows):
                x = col * self.cell_size + self.cell_size/2
                y = row * self.cell_size + self.cell_size/2
                # Create background rectangle first
                bg_rect = self.canvas.create_rectangle(
                    0, 0, 0, 0,  # Initial size, will be updated
                    fill='yellow' if (col != self.center_col or row != self.center_row) else '#00FF00',
                    outline=''
                )
                # Create text item
                text_item = self.canvas.create_text(
                    x, y,
                    text="",
                    fill='black'
                )
                # Store text and background rectangle
                self.coordinate_texts[(col, row)] = text_item
                self.text_backgrounds[(col, row)] = bg_rect

    def update_coordinates(self, base_x, base_y):
        """Update all coordinates relative to the center position"""
        self.current_x = base_x
        self.current_y = base_y
        
        # Draw center coordinates bigger and bolder
        center_text = self.coordinate_texts.get((self.center_col, self.center_row))
        center_bg = self.text_backgrounds.get((self.center_col, self.center_row))
        if center_text:
            self.canvas.itemconfig(
                center_text,
                text=f"({base_x}, {base_y})",
                font=('Arial', 12, 'bold'),
                fill='black'  # Ensure center is black
            )
            # Update the background rectangle for the center text
            bbox = self.canvas.bbox(center_text)
            if bbox:
                self.canvas.coords(center_bg, bbox)
        
        # Update all other cells with relative coordinates
        for col in range(self.cols):
            for row in range(self.rows):
                # Skip center as it's already updated
                if col == self.center_col and row == self.center_row:
                    continue
                    
                # Calculate relative coordinates
                rel_x = base_x + (col - self.center_col)
                rel_y = base_y + (self.center_row - row)
                
                text_item = self.coordinate_texts.get((col, row))
                bg_rect = self.text_backgrounds.get((col, row))
                if text_item:
                    self.canvas.itemconfig(
                        text_item,
                        text=f"({rel_x}, {rel_y})",
                        font=('Arial', 10),  # Slightly bigger font
                        fill='#000000'  # Pure black color for better visibility
                    )
                    # Update the background rectangle for the text
                    bbox = self.canvas.bbox(text_item)
                    if bbox:
                        self.canvas.coords(bg_rect, bbox)
                    
    def check_coordinates(self):
        """Check coordinates using the provided method"""
        try:
            x, y = self.memory.get_coordinates()
            self.update_coordinates(x, y)
        except:
            print("Error getting coordinates")
    
    def run(self):
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        
        # Update coordinates periodically
        def update_loop():
            self.check_coordinates()
            self.root.after(50, update_loop)  # Check every 100ms
        
        update_loop()
        self.root.mainloop()


# Create and run the grid
