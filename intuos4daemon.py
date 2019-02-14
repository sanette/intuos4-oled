#!/usr/bin/python
# -*- coding: utf-8 -*
#
#

import daemon
import sys
import os
import os.path
import time

sys.path.append('/usr/local/bin')

import intuos4oled as i4o

TEMP = "/tmp/intuos_init"
LOCK = "/tmp/intuos4oled.lock"

def reset ():
    ok = False
    while not ok:
        try:
            s = i4o.Screen()
            ok = True
        except:
            print ("Error:", sys.exc_info()[0])
            print ('Cannot connect to the Intuos... retrying in 5 sec.')
            time.sleep(5)
    return (s)

def main ():
    s = reset()
    led = s.led
    _ = os.system("/usr/bin/touch " + LOCK)
    
    while True:
        try:
            s.update_led()
        except:
            print ('Error. Intuos might be disconnected. Waiting for 5 sec.')
            _ = os.system("echo 'LED ERROR' >> %s"%TEMP)
            time.sleep(3)
            s = reset()
        if led != s.led:
            led = s.led
            s.load()
            _ = os.system('/bin/date >> %s'%TEMP)
        time.sleep(1)

if os.path.exists(LOCK):
    print ("Intuos4daemon is already running. If this is not the case, remove '%s'."%LOCK)
    exit (1)
else:
    with daemon.DaemonContext():
        main()
        os.remove(LOCK)


