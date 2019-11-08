from tkinter import Tk, W, E, StringVar, Label
from tkinter.ttk import Frame, Button, Entry, Style, OptionMenu
import tkinter as tk
from PIL import Image, ImageTk
from random import randint

from subscriber import SubscriberManager, SubscriberSlave


class Example(Frame):

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
        # self.subscriber.sendTopicDiscovery()
        # self.subscriber.receive()
        self.subscriber.start()
        topicLst = self.subscriber.getDiscoveredTopics()
        print(topicLst)
        numTopics = randint(5, 10)
        # topicLst = ["t" + str(n) for n in range(numTopics)]
        variable = StringVar(self)
        variable.set("one") # default value
        self.discoverMenu = OptionMenu(self, variable, *topicLst)
        self.discoverMenu.grid(row=1, column=4)
        self.pack() 
        return topicLst

    def initUI(self):

        self.master.title("Calculator")

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
        clo = Button(self, text="Close")
        clo.grid(row=1, column=3)
        sev = Button(self, text="7")
        sev.grid(row=2, column=0)
        eig = Button(self, text="8")
        eig.grid(row=2, column=1)
        nin = Button(self, text="9")
        nin.grid(row=2, column=2)
        div = Button(self, text="/")
        div.grid(row=2, column=3)

        fou = Button(self, text="4")
        fou.grid(row=3, column=0)
        fiv = Button(self, text="5")
        fiv.grid(row=3, column=1)
        six = Button(self, text="6")
        six.grid(row=3, column=2)
        mul = Button(self, text="*")
        mul.grid(row=3, column=3)

        one = Button(self, text="1")
        one.grid(row=4, column=0)
        two = Button(self, text="2")
        two.grid(row=4, column=1)
        thr = Button(self, text="3")
        thr.grid(row=4, column=2)
        mns = Button(self, text="-")
        mns.grid(row=4, column=3)

        zer = Button(self, text="0")
        zer.grid(row=5, column=0)
        dot = Button(self, text=".")
        dot.grid(row=5, column=1)
        equ = Button(self, text="=")
        equ.grid(row=5, column=2)
        pls = Button(self, text="+")
        pls.grid(row=5, column=3)

        self.canvas.grid(row=1, column=4)   
        self.discoverMenu.grid(row=1, column=4)
        self.topicMenu.grid(row=1, column=5)

        self.pack()


def main():

    root = Tk()
    app = Example()
    root.mainloop()


if __name__ == '__main__':
    main()