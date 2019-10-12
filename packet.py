import struct

from const import RDP_VERSION, PACKET_HEADER_STRUCT

class RDPPacket:
    def __init__(
        self, data=None, version=RDP_VERSION, flags=0x0, opt_ptr=0x0, protocol=0x0, 
        source_port=0x0, dest_port=0x0, sequence_no=0x0, ack_no=0x0, window=0x0
    ):
        self.data = data
        self.version = version
        self.flags = flags
        self.opt_ptr = opt_ptr
        self.protocol = protocol
        self.source_port = source_port
        self.dest_port = dest_port
        self.sequence_no = sequence_no
        self.ack_no = ack_no
        self.window = window

    def calculate_checksum(self):
        return 0x0
    
    def build_header(self):
        packet_header = struct.Struct(PACKET_HEADER_STRUCT)

        self.header_len = packet_header.size
        self.checksum = self.calculate_checksum()
        self.payload_len = 0
        if self.data:
            self.payload_len = len(self.data)

        return packet_header.pack(
            self.version,
            self.flags,
            self.opt_ptr,
            self.protocol,
            self.header_len,
            self.checksum,
            self.source_port,
            self.dest_port,
            self.sequence_no,
            self.ack_no,
            self.window,
            self.payload_len
        )

    def to_bytes(self):
        packet = self.build_header()
        if self.data:
            packet += bytes(self.data)
        return packet
