import binascii
import struct
import sys

import random
import copy
import collections
import threading
import time

from const import (SOCK352_SYN, SOCK352_ACK, SOCK352_RESET, MAX_RDP_SEQ_NO, MAX_RDP_PACKET_LENGTH, \
                  RDP_HEADER_STRUCT, RDP_TIMEOUT, CONNECTION_ESTABLISHED, CONNECTION_SYN_SENT,     \
                  CONNECTION_SYN_RECIEVED)
from transport import UDPTransport
from packet import RDP_HEADER_SIZE, RDPPacket
from connection import Connection

# Bind UDP to all interfaces
UDP_HOST = ''

MAX_PAYLOAD_SIZE = MAX_RDP_PACKET_LENGTH - RDP_HEADER_SIZE

udp_transport = None

def init(TX_port, RX_port):
    global udp_transport

    TX_port = int(TX_port)
    RX_port = int(RX_port)
        
    udp_transport = UDPTransport(UDP_HOST, TX_port, RX_port)
    udp_transport.bind()

def ack_timeout(connection, ack_no, retransmit):
    time.sleep(RDP_TIMEOUT)

    connection.mutex.acquire()
    last_ack = connection.last_ack
    connection.mutex.release()

    if last_ack >= ack_no:
        return
    
    # houston we have a problem
    # connection.mutex.acquire()
    # retransmit[0] = 1
    # connection.mutex.release()

def ack_listener(connection, expected_last_ack):
    global udp_transport
    
    bytes_available = collections.deque(maxlen=MAX_RDP_PACKET_LENGTH)

    while True:
        # Reduce number of syscalls
        if len(bytes_available) < RDP_HEADER_SIZE:
            _, request = udp_transport.recv(MAX_RDP_PACKET_LENGTH)
            data, _ = request
            bytes_available.extend(data)
        
        header_bytes = bytes([bytes_available.popleft() for _ in range(RDP_HEADER_SIZE)])

        packet_header = RDPPacket()
        packet_header.from_bytes(header_bytes)

        # TODO: Verify not RESET
        # TODO: Verify not FIN

        # Verify zero payload
        assert packet_header.payload_len == 0

        ack_no = packet_header.ack_no

        connection.mutex.acquire()
        if ack_no > connection.last_ack:
            connection.last_ack = ack_no
        connection.mutex.release()

        if ack_no >= expected_last_ack:
            break
    
