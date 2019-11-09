import socket
import ast
import time 
import constants as c
import cv2
import zlib
import pickle
import datetime
import threading

from select import select
from time import sleep
from random import randint as ri
from copy import deepcopy

class SubscriberSlave:
    def __init__(self, addr, port):
        self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dataSocket.bind((addr, port))
        self.initialSeqNum = 0
        self.buffer = ""
        self.image = ""
    
    def receive(self, type):
        hasMore = True

        while hasMore:
            rawData, addr = self.controlSocket.recvfrom(2048)
            hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

            # if not corrupted packet
            if c.verifyPacket(hash, payload):
                payload = payload.decode()
                payload = payload.split("  ")
                hasMore = self.handlePayload(payload)

        self.storeImage(buffer)
        
        # ack logic goes here
        # upon finish, call returnImage

    # handles the image payload
    # packet structure is as follows:
    #
    # ----------------------------------------------
    # sequence number (4 bytes) | more flag (1 byte)
    # ----------------------------------------------
    #         image byte data (max 571 bytes)
    # ----------------------------------------------
    #
    # precondition: payload excludes hash value
    def handlePayload(self, payload):
        seqNumHeader = payload[16:20]
        moreFlagHeader = payload[20:21]
        imageData = payload[21:]

        data = zlib.decompress(imageData)
        recvData = pickle.loads(data, fix_imports=True, encoding="bytes")
        # recvImage = cv2.imdecode(recvData, cv2.IMREAD_COLOR)

        if seqNumHeader == self.initialSeqNum:
            self.buffer += recvData
            self.initialSeqNum += len(recvData)

        # Will return true if there is more data to be received
        return (moreFlagHeader == 1)  || (seqNumHeader != self.initialSeqNum)

    # TODO: create a local variable 'topic' and store whatever topic the subscriber is listening to at the moment
    def storeImage(self, imageBytes):
        recvData = pickle.loads(imageBytes, fix_imports=True, encoding="bytes")
        recvImage = cv2.imdecode(recvData, cv2.IMREAD_COLOR)

        cv2.imwrite(datetime.datetime.now().strftime('%Y-%m-%d%H:%M:%S') + '.jpg', recvImage)

    def returnImage(self):
        # pass this to the manager for him to pass to the frontEnd
        pass

