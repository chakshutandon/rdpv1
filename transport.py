import socket

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

    def recv(self, size):
        self.rx_socket.recvfrom(size)

    def send(self, packet, host):
        self.tx_socket.sendto(packet, (host, self.TX_port))
