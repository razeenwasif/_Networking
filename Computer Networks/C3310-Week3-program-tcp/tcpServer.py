#!/usr/bin/env python

"""
    TCP echo server program for ANU COMP3310.

    Run with
        python tcpServer.py [ IP addr ] [ port ]

    Written by Hugh Fisher u9011925, ANU, 2024
    Released under Creative Commons CC0 Public Domain Dedication
    This code may be freely copied and modified for any purpose
"""

import sys
import socket
# Keep the code short for this tiny program
from socket import *

# Shared by client and server
import sockLine
from sockLine import readLine, writeLine, slowSend


# IP address and port
serviceHost = "0.0.0.0"
servicePort = 3310


def clientLoop(host, port):
    """Accept client connections on given host and port"""
    # Create TCP socket
    serverSock = socket(AF_INET, SOCK_STREAM)
    # Servers should set this option which allows them to be re-run immediately.
    # If you don't, you may have to wait a few minutes before restarting the server.
    serverSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    # Address and port clients will connect to
    serverSock.bind((host, port))
    # This is the limit on established TCP connections that have not yet
    # been accepted. (Not the number of connections.) A really busy server
    # might need to increase this but for now, don't worry about it.
    serverSock.listen(5)
    print("Created server socket for", serverSock.getsockname()[0],
                                        serverSock.getsockname()[1])
    while True:
        # A TCP server is different to UDP. Instead of packets,
        # we get connection requests from clients.
        try:
            client, clientAddr = serverSock.accept()
        # If something goes wrong with the network, we will stop
        except OSError as e:
            print(type(e).__name__, "in clientLoop", e.args)
            break
        print("Accepted client connection from", clientAddr)
        # Each connection accepted creates a new socket for that
        # particular client. Use for requests and replies.
        serverLoop(client)
        # We don't get back here until the client session ends
        #
    print("Close server socket")
    serverSock.close()

def serverLoop(sock):
    """Echo service for a single client"""
    # Read and respond until client shuts down the socket,
    # using shared line read/write code
    while True:
        try:
            request = readLine(sock)
            if request is None:
                print("Client disconnected")
                break
            if request == "BYE":
                print("Server received BYE, closing connection")
                sock.close()
                break
            print("Server received", request)
            handleRequest(sock, request)
        # Try not to crash if the client does something wrong
        except OSError as e:
            print(type(e).__name__, "in serverLoop", e.args)
            break
    print("Close client socket")
    sock.close()

def handleRequest(sock, message):
    """Respond to one client request"""
    if message == "it":
        reply = ""
    elif message == "ni":
        reply = "ACK: " + message + "\n" + message + "\n" + message + "\n"
    else:
        reply = "ACK: " + message + "\n"
    print("Server sending reply", reply)
    writeLine(sock, reply)


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
    clientLoop(serviceHost, servicePort)
    print("Done.")
