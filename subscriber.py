import socket
import os
import time
import constants as c
import cv2
import zlib
import pickle
import datetime
import threading
import logging

# This class models a subscriber slave that registers on and  listens for
# new data sent by the publisher on the data plane.
class SubscriberSlave():
    def __init__(self, topic):
        self.topic = topic
        self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.currSeqNum = 0

    # Actively listens for new image sent to the subscriber.
    def listenForNewImage(self):
        while True:
            success, imageData = self.receive()
            if success:
                self.storeImage(imageData)

    # Registers with the publisher by sending a TOPIC_REGISTRATION packet.
    def registerTopic(self, addr):
        topicRegistrationPacket = createPacket(c.TOPIC_REGISTRATION, 0, 0, "")

        registerSuccess = False
        attempts = 0
        while not registerSuccess and attempts < c.RETRY_POLICY:
            self.dataSocket.sendto(topicRegistrationPacket, addr)
            registerSuccess, data = self.receive()
            attempts += 1

        return registerSuccess

    # Ensures that data is susccessfully received.
    # Returns whether the data was successfully received and
    # a buffer containing the received data (a tuple).
    def receive(self):
        hasMore = True
        expectedSeqNum = 0
        buffer = bytearray()

        while hasMore:
            rawData, addr = self.dataSocket.recvfrom(2048)
            hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

            # if not corrupted packet
            if not c.verifyPacket(hash, payload):
                self.ack(expectedSeqNum, addr)
                continue

            pktType, hasMore, seqNum, data = handlePayload(payload)
            if pktType == c.ACK:
                return data == str(self.currSeqNum), None
            elif pktType == c.IMAGE:
                if seqNum == expectedSeqNum:
                    logging.info(' Successfully received image pkt seqnum: ' + str(seqNum))
                    buffer += data

                    expectedSeqNum += len(data)
                    self.ack(expectedSeqNum, addr)
                else:
                    self.ack(expectedSeqNum, addr)
            else:
                logging.error(' Unhandled packet type received on subscriber')

        logging.info(' Successfully received complete image payload')
        return (True, buffer)


    def ack(self, ackSeqNum, addr):
        ackPkt = createPacket(c.ACK, 0, self.currSeqNum, str(ackSeqNum))
        self.dataSocket.sendto(ackPkt, addr)

    # Checks if the packet is the expected packet.
    def checkValidPacket(self, expectedSeqNum, actualSeqNum):
        return expectedSeqNum == actualSeqNum

    # Saves the image to the local machine, in the format <topic>-<datetime>.jpg
    def storeImage(self, imageBytes):
        originalFrames = zlib.decompress(imageBytes)
        recvData = pickle.loads(originalFrames, fix_imports=True, encoding="bytes")
        recvImage = cv2.imdecode(recvData, cv2.IMREAD_COLOR)

        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        filename = self.topic \
                   + '-' \
                   + datetime.datetime.now().strftime('%Y-%m-%d%H-%M-%S') \
                   + '.jpg'
        if not cv2.imwrite(os.path.join(ROOT_DIR, 'images', filename), recvImage):
            logging.error(' Failed to save image')
        else:
            logging.info(' Image saved!')


