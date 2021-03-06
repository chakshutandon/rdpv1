import threading
import collections
import random


from const import (
    RDP_MAX_SEQ_NO,
    RDP_MAX_PACKET_LENGTH,
    RDP_MAX_RECEIVER_WINDOW,
    RDP_TIMEOUT,
    SOCK352_SYN,
    SOCK352_FIN,
    SOCK352_RESET,
    SOCK352_ACK,
    CONNECTION_DEFAULT,
    CONNECTION_SYN_SENT,
    CONNECTION_SYN_RECIEVED,
    CONNECTION_ESTABLISHED,
    PACKET_DROP_THRESHOLD)

from transport import UDPTransport
from packet import RDPPacket, RDP_HEADER_LENGTH
from connection import Connection

DEBUG = False

RDP_MAX_PAYLOAD_LENGTH = RDP_MAX_PACKET_LENGTH - RDP_HEADER_LENGTH

# Bind UDP to all interfaces
UDP_HOST = ''

udp_transport = None


def init(TX_port, RX_port):
    global udp_transport

    TX_port = int(TX_port)
    RX_port = int(RX_port)

    udp_transport = UDPTransport(UDP_HOST, TX_port, RX_port)
    udp_transport.bind()


def send_packet(packet, address):
    if DEBUG and random.uniform(0, 1) < PACKET_DROP_THRESHOLD:
        return
    # Test race condition closed udp_transport
    try:
        udp_transport.send(packet.to_bytes(), address)
    except BaseException:
        pass


def ack_timeout(
        connection,
        buffer,
        init_sn,
        dest_address,
        pause_transmission,
        stop_timer,
        msg):
    if not stop_timer.wait(RDP_TIMEOUT):
        # Timeout, resend data in buffer
        pause_transmission.set()

        connection.mutex.acquire()
        base = connection.base
        bound = connection.current_sn
        ack_no = connection.peer_sn

        if DEBUG:
            print(
                f"[ack_timeout] [calling thread = {msg}]: {vars(connection)}")

        connection.mutex.release()

        offset = base - init_sn
        while offset < (bound - init_sn):
            payload = buffer[offset:offset + RDP_MAX_PAYLOAD_LENGTH]
            payload_length = len(payload)

            if not payload_length:
                break

            # Send data packet
            data_packet = RDPPacket(
                data=payload, sequence_no=(offset + init_sn), ack_no=ack_no
            )
            send_packet(data_packet, dest_address)

            if DEBUG:
                print(f"[ack_timeout] Sent: {offset + init_sn}")

            offset += payload_length

        threading.Thread(
            target=ack_timeout,
            args=(
                connection,
                buffer,
                init_sn,
                dest_address,
                pause_transmission,
                stop_timer,
                "ack_timeout")).start()

        pause_transmission.clear()


def ack_listener(
        connection,
        buffer,
        init_sn,
        dest_address,
        pause_transmission,
        stop_timer,
        final_ack_no):
    while True:
        _, request = udp_transport.recv(RDP_HEADER_LENGTH)
        data, _ = request

        packet_header = RDPPacket()
        packet_header.from_bytes(data)

        if DEBUG:
            print(f"[ack_listener] Got ACK: {packet_header.ack_no}")

        connection.mutex.acquire()

        if connection.base < packet_header.ack_no:
            bytes_ack = packet_header.ack_no - connection.base
            connection.base = packet_header.ack_no
            connection.in_flight -= bytes_ack

        connection.recv_window = packet_header.window

        stop_timer.set()

        if connection.base != connection.current_sn:
            stop_timer = threading.Event()
            threading.Thread(
                target=ack_timeout,
                args=(
                    connection,
                    buffer,
                    init_sn,
                    dest_address,
                    pause_transmission,
                    stop_timer,
                    "ack_listener"
                )
            ).start()
        connection.mutex.release()

        if packet_header.ack_no == final_ack_no:
            break


