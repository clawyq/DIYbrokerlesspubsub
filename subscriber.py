import socket
import constants as c
from select import select
from time import sleep
from random import randint

class Subscriber:
    def __init__(self):
        # self.meaddress = socket.gethostbyname(socket.gethostname())
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.controlSocket.settimeout(3)
        self.controlSocket.bind(("", c.CONTROL_PLANE_PORT))
        
        self.socketsToListenTo = [self.controlSocket]

        # keeps track of topic/ports
        self.topics = {}
        
        # keeps track of ports/seqNum
        self.publishers = {}

    #  a subscriber should send ACKs and topic discoveries and topic registrations
    # packet structure: hash -- P/S -- type -- ackNum
    def createPacket(self, type, message):
        payload = ""
        if type != "TOPIC_DISCOVERY":
            payload += f"{message}"
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # sending tables - if no one replies, default {}. If a publisher replies, update my table
    def topicDiscovery(self, socket):
        topicDiscoveryPacket = self.createPacket('TOPIC_DISCOVERY', "")
        return socket.sendto(topicDiscoveryPacket, ('<broadcast>', c.CONTROL_PLANE_PORT))

    def topicRegistration(self, socket, topic):
        topicRegistrationPacket = self.createPacket("TOPIC_REGISTRATION", topic)
        return socket.sendto(topicRegistrationPacket, ('<broadcast>', c.CONTROL_PLANE_PORT))

    def sendAck(self, socket, addr):
        ackPacket = self.createPacket("SEND_ACK", addr) #TODO: ADDR IS A PLACEHOLDER
        return socket.sendto(ackPacket, (addr, c.CONTROL_PLANE_PORT))

    # by separating the receive calls, we dont have to encode so much information in our packets
    # packet structure: hash -- payload
    def control_receive(self, socket):
        rawData, addr = socket.recvfrom(1024)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        # if not corrupted packet
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
            print(payload)

            if payload[0] != "":
                [topic, port] = payload
                if topic not in self.topics:
                    dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    dataSocket.bind((addr, port))
                    self.socketsToListenTo.append(dataSocket)
                    self.topics[topic] = port
                    return True
        return False

    def data_receive(self, socket, image):
        rawData, addr = socket.recvfrom(1024)
        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        # if not corrupted packet
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
            print(payload)
        
            if payload:
                # have to insert ack logic
                newImage = image + payload
                return newImage
        return False

    def start(self):
        app = Flask
        for i in range(c.RETRY_POLICY): # use timr to space discovery by 30s or smth
            self.topicDiscovery(self.controlSocket)
            self.control_receive(self.controlSocket)
        print(f'this is my fking table {self.topics}')
        ready, _, _ = select(self.socketsToListenTo, [], [])
        for r in ready:
            # destAddress = self.r.getsockname()[0]
            self.data_receive(r)
            

if __name__ == "__main__":
    subscriber = Subscriber()
    subscriber.start()
