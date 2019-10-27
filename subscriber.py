import socket
import constants as c
from select import select
from time import sleep
from random import randint
from copy import deepcopy

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
        self.seqNums = {}

    # packets that a subscriber should send includes ACKs and table information
    # packet structure: hash -- ID -- type (ack, table info) -- payload (ack num, table information)
    def createPacket(self, type):
        payload = f"{c.SUBSCRIBER}  {type}  "
        if type == "SEND_NWINFO":
            payload += f"{self.topics}"
        utfPayload = payload.encode()
        hash = c.generateHash(utfPayload)
        return hash + utfPayload

    # sending tables - if no one replies, i use my own. If someone replies, update my table according to his
    def sendNetworkInfo(self, socket):
        networkInfoPacket = self.createPacket("SEND_NWINFO")
        return socket.sendto(networkInfoPacket, ('<broadcast>', c.CONTROL_PLANE_PORT))

    def sendAck(self, socket, addr):
        ackPacket = self.createPacket("SEND_ACK")
        return socket.sendto(ackPacket, (addr, c.CONTROL_PLANE_PORT))

    # packet structure: hash -- type (table info, topic registrations, image) -- payload
    def receive(self, socket):
        rawData, addr = socket.recvfrom(1024)
        # TODO: ADD A FILTER TO THROW AWAY PACKETS FROM MYSELF

        hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

        # if not corrupted packet
        if c.verifyPacket(hash, payload):
            payload = payload.decode()
            payload = payload.split("  ")
            print(payload)
            # if the message came from a subscriber, it must be a table!
            if payload[0] == c.SUBSCRIBER: 
                self.tables = deepcopy(payload[1])
                return True
            else:
                # register topics
                if payload[1] == c.TOPIC_REGISTRATION:
                    table = payload[2]
                    for key in table.keys():
                        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        dataSocket.bind((addr, table[key]))
                        self.socketsToListenTo.append(dataSocket)
                        self.topics[key] = table[key]

                # TODO: ack this shit
                else:
                    return True
        return False

    def start(self):
        for i in range(c.RETRY_POLICY):
            self.sendNetworkInfo(self.controlSocket)
            print('hi')
            if (self.receive(self.controlSocket)): break
        print(f'this is my fking table {self.topics}')
        while True:
            print(self.socketsToListenTo)
            ready, _, _ = select(self.socketsToListenTo, [], [])
            for r in ready:
                client, address = r.accept()

if __name__ == "__main__":
    subscriber = Subscriber()
    subscriber.start()