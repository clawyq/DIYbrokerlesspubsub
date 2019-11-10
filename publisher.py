import constants as c
import socket
import threading
import cv2
import zlib
import pickle
import os
import datetime

from select import select
from time import sleep
from random import randint
#from picamera import PiCamera
#import RPi.GPIO as gpio
from math import ceil


class Publisher:
    def __init__(self, topic, port, timeout):
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.bind(("", c.CONTROL_PLANE_PORT))
        self.topic = topic
        self.port = port
        self.timeout = timeout

        self.lock = threading.Lock()

        # self.camera = VideoCapture(0)

        # keeps track of ip addresses and ports
        self.subscribers = []

    # Packet has the following structure:
    # ----------------------------------------------------------------
    #   type flag (1 byte) | 'MORE' flag (1 byte) | seqNum (4 bytes)
    # ----------------------------------------------------------------
    #                      data (570 bytes max)
    # ----------------------------------------------------------------
    #
    # typeFlag: indicates type of content in the packet
    # seqNum: starting sequence number of the data
    # moreFlag: 1 if there is a subsequent packet, 0 else
    def createPacket(self, pktType, more, seqNum, data):
        typeFlagInBytes = int.to_bytes(pktType, byteorder="big", length=1)
        moreFlagInBytes = int.to_bytes(more, byteorder="big", length=1)
        seqNumInBytes = int.to_bytes(seqNum, byteorder="big", length=4)

        if pktType != c.IMAGE:
            data = data.encode()

        utfPayload = typeFlagInBytes + moreFlagInBytes + seqNumInBytes + data
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    def deliverPacket(self, socket, toSend, addr, expectedSeqNum):
        if socket.sendto(toSend, addr) != 0:
            rawData, subscriberAddr = socket.recvfrom(2048)
            hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]
            if c.verifyPacket(hash, payload):
                typeFlag, moreFlag, seqNum, data = self.handlePayload(payload)

                expectedSeqNum = str(expectedSeqNum)
                if typeFlag == c.ACK:
                    return expectedSeqNum == data

        return False

    # handles the payload
    # packet structure is as follows:
    #
    # ----------------------------------------------------------------
    #     type (1 byte) | 'MORE' flag (1 byte) | seqNum (4 bytes)
    # ----------------------------------------------------------------
    #                      data (570 bytes max)
    # ----------------------------------------------------------------
    #
    # precondition: payload excludes hash value
    def handlePayload(self, payload):
        typeFlag = int.from_bytes(payload[:1], byteorder="big")
        moreFlag = int.from_bytes(payload[1:2], byteorder="big")
        seqNum = int.from_bytes(payload[2:6], byteorder="big")
        payload = payload[6:]

        if typeFlag != c.IMAGE:
            data = payload.decode()
        else:
            data = payload

        return typeFlag, moreFlag, seqNum, data

    def ack(self, ackSeqNum, addr):
        ackPkt = self.createPacket(c.ACK, 0, 0, str(ackSeqNum))
        self.controlSocket.sendto(ackPkt, addr)

    # remove an unreachable subscriber from the subscribers list
    def removeUnreachableSubscriber(self, addr):
        self.lock.acquire()
        if addr in self.subscribers:
            self.subscribers.remove(addr)
            print('Subscriber at ' + str(addr) + ' has been removed')
        self.lock.release()

    def sendImage(self, sock, imageData, targetAddr):
        print('start sending image to ' + str(targetAddr))

        seqNum = 0
        while len(imageData) > 0:
            if len(imageData) > c.CAPACITY:
                toSend = imageData[:c.CAPACITY]
                imageData = imageData[c.CAPACITY:]
                hasMore = 1
            else:
                toSend = imageData
                imageData = b''
                hasMore = 0

            imagePacket = self.createPacket(c.IMAGE, hasMore, seqNum, toSend)

            attempt = 0
            while attempt < c.RETRY_POLICY:
                try:
                    sentSuccess = self.deliverPacket(sock, imagePacket, targetAddr, seqNum + len(toSend))
                    if sentSuccess:
                        # print('successfully sent packet seqnum: ' + str(seqNum))
                        seqNum += len(toSend)
                        break

                except socket.timeout:
                    print('failed to send packet to ' + str(targetAddr))

                attempt += 1

            if attempt >= c.RETRY_POLICY:
                self.removeUnreachableSubscriber(targetAddr)
                return

        print('finish sending image to ' + str(targetAddr))

    def sendTopic(self, addr):
        registerTopicPacket = self.createPacket(c.TOPIC_INFO, 0, 0, self.topic)
        self.controlSocket.sendto(registerTopicPacket, addr)

    def listenOnControlPlane(self):
        while True:
            rawData, addr = self.controlSocket.recvfrom(2048)
            hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

            if c.verifyPacket(hash, payload):
                typeHdr, moreHdr, seqNum, data = self.handlePayload(payload)

                if typeHdr == c.TOPIC_REGISTRATION:
                    self.lock.acquire()
                    self.subscribers.append(addr)
                    self.lock.release()
                    self.ack(0, addr)   # sends an ACK so that the publisher knows the registration was a success
                elif typeHdr == c.TOPIC_DISCOVERY:
                    self.sendTopic(addr)
                else:
                    print('something wrong you should not be here')

                print('received registration' + str(self.subscribers))
            sleep(.2)

    def listenForNewImage(self):
        #while True:
        #    btnPressed = gpio.input(17)
        #    if btnPressed == False:
        #        print("[DEBUG] Button Pressed!")
        #        filename = '/home/pi/Documents/CS3103/' + datetime.datetime.now().strftime('%Y-%m-%d%H:%M:%S') + '.jpg'
        #        self.camera.capture(filename)
        #        break
        #    sleep(.2)

        sleep(randint(5,60))
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

        frame = cv2.imread(os.path.join(ROOT_DIR, 'images', 't1-max.jpg'))  # change filename to a proper filename
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        result, frame = cv2.imencode('.jpg', frame, encode_param)
        data = zlib.compress(pickle.dumps(frame, 0), 6)
        return data

    def setupCamera(self):
        #self.camera = PiCamera()
        #self.camera.exposure_mode = 'antishake'

        #gpio.setmode(gpio.BCM)
        #gpio.setup(17, gpio.IN, pull_up_down=gpio.PUD_UP)
        pass

    def start(self):
        print("[DEBUG] Publisher start")
        # create a separate thread to listen for topic discovery by subscribers
        controlPlaneThread = threading.Thread(target=self.listenOnControlPlane)
        controlPlaneThread.daemon = True
        controlPlaneThread.start()

        self.setupCamera()

        # actively waits for the PI camera to be triggered and sends the image to subscribers
        while True:
            imageBytes = self.listenForNewImage()

            self.lock.acquire()
            subscribersAddrList = self.subscribers.copy()
            self.lock.release()

            print(subscribersAddrList)

            for subscriberAddr in subscribersAddrList:
                print(subscriberAddr)
                dataPlaneSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                dataPlaneSock.settimeout(c.TIMEOUT)
                dataPlaneThread = threading.Thread(target=self.sendImage,
                                                   args=(dataPlaneSock, imageBytes, subscriberAddr))
                dataPlaneThread.daemon = True
                dataPlaneThread.start()


if __name__ == "__main__":
    # dummy - frontend will call this program with the parameters
    topic = 'food'
    port = 7435
    timeout = 60
    publisher = Publisher(topic, port, timeout)
    publisher.start()