class SubscriberManager:
    def __init__(self):
        # self.meaddress = socket.gethostbyname(socket.gethostname())
        self.local_ip = self._getLocalIP()
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.controlSocket.settimeout(60)
        self.controlSocket.bind((self.local_ip, c.CONTROL_PLANE_PORT))
        
        # socket objects to listen to
        self.socketsToListenTo = [self.controlSocket]

        # keeps track of topic: {addr, port}
        self.registeredTopics = {}

        # keeps track of what is available, mainly to show frontend topic: {address, port, registered?}
        self.discoveredTopics = {}

    def _getLocalIP(self):
        """
            Hacky way to get the local IP
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        return ip

    #  a subscriber should send ACKs and topic discoveries and topic registrations
    # packet structure: hash -- P/S -- type -- ackNum
    def createPacket(self, type, message):
        payload = type + "  "
        if type != c.TOPIC_DISCOVERY:
            payload += message
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # sending tables - if no one replies, default {}. iF a publisher replies, update my table
    def sendTopicDiscovery(self):
        topicDiscoveryPacket = self.createPacket(c.TOPIC_DISCOVERY, "")
        return self.controlSocket.sendto(topicDiscoveryPacket,
                                         ('<broadcast>', c.CONTROL_PLANE_PORT))

    def sendTopicRegistration(self, topic):
        topicRegistrationPacket = self.createPacket(c.TOPIC_REGISTRATION, topic)
        return self.controlSocket.sendto(topicRegistrationPacket,
                                         (self.discoveredTopics[topic]["address"], c.CONTROL_PLANE_PORT))

    def addDiscoveredTopic(self, addr, payload):
        if payload[0] != "":
            [topic, port] = payload
            if topic not in self.discoveredTopics:
                self.discoveredTopics[topic] = {"address": addr[0], "port": port, "registered": False}
                #tell front end success
                print("discover success ", self.discoveredTopics)
            else:
                #tell front end fail
                print("discover fail")

    # def sendAck(self, addr, ackNum):
    #     ackPacket = self.createPacket("SEND_ACK", ackNum) #TODO: ADDR IS A PLACEHOLDER
    #     return self.controlSocket.sendto(ackPacket, (addr, c.CONTROL_PLANE_PORT))

    # by separating the receive calls, we dont have to encode so much information in our packets
    # packet structure: hash -- payload
    def receiveDiscovery(self):
        """
            Receives packets from the publisher and stores the information in the
            subscriber. If it does not receive anything after 5 seconds then it will simply return
            an empty list
            ** Currently only does registration **
        """
        start = time.time()
        self.controlSocket.settimeout(5)
        try:
            while True:
                # If the total time exceeds 5 seconds we end
                end = time.time()
                if end - start > 5:
                    self.controlSocket.settimeout(60)
                    break

                rawData, addr = self.controlSocket.recvfrom(2048)
                # If we receive our own packet we don't care
                if addr[0] == self.local_ip:
                    continue

                hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

                # if not corrupted packet
                if c.verifyPacket(hash, payload):
                    payload = payload.decode()
                    payload = payload.split("  ")
                    # Convert from string to list representation
                    print(payload)
                    payload[1] = ast.literal_eval(payload[1])
                
                if payload[0] == c.TOPIC_DISCOVERY:
                    self.addDiscoveredTopic(addr, payload[1])
                else:
                    print('something wrong you should not be here')

        except socket.timeout:
            # Case where there is nothing I will just time out
            self.controlSocket.settimeout(60)
            return False

        # Indicates the end of time allocated
        return True

    def registerTopic(self, topic):
            # need try catch
            port = self.discoveredTopics[topic]["port"]
            addr = self.discoveredTopics[topic]["address"]
            # topicSocket = SubscriberSlave(addr, port)
            # self.socketsToListenTo.append(topicSocket)
            self.registeredTopics[topic] = {"address": addr, "port": port}
            self.discoveredTopics[topic]["registered"] = True
            #tell front end success
            print("register success", self.registeredTopics)


    def getDiscoveredTopics(self):
        """
            Returns the discovered topics in a form of a list
        """
        return list(self.discoveredTopics.keys())

    def discoverTopics(self):
        # for i in range(c.RETRY_POLICY): # use timer to space discovery by 30s or smth
            self.sendTopicDiscovery()
            print('sent discovery')
            received = self.receiveDiscovery()
            # received is True if there is topics discovered
            if received:
                print('this is my discover table', self.discoveredTopics)
                print("="*50)
            else:
                # Call the front end to retrieve self.discoveredTopics
                print("No other topics were found, finish discovery")

    def executeSlave(self, addr, port):
        print("Created slave on ", addr, port)
        slave = SubscriberSlave(addr, port)
        while True:
            img = slave.receive()
            if self.frontEndListening == addr:
                #TODO: Let front end display this image
                print("Front end displays image")
            

    def start(self):
        self.discoverTopics()
        print(self.discoveredTopics)

        for topic in self.discoveredTopics:
            self.registerTopic(topic)
            self.sendTopicRegistration(topic)
            dataPlaneThread = threading.Thread(target=self.executeSlave, 
                    args=(self.discoveredTopics[topic]["address"], 
                        self.discoveredTopics[topic]["port"]))
            dataPlaneThread.daemon = True
            dataPlaneThread.start()

            print('this is my discover table', self.discoveredTopics)
            print('this is my registered table', self.registeredTopics)
            print("="*50)
        

        # ready, _, _ = select(self.socketsToListenTo, [], [])
        # for r in ready:
        #     # destAddress = self.r.getsockname()[0]
        #     self.data_receive(r)
                

if __name__ == "__main__":
    subscriber = SubscriberManager()
    subscriber.start()
