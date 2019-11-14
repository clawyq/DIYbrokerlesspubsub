import constants as c
import socket
import threading
import cv2
import zlib
import pickle
import datetime
import logging

from time import sleep
from picamera import PiCamera
import RPi.GPIO as gpio

# This class models the Publisher in Publisher-Subscriber IOT protocol.
# It uses multithreading to listen and register new subscribers on the control plane,
# and sends data of newly captured image to its registered subscribers on the data plane.
class Publisher:
    def __init__(self, topic):
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.bind(("", c.CONTROL_PLANE_PORT))
        self.topic = topic

        self.lock = threading.Lock()

        # keeps track of subscribers' ip addresses and ports
        self.subscribers = []

    # Packet has the following structure:
    # ----------------------------------------------------------------
    #         type flag (3 bytes)         |    'MORE' flag (1 byte)
    # ----------------------------------------------------------------
    #                        seqNum (4 bytes)
    # ----------------------------------------------------------------
    #                              data
    # ----------------------------------------------------------------
    #
    # typeFlag: indicates type of content in the packet
    # seqNum: starting sequence number of the data
    # moreFlag: 1 if there is a subsequent packet, 0 else
    def createPacket(self, pktType, more, seqNum, data):
        typeFlagInBytes = int.to_bytes(pktType, byteorder="big", length=3)
        moreFlagInBytes = int.to_bytes(more, byteorder="big", length=1)
        seqNumInBytes = int.to_bytes(seqNum, byteorder="big", length=4)

        if pktType != c.IMAGE:
            data = data.encode()  # image file is already in bytes

        utfPayload = typeFlagInBytes + moreFlagInBytes + seqNumInBytes + data
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # Ensures the the packet is delivered successfully to the intended addressee.
    # Returns True if successfully delivered, False otherwise.
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

    # Process the payload and returns the individual fields as a tuple.
    #
    # Precondition: payload excludes hash value
    def handlePayload(self, payload):
        typeFlag = int.from_bytes(payload[:3], byteorder="big")
        moreFlag = int.from_bytes(payload[3:4], byteorder="big")
        seqNum = int.from_bytes(payload[4:8], byteorder="big")
        payload = payload[8:]

        if typeFlag != c.IMAGE:
            data = payload.decode()
        else:
            data = payload

        return typeFlag, moreFlag, seqNum, data

    def ack(self, ackSeqNum, addr):
        ackPkt = self.createPacket(c.ACK, 0, 0, str(ackSeqNum))
        self.controlSocket.sendto(ackPkt, addr)

    # Removes an unreachable subscriber from the subscribers list
    def removeUnreachableSubscriber(self, addr):
        self.lock.acquire()
        if addr in self.subscribers:
            self.subscribers.remove(addr)
            logging.info(' Subscriber at ' + str(addr) + ' has been removed')
        self.lock.release()

    # Sends an image to the target subscriber.
    def sendImage(self, sock, imageData, targetAddr):
        logging.info(' Start sending image to ' + str(targetAddr))

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
                        logging.info(' Successfully sent packet seqnum: ' + str(seqNum))
                        seqNum += len(toSend)
                        break

                except socket.timeout:
                    logging.warning(' Failed to send packet to ' + str(targetAddr) + ' retry(' + str(attempt + 1) + ')')

                attempt += 1

            # Removes subscriber from address list if failed to deliver packets after max attempts.
            # Assumes the subscriber is not reachable/no longer in the network.
            if attempt >= c.RETRY_POLICY:
                logging.warning(' Failed to send packet to ' + str(targetAddr) + " max retries exceeded...")
                self.removeUnreachableSubscriber(targetAddr)
                return

    # Sends information on publisher's topic to the interested publisher.
    def sendTopic(self, targetAddr):
        registerTopicPacket = self.createPacket(c.TOPIC_INFO, 0, 0, self.topic)
        self.controlSocket.sendto(registerTopicPacket, targetAddr)

    # Actively listens on the control plane for any subscribers to register.
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
                    self.ack(0, addr)
                elif typeHdr == c.TOPIC_DISCOVERY:
                    self.sendTopic(addr)
                else:
                    logging.warning(' Something wrong you should not be here')

                logging.info(' Received registration. Updated subscribers list - ' + str(self.subscribers))
            sleep(.1)

    # Actively listens for a new image to be captured by the Raspberry PI camera.
    def listenForNewImage(self):
        logging.info(" Listening for new images...")
        while True:
            btnPressed = gpio.input(17)
            if btnPressed == False:
                logging.info(" Button Pressed!")
                filename = '/home/pi/Documents/CS3103/' + datetime.datetime.now().strftime('%Y-%m-%d%H:%M:%S') + '.jpg'
                self.camera.capture(filename)
                break
            sleep(2)

        image = cv2.imread(filename)
        frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # convert image to grayscale for reduced file size
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        result, frame = cv2.imencode('.jpg', frame, encode_param)
        data = zlib.compress(pickle.dumps(frame, 0), 6)
        return data

    # Initial setup for the camera module.
    def setupCamera(self):
        self.camera = PiCamera()
        self.camera.exposure_mode = 'antishake'

        gpio.setmode(gpio.BCM)
        gpio.setup(17, gpio.IN, pull_up_down=gpio.PUD_UP)

    def start(self):
        logging.info("Publisher start")
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
    logging.basicConfig(level=logging.INFO)

    topic = 'door'
    publisher = Publisher(topic)
    publisher.start()
