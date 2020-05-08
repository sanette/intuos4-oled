#!/usr/bin/python
# -*- coding: utf-8 -*
#
# this daemon should be run by the user, not root.
# It watches the led status of the tablet and changes button images accordingly.
#
# This is part of intuos4oled
#
# San Vu Ngoc 2019
#

#import daemon
import sys
import os
from os.path import exists
from time import sleep
import signal

sys.path.append('/usr/local/bin')

import intuos4oled as i4o

USER = os.getenv('USER')
TEMP = "/tmp/intuos4init-" + USER
LOCK = "/tmp/intuos4oled-" + USER + ".lock"

def at_exit(signum, frame):
    print ("Intuos4Daemon killed with signal %i."%signum)
    os.remove(LOCK)
    exit (1)
    
def reset ():
    ok = False
    s = None
    while (not ok):
        try:
            s = i4o.Screen()
            ok = True
        except:
            print (sys.exc_info()[0], file = stderr)
            print ('Cannot connect to the Intuos... retrying in 5 sec.')
            sleep(5)
    return (s)

def main ():
    ret = os.system("/usr/bin/touch " + LOCK)
    s = reset()
    led = s.led
    
    while True:
        try:
            s.update_led()
        except:
            print ('Error reading LED. Intuos might be disconnected. Waiting for 3 sec.')
            _ = os.system("echo 'Error reading LED. Intuos might be disconnected. Waiting for 3 sec.' >> %s"%TEMP)
            sleep(3)
            s = reset()
        if led != s.led:
            led = s.led
            s.load()
            _ = os.system('/bin/date >> %s'%TEMP)
        sleep(1)

if exists(LOCK):
    print ("Intuos4daemon is already running. If this is not the case, remove '%s'."%LOCK)
    exit (1)
else:
    #with daemon.DaemonContext():
    signal.signal(signal.SIGINT, at_exit)
    signal.signal(signal.SIGTERM, at_exit)
    main()
