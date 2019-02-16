#!/bin/sh

# the intuos button files will be created AFTER udev rules are
# done. So we MUST detach or fork this call to allow it to wait after
# buttons are up and running...

# this doesn't work:
#/sbin/start-stop-daemon -S --exec /usr/local/bin/intuos4oled.py -- init --id $1 > /tmp/intuos_init 2>&1

# this doesn't work:
#/sbin/start-stop-daemon -S --background --exec /usr/local/bin/intuos4oled.py -- init --id $1

# this works for me:
echo "/usr/local/bin/intuos4oled.py init --id $1 > /tmp/intuos_init 2>&1" | at now
