import threading

from const import CONNECTION_DEFAULT


class Connection:
    def __init__(self):
        # state of the connection
        self.state = CONNECTION_DEFAULT
        # sequence number of the next byte to be sent
        self.current_sn = 0
        # sequence number of the next byte expected from peer
        self.peer_sn = 0
        # base of sliding window
        self.base = 0
        # threading lock
        self.mutex = threading.Lock()
