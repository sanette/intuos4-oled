#!/usr/bin/python
# -*- coding: utf-8 -*
#
#

import daemon
import sys
import os
import time

sys.path.append('/usr/local/bin')

import intuos4oled as i4o

TEMP = "/tmp/intuos_init"

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

if os.system("pgrep -f intuos4daemon") == 0:       
    print ("Intuos4daemon is already running.")
    exit (1)
else:
    with daemon.DaemonContext():
        main()


