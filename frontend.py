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
    if c == 1:
        return r + 1, 0
    else:
        return r, c + 1

class mainFrame(Frame):

    def __init__(self):
        super().__init__()
        self.canvas = tk.Canvas(self, height=500, width=500, bg='white')
        self.img = None
        self.image_id = self.canvas.create_image(200, 200, image=self.img)
        self.image_path = "Test"
        
        self.variable = StringVar(self)
        self.variable.set("None")
        self.buttons = []

        self.v = set()
        self.topicQueues = collections.defaultdict(collections.deque)

        self.status = tk.Label(self, text="Waiting for input.", font="Helvetica 30", bg='white')
        self.initUI()
        
    def getTopics(self):
        topics = []
        print(list(self.topicQueues.keys()))

        for topic in list(self.topicQueues.keys()):
            if not topic == 'None': 
                topics.append(topic)
        return topics


    def showImage(self, path):
        print("Showing Image")
        pil_img = Image.open(path)
        pil_img.thumbnail((500, 500), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(pil_img)
        self.canvas.create_image(200, 200, image=img)
        self.canvas.image = img
    
    def discover(self):
        self.destroyButtons()
        topics = self.getTopics()
        self.pack()
        self.buttons = self.generateButtons(topics)

    def setSpecVar(self, topic):
        return lambda: self.variable.set(topic)

    def generateButtons(self, topics):
        r = 1
        c = 0
        buttons = []
        for t in topics:
            print('setting button topic to {}'.format(t))
            funct = self.setSpecVar(t)
            b = Button(self, text=t, command=funct)
            b.grid(row=r, column=c)
            r, c = nextGridNums(r, c)
            print("r: {} c: {}".format(r,c))
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
                print('adding {} to queue {}'.format(path, topic))
                self.topicQueues[topic].append(path)
                self.v.add(path)

    def refresh_image(self, canvas, img, image_path, image_id):
        try:
            print("Refreshing...")
            self.discover()
            self.addNewImagesToQueues()
            topic = self.variable.get()
            q = self.topicQueues[topic]
            print(topic)
            if len(q) == 0:
                # show BLANK
                pass
            else:
                img_path = "images/"+ q.pop()
                print("Showing image {}".format(img_path))
                self.showImage(img_path)
                self.status["text"] = "Showing images from [{}]\n Images left in queue: {}".format(topic, len(q))
        except IOError:  # missing or corrupt image file
            img = None
        # repeat every half sec
        canvas.after(500, self.refresh_image, self.canvas, self.img, self.image_path, self.image_id)  

    def initUI(self):

        self.master.title("CameraView")


        Style().configure("TFrame", background="white")
        Style().configure("TButton", padding=(0, 5, 0, 5),
            font='serif 10', foreground='white', background="#1976D2")

        self.columnconfigure(0, pad=3)
        self.columnconfigure(1, pad=3)
        self.columnconfigure(2, pad=3)
        self.columnconfigure(3, pad=3)
        self.columnconfigure(4, pad=3)

        self.rowconfigure(0, pad=3)
        self.rowconfigure(1, pad=3)
        self.rowconfigure(2, pad=3)
        self.rowconfigure(3, pad=3)
        self.rowconfigure(4, pad=3)


        self.canvas.grid(row=1, column=4, columnspan=10, rowspan=10)
        self.status.grid(row=0, column=4, sticky='ew', columnspan=4)

        self.pack()


def main():

    root = Tk()
    app = mainFrame()
    app.refresh_image(app.canvas, app.img, app.image_path, app.image_id)
    root.mainloop()


if __name__ == '__main__':
    main()