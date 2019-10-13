from const import CONNECTION_DEFAULT

class Connection:
    def __init__(self):
        self.state = CONNECTION_DEFAULT     # state of the connection
        self.current_sn = 0                 # sequence number of the next byte to be sent
        self.last_ack_no = 0                # sequence number of the last acknowledged seq_no
        self.peer_sn = 0                    # sequence number of the next byte expected from peer
