# intuos4-oled
send cool images and text to the Wacom Intuos 4 OLEDs on Linux.

The Intuos4 is an old tablet, but it works well, and you can have fun playing with the small OLED screens.
There is built-in support in the Linux kernel, but the access to it is not so obvious (and several pages on the web are outdated).
The purpose of this project is to make it easy. It already works, but I will add more goodies if time permits.

```
python ./intuos4-oled.py --help
usage: intuos4-oled.py [-h] [-f] [--clear] [-i IMAGE] [-t TEXT] [-s SPAN]
                       button

positional arguments:
  button                button number

optional arguments:
  -h, --help            show this help message and exit
  -f, --flip            Flip images upside-down (for left-handed)
  --clear               Clear button
  -i IMAGE, --image IMAGE
                        image file
  -t TEXT, --text TEXT  text message
  -s SPAN, --span SPAN  if the image has to span over several buttons       
  ```
  
  Warning: it has to be run with sudo.
  
  ## Examples
  
  ```
  sudo python ./intuos4-oled.py 7 -i woman64.png -f -s 4
  ````
  This will display the image "woman64.png" on the tablet, spanning over 4 buttons, flipped in order to fit the left-handed mode. The number '7' here is the top button in the left-handed orientation.
