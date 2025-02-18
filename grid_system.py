from tkinter import Tk, Canvas
import threading
import logging
import queue

class Grid:
    def __init__(self, memory, learner, screen_width=1920, screen_height=1080, cell_size=210):
        self.memory = memory
        self.learner = learner
        self.width = screen_width
        self.height = screen_height
        self.cell_size = cell_size
        self.cols = self.width // cell_size
        self.rows = self.height // cell_size
        self.center_col = (self.width // (2 * cell_size))
        self.center_row = (self.height // (2 * cell_size))

        # Initialize control variables
        self._destroyed = False
        self._destroy_lock = threading.Lock()
        self._running = threading.Event()
        self._running.set()
        self._mainloop_stopped = threading.Event()
        
        # Initialize Tkinter components
        self.root = None
        self.canvas = None
        self._update_after_id = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Store text items and background rectangles
        self.coordinate_texts = {}
        self.text_backgrounds = {}

        self._shutdown_complete = threading.Event()
        self.event_queue = queue.Queue()
        
        # Initialize the window
        self.initialize_window()

    def initialize_window(self):
        """Initialize the Tkinter window and canvas."""
        if not self.is_destroyed():
            self.root = Tk()
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.attributes('-alpha', 0.7)
            self.root.attributes('-topmost', True)
            self.root.overrideredirect(True)

            self.canvas = Canvas(
                self.root,
                width=self.width,
                height=self.height,
                bg='white',
                highlightthickness=0
            )
            self.canvas.pack()

            self.root.wm_attributes('-transparentcolor', 'white')
            self.draw_grid()

    def is_destroyed(self):
        """Thread-safe check if the grid has been destroyed."""
        with self._destroy_lock:
            return self._destroyed

    def on_closing(self):
        """Handle window close event"""
        self.stop()
        self.event_queue.put(("destroy", None))
        self.destroy()


    def process_events(self):
        """Process events from the queue"""
        try:
            while True:
                event, data = self.event_queue.get_nowait()
                if event == "destroy":
                    self.destroy()
        except queue.Empty:
            pass
        finally:
            if not self.is_destroyed() and self.root and self._running.is_set():
                self.root.after(100, self.process_events)

    def destroy(self):
        """Thread-safe destruction of the grid window."""
        with self._destroy_lock:
            if not self._destroyed and self.root:
                try:
                    self.stop()  # Stop all operations
                    self.root.quit()
                    self.root.destroy()
                except Exception as e:
                    self.logger.error(f"Error during grid destruction: {e}")
                finally:
                    self._destroyed = True
                    self.root = None
                    self.canvas = None

    def draw_grid(self):
        """Draw the grid lines and initialize cell texts and backgrounds."""
        # Draw grid lines
        for x in range(0, self.width, self.cell_size):
            self.canvas.create_line(x, 0, x, self.height, fill='#A0A0A0', dash=(4, 4))
        for y in range(0, self.height, self.cell_size):
            self.canvas.create_line(0, y, self.width, y, fill='#A0A0A0', dash=(4, 4))

        # Highlight the center cell in green
        green_cells = [(self.center_col, self.center_row)]
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

                bg_rect = self.canvas.create_rectangle(
                    0, 0, 0, 0,
                    fill='yellow',
                    outline=''
                )

                text_item = self.canvas.create_text(
                    x, y,
                    text="",
                    fill='black'
                )

                self.coordinate_texts[(col, row)] = text_item
                self.text_backgrounds[(col, row)] = bg_rect

    def check_coordinates(self):
        """Check and update the current coordinates from memory."""
        if not self._running.is_set():
            return
            
        try:
            x, y = self.memory.get_coordinates()
            self.update_coordinates(x, y)
        except Exception as e:
            self.logger.error(f"Error getting coordinates: {e}")

    def update_coordinates(self, base_x, base_y):
        """Update the coordinate labels for all cells based on the current position."""
        if not self._running.is_set():
            return
            
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

    def update_background_colors(self, recorded_coords: set):
        """Update the background color of cells based on recorded coordinates."""
        if not self._running.is_set():
            return
            
        for col in range(self.cols):
            for row in range(self.rows):
                rel_x = self.current_x + (col - self.center_col)
                rel_y = self.current_y + (self.center_row - row)

                bg_rect = self.text_backgrounds.get((col, row))
                if bg_rect:
                    if (rel_x, rel_y) in recorded_coords:
                        self.canvas.itemconfig(bg_rect, fill='#00FF00')
                    else:
                        self.canvas.itemconfig(bg_rect, fill='yellow')

    def check_surrounding_coordinates(self, recorded_coords: set):
        """Check if surrounding coordinates have been discovered."""
        if not self._running.is_set():
            return
            
        surrounding_coords = [
            (self.current_x + dx, self.current_y + dy)
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            if not (dx == 0 and dy == 0)
        ]

        for coord in surrounding_coords:
            if coord in recorded_coords:
                self.logger.debug(f"Coordinate {coord} has been discovered.")
            else:
                self.logger.debug(f"Coordinate {coord} has not been discovered.")

    def stop(self):
        """Immediately stop all grid operations."""
        self.logger.info("Stopping grid operations...")
        with self._destroy_lock:
            if not self._running.is_set():
                return
                
            # Clear running flag first
            self._running.clear()
            
            if self.root:
                try:
                    # Cancel any pending updates
                    if self._update_after_id:
                        self.root.after_cancel(self._update_after_id)
                        self._update_after_id = None
                    
                    # Schedule destruction in GUI thread
                    self.root.after_idle(self._destroy_sequence)
                except Exception as e:
                    self.logger.error(f"Error during stop: {e}")
                finally:
                    # Wait for shutdown with timeout
                    self._shutdown_complete.wait(timeout=2.0)

    def _destroy_sequence(self):
        """Internal method to handle the destruction sequence"""
        try:
            self.logger.info("Executing destroy sequence...")
            if not self._mainloop_stopped.is_set():
                self.root.quit()
                self._mainloop_stopped.set()
            
            if self.root:
                self.root.destroy()
            self._destroyed = True
            self.root = None
            self.canvas = None
            self.logger.info("Grid destroyed successfully")
        except Exception as e:
            self.logger.error(f"Error in destroy sequence: {e}")
        finally:
            self._shutdown_complete.set()

    def run(self):
        """Start the main loop for the grid application."""
        if self.is_destroyed():
            return

        self.root.geometry(f"{self.width}x{self.height}+0+0")
        self.root.bind('<Escape>', lambda e: self.stop())

        def update_loop():
            """Continuous update loop for the grid."""
            if not self._running.is_set() or self.is_destroyed():
                return
            
            try:
                if not self._running.is_set():
                    return
                
                self.check_coordinates()
                if hasattr(self, 'learner'):
                    recorded_coords = self.learner.get_recorded_coords()
                    self.update_background_colors(recorded_coords)
                    self.check_surrounding_coordinates(recorded_coords)
                
                if self._running.is_set() and not self.is_destroyed():
                    self._update_after_id = self.root.after(50, update_loop)
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")

        # Start initial update if still running
        if self._running.is_set():
            self._update_after_id = self.root.after(0, update_loop)

        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in mainloop: {e}")
        finally:
            self._mainloop_stopped.set()