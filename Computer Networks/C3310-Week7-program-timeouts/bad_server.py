#!/usr/bin/env python

"""
Flaky TCP echo server program for ANU COMP3310.

Run with
    python bad_server.py [port]

Written by Hugh Fisher (u9100925) and Felix Friedlander (u6675843), ANU,
2024.
CC0: This code is dedicated to the public domain.
This code may be freely copied and modified for any purpose.
https://creativecommons.org/publicdomain/zero/1.0/
"""

import socket
from sys import argv

service_port = 3310

def server_loop(port):
    """Accept client connections on given host and port"""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set "reuse address" socket option, in case there are still
    # connections open to an old copy of the server
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", port))
    server.listen()

    server_host, server_port = server.getsockname()
    print(f"Server listening on {server_host}:{server_port}")

    while True:
        try:
            client, (client_host, client_port) = server.accept()
        # If something goes wrong with the network, we will stop
        except OSError as e:
            print(f"server_loop: {e}")
            break

        print(f"Accepted client connection from {client_host}:{client_port}")

        client_loop(client)

    print("Closing server socket")
    server.close()

def client_loop(sock):
    """Echo service for a single client"""

    # Keep track of the number of requests we've seen
    requests = 0

    sock_io = sock.makefile("rw")

    while True:
        try:
            request = sock_io.readline()
            if request == "":
                break
            print("Received:", request, end="")

            requests += 1
            if requests % 3 == 0:
                print("Not responding >:)")
            else:
                response = "ACK " + request
                sock_io.writelines([response])
                sock_io.flush()
                print("Sent:", response, end="")

        # Try not to crash if the client does something wrong
        except OSError as e:
            print(type(e).__name__, "in client_loop", e.args)
            break

    print("Closing client socket")
    sock_io.close()
    sock.close()

if __name__ == "__main__":
    port = argv[1] if len(argv) >= 2 else service_port

    server_loop(port)
    print("Done.")
