import socket
import ast
import constants as c
from select import select
from time import sleep
from random import randint as ri
from copy import deepcopy

class SubscriberSlave:
    def __init__(self, addr, port):
        self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dataSocket.bind((addr, port))
        self.initialSeqNum = 0
        self.image = ""
    
    def receive(self, type):
        rawData, addr = self.controlSocket.recvfrom(2048)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        # if not corrupted packet
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
        
        # ack logic goes here
        # upon finish, call returnImage

    def returnImage(self):
        # pass this to the manager for him to pass to the frontEnd
        pass

class SubscriberManager:
    def __init__(self):
        # self.meaddress = socket.gethostbyname(socket.gethostname())
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.controlSocket.settimeout(60)
        self.controlSocket.bind(("127.0.0.2", c.CONTROL_PLANE_PORT))
        
        # socket objects to listen to
        self.socketsToListenTo = [self.controlSocket]

        # keeps track of topic: {addr, port}
        self.registeredTopics = {}

        # keeps track of what is available, mainly to show frontend topic: {address, port, registered?}
        self.discoveredTopics = {}

    #  a subscriber should send ACKs and topic discoveries and topic registrations
    # packet structure: hash -- P/S -- type -- ackNum
    def createPacket(self, type, message):
        payload = f"{type}  "
        if type != c.TOPIC_DISCOVERY:
            payload += f"{message}"
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # sending tables - if no one replies, default {}. If a publisher replies, update my table
    def sendTopicDiscovery(self):
        topicDiscoveryPacket = self.createPacket(c.TOPIC_DISCOVERY, "")
        return self.controlSocket.sendto(topicDiscoveryPacket, ('localhost', c.CONTROL_PLANE_PORT))

    def sendTopicRegistration(self, topic):
        topicRegistrationPacket = self.createPacket(c.TOPIC_REGISTRATION, topic)
        return self.controlSocket.sendto(topicRegistrationPacket, (self.discoveredTopics[topic]["address"], c.CONTROL_PLANE_PORT))

    # def sendAck(self, addr, ackNum):
    #     ackPacket = self.createPacket("SEND_ACK", ackNum) #TODO: ADDR IS A PLACEHOLDER
    #     return self.controlSocket.sendto(ackPacket, (addr, c.CONTROL_PLANE_PORT))

    # by separating the receive calls, we dont have to encode so much information in our packets
    # packet structure: hash -- payload
    def receive(self):
        rawData, addr = self.controlSocket.recvfrom(2048)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        # if not corrupted packet
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
            # Convert from string to list representation
            payload[1] = ast.literal_eval(payload[1])
        
        if payload[0] == c.TOPIC_DISCOVERY:
            self.discoverTopics(addr, payload[1])
        else:
            print('something wrong you should not be here')


    def registerTopic(self, topic):
            # need try catch
            port = self.discoveredTopics[topic]["port"]
            addr = self.discoveredTopics[topic]["address"]
            topicSocket = SubscriberSlave(addr, port)
            self.socketsToListenTo.append(topicSocket)
            self.registeredTopics[topic] = {"address": addr, "port": port}
            self.discoveredTopics[topic]["registered"] = True
            #tell front end success
            print(f"register success {self.registeredTopics}")

    def discoverTopics(self, addr, payload):
        if payload[0] != "":
            [topic, port] = payload
            if topic not in self.discoveredTopics:
                self.discoveredTopics[topic] = {"address": addr[0], "port": port, "registered": False}
                #tell front end success
                print(f"discover success {self.discoveredTopics}")
            else:
                #tell front end fail
                print("discover fail")

    def start(self):
        notListening = True
        while notListening:
        # for i in range(c.RETRY_POLICY): # use timer to space discovery by 30s or smth
            self.sendTopicDiscovery()
            print('sent discovery')
            self.receive()
            notListening = False
            print(f'this is my discover table {self.discoveredTopics}')
            print(f'this is my registered table {self.registeredTopics}')
            print("="*50)
        # testing
        for topic in self.discoveredTopics:
            self.registerTopic(topic)
            self.sendTopicRegistration(topic)
            print(f'this is my discover table {self.discoveredTopics}')
            print(f'this is my registered table {self.registeredTopics}')
            print("="*50)
        

        # ready, _, _ = select(self.socketsToListenTo, [], [])
        # for r in ready:
        #     # destAddress = self.r.getsockname()[0]
        #     self.data_receive(r)
                

if __name__ == "__main__":
    subscriber = SubscriberManager()
    subscriber.start()
    subscriber.sendTopicDiscovery()
    subscriber.receive()
