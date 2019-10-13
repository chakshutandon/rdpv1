import struct

from const import RDP_VERSION, PACKET_HEADER_STRUCT

packet_header = struct.Struct(PACKET_HEADER_STRUCT)
RDP_HEADER_SIZE = packet_header.size

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
        self.header_len = RDP_HEADER_SIZE
        self.checksum = self.calculate_checksum()
        self.payload_len = 0
        if self.data:
            self.payload_len = len(self.data)

        header = struct.Struct(PACKET_HEADER_STRUCT)
        return header.pack(
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

    def from_bytes(self, bytes):
        payload = bytes[RDP_HEADER_SIZE:]
        self.data = payload

        header_data = bytes[:RDP_HEADER_SIZE]
        header = struct.Struct(PACKET_HEADER_STRUCT)

        fields = header.unpack(header_data)
        self.version        = fields[0]
        self.flags          = fields[1]
        self.opt_ptr        = fields[2]
        self.protocol       = fields[3]
        self.header_len     = fields[4]
        self.checksum       = fields[5]
        self.source_port    = fields[6]
        self.dest_port      = fields[7]
        self.sequence_no    = fields[8]
        self.ack_no         = fields[9]
        self.window         = fields[10]
        self.payload_len    = fields[11]

    def to_bytes(self):
        packet = self.build_header()
        if self.data:
            packet += bytes(self.data)
        return packet
