import hashlib
# META INFORMATION
CONTROL_PLANE_PORT = 9853
RETRY_POLICY = 3
TIMEOUT = 2000 # IN MILLISECONDS => 2 SECONDS
HASHSIZE = 16
CAPACITY = 571 # first 4 bytes for seq num and 1 byte for "MORE" flag
REFRESH_RATE = 5

SUBSCRIBER = '1'
PUBLISHER = '0'
TOPIC_INFO = '0'
IMAGE = '1'

# PACKET STRUCTURE
ACK = '1'
TOPIC_DISCOVERY = '0'
TOPIC_REGISTRATION = '1'
ACK = '2'


def generateHash(payload):
    return hashlib.md5(payload).digest()

def verifyPacket(hash, payload):
    return generateHash(payload) == hash