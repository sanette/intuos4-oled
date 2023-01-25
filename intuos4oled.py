#!/usr/bin/python3
# -*- coding: utf-8 -*

#
# send images to the Wacom Intuos4 OLEDs.
# San Vu Ngoc, 2019-2023
#
#

import sys
import stat
import re
import subprocess
import os.path
import argparse
import tempfile
import time

import PIL.Image as Image
import struct

CONF_PATH = os.path.join(os.path.expanduser("~"), ".intuos")
DEVICES_PATH = "/sys/bus/hid/devices/"
WACOM_LED = "wacom_led"
STATUS_LED0 = "status_led0_select"
BUTTON = "button%u_rawimg"
LUMINANCE = "buttons_luminance"
DEFAULT_FONT = "Ubuntu-R.ttf"
WACOM_ID = 0x056a
# https://github.com/linuxwacom/input-wacom/wiki/Device-IDs
USB_IDS = [
    ((WACOM_ID, 0x00b9), "PTK-640", "Intuos4", "(6x9)"),
    ((WACOM_ID, 0x00ba), "PTK-840", "Intuos4", "(8x13)"),
    ((WACOM_ID, 0x00bb), "PTK-1240", "Intuos4", "(12x19)"),
    ((WACOM_ID, 0x00bc), "PTK-540WL", "Intuos4", "Wireless")]
TARGET_WIDTH = 64
TARGET_HEIGHT = 32

def check_range (button):
    if button < 0 or button > 7:
        print ("ERROR: button %i out of range."%button)
        return (False)
    else:
        return (True)
    
class Screen:
    """Data for the 8 button images for all 4 led positions"""

    def __init__(self, ids = None, datafile = None, sync = True):
        if ids is None:
            ids = get_usb_ids ()
        self.ids = ids
        w = wacom_from_id(ids)[0]
        self.model = w[2] + " " + w[3]
        self.path = get_path(ids)
        self.update_led()
        if sync:
            if datafile is None:
                datafile = CONF_PATH
        else:
            datafile = None
        self.datafile = datafile
        self.raw = [[None for x in range(8)] for led in range(4)]
        self.load()
        
    def update_led (self):
        """Get the status led: 0,1,2,3"""
        led_path = os.path.join(self.path, STATUS_LED0)
        with open(led_path, 'r') as f:
            line = f.readline()
        self.led = int(line)
        print ("Active led = %u"%self.led)

    def update (self):
        """Update path and led status."""
        self.path = get_path(ids)
        self.update_led()

    def refresh (self):
        """Refresh all saved buttons"""
        # Use this if the tablet has been deconnected.
        for button in range(8):
            raw = self.raw[self.led][button]
            if raw is not None:
                send_raw(raw, button, self)
        
    def get_raw (self, button):
        if check_range(button):
            return (self.raw[self.led][button])
        else:
            return (None)

    def set_raw(self, button, raw_data):
        if check_range(button):
            self.raw[self.led][button] = raw_data

    def save(self, filename = None):
        if self.datafile is None:
            return (None)
        if filename is None:
            filename = self.datafile
        print ("Saving to %s"%filename)
        with open(filename, 'wb') as outfile:
            outfile.write(("(%u,%u)\n" % (self.ids[0], self.ids[1])).encode())
            for led in range(4):
                for button in range(8):
                    if self.raw[led][button] is None:
                        outfile.write("None\n".encode())
                    else:
                        outfile.write("Raw:\n".encode())
                        outfile.write(self.raw[led][button])

    def load(self, filename = None):
        """Load config file and update the tablet"""
        if self.datafile is None:
            return (None)
        size = int(TARGET_HEIGHT*TARGET_WIDTH/2)
        if filename is None:
            filename = self.datafile
        if os.path.exists(filename):
            print ("Loading datafile %s"%filename)
            with open(filename, 'rb') as file:
                l = file.readline().strip()
                for led in range(4):
                    current_led = (led == self.led)
                    for button in range(8):
                        l = file.readline().strip()
                        if l == b"Raw:":
                            raw = file.read(size)
                            if current_led:
                                send_raw(raw, button, self)
                            else:
                                self.raw[led][button] = raw
                        elif l == b"None":
                            #print ("No saved image for led=%i, button=%i."%(led, button))
                            pass
                        else:
                            print ("ERROR: wrong format in file %s for led=%i, button=%i."%(filename, led, button))

