import socket
import select


class UDPTransport:
    def __init__(self, host, TX_port, RX_port):
        self.host = host
        self.TX_port = TX_port
        self.RX_port = RX_port
        self.tx_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )
        self.rx_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

    def bind(self):
        self.rx_socket.bind((self.host, self.RX_port))

    def recv(self, size, timeout=None):
        is_ready = select.select([self.rx_socket], [], [], timeout)
        if not is_ready[0]:
            return ("self.rx_socket timed out", None)
        return None, self.rx_socket.recvfrom(size)

    def send(self, packet, address):
        host, _ = address
        self.tx_socket.sendto(packet, (host, self.TX_port))
