import binascii
import struct
import sys

import random
import copy

from const import SOCK352_SYN, SOCK352_ACK, SOCK352_RESET, MAX_TCP_SEQ_NO, PACKET_HEADER_STRUCT, \
                  RDP_TIMEOUT, CONNECTION_ESTABLISHED, CONNECTION_SYN_SENT, CONNECTION_SYN_RECIEVED
from transport import UDPTransport
from packet import RDP_HEADER_SIZE, RDPPacket
from connection import Connection

# Bind UDP to all interfaces
UDP_HOST = ''

udp_transport = None

def init(TX_port, RX_port):
    TX_port = int(TX_port)
    RX_port = int(RX_port)
    
    global udp_transport
    udp_transport = UDPTransport(UDP_HOST, TX_port, RX_port)
    udp_transport.bind()
    
class socket:
    def __init__(self):
        return
    
    def bind(self, address):
        return 

    def connect(self, address):
        # Establish three way handshake
        self.connection = Connection()
        while True:
            # Send SYN
            ISN = random.randint(0, MAX_TCP_SEQ_NO)
            syn_packet = RDPPacket(flags=SOCK352_SYN, sequence_no=ISN)
            self.send_packet(syn_packet, address)

            self.connection.state = CONNECTION_SYN_SENT
            self.connection.current_sn = ISN + 1

            # Block for SYN, ACK
            err, response = udp_transport.recv(RDP_HEADER_SIZE, timeout=RDP_TIMEOUT)
            if err: continue

            data, address = response
            syn_ack_packet = RDPPacket()
            syn_ack_packet.from_bytes(data)

            # Verify did not reset
            if syn_ack_packet.flags & SOCK352_RESET:
                continue

            # Verify is ACK packet
            if not syn_ack_packet.flags & SOCK352_ACK:
                continue

            # Verify correct ACK number
            if syn_ack_packet.ack_no != self.connection.current_sn:
                continue

            # Verify is SYN packet
            if not syn_ack_packet.flags & SOCK352_SYN:
                continue

            self.connection.state = CONNECTION_ESTABLISHED
            self.connection.last_ack_no = syn_ack_packet.ack_no
            self.connection.peer_sn = syn_ack_packet.sequence_no + 1
            
            # Send ACK
            seq_no = self.connection.current_sn
            ack_no = self.connection.peer_sn
            ack_packet = RDPPacket(flags=SOCK352_ACK, sequence_no=seq_no, ack_no=ack_no)
            self.send_packet(ack_packet, address)

            # Connection Established
            print("Connection Established")
            break
        return 
    
    def listen(self, backlog):
        return

    def accept(self):
        self.connection = None
        clientsocket = socket()
        address = None
        # Establish three way handshake
        while True:
            # Block for SYN
            _, request = udp_transport.recv(RDP_HEADER_SIZE)

            data, address = request
            syn_packet = RDPPacket()
            syn_packet.from_bytes(data)

            # Verify is SYN packet
            if not syn_packet.flags & SOCK352_SYN:
                continue

            ISN = random.randint(0, MAX_TCP_SEQ_NO)
            ack_no = syn_packet.sequence_no + 1

            # Reset if connection exists
            if self.connection and self.connection.state == CONNECTION_ESTABLISHED:
                reset_packet = RDPPacket(flags=SOCK352_SYN | SOCK352_ACK | SOCK352_RESET, sequence_no=ISN, ack_no=ack_no)
                self.send_packet(reset_packet, address)
                continue
            
            # New connection
            self.connection = Connection()

            self.connection.state = CONNECTION_SYN_RECIEVED
            self.connection.current_sn = ISN + 1
            self.connection.peer_sn = syn_packet.sequence_no + 1

            # Send SYN, ACK
            ack_no = self.connection.peer_sn
            syn_ack_packet = RDPPacket(flags=SOCK352_SYN | SOCK352_ACK, sequence_no=ISN, ack_no=ack_no)
            self.send_packet(syn_ack_packet, address)
            
            # Block for ACK
            err, response = udp_transport.recv(RDP_HEADER_SIZE, timeout=RDP_TIMEOUT)
            if err: continue

            data, address = response
            ack_packet = RDPPacket()
            ack_packet.from_bytes(data)

            # Verify is ACK packet
            if not ack_packet.flags & SOCK352_ACK:
                continue

            # Verify correct ACK number
            if ack_packet.ack_no != self.connection.current_sn:
                continue

            self.connection.last_ack_no = ack_packet.ack_no

            # Connection Established
            self.connection.state = CONNECTION_ESTABLISHED
            clientsocket.connection = copy.deepcopy(self.connection)
            print("Connection Established")
            break

        return (clientsocket,address)
    
    def close(self):   # fill in your code here 
        return 

    def send(self, buffer):
        bytessent = 0     # fill in your code here
        return bytessent

    def send_packet(self, packet, address):
        host, _ = address
        udp_transport.send(packet.to_bytes(), host)

    def recv(self, nbytes):
        bytesreceived = 0     # fill in your code here
        return bytesreceived
