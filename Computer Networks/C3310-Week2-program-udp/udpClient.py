#!/usr/bin/env python

"""
    Python UDP echo client program for ANU COMP3310.

    This is the other half of a client-server architecture.
    The client knows the server, and makes requests to get a response.

    Run with
        python udpClient.py [ IP addr ] [ port ]

    Written by Hugh Fisher u9011925, ANU, 2024
    Released under Creative Commons CC0 Public Domain Dedication
    This code may be freely copied and modified for any purpose
"""

import sys
import socket
# Keep the code short for this tiny program
from socket import *
# This makes the Python code nicer
from socket import timeout as SocketTimeOutError


# IP address and port that client will contact
serviceHost = "127.0.0.1"
servicePort = 3310

# Our maximum UDP data size, in bytes.
# Absolute maximum for UDP would be 64K, but reliability goes down a lot
# for packets larger than 1K or so, and more than 8K is unlikely.
MSG_MAX = 1024

# Maximum time to wait for a reply, in seconds
TIMEOUT = 4.0


def inputLoop(host, port):
    """Read input until EOF. Send as request to host, print response"""
    # Create an Internet UDP socket
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    # This client will only connect to a single server, so we can set the peer
    # address, ie the remote server, for this socket just once.
    sock.connect((host, port))
    print("Client created socket to", sock.getpeername()[0], sock.getpeername()[1])
    # UDP, like IP, is not a reliable protocol so we can't guarantee packets get
    # there, and in fact we can't even be sure that there is a server! This is
    # the maximum time to wait for a reply. (Also the maximum time to wait when
    # trying to send, but that usually is not a problem.)
    sock.settimeout(TIMEOUT)
    # Now keep reading lines and sending them
    while True:
        try:
            line = input()
        except EOFError:
            break
        sendRequest(sock, line)
        print("Sent request to server")
        reply = readReply(sock)
        if reply is None:
            print("TIME OUT")
        else:
            print(reply)
    print("Client close")
    sock.close()

def sendRequest(sock, request):
    """Send our request to server"""
    # Like the server, encoding into wire format is done at the last moment
    request = request.encode('utf-16')
    # Our client socket is already connected to the server address,
    # so we just need to provide the data
    sock.send(request)

def readReply(sock):
    """Read string and return, or None if the socket times out"""
    # Socket is permanently connected so we know who it came from.
    try:
        inData = sock.recv(MSG_MAX)
    except SocketTimeOutError:
        return None
    # We hope the server sent us UTF-8, but don't count on it
    reply = inData.decode('utf-8', 'backslashreplace')
    return reply


def processArgs(argv):
    """Handle command line arguments"""
    global serviceHost, servicePort
    #
    # This program has only two CLI arguments, and we know the order.
    # For any program with more than two args, use a loop or look up
    # the standard Python argparse library.
    if len(argv) > 1:
        serviceHost = argv[1]
        if len(argv) > 2:
            servicePort = int(argv[2])

##

if __name__ == "__main__":
    processArgs(sys.argv)
    inputLoop(serviceHost, servicePort)
    print("Done.")