class socket:
    def __init__(self):
        return
    
    def bind(self, address):
        return 

    def connect(self, address):
        self.dest_address = address
        # Establish three way handshake
        self.connection = Connection()
        while True:
            # Send SYN
            ISN = random.randint(0, MAX_RDP_SEQ_NO)
            syn_packet = RDPPacket(flags=SOCK352_SYN, sequence_no=ISN)
            self.send_packet(syn_packet, self.dest_address)

            self.connection.state = CONNECTION_SYN_SENT
            self.connection.current_sn = ISN + 1

            # Block for SYN, ACK
            err, response = udp_transport.recv(RDP_HEADER_SIZE, timeout=RDP_TIMEOUT)
            if err: continue

            data, self.dest_address = response
            syn_ack_packet = RDPPacket()
            syn_ack_packet.from_bytes(data)

            # Verify not RESET
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

            # Connection Established
            self.connection.state = CONNECTION_ESTABLISHED
            self.connection.last_ack_no = syn_ack_packet.ack_no
            self.connection.peer_sn = syn_ack_packet.sequence_no + 1
            
            # Send ACK
            seq_no = self.connection.current_sn
            ack_no = self.connection.peer_sn
            ack_packet = RDPPacket(flags=SOCK352_ACK, sequence_no=seq_no, ack_no=ack_no)
            self.send_packet(ack_packet, self.dest_address)
            break
        return 
    
    def listen(self, backlog):
        return

    def accept(self):
        client_socket = socket()
        self.dest_address = None

        self.connection = None
        # Establish three way handshake
        while True:
            # Block for SYN
            _, request = udp_transport.recv(RDP_HEADER_SIZE)

            data, self.dest_address = request
            syn_packet = RDPPacket()
            syn_packet.from_bytes(data)

            # Verify is SYN packet
            if not syn_packet.flags & SOCK352_SYN:
                continue

            ISN = random.randint(0, MAX_RDP_SEQ_NO)
            ack_no = syn_packet.sequence_no + 1

            # Reset if connection exists
            if self.connection and self.connection.state == CONNECTION_ESTABLISHED:
                reset_packet = RDPPacket(flags=SOCK352_SYN | SOCK352_ACK | SOCK352_RESET, sequence_no=ISN, ack_no=ack_no)
                self.send_packet(reset_packet, self.dest_address)
                continue
            
            # New connection setup
            self.connection = Connection()

            self.connection.state = CONNECTION_SYN_RECIEVED
            self.connection.current_sn = ISN + 1
            self.connection.peer_sn = syn_packet.sequence_no + 1

            # Send SYN, ACK
            ack_no = self.connection.peer_sn
            syn_ack_packet = RDPPacket(flags=SOCK352_SYN | SOCK352_ACK, sequence_no=ISN, ack_no=ack_no)
            self.send_packet(syn_ack_packet, self.dest_address)
            
            # Block for ACK
            err, response = udp_transport.recv(RDP_HEADER_SIZE, timeout=RDP_TIMEOUT)
            if err: continue

            data, _ = response
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
            client_socket.connection = Connection()
            
            client_socket.connection.state = self.connection.state
            client_socket.connection.current_sn = self.connection.current_sn
            client_socket.connection.last_ack = self.connection.last_ack
            client_socket.connection.peer_sn = self.connection.peer_sn

            client_socket.dest_address = self.dest_address
            break

        client_address = self.dest_address
        return (client_socket, client_address)
    
    def close(self):
        return 

    def send(self, buffer):
        bytes_ack = 0
        buffer_size = len(buffer)

        expected_last_ack = self.connection.current_sn + buffer_size

        args = (self.connection, expected_last_ack)
        ack_listener_thread = threading.Thread(
            target=ack_listener, 
            args=args
        )
        ack_listener_thread.start()

        offset = 0
        while bytes_ack < buffer_size:
            data = buffer[offset:offset+MAX_PAYLOAD_SIZE]
            payload_size = len(data)

            # Send data packet
            seq_no = self.connection.current_sn
            ack_no = self.connection.peer_sn
            data_packet = RDPPacket(data=data, sequence_no=seq_no, ack_no=ack_no)
            self.send_packet(data_packet, self.dest_address)

            # Update current sequence number
            self.connection.current_sn += payload_size
            offset += payload_size

            bytes_ack += payload_size

        return bytes_ack

    def recv(self, nbytes):
        bytes_received = bytearray()
        bytes_available = collections.deque(maxlen=MAX_RDP_PACKET_LENGTH)

        peer_last_ack = self.connection.peer_sn

        # offset = 0
        while len(bytes_received) != nbytes:
            # Reduce number of syscalls
            if len(bytes_available) < RDP_HEADER_SIZE:
                _, request = udp_transport.recv(MAX_RDP_PACKET_LENGTH)
                data, _ = request
                bytes_available.extend(data)

            header_bytes = bytes([bytes_available.popleft() for _ in range(RDP_HEADER_SIZE)])

            packet_header = RDPPacket()
            packet_header.from_bytes(header_bytes)

            # TODO: Verify not RESET
            # TODO: Verify not FIN

            peer_sn = packet_header.sequence_no

            # Go Back N (GBN) discards out-of-order packets
            if peer_sn != self.connection.peer_sn:
                print(f"Missing {self.connection.peer_sn}, Sent ACK for {peer_last_ack}")
                
                # Send ACK for last in-order packet
                seq_no = self.connection.current_sn
                ack_packet = RDPPacket(flags=SOCK352_ACK, sequence_no=seq_no, ack_no=peer_last_ack)
                self.send_packet(ack_packet, self.dest_address)

                # Discard packet
                payload_size = packet_header.payload_len
                for _ in range(payload_size):
                    bytes_available.popleft()
                continue

            payload_size = packet_header.payload_len

            if len(bytes_available) < payload_size:
                _, request = udp_transport.recv(MAX_RDP_PACKET_LENGTH)
                data, _ = request
                bytes_available.extend(data)

            payload = [bytes_available.popleft() for _ in range(payload_size)]
            bytes_received.extend(payload)

            peer_last_ack = self.connection.peer_sn
            self.connection.peer_sn += payload_size
            
            # Send ACK for last packet
            seq_no = self.connection.current_sn
            ack_no = self.connection.peer_sn
            ack_packet = RDPPacket(flags=SOCK352_ACK, sequence_no=seq_no, ack_no=ack_no)
            self.send_packet(ack_packet, self.dest_address)         

        return bytes_received

    def send_packet(self, packet, address):
        host, _ = address
        udp_transport.send(packet.to_bytes(), host)
