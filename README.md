# RDPv1

**Project Members: Chakshu Tandon, Albert Wen**  
**Python version: 3.6.8**

Reliable Data Protocol (RDP) version 1 (352 RDPv1)

RDPv1 builds on python SOCK_DGRAM (UDP) sockets to reliably transfer files between two nodes.

Supports:

```
- [x] Go-Back N Protocol
- [x] Flow Control
- [ ] Multiple Clients
```

API:

```
bind(address)
connect(address)
listen(backlog)
accept()
close()
send(buffer)
recv(numBytes)
```




# Getting Started

Clone into repository:

`git clone https://gitlab.com/chakshutandon/rdpv1.git`

Change into directory:

`cd rdpv1`

Run using python:

`python3 server2.py -f<filepath> -u<rx_port> -v<tx_port>`

`python3 client2.py -f<filepath> -d<hostname> -u<rx_port> -v<tx_port>`
