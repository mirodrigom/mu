import tkinter as tk
from PIL import ImageGrab
import cv2
import numpy as np
import time
class OCRHighlighter:
   def __init__(self):
       root = tk.Tk()
       root.attributes('-alpha', 0.3, '-topmost', True)
       root.overrideredirect(True)

       coords = {
           'position': [260, 23, 330, 49],
           'reset': [1093, 360, 1118, 385], 
           'level': [1114, 336, 1154, 354],
           'play': [300, 65, 307, 71]
       }

       for name, coords in coords.items():
           x1, y1, x2, y2 = coords
           root.geometry(f"{x2-x1}x{y2-y1}+{x1}+{y1}")
           label = tk.Label(root, text=name, bg='red')
           label.pack(fill='both', expand=True)
           root.update()

           img = ImageGrab.grab(bbox=coords)
           img.save(f'{name}_capture.png')

           # Process image like in bot code
           cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
           gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) 
           lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
           l, _, _ = cv2.split(lab)
           clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
           cl = clahe.apply(l)
           _, thresh = cv2.threshold(cl, 150, 255, cv2.THRESH_BINARY)
           cv2.imwrite(f'{name}_processed.png', thresh)
           
           time.sleep(2)

       root.destroy()

if __name__ == "__main__":
   OCRHighlighter()