def sudo_init (ids):
    """Set leds writable by all
    
    This has to be executed with root priviledges after each
    connection of the Tablet if there is no udev rules that take care of
    this.
    """
    path = get_path(ids)
    for button in range(8):
        btn_path = os.path.join(path, BUTTON%button)
        for i in range(10):
            if not os.path.exists(btn_path):
                print ("Waiting for button %i"%button)
                time.sleep(1)
            else:
                break
        os.chmod(btn_path, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    RWALL = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    led_path = os.path.join(path, STATUS_LED0)
    os.chmod(led_path, RWALL)
    luminance = os.path.join(path, LUMINANCE)
    os.chmod(luminance, RWALL)

def set_luminance (path, luminance):
    lumi_path = os.path.join(path, LUMINANCE)
    with open(lumi_path, 'wb') as outfile:
        outfile.write(str(luminance).encode())

def img_to_raw (im, flip, rv, keep_ratio = False):
    """Convert an image to a raw 1024 bytearray for the Intuos4.

    Suitable for displaying on one button screen.  'flip' should be True
    if the buttons are on the right-hand side (left-handed configuration).
    """

# cf https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-driver-wacom
# :
# When writing a 1024 byte raw image in Wacom Intuos 4
# interleaving format to the file, the image shows up on Button N
# of the device. The image is a 64x32 pixel 4-bit gray image. The
# 1024 byte binary is split up into 16x 64 byte chunks. Each 64
# byte chunk encodes the image data for two consecutive lines on
# the display. The low nibble of each byte contains the first
# line, and the high nibble contains the second line.
# When the Wacom Intuos 4 is connected over Bluetooth, the
# image has to contain 256 bytes (64x32 px 1 bit colour).
# The format is also scrambled, like in the USB mode, and it can
# be summarized by converting 76543210 into GECA6420.
#                             HGFEDCBA      HFDB7531

    # Background color
    color, name = ((255,255,255), "white") if rv else ((0,0,0), "black")
    
    # If there is an alpha channel, we need to blend it.
    if 'A' in im.getbands(): 
        print ("Blending alpha channel to %s."%name)
        im = im.convert(mode='RGBA')
        im2 = Image.new('RGBA', im.size, color)
        im = Image.alpha_composite(im2, im)

    # Convert to 8bit grayscale
    im = im.convert(mode='L')

    # Resize image
    (w, h) = im.size
    if keep_ratio:
        if w * TARGET_HEIGHT < h * TARGET_WIDTH: # too tall
            tw, th = w*TARGET_HEIGHT/h, TARGET_HEIGHT
        else: # too wide
            tw, th = TARGET_WIDTH, h*TARGET_WIDTH/w
    else:
        tw, th = TARGET_WIDTH, TARGET_HEIGHT
    if w != tw or h != th:
        print ("Warning: we need to resize the %ix%i image to %ix%i."
                   %(w, h, tw, th))
        im = im.resize((tw, th), Image.LANCZOS)

    # Center image
    if tw != TARGET_WIDTH or th != TARGET_HEIGHT:
        print ("Centering image.")
        im2 = Image.new('L', (TARGET_WIDTH, TARGET_HEIGHT), color[0])
        if tw < TARGET_WIDTH:
            x, y = (TARGET_WIDTH - tw)/2, 0
        else: # we must have th < TARGET_HEIGHT:
            x, y = 0, (TARGET_HEIGHT - th)/2
        im2.paste(im,(x,y))
        print(x,y)
        im.save('/tmp/aaa.png')
        
        im = im2
        
    # Convert grayscale image into interlaced 4bits raw bytes.
    (w, h) = (TARGET_WIDTH, TARGET_HEIGHT)
    raw = bytearray(int(w * h / 2))
    pos = 0

    for j in range(int(h / 2)):
        (y, n1, n2) = (h - 2*j, -1, -2) if flip else (2*j, 0, 1)
        
        for i in range(w):
            x = i if flip else w - i - 1
            low = im.getpixel((x, y + n1)) >> 4  # divide by 16 to convert to 4bit grayscale 
            high = im.getpixel((x, y + n2)) & 0xF0 # (= keep only higher 4 bits)
            byte = high | low
            raw[pos] = 255 - byte if rv else byte
            pos += 1

    return (raw)

# not used
def img_to_multi_raw(image, span, flip):
    image = Image.open(filename)
    width, height = image.size
    raws = [img_to_raw(image.crop((0,i*height/btn_span, width, (i+1)*height/btn_span)), flip)
                for i in range(span)]
    return (raws)

def ids_from_string (s):
    """Extract (vendor,product) for a line printed by lsusb"""
    s = re.search(r'ID ([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})\b', s)
    if s is not None:
        vendor = s.group(1)
        product = s.group(2)
        return (int(vendor,16), int(product, 16))
    else:
        print ("ERROR: badly formatted line from lsusb:\n%s"%s)
        return (None)

def wacom_from_id (id):
    return ([wac for wac in USB_IDS if id == wac[0]])
    
def get_usb_ids (): # somewhat slow; do it only once if possible.
    """Extract Intuos4 (vendor,product) from lsusb.

    For me it's (0x056A, 0x00B9) = Intuos4 M
    """
    ids = subprocess.check_output(["lsusb"])
    ids = ids.splitlines()
    wacoms = []
    for x in ids:
       w = wacom_from_id (ids_from_string (x.decode('utf-8')))
       if w != []:
           wacoms += w
    if wacoms == []:
        print ("ERROR: No compatible Wacom tablet is connected or recognized.")
        return (None)
    elif len(wacoms) > 1:
        print ("WARNING: several Wacom tablet are connected. We choose the first one")
    w = wacoms[0]
    print ("Using Wacom %s %s (%s)"%(w[2], w[3], w[1]))
    return (w[0])

def split_path (path):
    """Extract (vendor,product) from path.

    example: '0003:056A:00B9.0004' ==> 0x056A, 0x00B9
    """
    l = path.replace(':', '.').split('.')
    return (int(l[1], 16), int(l[2], 16))

def get_path (ids):  # this is a bit slow (60ms?)
    """Find corresponding path in DEVICES_PATH.
    """
    vendor, product = ids
    l = os.listdir(DEVICES_PATH)
    file = [x for x in l if split_path(x) == (vendor, product)]
    if len(file) == 0:
        raise Exception ("ERROR: no corresponding directory found in %s for device (%04x,%04x)"%(DEVICES_PATH, vendor, product))
    else:
        if len(file) > 1:
            print ("Warning: found more than one corresponding directory in %s"%DEVICES_PATH)
        return (os.path.join(DEVICES_PATH, file[0], WACOM_LED))
    
def send_raw (raw, button, screen):

    if check_range(button):
        btn_path = os.path.join(screen.path, BUTTON%button)
        #os.chmod(btn_path, stat.S_IWOTH)
        with open(btn_path, "wb") as outfile:
            outfile.write(raw)
        screen.set_raw(button, raw)

def update_raw (raw, button, screen):
    """Send the image to the button only if it has changed."""
    if raw != screen.get_raw(button):
        send_raw(raw, button, screen)
        
def send_image (filename, button, screen,
                    flip = False, rv = False, keep_ratio = False):

    im = Image.open(filename)
    raw = img_to_raw(im, flip, rv, keep_ratio)
    update_raw (raw, button, screen)

def send_multi_image (filename, top_button, btn_span, screen,
                          flip = False, rv = False):
    """Send an image that will span vertically over several buttons.

    The image will start at 'top_button'. 'btn_span' is total the number
    of buttons over which the image has to be displayed.
    """
    button = (7 - top_button if flip else top_button)
    if button + btn_span > 8:
        print ("ERROR: there are no %u button(s) available below #%u"%(btn_span, top_button)) 
        return (None)
    image = Image.open(filename)
    width = image.size[0]
    height = image.size[1]
    for i in range(btn_span):
        im = image.crop((0,i*height/btn_span, width, (i+1)*height/btn_span))
        raw = img_to_raw(im, flip, rv)
        button = top_button - i if flip else top_button + i
        update_raw (raw, button, screen)
        # TODO: better to resize first and split next.

def clear_buttons (button, span, screen, flip):
    last_button = (button if span is None else
                       (button - span + 1 if flip else button + span - 1))
    r = range(min(button, last_button), max(button, last_button)+1)
    raw = bytearray(int(TARGET_HEIGHT * TARGET_WIDTH / 2))
    for b in r:
        print ("Clearing button %u"%b)
        update_raw (raw, b, screen)

def get_font_path (font):
    l = subprocess.check_output(["fc-list", font], text=True)
    l = l.splitlines()
    f = [x for x in l if font in x]
    if f == []:
        print ("ERROR: font %s not found"%font)
        return (None)
    return (f[0].split(':')[0])
    
def text_to_img (text, output, font = DEFAULT_FONT, size = None, span = None):

    span = 1 if span is None else span
    if size is None:
        resize = []
    else:
        resize = ["-pointsize", "%u"%size]
    font_path = get_font_path(font)
    args1 = ["convert",
                 "-size",  "%ux%u"%(TARGET_WIDTH, span * TARGET_HEIGHT),
                 "-gravity", "Center",
                 "-font", font_path,
                 "-background", "black",
                 "-fill", "white"]
    args2 = ["caption:%s"%text, output]
    ret = subprocess.call(args1 + resize + args2)
    if ret == 0:
        #print ("Image %s successfully created"%output)
        pass
    else:
        print ("ERROR: in creating %s"%output)
    
def send_text (text, button, screen, flip = False, span = None,
                   font = None, size = None):
    """Send text to button.

    One can use newline break with '\n'. If 'span' is not None, the text
    will be vertically spread over 'span' buttons.
    """
    if font is None:
        font = DEFAULT_FONT
    _, filename = tempfile.mkstemp(prefix="wacom-", suffix=".png")
    text_to_img(text, filename, font, size, span)
    if span is None:
        send_image(filename, button, screen, flip)
    else:
        send_multi_image (filename, button, span, screen, flip)
    os.remove(filename)
    
        
#---------------------#
# Command-line Script #
#---------------------#

if __name__ == "__main__":
    commands = ['update', 'set', 'clear', 'init']
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help=", ".join(commands))
    parser.add_argument("-t", "--text", help="text message")
    parser.add_argument("-i", "--image", help="image file")
    parser.add_argument("-b", "--button", help="button number, between 0 and 7", type=int)
    parser.add_argument("-s", "--span", help="if the image has to span over several buttons", type=int)
    parser.add_argument("-f", "--flip", action="store_true",
                        help="Flip images upside-down (for left-handed)")
    parser.add_argument("--font", help="Font to use for texts")
    parser.add_argument("--kr", action="store_true", help="Keep image ratio")
    parser.add_argument("--rv", action="store_true", help="Reverse video")
    parser.add_argument("--id", help="Wacom Tablet product ID")
    parser.add_argument("--lum", help="Oled luminance, between 0 and 15")
    parser.add_argument("--sync", help="Specify the file used to store and synchronize all images")
    parser.add_argument("--nosync", action="store_true", help="Don't synchronize images with datafile")
    args = parser.parse_args()

    if args.command not in commands:
        print ("Command argument not recognized. Should be one of %s."%(", ".join(commands)))
        exit (1)

    if args.id is None:
        ids = get_usb_ids ()
        if ids is None:
            print ("ERROR: Cannot get the Intuos4 ids.")
            exit (1)
    else:
        ids = (WACOM_ID, int(args.id, 0))

    # INIT
    if args.command == 'init':
        sudo_init (ids)
        print ("Root initialization done.")
        print (time.strftime('%X %x %Z'))
        exit (0)

    screen = Screen(ids, datafile = args.sync, sync = not args.nosync)

    
    # UPDATE
    if args.command == 'update':
        exit (0)

    # LOAD or CLEAR
    if args.button is None:
        args.button = 7 if args.flip else 0
        args.span = 8
        
    if not check_range(args.button):
        exit (1)

    # CLEAR
    if args.command == 'clear':
        clear_buttons(args.button, args.span, screen, args.flip)

    # SET
    else:
        if args.lum is not None:
            set_luminance(screen.path, args.lum)
        if args.image is None:
            if args.text is None:
                if args.lum is None:
                    print ("ERROR: Nothing to be set.")
                    exit (1)

            else: # text is not None
                print ("Sending \"%s\" to button %u"%(args.text, args.button))
                send_text(args.text, args.button, screen, flip = args.flip,
                        span = args.span, font = args.font, size = None)
        else: # image is not None
            if args.text is not None:
                print ("Using image %s and ignoring text %s."%(args.image, args.text))
            if args.span is None:
                send_image(args.image, args.button, screen,
                           flip = args.flip, rv = args.rv, keep_ratio = args.kr)
            else:
                send_multi_image(args.image, args.button, args.span, screen,
                                 args.flip, rv = args.rv)

    if args.text is not None or args.image is not None:
        screen.save()
    print ("Done")
    
