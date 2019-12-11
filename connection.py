import threading

from const import CONNECTION_DEFAULT


class Connection:
    def __init__(self):
        # state of the connection
        self.state = CONNECTION_DEFAULT
        # base of sliding window
        self.base = 0
        # sequence number of the next byte to be sent
        self.current_sn = 0
        # sequence number of the next byte expected from peer
        self.peer_sn = 0
        # bytes sent but not acknowledged
        self.in_flight = 0
        # length of receiver window
        self.recv_window = 0
        # threading lock
        self.mutex = threading.Lock()