def packet_listener(connection, buffer, dest_address, stop_event):
    bytes_available = collections.deque(maxlen=RDP_MAX_PACKET_LENGTH)
    while True:
        if stop_event.is_set():
            break
        if len(bytes_available) < RDP_HEADER_LENGTH:
            err, request = udp_transport.recv(
                RDP_MAX_PACKET_LENGTH, timeout=RDP_TIMEOUT)
            if err:
                continue
            data, _ = request
            bytes_available.extend(data)

        header_bytes = bytes([bytes_available.popleft()
                              for _ in range(RDP_HEADER_LENGTH)])

        packet_header = RDPPacket()
        packet_header.from_bytes(header_bytes)

        peer_sn = packet_header.sequence_no

        if packet_header.flags & SOCK352_FIN:
            if DEBUG:
                print(
                    f"[packet_listener] Got FIN: {packet_header.sequence_no}")
                break

        connection.mutex.acquire()
        if peer_sn != connection.peer_sn:
            # Discard packet
            payload_length = packet_header.payload_len
            [bytes_available.popleft() for _ in range(payload_length)]

            if DEBUG:
                print(
                    f"[packet_listener: --Discard--] Got: {peer_sn}, Expected {connection.peer_sn}")

            # Send ACK packet for last correct packet
            ack_packet = RDPPacket(
                flags=SOCK352_ACK,
                sequence_no=connection.current_sn,
                ack_no=connection.peer_sn,
                window=RDP_MAX_RECEIVER_WINDOW -
                len(buffer))
            send_packet(ack_packet, dest_address)

            if DEBUG:
                print(
                    f"[packet_listener: --Discard--] Sent ACK: {connection.peer_sn}")

            connection.mutex.release()
            continue

        if DEBUG:
            print(
                f"[packet_listener] Got: {peer_sn}, Expected {connection.peer_sn}")
        connection.mutex.release()

        payload_length = packet_header.payload_len

        if len(bytes_available) < payload_length:
            _, request = udp_transport.recv(RDP_MAX_PACKET_LENGTH)
            data, _ = request
            bytes_available.extend(data)

        payload = bytes([bytes_available.popleft()
                         for _ in range(payload_length)])
        buffer.extend(payload)

        if DEBUG:
            print(f"[packet_listener] Wrote {payload_length} bytes to buffer")

        connection.mutex.acquire()
        connection.peer_sn += payload_length
        # Send ACK packet
        ack_packet = RDPPacket(
            flags=SOCK352_ACK,
            sequence_no=connection.current_sn,
            ack_no=connection.peer_sn,
            window=RDP_MAX_RECEIVER_WINDOW -
            len(buffer))
        send_packet(ack_packet, dest_address)

        if DEBUG:
            print(f"[packet_listener] Sent ACK: {connection.peer_sn}")
        connection.mutex.release()


