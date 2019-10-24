RDP_VERSION = 0x1

# Sequence numbers should be in the range [0, 18446744073709551615]
MAX_RDP_SEQ_NO = 2 ** 64 - 1

# UDP supports max packet size of 65535 bytes
UDP_MAX_PACKET_LENGTH = 64 * 1024 - 1
# UDP header length
UDP_HEADER_LENGTH = 8
# IP header
IPV4_HEADER_LENGTH = 20
# Padding
PADDING = 512

MAX_RDP_PACKET_LENGTH = UDP_MAX_PACKET_LENGTH - UDP_HEADER_LENGTH - IPV4_HEADER_LENGTH - PADDING

# Seconds till packet retransmission
RDP_TIMEOUT = 0.2

# For best match with hardware and network realities, the value of bufsize should be a relatively small power of 2, for example, 4096.
UDP_BUFFER_SIZE = 4096

# RDP Connection states
CONNECTION_DEFAULT          = 0
CONNECTION_SYN_SENT         = 1
CONNECTION_SYN_RECIEVED     = 2
CONNECTION_ESTABLISHED      = 3

# Flag Name       Byte Value (Hex)      Byte Value (Binary)     Meaning
# SOCK352_SYN     0x01                  00000001                Connection initiation
# SOCK352_FIN     0x02                  00000010                Connection end
# SOCK352_ACK     0x04                  00000100                Acknowledgement number
# SOCK352_RESET   0x08                  00001000                Reset connection
# SOCK352_HAS_OPT 0xA0                  00010000                Option field is valid

SOCK352_SYN      = 0b00000001
SOCK352_FIN      = 0b00000010
SOCK352_ACK      = 0b00000100
SOCK352_RESET    = 0b00001000
SOCK352_HAS_OPT  = 0b00010000

# struct __attribute__ ((__packed__)) rdp_header { 
    # uint8_t version;              /* version number */
    # uint8_t flags;                /* for connection set up, tear-down, control */
    # uint8_t opt_ptr;              /* option type between the header and payload */
    # uint8_t protocol;             /* higher-level protocol */
    # uint16_t header_len;          /* length of the header */
    # uint16_t checksum;            /* checksum of the packet */
    # uint32_t source_port;         /* source port */
    # uint32_t dest_port;           /* destination port */
    # uint64_t sequence_no;         /* sequence number */
    # uint64_t ack_no;              /* acknowledgement number */
    # uint32_t window;              /* receiver advertised window in bytes*/
    # uint32_t payload_len;         /* length of the payload */
# };

RDP_HEADER_STRUCT = '!BBBBHHLLQQLL'
