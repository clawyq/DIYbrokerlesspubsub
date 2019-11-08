from tkinter import Tk, W, E, StringVar, Label
from tkinter.ttk import Frame, Button, Entry, Style, OptionMenu
import tkinter as tk
from PIL import Image, ImageTk
from random import randint
import time

from subscriber import SubscriberManager, SubscriberSlave

def genFakeTopics():
    numTopics = randint(5, 10)
    topics = ["t" + str(n) for n in range(numTopics)]
    return topics

def nextGridNums(r, c):
    if c == 2:
        return r + 1, 0
    else:
        return r, c + 1

class mainFrame(Frame):

    def __init__(self):
        super().__init__()
        self.canvas = tk.Canvas(self, height=200, width=200)
        img = None
        self.image_id = self.canvas.create_image(200, 200, image=img)
        self.variable = StringVar(self)
        self.variable.set("Empty.")
        self.variable.trace("w", self.selectTopic)
        self.discoverMenu = OptionMenu(self, self.variable)
        self.topicMenu = OptionMenu(self, self.variable)
        self.initUI()

        self.subscriber = SubscriberManager()
        # self.subscriber.start()
        # self.subscriber.sendTopicDiscovery()
        # self.subscriber.receive()

    def selectTopic(*args):
        print(self.variable.get())


    def showImage(self):
        print("Showing Image")
        path = "images/download1.jpg"
        pil_img = Image.open(path).resize((400, 400), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(pil_img)
        # self.canvas.itemconfigure(self.image_id, image=img)
        self.canvas.create_image(200, 200, image=img)
        self.canvas.image = img
    
    def discover(self):
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
        variable = StringVar(self)
        variable.set(topics[0]) # TODO: cope for null inputs
        self.discoverMenu = OptionMenu(self, variable, *topics)
        self.discoverMenu.grid(row=1, column=4)
        self.pack()

        self.buttons = self.generateButtons(topics)

    def generateButtons(self, topics):
        r = 3
        c = 0
        buttons = []
        for topic in topics:
            b = Button(self, text=topic)
            b.grid(row=r, column=c)
            r, c = nextGridNums(r, c)
            print(f"r: {r} c: {c}")
            buttons.append(b)

        self.pack()

        return buttons

    def destroyButtons(self):
        for b in self.buttons:
            b.destroy()


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

        cls = Button(self, text="Cls", command=self.showImage)  
        cls.grid(row=1, column=0)
        bck = Button(self, text="Discover", command=self.discover)
        bck.grid(row=1, column=1)
        lbl = Button(self)
        lbl.grid(row=1, column=2)
        clo = Button(self, text="Destory", command=self.destroyButtons)
        clo.grid(row=1, column=3)
        sev = Button(self, text="7")
        sev.grid(row=2, column=0)
        eig = Button(self, text="8")
        eig.grid(row=2, column=1)
        nin = Button(self, text="9")
        nin.grid(row=2, column=2)
        div = Button(self, text="/")
        div.grid(row=2, column=3)

        self.canvas.grid(row=1, column=4)   
        self.discoverMenu.grid(row=1, column=4)
        self.topicMenu.grid(row=1, column=5)

        self.pack()


def main():

    root = Tk()
    app = mainFrame()
    root.mainloop()


if __name__ == '__main__':
    main()