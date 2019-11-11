from tkinter import Tk, W, E, StringVar, Label
from tkinter.ttk import Frame, Button, Entry, Style, OptionMenu
import tkinter as tk
from PIL import Image, ImageTk
from random import randint
import time
import os
import collections

from subscriber import SubscriberManager, SubscriberSlave

MAX_W = 500
MAX_H = 500

def genFakeTopics():
    numTopics = randint(2, 5)
    topics = ["t" + str(n) for n in range(1, numTopics+1)]
    return topics

def nextGridNums(r, c):
    if c == 2:
        return r + 1, 0
    else:
        return r, c + 1

class mainFrame(Frame):

    def __init__(self):
        super().__init__()
        self.canvas = tk.Canvas(self, height=500, width=500)
        self.img = None
        self.image_id = self.canvas.create_image(200, 200, image=self.img)
        self.image_path = "Test"
        
        self.variable = StringVar(self)
        self.variable.set("t1")
        self.buttons = []

        self.v = set()
        self.topicQueues = collections.defaultdict(collections.deque)
        self.initUI()

        self.subscriber = SubscriberManager()


    def showImage(self, path):
        print("Showing Image")
        pil_img = Image.open(path)
        pil_img.thumbnail((500, 500), Image.ANTIALIAS)
        # resizeRatio = min(MAX_W / pil_img.width, MAX_H / pil_img.height)
        # pil_img.resize((500, 500), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(pil_img)
        
        
        # self.canvas.itemconfigure(self.image_id, image=img)
        self.canvas.create_image(200, 200, image=img)
        self.canvas.image = img
    
    def discover(self):
        self.destroyButtons()
        print("Starting discovery...")
        """
            Sends discovery request to all subscribers. 
            
            From topics:
                check for a new image every 30 seconds
                if there is an image, add it to list. 

            Generates Button for every topic, when button is pressed, displays 'channel'.
            
            Returns list of topics.

        """
        
        topics = genFakeTopics()
        self.pack()
        self.buttons = self.generateButtons(topics)

    def setSpecVar(self, topic):
        return lambda: self.variable.set(topic)

    def generateButtons(self, topics):
        r = 1
        c = 0
        buttons = []
        for t in topics:
            print(f'setting button topic to {t}')
            funct = self.setSpecVar(t)
            b = Button(self, text=t, command=funct)
            b.grid(row=r, column=c)
            r, c = nextGridNums(r, c)
            print(f"r: {r} c: {c}")
            buttons.append(b)

        self.pack()

        return buttons

    def destroyButtons(self):
        for b in self.buttons:
            b.destroy()

    def getTopic(self, path):
        topic = path.split('-')[0]
        return topic

    def addNewImagesToQueues(self):
        for path in list(os.walk('images'))[0][2]:
            if path not in self.v:
                topic = self.getTopic(path)
                print(f'adding {path} to queue {topic}')
                self.topicQueues[topic].append(path)
                self.v.add(path)

    def refresh_image(self, canvas, img, image_path, image_id):
    
        # if no images in queue, show blank
        # otherwise, cycle though images in 30 second cycle, 5 seconds each
        try:
            print("Refreshing...")
            self.addNewImagesToQueues()
            topic = self.variable.get()
            q = self.topicQueues[topic]
            print(topic)
            if len(q) == 0:
                # show BLANK
                pass
            else:
                img_path = "images/"+ q.pop()
                print(f"Showing image {img_path}")
                # pil_img = Image.open(img_path).resize((200, 200), Image.ANTIALIAS)
                # img = ImageTk.PhotoImage(pil_img)
                # self.canvas.itemconfigure(self.image_id, image=img)
                self.showImage(img_path)
        except IOError:  # missing or corrupt image file
            img = None
        # repeat every half sec
        canvas.after(1000, self.refresh_image, self.canvas, self.img, self.image_path, self.image_id)  

    def initUI(self):

        self.master.title("Frontend")

        Style().configure("TButton", padding=(0, 5, 0, 5),
            font='serif 10')

        self.columnconfigure(0, pad=3)
        self.columnconfigure(1, pad=3)
        self.columnconfigure(2, pad=3)
        self.columnconfigure(3, pad=3)

        self.rowconfigure(0, pad=3)
        self.rowconfigure(1, pad=3)
        self.rowconfigure(2, pad=3)
        self.rowconfigure(3, pad=3)
        self.rowconfigure(4, pad=3)

        bck = Button(self, text="Discover", command=self.discover)
        bck.grid(row=0, column=0)
        clo = Button(self, text="Destory", command=self.destroyButtons)
        clo.grid(row=0, column=1)
        self.canvas.grid(row=0, column=4, columnspan=10, rowspan=10)   
        # self.discoverMenu.grid(row=1, column=4)
        # self.topicMenu.grid(row=1, column=5)

        self.pack()


def main():

    root = Tk()
    app = mainFrame()
    app.refresh_image(app.canvas, app.img, app.image_path, app.image_id)
    root.mainloop()


if __name__ == '__main__':
    main()