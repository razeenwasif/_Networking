#!/usr/bin/env python

"""
TCP echo client program for ANU COMP3310.

Run with
    python tcp_client.py [address [port]]

Written by Hugh Fisher (u9100925) and Felix Friedlander (u6675843), ANU,
2024.
CC0: This code is dedicated to the public domain.
This code may be freely copied and modified for any purpose.
https://creativecommons.org/publicdomain/zero/1.0/
"""

from socket import socket, AF_INET, SOCK_STREAM
from sys import argv

service_host = "127.0.0.1"
service_port = 3310

def loop(host, port):
    """
    Read lines of input, send them to the echo server, and wait for and print
    the server's response.
    """

    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))

    connected_host, connected_port = sock.getpeername()
    print(f"Connected to {connected_host}:{connected_port}")

    while True:
        try:
            line = input()
        except EOFError:
            break

        send_request(sock, line + "\n")
        read_reply(sock)

    print("Closing socket")
    sock.close()

def send_request(sock, request):
    """Send our request to server"""

    with sock.makefile("w") as sock_file:
        sock_file.writelines([request])
        sock_file.flush()
        print("Sent request to server...")


def read_reply(sock):
    """Read and print a response from the server"""

    with sock.makefile("r") as sock_file:
        reply = sock_file.readline()
        print("Received response:", reply, end="")

if __name__ == "__main__":
    host = argv[1] if len(argv) >= 2 else service_host
    port = argv[2] if len(argv) >= 3 else service_port

    loop(host, port)
    print("Done.")
