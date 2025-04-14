#!/usr/bin/env python

"""
    COMP3310 Tute 0 programming warmup exercise.
    This is the first of two programs. Run with
        python peasant.py

    Written by Hugh Fisher u9011925, ANU, 2024
    Released under Creative Commons CC0 Public Domain Dedication
    This code may be freely copied and modified for any purpose
"""

import sys


name = None


def inputLoop():
    """Just read and echo input until EOF"""
    global name
    #
    while True:
        try:
            line = input()
        except EOFError:
            break
        if name is None:
            response = line
        else:
            response = "{}: {}".format(name, line)
        print(response)

def processArgs(argv):
    """Handle command line arguments, just one for this program"""
    global name
    #
    if len(argv) > 1:
        name = argv[1]

##

if __name__ == "__main__":
    processArgs(sys.argv)
    inputLoop()
    print("Done.")
