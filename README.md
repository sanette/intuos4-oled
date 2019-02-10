# intuos4-oled
send cool images and text to the Wacom Intuos 4 OLEDs on Linux.

The Intuos4 is an old tablet, but it works well, and you can have fun
playing with the small OLED screens.  There is built-in support in the
Linux kernel, but the access to it is not so obvious (and several
pages on the web are outdated).  The purpose of this project is to
make it easy. It already works, but I will add more goodies if time
permits.

```
python ./intuos4oled.py --help
usage: intuos4oled.py [-h] [-f] [--clear] [-b BUTTON] [-i IMAGE] [--id ID]
                      [--font FONT] [--sync SYNC] [-t TEXT] [-s SPAN]
                      command

positional arguments:
  command               update, set, clear, init

optional arguments:
  -h, --help            show this help message and exit
  -f, --flip            Flip images upside-down (for left-handed)
  --clear               Clear button
  -b BUTTON, --button BUTTON
                        button number, between 0 and 7
  -i IMAGE, --image IMAGE
                        image file
  --id ID               Wacom Tablet product ID
  --font FONT           Font to use for texts
  --sync SYNC           Specify the file used to store and synchronize all
                        images
  -t TEXT, --text TEXT  text message
  -s SPAN, --span SPAN  if the image has to span over several buttons
```

## Examples

```
intuos4oled.py set -i tux.png -b 0
```

This will display the "tux.png" icon on the button #0.

```
intuos4oled.py set -b 7 -i woman64.png -f -s 4
```

This will display the image "woman64.png" on the tablet, spanning over
4 buttons, flipped in order to fit the left-handed mode. The number
'7' here is the top button in the left-handed orientation.

```
intuos4oled.py set -t "Don't forget\nthe bread" -b 2 --font "Ubuntu-C.ttf"
```

This will display some text on button #2. Notice how you can insert a
line break with '\n', and change the font.

## Restore images

After the Tablet has been disconnected, you can easily restore the
previous state:

```
intuos4oled.py update
```

## Installation

### Python

You need a standard Python install. It should work with Python2 (for
instance with Ubuntu 16.4) or Python3.

If you just want to test, make the script executable:
```
chmod 755 intuos4oled.py
```

There is nothing more to do. But, depending on your system, you may
have to run the script with `sudo`.

In this case, it's easier to simply do once:
```
sudo ./intuos4oled.py init
```

And then for all subsequent calls, you don't need sudo anymore. You
may try the examples above!

### Permanent installation

1. Make the script executable and move it to a location in you
   `$PATH`. Here we use /usr/local/bin. This should work for everyone.

```
chmod 755 intuos4oled.py
sudo cp intuos4oled.py /usr/local/bin/
```

2. By using `udev` rules the initialization will be done automagically
   every time you plug in the tablet:

```
sudo cp 99-wacom.rules /etc/udev/rules.d/99-wacom.rules
```
(This might require a restart)

3. Using your session-manager startup scripts, update the tablet with
   `intuos4oled update` whenever you open a session.

