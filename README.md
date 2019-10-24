# RDPv1

**Project Members: Chakshu Tandon, Albert Wen**  
**Python version: 3.6.8**

Reliable Data Protocol (RDP) version 1 (352 RDPv1)

RDPv1 uses python SOCK_DGRAM (UDP) sockets to reliably transfer files between two nodes.  


# Getting Started

Clone into repository:

`git clone https://gitlab.com/chakshutandon/rdpv1.git`

Change into directory:

`cd rdpv1`

Run using python:

`python3 server1.py -f<filepath> -u<rx_port> -v<tx_port>`

`python3 client1.py -f<filepath> -d<hostname> -u<rx_port> -v<tx_port>`
