import constants as c
import socket
from select import select
from cv2 import VideoCapture
from time import sleep
from math import ceil

class Publisher:
    def __init__(self, topic, port, timeout):
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.controlSocket.bind(("", c.CONTROL_PLANE_PORT))
        self.controlSocket.settimeout(3)
        
        self.topic = topic
        self.port = port
        self.timeout = timeout

        self.camera = VideoCapture(0)

        # keeps track of ip addresses
        self.subscribers = []
    
    def generateImage(self):
        sleep(self.timeout)
        success, frame = self.camera.read()
        if success is False:
            print('Camera is unable to record input.')
            exit(1)
        # frame = frame.compress()
        return frame;

    def createPacket(self, type, payload):
        payload = f""
        if type == c.TOPIC_INFO:
            payload += f"{[self.topic, self.port]}"
        else:
            payload += f"{payload}"
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    def sendImage(self, image):
        # numPackets = image.size/capacity
        # self.generateImage()
        imagePacket = self.createPacket(c.IMAGE, "") #replace "" with spliced image payloads

    def sendTopic(self, topic, port):
        registerTopicPacket = self.createPacket(c.TOPIC_INFO, "")
        self.controlSocket.sendto(registerTopicPacket, ('<broadcast>', c.CONTROL_PLANE_PORT))

    def start(self):
        for i in range(c.RETRY_POLICY):
            self.sendTopic(self.topic, self.port)
        while True:
            imageFrame = self.generateImage()
            for subscriber in self.subscribers:
                # apply security algorithm
                # put in buffer, send message
                self.sendImage(imageFrame)
                # wait for ack, if timeout, throw out what is in the buffer
                # try 3 times, else log

if __name__ == "__main__":
    # dummy - frontend will call this program with the parameters
    topic = 'door'
    port = 7435
    timeout = 3
    publisher = Publisher(topic, port, timeout)
    publisher.start()