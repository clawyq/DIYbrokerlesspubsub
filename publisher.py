import constants as c
import socket
from select import select
# from cv2 import VideoCapture
from time import sleep
from math import ceil

class Publisher:
    def __init__(self, topic, port, timeout):
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.bind(("localhost", c.CONTROL_PLANE_PORT))
        self.controlSocket.settimeout(60)
        
        self.topic = topic
        self.port = port
        self.timeout = timeout

        # self.camera = VideoCapture(0)

        # keeps track of ip addresses
        self.subscribers = []
    
    # def generateImage(self):
    #     sleep(self.timeout)
    #     success, frame = self.camera.read()
    #     if success is False:
    #         print('Camera is unable to record input.')
    #         exit(1)
    #     # frame = frame.compress()
    #     return frame;

    def createPacket(self, type, message):
        payload = f"{type}  "
        if type == c.TOPIC_INFO:
            payload += f"{[self.topic, self.port]}"
        else:
            payload += f"{message}"
        print(payload)
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    def sendImage(self, image):
        # numPackets = image.size/capacity
        # self.generateImage()
        imagePacket = self.createPacket(c.IMAGE, "") #replace "" with spliced image payloads

    def sendTopic(self, addr, port):
        registerTopicPacket = self.createPacket(c.TOPIC_INFO, "")
        self.controlSocket.sendto(registerTopicPacket, (addr, c.CONTROL_PLANE_PORT))
    
    def receive(self):
        print('Receiving...')
        rawData, addr = self.controlSocket.recvfrom(2048)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
        
        if payload[0] == c.TOPIC_REGISTRATION:
            self.subscribers.append(addr[0])
            print(f'received registration {self.subscribers}')
        elif payload[0] == c.TOPIC_DISCOVERY:
            self.sendTopic(addr[0], self.port)
        else:
            print('something wrong you should not be here')
        

    def start(self):
        while True:
        # for i in range(c.RETRY_POLICY):
            self.receive()
            sleep(0.5)
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
    timeout = 60
    publisher = Publisher(topic, port, timeout)
    publisher.start()
