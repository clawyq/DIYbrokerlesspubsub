import hashlib
# META INFORMATION
CONTROL_PLANE_PORT = 9853
RETRY_POLICY = 3
TIMEOUT = 2000 # IN MILLISECONDS => 2 SECONDS
HASHSIZE = 16

SUBSCRIBER = '1'
PUBLISHER = '0'
TOPIC_REGISTRATION = '0'
ACTUAL_IMAGE = '1'

# PACKET STRUCTURE
ACK = '1'
REQUEST = '0'
REPLY = '1'

def generateHash(payload):
    return hashlib.md5(payload).digest()

def verifyPacket(hash, payload):
	return generateHash(payload) == hash