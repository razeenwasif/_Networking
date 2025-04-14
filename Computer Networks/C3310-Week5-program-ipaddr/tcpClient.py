#!/usr/bin/env python

"""
    TCP echo client program for ANU COMP3310.

    Run with
        python tcpClient.py [ IP addr ] [ port ]

    Written by Hugh Fisher u9011925, ANU, 2024
    Released under Creative Commons CC0 Public Domain Dedication
    This code may be freely copied and modified for any purpose
"""

import sys
import socket
# Keep the code short for this tiny program
from socket import *

# Shared by client and server
# (we might not need these for sending the request anymore)
# but potentially useful if reading response line-by-line later.
# for simplicity. we'll read the whole response later using recv loop.
# from sockLine import readLine, writeLine


# IP address and port that client will contact
#serviceHost = "127.0.0.1"
#servicePort = 3310

# To start a localhost server:
# >> python -m http.server 8080 -> starts localhost on port 8080


#def inputLoop(host, port):
#    """Read input until EOF. Send as request to host, print response"""
#    # Create TCP socket
#    sock = socket(AF_INET, SOCK_STREAM)
#    # A TCP active (client) socket must be connected to a single host
#    sock.connect((host, port))
#    print("Client connected to", sock.getpeername()[0], sock.getpeername()[1])
#    # Keep reading lines and sending them
#    while True:
#        try:
#            line = input()
#        except EOFError:
#            break
#        sendRequest(sock, line)
#        readReply(sock)
#    print("Client close")
#    # Tell the server we are done
#    writeLine(sock, "BYE")
#    sock.close()

#def sendRequest(sock, request):
#    """Send our request to server"""
#    # No try: if anything goes wrong, higher level will handle
#    writeLine(sock, request)
#    print("Sent request to server")


#def readReply(sock):
#    """Read and print server response"""
#    reply = readLine(sock)
#    print(reply)


# Default values (will be overridden by command line args)
targetHost = "neverssl.com"
targetPort = 80
httpMethod = "HEAD" # Default method 

def readHttpResponse(sock):
    """Read the entire response from the server until connection close"""
    print("---Reading Response---")
    response_data = b""
    buffer_size = 4096 # Read in chunks 
    try:
        while True:
            chunk = sock.recv(buffer_size)
            if not chunk:
                # Empty chunk means server closed connection
                break
            response_data += chunk 
            # printing progress for large files:
            print(f"Received {len(chunk)} bytes...")
    except Exception as e:
        print(f"Error reading from socket: {e}")
    finally:
        # Ensure socket is closed even if error occurs during read 
        print("---Server closed connection---")
        sock.close()
        print("Client socket closed")

    # Decode the received bytes into a string for printing 
    # error='ignore' to handle potential non UTF-8 chars in binary data 
    print(response_data.decode('utf-8', errors='ignore'))

def makeHttpRequest(host, port, method):
    """Connect, send an HTTP request, and read the response"""
    # Create tcp socket 
    sock = socket(AF_INET, SOCK_STREAM)

    try:
        # A TCP active (client) socket must be connected to a single host 
        print(f"Connecting to {host} on port {port}...")
        sock.connect((host, port))
        print("Client connected to", sock.getpeername()[0], sock.getpeername()[1])

        # --- Construct the HTTP request --- 
        # Use f-string for easy variable insertion 
        # IMPORTANT: Each line MUST end with \r\n 
        # IMPORTANT: Headers MUST be followed by an empty line (\r\n)
        request = (
                f"{method} / HTTP/1.0\r\n" # Request line (Method, Path. Version)
                f"Host: {host}\r\n"        # Host header is required by many servers 
                f"User-Agent: MyCOMP3310Client/1.0\r\n" # Identify our client 
                f"Connection: close\r\n"   # Ask server to close connection after response 
                f"\r\n"                    # Crucial empty line ending the headers
        )
        print("---Sending Request---")
        print(request.replace('\r\n', '\\r\\n\n')) # print request for debugging, showing \r\n 
        
        # Send the request - must be encoded to bytes 
        sock.sendall(request.encode('utf-8'))
        print("---Request Sent---")

        # --- Read the response --- 
        # The readHttpResponse function now handles reading and closing 
        readHttpResponse(sock)

    except gaierror as e:
        print(f"Error resolving hostname {host}: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused by server {host}:{port}. Is it running?")
    except TimeoutError:
        print(f"Connection timed out to {host}:{port}.")
    except Exception as e:
        print(f"An error occurred: {e}")
        # Ensure socket is closed if connected but error occurred before readHttpResponse
        if sock.fileno() != -1: # Check if socket object exists and seems valid
            try:
                sock.close()
                print("Client socket closed due to error.")
            except Exception as close_e:
                print(f"Error closing socket after error: {close_e}")

#def processArgs(argv):
#    """Handle command line arguments"""
#    global serviceHost, servicePort
#    #
#    # This program has only two CLI arguments, and we know the order.
#    # For any program with more than two args, use a loop or look up
#    # the standard Python argparse library.
#    if len(argv) > 1:
#        serviceHost = argv[1]
#        if len(argv) > 2:
#            servicePort = int(argv[2])

def processArgs(argv):
    """Handle command line arguments"""
    global targetHost, targetPort, httpMethod

    if len(argv) > 1:
        targetHost = argv[1]
    if len(argv) > 2:
        try:
            targetPort = int(argv[2])
        except ValueError:
            print(f"Error: Port '{argv[2]}' must be an integer.")
            sys.exit(1)
    if len(argv) > 3:
        # Convert method to uppercase for consistency
        method_arg = argv[3].upper()
        if method_arg in ["GET", "HEAD"]:
            httpMethod = method_arg 
        else:
            print(f"Warning: Unsupported method '{argv[3]}'. Using default '{httpMethod}'.")
##

if __name__ == "__main__":
    processArgs(sys.argv)
    #inputLoop(serviceHost, servicePort)
    makeHttpRequest(targetHost, targetPort, httpMethod)
    print("Done.")
