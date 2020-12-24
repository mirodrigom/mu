import numpy as np
from PIL import ImageGrab
import cv2
import pytesseract 
import time
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class Game(object):
    #Box coordinate
    coordinates_x_start = 0
    coordinates_x_end = 0
    coordinates_y_start = 0
    coordinates_y_end = 0

    def __init__(self):
        pass

    def setCoordinates(self,xs,xe,ys,ye):
        self.coordinates_x_start = xs
        self.coordinates_x_end = xe
        self.coordinates_y_start = ys
        self.coordinates_y_end = ye

    def existCoodinates(self):
        if(self.coordinates_x_start != 0 and self.coordinates_x_end != 0 and self.coordinates_y_start != 0 and self.coordinates_y_end != 0):
            return True
        return False

def findCoordinatesBox(dictPossibles,lendict):
    x_start = None
    x_end = None
    y_start = None
    y_end = None
    for elementDict in range(lendict):
        print(dictPossibles[elementDict])
        element_a = int(dictPossibles[elementDict][0])
        element_b = int(dictPossibles[elementDict][1])
        element_c = int(dictPossibles[elementDict][2])
        element_d = int(dictPossibles[elementDict][3])
        if x_start == None or x_start > element_a:
            x_start = element_a
        if y_start == None or y_start > element_b:
            y_start = element_b
        if x_end == None or x_end < element_c:
            x_end = element_c
        if y_end == None or y_end < element_d:
            y_end = element_d
    if x_start != None and x_end != None and y_start != None and y_end != None:
        gameObject.setCoordinates(x_start,x_end,y_start,y_end)
        print(gameObject.coordinates_x_start,gameObject.coordinates_x_end,gameObject.coordinates_y_start,gameObject.coordinates_y_end)

def checkCoordinates(txt):
    #$ 5 S 100,200
    x = re.findall(r'[+|5|$|S|" "]?[\d]?\d\d[,|.][\d]?\d\d', txt) 
    return x

def cleanCoordinates(txt):
    newtxt = ""
    for word in txt[0]:
        if(word.isnumeric() or word == "." or word == ","):
            newtxt = newtxt + word
    return newtxt

def process_img(image):
    original_image = image
    # convert to gray
    processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # edge detection
    ret, processed =  cv2.threshold(processed_img, 244, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    return processed

def getText(image,oldimg):
    # Specify structure shape and kernel size.  
    # Kernel size increases or decreases the area  
    # of the rectangle to be detected. 
    # A smaller value like (10, 10) will detect  
    # each word instead of a sentence. 
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18)) 
    
    # Appplying dilation on the threshold image 
    dilation = cv2.dilate(image, rect_kernel, iterations = 1) 
    
    # Finding contours 
    contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 

    for cnt in contours: 
        x, y, w, h = cv2.boundingRect(cnt) 

        # Drawing a rectangle on copied image 
        rect = cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2) 
        
        # Cropping the text block for giving input to OCR 
        cropped = image[y:y + h, x:x + w] 
        
        imgtostring = pytesseract.image_to_string(cropped)
        find = checkCoordinates(imgtostring)
        if(bool(find) == True):
            textcoordinates = cleanCoordinates(find)
            lenghtTextCoordinates = len(textcoordinates)
            coordinateswithWords = {}
            count = 0
            data = pytesseract.image_to_boxes(cropped)
            data = data.split("\n")
            for word in data:
                wordsplitted = word.split(" ")
                if(count < lenghtTextCoordinates):
                    if(count == 0):
                        if wordsplitted[0] == textcoordinates[count]:
                            print(wordsplitted,textcoordinates[count])
                            coordinateswithWords[count] = wordsplitted[1:-1]
                            count = count + 1
                            
                    else:
                        if wordsplitted[0] == textcoordinates[count]:
                            print(wordsplitted,textcoordinates[count])
                            coordinateswithWords[count] = wordsplitted[1:-1]
                            count = count + 1
                        else:
                            count = 0
                            coordinateswithWords = {}
                elif(count == lenghtTextCoordinates):
                    break
            if(any(coordinateswithWords)):
                findCoordinatesBox(coordinateswithWords,count)
                break

def learnCoordinates():
    screen = np.array(ImageGrab.grab(bbox=(0,0,800,600)))
    new_screen = process_img(screen)
    getText(new_screen,screen)
    if(gameObject.existCoodinates() == True):
        #cv2.imshow('nazheee', new_screen)
        h, w, c = screen.shape
        #print(h)
        #print(gameObject.coordinates_x_start, h- gameObject.coordinates_y_start, gameObject.coordinates_x_end, h -gameObject.coordinates_y_end)
        #img = cv2.rectangle(screen, (gameObject.coordinates_x_start, h- gameObject.coordinates_y_start), (gameObject.coordinates_x_end, h -gameObject.coordinates_y_end), (0, 255, 0), 2)
        #cv2.imshow('img', img)
        #cv2.waitKey(0)
        
        showMeCoordinates(h)
    else:
        print("no pudo calcular")
        learnCoordinates()

def showMeCoordinates(h):
    last_time = time.time()
    while(True):
        #screen = np.array(ImageGrab.grab(bbox=(136,8,166,50)))
        #VER ESTO XQ NO COINCIDE!!
        screen = np.array(ImageGrab.grab(bbox=(gameObject.coordinates_x_start-10,20, gameObject.coordinates_x_end+5, h-gameObject.coordinates_y_end+10)))
        #print('loop took {} seconds'.format(time.time()-last_time))
        last_time = time.time()
        #new_screen = process_img(screen)
        cv2.imshow('testmu', screen)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break

'''
def screen_record(): 
    last_time = time.time()
    while(True):
        # 800x600 windowed mode
        screen = np.array(ImageGrab.grab(bbox=(0,40,800,640)))
        print('loop took {} seconds'.format(time.time()-last_time))
        last_time = time.time()
        new_screen = process_img(screen)
        getText(new_screen,screen)
        cv2.imshow('nazheee', new_screen)
        #cv2.imshow('window',cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break
'''
gameObject = Game()
learnCoordinates()