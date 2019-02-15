#!/usr/bin/python
# -*- coding: utf-8 -*
#
#

import daemon
import sys
import os
from os.path import exists
from time import sleep
import signal

sys.path.append('/usr/local/bin')

import intuos4oled as i4o

TEMP = "/tmp/intuos_init"
LOCK = "/tmp/intuos4oled.lock"

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
            print ("Error:", sys.exc_info()[0])
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
            print ('Error. Intuos might be disconnected. Waiting for 3 sec.')
            _ = os.system("echo 'LED ERROR' >> %s"%TEMP)
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
    with daemon.DaemonContext():
        signal.signal(signal.SIGINT, at_exit)
        signal.signal(signal.SIGTERM, at_exit)
        main()
