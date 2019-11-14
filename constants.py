import hashlib
# META INFORMATION
CONTROL_PLANE_PORT = 9853
RETRY_POLICY = 3
TIMEOUT = 2000 # IN MILLISECONDS => 2 SECONDS
HASHSIZE = 16
CAPACITY = 2024 # receive 2048 bytes, 16 bytes for hash, 1 byte for pkt type, 4 bytes for seq num, 1 byte for "MORE" flag
REFRESH_RATE = 120

SUBSCRIBER = '1'
PUBLISHER = '0'

# PACKET STRUCTURE TYPE
TOPIC_DISCOVERY = 0
TOPIC_REGISTRATION = 1
ACK = 2
IMAGE = 3
TOPIC_INFO = 4

def generateHash(payload):
    return hashlib.md5(payload).digest()

def verifyPacket(hash, payload):
    return generateHash(payload) == hash
