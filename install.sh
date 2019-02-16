#!/bin/sh -xe
# to be run as
# sudo ./install.sh $USER
# This is part of intuos4oled
# It install the python script to /usr/local/bin,
# the init script to /usr/local/lib/intuos4oled
# the udev rules to /etc/udev/rules.d
# and tries to autostart the daemon for the user's session
# and starts it.

PREFIX='/usr/local'
user=$1

if [ "A${user}B" = "AB" ]
then
    echo "Error: no user provided. Type 'sudo ./install \$USER'"
    exit 1
fi

su $user -c "echo 'try user'"

chmod 755 intuos4oled.py
chmod 755 init.sh
cp intuos4oled.py $PREFIX/bin/
if ! [ `which at` ]
then
    echo "You should install the 'at' program first."
    exit 1
fi
mkdir -p $PREFIX/lib/intuos4oled
cp init.sh $PREFIX/lib/intuos4oled/
cp intuos4daemon.py $PREFIX/lib/intuos4oled/
cp 99-wacom.rules /etc/udev/rules.d/99-wacom.rules
udevadm control --reload-rules && udevadm trigger
su $user -c 'if ! [ -e $HOME/.intuos ]; then cp sample.sync $HOME/.intuos; fi'
su $user -c 'if [ -d $HOME/.config/autostart ]; then cp intuos4daemon.desktop $HOME/.config/autostart/; fi'

su $user -c '/sbin/start-stop-daemon -S --background --exec /usr/local/lib/intuos4oled/intuos4daemon.py'

echo "Installation completed. You may now plug the Intuos in."