class socket:
    def __init__(self):
        self.connection = None

    def bind(self, address):
        return

    def connect(self, address):
        self.dest_address = address
        # Establish three way handshake
        self.connection = Connection()

        while True:
            # Send SYN packet
            ISN = random.randint(0, RDP_MAX_SEQ_NO)
            syn_packet = RDPPacket(flags=SOCK352_SYN, sequence_no=ISN)
            send_packet(syn_packet, self.dest_address)

            self.connection.state = CONNECTION_SYN_SENT
            self.connection.current_sn = ISN + 1

            # Block with timeout for SYN/ACK packet
            err, request = udp_transport.recv(
                RDP_HEADER_LENGTH, timeout=RDP_TIMEOUT)
            if err:
                continue
            data, _ = request

            syn_ack_packet = RDPPacket()
            syn_ack_packet.from_bytes(data)

            if not syn_ack_packet.flags & SOCK352_SYN:
                continue
            if not syn_ack_packet.flags & SOCK352_ACK:
                continue
            if syn_ack_packet.ack_no != self.connection.current_sn:
                continue

            self.connection.recv_window = syn_ack_packet.window

            # Connection Established
            self.connection.state = CONNECTION_ESTABLISHED
            self.connection.peer_sn = syn_ack_packet.sequence_no + 1

            # Send ACK packet
            ack_packet = RDPPacket(
                flags=SOCK352_ACK, sequence_no=self.connection.current_sn,
                ack_no=self.connection.peer_sn, window=RDP_MAX_RECEIVER_WINDOW
            )
            send_packet(ack_packet, self.dest_address)

            if DEBUG:
                print(f"Connection Established: {vars(self.connection)}")

            break

    def accept(self):
        self.connection = None
        self.dest_address = None

        client_socket = None

        # Establish three way handshake
        while True:
            # Block for SYN
            _, request = udp_transport.recv(RDP_HEADER_LENGTH)
            data, self.dest_address = request

            syn_packet = RDPPacket()
            syn_packet.from_bytes(data)

            if not syn_packet.flags & SOCK352_SYN:
                continue

            ISN = random.randint(0, RDP_MAX_SEQ_NO)

            if self.connection and self.connection.state == CONNECTION_ESTABLISHED:
                ack_no = syn_packet.sequence_no + 1
                reset_packet = RDPPacket(
                    flags=SOCK352_SYN | SOCK352_ACK | SOCK352_RESET,
                    sequence_no=ISN, ack_no=ack_no
                )
                send_packet(reset_packet, self.dest_address)
                continue

            # New connection
            self.connection = Connection()
            self.connection.state = CONNECTION_SYN_RECIEVED
            self.connection.current_sn = ISN + 1
            self.connection.peer_sn = syn_packet.sequence_no + 1

            # Send SYN/ACK packet
            syn_ack_packet = RDPPacket(
                flags=SOCK352_SYN | SOCK352_ACK, sequence_no=ISN,
                ack_no=self.connection.peer_sn, window=RDP_MAX_RECEIVER_WINDOW
            )
            send_packet(syn_ack_packet, self.dest_address)

            # Block with timeout for ACK packet
            err, request = udp_transport.recv(
                RDP_HEADER_LENGTH, timeout=RDP_TIMEOUT)
            if err:
                continue

            data, _ = request

            ack_packet = RDPPacket()
            ack_packet.from_bytes(data)

            if ack_packet.ack_no < self.connection.current_sn:
                continue

            self.connection.recv_window = ack_packet.window

            # Connection Established
            self.connection.state = CONNECTION_ESTABLISHED
            self.buffer = collections.deque(maxlen=RDP_MAX_RECEIVER_WINDOW)

            client_socket = socket()
            client_socket.connection = Connection()
            client_socket.connection.state = self.connection.state
            client_socket.connection.current_sn = self.connection.current_sn
            client_socket.connection.peer_sn = self.connection.peer_sn
            client_socket.dest_address = self.dest_address
            client_socket.buffer = self.buffer

            client_socket.stop_packet_listener = threading.Event()

            if DEBUG:
                print(f"Connection Established: {vars(self.connection)}")

            threading.Thread(
                target=packet_listener,
                args=(
                    client_socket.connection,
                    client_socket.buffer,
                    client_socket.dest_address,
                    client_socket.stop_packet_listener
                )
            ).start()

            break

        return (client_socket, client_socket.dest_address)

    def listen(self, backlog):
        return

    def close(self):
        # Send FIN packet
        fin_packet = RDPPacket(
            flags=SOCK352_FIN,
            sequence_no=self.connection.current_sn,
            ack_no=self.connection.peer_sn
        )
        send_packet(fin_packet, self.dest_address)

        if DEBUG:
            print(f"[close] Sent FIN: {fin_packet.sequence_no}")

        try:
            self.stop_packet_listener.set()
        except BaseException:
            pass
        self.connection.state = CONNECTION_DEFAULT

        udp_transport.rx_socket.close()
        udp_transport.tx_socket.close()

    def send(self, buffer):
        offset = 0
        pause_transmission = threading.Event()
        stop_timer = threading.Event()

        buffer_length = len(buffer)

        init_sn = self.connection.current_sn

        self.connection.mutex.acquire()
        self.connection.base = self.connection.current_sn
        final_ack_no = self.connection.base + buffer_length
        self.connection.mutex.release()

        # Start ACK listener thread
        listener = threading.Thread(
            target=ack_listener,
            args=(
                self.connection,
                buffer,
                init_sn,
                self.dest_address,
                pause_transmission,
                stop_timer,
                final_ack_no))
        listener.start()

        while True:
            payload = buffer[offset:offset + RDP_MAX_PAYLOAD_LENGTH]
            payload_length = len(payload)

            if not payload_length:
                break

            while pause_transmission.isSet():
                continue

            self.connection.mutex.acquire()

            if self.connection.in_flight + payload_length > self.connection.recv_window:
                self.connection.mutex.release()
                continue

            data_packet = RDPPacket(
                data=payload,
                sequence_no=self.connection.current_sn,
                ack_no=self.connection.peer_sn
            )
            if self.connection.base == self.connection.current_sn:
                # Start ACK timeout thread
                threading.Thread(
                    target=ack_timeout,
                    args=(
                        self.connection,
                        buffer,
                        init_sn,
                        self.dest_address,
                        pause_transmission,
                        stop_timer,
                        "send")).start()
            self.connection.current_sn += payload_length
            # Send data packet
            send_packet(data_packet, self.dest_address)

            if DEBUG:
                print(f"[send] Sent: {data_packet.sequence_no}")

            self.connection.in_flight += payload_length
            self.connection.mutex.release()

            offset += payload_length

        listener.join()

        return buffer_length

    def recv(self, nbytes):
        if DEBUG:
            print(f"[recv] Waiting to read {nbytes} bytes from buffer...")

        while True:
            self.connection.mutex.acquire()
            if len(self.buffer) < nbytes:
                self.connection.mutex.release()
                continue

            payload = bytes([self.buffer.popleft() for _ in range(nbytes)])

            if DEBUG:
                print(f"[recv] Read {nbytes} bytes from buffer")

            # Send ACK packet
            ack_packet = RDPPacket(flags=SOCK352_ACK,
                                   sequence_no=self.connection.current_sn,
                                   ack_no=self.connection.peer_sn,
                                   window=RDP_MAX_RECEIVER_WINDOW - len(self.buffer))
            send_packet(ack_packet, self.dest_address)

            if DEBUG:
                buffer_length = len(self.buffer)
                capacity = RDP_MAX_RECEIVER_WINDOW - len(self.buffer)
                print(
                    f"[recv] Sent ACK: {ack_packet.ack_no}, Buffer: {buffer_length}, Capacity: {capacity}")
            self.connection.mutex.release()

            return payload