# This class models a subscriber that listens on the control plane.
# Upon detecting new publisher, it will spawn new SubscriberSlave to
# register and receive information from that publisher.
class SubscriberManager:
    def __init__(self):
        self.local_ip = self._getLocalIP()
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.controlSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.controlSocket.settimeout(5)
        self.controlSocket.bind((self.local_ip, c.CONTROL_PLANE_PORT))

        self.discoveredTopics = {}

        self.lock = threading.Lock()

    def _getLocalIP(self):
        """
            Hacky way to get the local IP
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        return ip

    # Broadcasts a TOPIC_DISCOVERY (query) packet to discover any new publishers on the network.
    def sendTopicDiscovery(self):
        topicDiscoveryPacket = createPacket(c.TOPIC_DISCOVERY, 0, 0, "")
        return self.controlSocket.sendto(topicDiscoveryPacket,
                                         ('<broadcast>', c.CONTROL_PLANE_PORT))

    # Adds information on a newly discovered topic.
    def addDiscoveredTopic(self, addr, topic):
        if topic != "":
            if topic not in self.discoveredTopics:
                self.discoveredTopics[topic] = {"address": addr[0],
                                                "port": addr[1],
                                                "registered": False,
                                                "slave": None}
                #tell front end success
                logging.info(" Topic Discovery success!\n ", self.discoveredTopics)
            else:
                #tell front end fail
                logging.info(" Topic Discovery failed")

    # Listens for TOPIC_INFO replies from publishers on the network,
    # in response to the TOPIC_DISCOVERY packet sent earlier.
    def receiveDiscovery(self):
        """
            Receives packets from the publisher and stores the information in the
            subscriber. If it does not receive anything after 5 seconds then it will simply return
            an empty list
            ** Currently only does registration **
        """
        start = time.time()
        try:
            while True:
                # If the total time exceeds 5 seconds we end
                end = time.time()
                if end - start > 5:
                    break

                rawData, addr = self.controlSocket.recvfrom(2048)
                # If we receive our own packet we don't care
                if addr[0] == self.local_ip:
                    continue

                hash, payload = rawData[0:c.HASHSIZE], rawData[c.HASHSIZE:]

                # if not corrupted packet
                if c.verifyPacket(hash, payload):
                    typeFlag, moreFlag, seqNum, data = handlePayload(payload)

                    if typeFlag == c.TOPIC_INFO:
                        self.addDiscoveredTopic(addr, data)
                    else:
                        logging.error(' Something wrong you should not be here')

        except socket.timeout:
            # Case where there is nothing I will just time out
            return False

        # Indicates the end of time allocated
        return True

    # Returns the discovered topics in a form of a list
    def getDiscoveredTopics(self):
        return list(self.discoveredTopics.keys())

    # Scans the local network for new publishers/topics to register to.
    def discoverTopics(self):
        print(" Start topic discovery...")
        # for i in range(c.RETRY_POLICY): # use timer to space discovery by 30s or smth
        self.sendTopicDiscovery()
        print(' Sent discovery')
        received = self.receiveDiscovery()
        # received is True if there is topics discovered
        if received:
            print(' This is my discover table\n ', self.discoveredTopics)
        else:
            # Call the front end to retrieve self.discoveredTopics
            print(" No new topics were found")

        print(" End of discovery")

    def executeSlave(self, topic, addr):
        logging.info(" created slave to listen on topic: " + topic)
        slave = SubscriberSlave(topic)
        registerSuccess = slave.registerTopic(addr)

        if not registerSuccess:
            logging.info(" slave failed to register to topic [" + topic + "] at " + str(addr))
            self.lock.acquire()
            self.discoveredTopics.pop(topic)
            self.lock.release()
            return
        while True:
            slave.listenForNewImage()
    
    def registerTopics(self):
        self.lock.acquire()
        for topic in self.discoveredTopics:
            if not self.discoveredTopics[topic]["registered"]:
                dataPlaneThread = threading.Thread(target=self.executeSlave,
                                                    args=(topic,
                                                            (self.discoveredTopics[topic]["address"],
                                                            self.discoveredTopics[topic]["port"])))
                dataPlaneThread.daemon = True
                dataPlaneThread.start()

                self.discoveredTopics[topic]["registered"] = True
                self.discoveredTopics[topic]["slave"] = dataPlaneThread.getName()
        self.lock.release()

    def registerTopic(self, topic):
        self.lock.acquire()
        if topic in self.discoveredTopics:
            if not self.discoveredTopics[topic]["registered"]:
                dataPlaneThread = threading.Thread(target=self.executeSlave,
                                                    args=(topic,
                                                            (self.discoveredTopics[topic]["address"],
                                                            self.discoveredTopics[topic]["port"])))
                dataPlaneThread.daemon = True
                dataPlaneThread.start()

                self.discoveredTopics[topic]["registered"] = True
                self.discoveredTopics[topic]["slave"] = dataPlaneThread.getName()

        self.lock.release()

        

    def start(self):
        while True:
            self.discoverTopics()
            self.registerTopics()

            time.sleep(c.REFRESH_RATE)


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
def createPacket(type, more, seqNum, data):
    typeFlagInBytes = int.to_bytes(type, byteorder="big", length=3)
    moreFlagInBytes = int.to_bytes(more, byteorder="big", length=1)
    seqNumInBytes = int.to_bytes(seqNum, byteorder="big", length=4)

    if type != c.IMAGE:
        data = data.encode()

    utfPayload = typeFlagInBytes + moreFlagInBytes + seqNumInBytes + data
    hash = c.generateHash(utfPayload)
    return hash + utfPayload


# Process the payload and returns the individual fields as a tuple.
#
# Precondition: payload excludes hash value
def handlePayload(payload):
    typeFlag = int.from_bytes(payload[:3], byteorder="big")
    moreFlag = int.from_bytes(payload[3:4], byteorder="big")
    seqNum = int.from_bytes(payload[4:8], byteorder="big")
    data = payload[8:]

    if typeFlag != c.IMAGE:
        data = data.decode()

    return typeFlag, moreFlag, seqNum, data

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    subscriber = SubscriberManager()
    subscriber.start()
