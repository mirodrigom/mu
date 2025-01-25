import tkinter as tk
from mss import mss
from PIL import ImageTk, Image

class CoordinateSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(fill="both", expand=True)
        
        with mss() as sct:
            screenshot = sct.grab(sct.monitors[0])  # Primary monitor
            self.img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            self.photo = ImageTk.PhotoImage(self.img)
            self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.coordinates = []
        
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        self.root.mainloop()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y, outline="red"
        )

    def on_release(self, event):
        coords = (self.start_x, self.start_y, event.x, event.y)
        print(f"Coordinates: {coords}")
        self.coordinates.append(coords)

if __name__ == "__main__":
    selector = CoordinateSelector()