import cv2
import numpy as np
from PIL import Image
import pytesseract

def get_reset_number(image_path):
    # Read and convert to grayscale
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Increase contrast
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    
    # Threshold
    _, thresh = cv2.threshold(cl, 150, 255, cv2.THRESH_BINARY)
    
    # Save debug images
    cv2.imwrite('processed_reset.png', thresh)
    
    # Tesseract config for single digit
    config = r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(Image.fromarray(thresh), config=config)
    
    print(f"Detected text: '{text}'")
    return text

result = get_reset_number('reset_test.png')