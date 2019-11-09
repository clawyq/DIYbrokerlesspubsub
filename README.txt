Pubsub without an intermediary broker.

Exchange meta-information over control plane, actual information on the data plane.

Meta-information includes the topic that is published, address and port from which 
a subscriber and publisher can identify the topic.

As a subscriber, I will interact with the control plane for:
  - topic discovery
  --- broadcasted so the publishers can send me their topics.
  --- fired after a regular interval
  - topic registration, 
  --- directed to the specific publisher I wish to listen to.
  --- fired after receiving user input expressing a want to listen to this topic.

As a publisher, I will interact with the control plane for:
  - topic meta-information, which is .
  --- carries information like topic name, my own IP and dedicated port for this topic.
  --- fired in response to a topic discovery message

As a subscriber, I will interact with the data plane for:
  - acknowledgement, to ack that a packet carrying information isnt corrupted or dropped

As a publisher, I will interact with the data plane for:
  - image transmission, which will be multicasted to the list of subscribers listening to my topic

Questions to ponder (301019 1800):
1. is there a way i can stop receiving my own broadcast message
  - workaround is troublesome
  --- recvfrom => check IP => if me call recvfrom again
2. what is the best way to listen to all these information for both P/S?
  - select library? run in a loop?
  - multithreaded program and use another class which runs in parallel solely dedicated to a specific plane
  --- 1 manager in charge of control plane, n slaves in charge of data plane

Topic Discovery(Assumption that publisher is there):
1. Subscriber comes in and broadcast topic discovery packet for 5 seconds.
2. Subscriber waits and listens for incoming reply. If there is no reply, then there
is a timeout else we will add to topic to a dictionary of discovered topics
3. After 5 seconds, the subscriber sends a registration packet to all the publisher and gets an ack back.
4. The subscriber then spawns a slave for each publisher
