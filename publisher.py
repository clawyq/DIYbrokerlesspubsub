import constants as c
import socket
import threading
import cv2
import zlib
import pickle

from select import select
# from cv2 import VideoCapture
from time import sleep
#from picamera import PiCamera
#import RPi.GPIO as gpio
from math import ceil

class Publisher:
    def __init__(self, topic, port, timeout):
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.bind(("", c.CONTROL_PLANE_PORT))
        self.controlSocket.settimeout(60)
        self.topic = topic
        self.port = port
        self.timeout = timeout

        self.lock = threading.Lock()

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
        payload = type + "  "
        if type == c.TOPIC_INFO:
            payload += str([self.topic, self.port])
            utfPayload = payload.encode()
        else:
            utfPayload = message    # image data is already in bytes format
        #print(payload)
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # header for image packet contains header of following structure:
    # ----------------------------------------------------------------
    # sequence number in bytes (4 bytes) | more flag in bytes (1 byte)
    # ----------------------------------------------------------------
    #
    # seqNum: starting sequence number of the data
    # moreFlag: 1 if there is a subsequent packet, 0 else
    def createHeader(self, seqNum, moreFlag):
        seqNumBytes = int.to_bytes(seqNum, byteorder="big", length=4)
        moreFlagBytes = int.to_bytes(moreFlag, byteorder="big", length=4)
        return seqNumBytes + moreFlagBytes

    def deliverPacket(self, socket, toSend, addr, expectedSeqNum):
        socket.sendto(toSend, addr)
        rawData, subscriberAddr = socket.recvfrom(2048)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")

            if payload[0] == c.ACK:
                return expectedSeqNum == int(payload[1])

        return False

    # remove an unreachable subscriber from the subscribers list
    def removeUnreachableSubscriber(self, addr):
        self.lock.acquire()
        if addr in self.subscribers:
            self.subscribers.remove(addr)
        self.lock.release()

    def sendImage(self, imageData, targetAddr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.05)
        seqNum = 0
        while len(imageData) > 0:
            if len(imageData) > c.CAPACITY:
                contentBody = imageData[0: c.CAPACITY]
                imageData = imageData[c.CAPACITY: len(imageData)]
                hasMore = 1
            else:
                contentBody = imageData
                imageData = b''
                hasMore = 0

            header = self.createHeader(seqNum, hasMore)
            imagePacket = self.createPacket(c.IMAGE, header + contentBody)  # replace "" with spliced image payloads

            for attempt in range(c.RETRY_POLICY):
                sentSuccess = self.deliverPacket(sock, imagePacket, targetAddr, seqNum + len(contentBody))
                if sentSuccess:
                    break
                elif (attempt + 1) == c.RETRY_POLICY:
                    self.removeUnreachableSubscriber(targetAddr)
                    return

            seqNum += len(contentBody)

    def sendTopic(self, addr):
        registerTopicPacket = self.createPacket(c.TOPIC_INFO, "")
        self.controlSocket.sendto(registerTopicPacket, (addr, c.CONTROL_PLANE_PORT))

    def listenOnControlPlane(self):
        while True:
            rawData, addr = self.controlSocket.recvfrom(2048)
            hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

            if c.verifyPacket(hash, payload):
                payload = payload.decode()
                payload = payload.split("  ")

                if payload[0] == c.TOPIC_REGISTRATION:
                    self.lock.acquire()
                    self.subscribers.append(addr)
                    self.lock.release()
                elif payload[0] == c.TOPIC_DISCOVERY:
                    self.sendTopic(addr)
                else:
                    print('something wrong you should not be here')

                print('received registration' + str(self.subscribers))
            sleep(c.REFRESH_RATE)

    def listenForNewImage(self):
        #camera = PiCamera()
        #camera.exposure_mode = 'antishake'

        #gpio.setmode(gpio.BCM)
        #gpio.setup(17, gpio.IN, pull_up_down=gpio.PUD_UP)

        #while True:
        #    btnPressed = gpio.input(17)
        #    if btnPressed == False:
        #        filename = '/home/pi/Documents/CS3103/' + datetime.datetime.now().strftime('%Y-%m-%d%H:%M:%S') + '.jpg'
        #        camera.capture(filename)
        #        sleep(c.REFRESH_RATE)

        frame = cv2.imread('sample.jpg')    # change filename to a proper filename
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        result, frame = cv2.imencode('.jpg', frame, encode_param)
        data = zlib.compress(pickle.dumps(frame, 0), 6)
        return data

    def start(self):
        # create a separate thread to listen for topic discovery by subscribers
        controlPlaneThread = threading.Thread(target=self.listenOnControlPlane)
        controlPlaneThread.daemon = True
        controlPlaneThread.start()

        # actively waits for the PI camera to be triggered and sends the image to subscribers
        while True:
            imageBytes = self.listenForNewImage()

            self.lock.acquire()
            subscribersAddrList = self.subscribers.copy()
            self.lock.release()

            for subscriberAddr in subscribersAddrList:
                # apply security algorithm
                # put in buffer, send message
                dataPlaneThread = threading.Thread(target=self.sendImage,
                                                   args=(imageBytes, subscriberAddr))
                dataPlaneThread.daemon = True
                dataPlaneThread.start()
                # wait for ack, if timeout, throw out what is in the buffer
                # try 3 times, else log

if __name__ == "__main__":
    # dummy - frontend will call this program with the parameters
    topic = 'door'
    port = 7435
    timeout = 60
    publisher = Publisher(topic, port, timeout)
    publisher.start()
