
"""
    TCP utility code for ANU COMP3310.
    Read and write lines of text over TCP socket, handling
    EOL and decoding/encoding UTF-8. Nothing very complex
    but avoids copying and pasting over and over again.

    There is no limit on the size of a line.

    Written by Hugh Fisher u9011925, ANU, 2024
    Released under Creative Commons CC0 Public Domain Dedication
    This code may be freely copied and modified for any purpose
"""

import socket

def writeLine(sock, txt):
    """Write single line with LF"""
    txt += '\n'
    # Use sendall rather than send because if txt is really long,
    # sendall will break into smaller chunks. send() does not.
    sock.sendall(txt.encode('utf-8'))

def readLine(sock):
    """Read single line terminated by \n from sock, or None if closed."""
    # Read as bytes. Only convert to UTF-8 when we have entire line.
    inData = b''
    while True:
        ch = sock.recv(1)
        if len(ch) == 0:
            # Socket closed. If we have any data it is an incomplete
            # line, otherwise immediately return None
            if len(inData) > 0:
                break
            else:
                return None
        inData += ch
        # This comparison always works with UTF-8 because high bytes
        # of multi byte characters have at least bit 7 set
        if ch == b'\n':
            break
    # Back slash replace won't raise exception on illegal char sequence
    txt = inData.decode('utf-8', 'backslashreplace')
    return txt


## This is just to demonstrate packets vs streams. Don't use in assignments

import time

def slowSend(sock, txt):
    """Send text byte by byte in tiny packets"""
    txt += '\n'
    data = txt.encode('utf-8')
    for i in range(0, len(data) - 1):
        sock.send(data[i:i+1])
        # Without this OS would probably buffer all the bytes internally
        # and send one packet, which is not what we want
        time.sleep(0.1)

